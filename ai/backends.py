from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from .knowledge import SecurityKnowledgeBase
from .models import AIResult, IncidentContext
from .prompts import SecurityPromptBundle, SecurityPromptBuilder


@dataclass(frozen=True, slots=True)
class ModelDraft:
    classification: str
    confidence: float
    mitre_techniques: tuple[str, ...]
    recommended_action: str
    escalate_to_human: bool
    reasoning: str
    reasoning_layers: tuple[str, ...] = ()


class SecurityModelBackend(Protocol):
    name: str

    def generate(self, prompt: SecurityPromptBundle, incident: IncidentContext) -> ModelDraft:
        ...


class HeuristicSecurityBackend:
    name = "heuristic-dynamic"

    def __init__(self, knowledge_base: SecurityKnowledgeBase | None = None) -> None:
        self.knowledge_base = knowledge_base or SecurityKnowledgeBase()

    def generate(self, prompt: SecurityPromptBundle, incident: IncidentContext) -> ModelDraft:
        # Rely entirely on the knowledge base vector retrieval instead of hardcoded strings
        retrieved_titles = [snippet.title.lower() for snippet in prompt.retrieved_context]
        retrieved_content = " ".join([snippet.content.lower() for snippet in prompt.retrieved_context])
        
        is_malicious_context = "malicious" in retrieved_content or "threat" in retrieved_content
        is_critical_technique = any("t1" in title for title in retrieved_titles)

        if is_malicious_context or is_critical_technique:
            return ModelDraft(
                classification="Identified Threat Activity (KB Match)",
                confidence=0.85,
                mitre_techniques=("T1059", "T1071") if is_critical_technique else (),
                recommended_action="kill_process",
                escalate_to_human=False,
                reasoning="Matched threat pattern dynamically from the knowledge base.",
                reasoning_layers=("vector_retrieval", "policy_check"),
            )

        return ModelDraft(
            classification="Unknown or Benign Activity",
            confidence=0.60,
            mitre_techniques=(),
            recommended_action="observe",
            escalate_to_human=True,
            reasoning="No definitive threat pattern found in context; human review advised.",
            reasoning_layers=("vector_retrieval", "analyst_review"),
        )


class OllamaChatBackend:
    name = "ollama-chat"

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 20.0,
        fallback: SecurityModelBackend | None = None,
    ) -> None:
        self.model = model or os.getenv("SECURITY_AI_OLLAMA_MODEL", "mistral")
        self.base_url = (base_url or os.getenv("SECURITY_AI_OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.fallback = fallback or HeuristicSecurityBackend()

    def generate(self, prompt: SecurityPromptBundle, incident: IncidentContext) -> ModelDraft:
        payload = {
            "model": self.model,
            "messages": list(prompt.messages),
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
            },
        }
        request = Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # nosec: stdlib HTTP client
                body = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, ValueError, json.JSONDecodeError):
            return self.fallback.generate(prompt, incident)

        content = self._extract_message_content(body)
        if not content:
            return self.fallback.generate(prompt, incident)

        parsed = self._parse_draft(content)
        if parsed is None:
            return self.fallback.generate(prompt, incident)
        return parsed

    def _parse_draft(self, content: str) -> ModelDraft | None:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return None

        try:
            return ModelDraft(
                classification=str(data.get("classification", "Unknown")),
                confidence=float(data.get("confidence", 0.5)),
                mitre_techniques=tuple(str(item) for item in data.get("mitre_techniques", ())),
                recommended_action=str(data.get("recommended_action", "observe")),
                escalate_to_human=bool(data.get("escalate_to_human", True)),
                reasoning=str(data.get("reasoning", "")),
                reasoning_layers=tuple(str(item) for item in data.get("reasoning_layers", ())),
            )
        except (KeyError, TypeError, ValueError):
            return None

    @staticmethod
    def _extract_message_content(body: dict[str, object]) -> str:
        message = body.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content.strip()
        return ""

