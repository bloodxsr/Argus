from __future__ import annotations

from dataclasses import dataclass

from .knowledge import KnowledgeSnippet
from .models import IncidentContext


@dataclass(frozen=True, slots=True)
class SecurityPromptBundle:
    system_prompt: str
    user_prompt: str
    messages: tuple[dict[str, str], ...]
    retrieved_context: tuple[KnowledgeSnippet, ...]
    profile_name: str = "ollama-style-security-profile"


class SecurityPromptBuilder:
    def __init__(self, profile_name: str = "ollama-style-security-profile") -> None:
        self.profile_name = profile_name

    def build(self, incident: IncidentContext, retrieved_context: tuple[KnowledgeSnippet, ...]) -> SecurityPromptBundle:
        system_prompt = (
            "You are Argus Security AI, a cyber defense model for incident triage and response. "
            "Use layered internal reasoning: 1) classify the incident, 2) map to MITRE ATT&CK, "
            "3) compare against retrieved threat knowledge, 4) apply policy-safe response guidance. "
            "Do not reveal hidden chain-of-thought. Return JSON only with the keys classification, "
            "confidence, mitre_techniques, recommended_action, escalate_to_human, reasoning."
        )
        context_block = "\n".join(snippet.to_prompt_block() for snippet in retrieved_context) or "- none"
        user_prompt = (
            f"Incident ID: {incident.incident_id}\n"
            f"Company: {incident.company}\n"
            f"Host: {incident.host}\n"
            f"Asset: {incident.asset_id}\n"
            f"Hour: {incident.hour_of_day}\n"
            f"Risk score: {incident.risk_score}\n"
            f"Labels: {', '.join(incident.labels) or 'none'}\n"
            f"Summary: {incident.summary}\n\n"
            f"Retrieved security context:\n{context_block}\n\n"
            "Return only valid JSON matching the schema."
        )
        messages = (
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        )
        return SecurityPromptBundle(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            messages=messages,
            retrieved_context=retrieved_context,
            profile_name=self.profile_name,
        )
