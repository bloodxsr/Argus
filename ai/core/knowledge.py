from __future__ import annotations

from dataclasses import dataclass

from .models import IncidentContext


@dataclass(frozen=True, slots=True)
class KnowledgeSnippet:
    title: str
    summary: str
    markers: tuple[str, ...]
    mitre_techniques: tuple[str, ...]
    recommended_action: str
    confidence_hint: float = 0.0

    def to_prompt_block(self) -> str:
        techniques = ", ".join(self.mitre_techniques) or "none"
        markers = ", ".join(self.markers) or "none"
        return (
            f"- {self.title}: {self.summary}\n"
            f"  markers={markers}\n"
            f"  mitre={techniques}\n"
            f"  recommended_action={self.recommended_action}"
        )


class SecurityKnowledgeBase:
    def __init__(self, snippets: tuple[KnowledgeSnippet, ...] | None = None) -> None:
        self._snippets = snippets or (
            KnowledgeSnippet(
                title="Prompt injection defence",
                summary="Instruction override language is a hostile input pattern and should trigger human review.",
                markers=("ignore previous instructions", "override rules", "system prompt"),
                mitre_techniques=(),
                recommended_action="observe",
                confidence_hint=0.15,
            ),
            KnowledgeSnippet(
                title="Web shell and remote execution",
                summary="Shell execution from temp paths with suspicious network activity often maps to code execution and beaconing.",
                markers=("/tmp/", "spawned bash", "powershell", "mimikatz", "beaconing"),
                mitre_techniques=("T1059.004", "T1071.001"),
                recommended_action="kill_process",
                confidence_hint=0.94,
            ),
            KnowledgeSnippet(
                title="Benign maintenance window",
                summary="Scheduled backups and routine maintenance usually merit observation rather than automatic response.",
                markers=("scheduled backup", "maintenance window", "log rotation", "routine deployment"),
                mitre_techniques=(),
                recommended_action="observe",
                confidence_hint=0.88,
            ),
            KnowledgeSnippet(
                title="Suspicious reconnaissance",
                summary="Mixed signals that resemble discovery or scanning should be escalated for analyst review.",
                markers=("nmap", "port scan", "external ip", "discovery", "suspicious outbound"),
                mitre_techniques=("T1046",),
                recommended_action="recommend",
                confidence_hint=0.61,
            ),
        )

    def retrieve(self, incident: IncidentContext, limit: int = 3) -> tuple[KnowledgeSnippet, ...]:
        text = " ".join((incident.summary, incident.host, incident.asset_id, *incident.labels)).lower()
        scored = sorted(
            ((self._score_snippet(snippet, text), snippet) for snippet in self._snippets),
            key=lambda item: (-item[0], item[1].title),
        )
        return tuple(snippet for score, snippet in scored[:limit] if score > 0) or self._snippets[:limit]

    def retrieve_from_text(self, text: str, limit: int = 3) -> tuple[KnowledgeSnippet, ...]:
        text = text.lower()
        scored = sorted(
            ((self._score_snippet(snippet, text), snippet) for snippet in self._snippets),
            key=lambda item: (-item[0], item[1].title),
        )
        return tuple(snippet for score, snippet in scored[:limit] if score > 0) or self._snippets[:limit]

    @staticmethod
    def _score_snippet(snippet: KnowledgeSnippet, text: str) -> int:
        score = 0
        for marker in snippet.markers:
            if marker in text:
                score += 2
        if snippet.recommended_action == "kill_process" and any(token in text for token in ("c2", "rce", "malware", "ransomware")):
            score += 1
        if snippet.recommended_action == "observe" and any(token in text for token in ("maintenance", "backup", "health check")):
            score += 1
        return score
