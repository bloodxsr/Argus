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
    name = "heuristic"

    def __init__(self, knowledge_base: SecurityKnowledgeBase | None = None) -> None:
        self.knowledge_base = knowledge_base or SecurityKnowledgeBase()

    def generate(self, prompt: SecurityPromptBundle, incident: IncidentContext) -> ModelDraft:
        text = f"{incident.summary} {' '.join(incident.labels)}".lower()
        retrieved_titles = tuple(snippet.title for snippet in prompt.retrieved_context)

        if self._looks_like_prompt_injection(text):
            return ModelDraft(
                classification="Prompt Injection Attempt",
                confidence=0.15,
                mitre_techniques=(),
                recommended_action="observe",
                escalate_to_human=True,
                reasoning="Input contains instruction override language and should be reviewed manually.",
                reasoning_layers=("signal_scan", "knowledge_retrieval", "safety_gate"),
            )

        if self._is_high_confidence_malicious(text):
            return ModelDraft(
                classification="Remote Code Execution + C2 Beaconing",
                confidence=0.94,
                mitre_techniques=("T1059.004", "T1071.001"),
                recommended_action="kill_process",
                escalate_to_human=False,
                reasoning="Execution from an unusual path with outbound beaconing is a high-confidence malicious pattern.",
                reasoning_layers=("signal_scan", "knowledge_retrieval", "attack_mapping", "policy_check"),
            )

        if self._looks_benign(text):
            return ModelDraft(
                classification="Benign Operational Activity",
                confidence=0.88,
                mitre_techniques=(),
                recommended_action="observe",
                escalate_to_human=False,
                reasoning="The event matches routine maintenance or expected automation.",
                reasoning_layers=("signal_scan", "knowledge_retrieval", "benign_validation"),
            )

        return ModelDraft(
            classification="Suspicious but Unconfirmed Activity",
            confidence=0.61,
            mitre_techniques=("T1046",),
            recommended_action="recommend",
            escalate_to_human=True,
            reasoning="Signals are mixed and the environment should review before taking action.",
            reasoning_layers=("signal_scan", "knowledge_retrieval", "analyst_review"),
        )

    @staticmethod
    def _looks_like_prompt_injection(text: str) -> bool:
        indicators = (
            "ignore previous instructions",
            "disregard policy",
            "override rules",
            "system prompt",
            "do anything now",
        )
        return any(marker in text for marker in indicators)

    @staticmethod
    def _is_high_confidence_malicious(text: str) -> bool:
        indicators = (
            "cobalt strike",
            "c2 beacon",
            "beaconing",
            "ransomware",
            "/tmp/",
            "powershell",
            "mimikatz",
            "lsass",
            "known malicious",
            "spawned bash",
            "external ip",
        )
        return any(marker in text for marker in indicators)

    @staticmethod
    def _looks_benign(text: str) -> bool:
        indicators = (
            "scheduled backup",
            "health check",
            "routine deployment",
            "maintenance window",
            "log rotation",
        )
        return any(marker in text for marker in indicators)


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
                classification=str(data["classification"]),
                confidence=float(data["confidence"]),
                mitre_techniques=tuple(str(item) for item in data.get("mitre_techniques", ())),
                recommended_action=str(data["recommended_action"]),
                escalate_to_human=bool(data["escalate_to_human"]),
                reasoning=str(data["reasoning"]),
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
