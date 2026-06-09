from __future__ import annotations

from datetime import datetime, timezone
from os import getenv

from .backends import FineTunedLlamaBackend, HeuristicSecurityBackend, ModelDraft, OllamaChatBackend, SecurityModelBackend
from .knowledge import SecurityKnowledgeBase
from .retriever import QdrantRetriever
from .models import AIResult, CompanyConstraints, Decision, IncidentContext
from .prompts import SecurityPromptBuilder


class HeuristicSecurityLLM:
    """Layered security reasoning service with an Ollama-compatible backend path.
    
    Backend priority:
    1. FineTunedLlamaBackend — if trained LoRA adapters exist on disk
    2. OllamaChatBackend — if SECURITY_AI_OLLAMA_BASE_URL env var is set
    3. HeuristicSecurityBackend — always available, zero dependencies
    """

    def __init__(
        self,
        backend: SecurityModelBackend | None = None,
        knowledge_base: SecurityKnowledgeBase | None = None,
        prompt_builder: SecurityPromptBuilder | None = None,
        retriever: QdrantRetriever | None = None,
    ) -> None:
        self.knowledge_base = knowledge_base or SecurityKnowledgeBase()
        self.prompt_builder = prompt_builder or SecurityPromptBuilder()
        self.backend = backend or self._default_backend()
        # retriever may be unavailable; QdrantRetriever will gracefully fallback
        self.retriever = retriever or QdrantRetriever()

    def _default_backend(self) -> SecurityModelBackend:
        heuristic = HeuristicSecurityBackend(self.knowledge_base)

        # Priority 1: Fine-tuned Llama 3.1 8B (if adapters exist on disk)
        import os
        adapter_path = getenv("AGRUS_MODEL_PATH", "models/agrus-v1-final")
        if os.path.isdir(adapter_path) and os.path.exists(os.path.join(adapter_path, "adapter_config.json")):
            return FineTunedLlamaBackend(
                adapter_path=adapter_path,
                fallback=heuristic,
            )

        # Priority 2: Ollama (if configured via env var)
        if getenv("SECURITY_AI_OLLAMA_BASE_URL"):
            return OllamaChatBackend(
                model=getenv("SECURITY_AI_OLLAMA_MODEL", "llama3.1"),
                base_url=getenv("SECURITY_AI_OLLAMA_BASE_URL"),
                fallback=heuristic,
            )

        # Priority 3: Analytical heuristic engine (always available)
        return heuristic

    def analyze(self, incident: IncidentContext) -> AIResult:
        # Try vector retrieval first; retriever handles fallbacks to in-memory KB
        retrieved_context = self.retriever.search(incident.summary, limit=3) or self.knowledge_base.retrieve(incident)
        prompt = self.prompt_builder.build(incident, retrieved_context)
        draft = self.backend.generate(prompt, incident)
        return self._draft_to_ai_result(incident, draft, prompt)

    def _draft_to_ai_result(
        self,
        incident: IncidentContext,
        draft: ModelDraft,
        prompt,
    ) -> AIResult:
        reasoning = "; ".join(
            (
                draft.reasoning,
                f"retrieved_context={', '.join(snippet.title for snippet in prompt.retrieved_context) or 'none'}",
                f"layers={', '.join(draft.reasoning_layers) or 'none'}",
            )
        )
        return AIResult(
            incident_id=incident.incident_id,
            classification=draft.classification,
            confidence=draft.confidence,
            mitre_techniques=draft.mitre_techniques,
            recommended_action=draft.recommended_action,
            escalate_to_human=draft.escalate_to_human,
            reasoning=reasoning,
        )


class SecurityDecisionEngine:
    def __init__(self, llm: HeuristicSecurityLLM | None = None) -> None:
        self.llm = llm or HeuristicSecurityLLM()

    def evaluate(self, incident: IncidentContext, constraints: CompanyConstraints) -> tuple[AIResult, Decision]:
        ai_result = self.llm.analyze(incident)
        decision = self._apply_constraints(incident, ai_result, constraints)
        return ai_result, decision

    def _apply_constraints(
        self,
        incident: IncidentContext,
        ai_result: AIResult,
        constraints: CompanyConstraints,
    ) -> Decision:
        fallback_action = "observe"
        action = ai_result.recommended_action if constraints.allows_action(ai_result.recommended_action) else fallback_action

        auto_execute = False

        enough_risk = incident.risk_score >= constraints.minimum_risk_for_auto_response
        enough_confidence = ai_result.confidence >= constraints.auto_response_threshold
        allowed_hour = constraints.is_hour_allowed(incident.hour_of_day)
        asset_allowed = not constraints.asset_is_blocked(incident.asset_id)
        
        is_critical_env = incident.environment in constraints.critical_environments
        is_critical_asset = incident.asset_id in constraints.critical_assets
        
        ai_allows_auto = not ai_result.escalate_to_human

        blocked_by_policy = not constraints.allows_action(ai_result.recommended_action)
        blocked_by_context = not enough_risk or not enough_confidence or not allowed_hour or not asset_allowed
        blocked_by_criticality = is_critical_env or is_critical_asset
        
        requires_human_approval = ai_result.escalate_to_human or blocked_by_policy or (action != "observe" and (blocked_by_context or blocked_by_criticality))

        if action != "observe":
            # "daddy for the whole shit" strict rule:
            # AI is never allowed to unilaterally execute a mitigation.
            # Active defense requires human authorization.
            auto_execute = False
            requires_human_approval = True
        elif action == "observe" and not ai_result.escalate_to_human and not blocked_by_policy:
            auto_execute = True
            requires_human_approval = False

        reasoning_parts = [
            ai_result.reasoning,
            f"policy={constraints.escalation_channel}",
            f"risk={incident.risk_score:.1f}",
        ]
        if not enough_risk:
            reasoning_parts.append("blocked_by_risk_threshold")
        if not enough_confidence:
            reasoning_parts.append("blocked_by_confidence_threshold")
        if not allowed_hour:
            reasoning_parts.append("blocked_by_time_policy")
        if not asset_allowed:
            reasoning_parts.append("blocked_by_asset_policy")
        if blocked_by_criticality:
            reasoning_parts.append(f"blocked_by_criticality(env={is_critical_env}, asset={is_critical_asset})")
        if not constraints.allows_action(ai_result.recommended_action):
            reasoning_parts.append("blocked_by_action_policy")

        audit_trail = {
            "company": incident.company,
            "asset_id": incident.asset_id,
            "auto_response_threshold": constraints.auto_response_threshold,
            "minimum_risk_for_auto_response": constraints.minimum_risk_for_auto_response,
            "allowed_hours": constraints.approved_hours,
            "no_auto_response_assets": sorted(constraints.no_auto_response_assets),
            "evaluated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "retrieved_context": [s.title for s in getattr(self.llm, "knowledge_base", SecurityKnowledgeBase()).retrieve(incident)],
            "reasoning_layers": getattr(ai_result, "reasoning", "").split("layers=")[-1].split(", ") if "layers=" in ai_result.reasoning else [],
            "model_backend": getattr(self.llm.backend, "name", "unknown"),
        }

        return Decision(
            incident_id=incident.incident_id,
            action=action,
            confidence=ai_result.confidence,
            requires_human_approval=requires_human_approval,
            auto_execute=auto_execute,
            reasoning="; ".join(reasoning_parts),
            fallback_action=fallback_action,
            audit_trail=audit_trail,
        )
