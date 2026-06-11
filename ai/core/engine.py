from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from os import getenv

from .backends import FineTunedLlamaBackend, HeuristicSecurityBackend, ModelDraft, OllamaChatBackend, SecurityModelBackend
from .knowledge import SecurityKnowledgeBase
from .retriever import QdrantRetriever
from .models import AIResult, CompanyConstraints, Decision, IncidentContext
from .prompts import SecurityPromptBuilder
from ..features.baselines import BaselineEngine
from ..features.container import get_container_for_pid, quarantine_container, kill_container
from ..features.correlation import CorrelationEngine


class HeuristicSecurityLLM:
    """Layered security reasoning service with an Ollama-compatible backend path.
    
    Backend priority:
    1. FineTunedLlamaBackend — if trained LoRA adapters exist on disk
    2. OllamaChatBackend — if SECURITY_AI_OLLAMA_BASE_URL env var is set
    3. HeuristicSecurityBackend — always available, zero dependencies
    """

    _state_lock = asyncio.Lock()
    _sync_lock = __import__("threading").Lock()

    def __init__(
        self,
        backend: SecurityModelBackend | None = None,
        knowledge_base: SecurityKnowledgeBase | None = None,
        prompt_builder: SecurityPromptBuilder | None = None,
        retriever: QdrantRetriever | None = None,
        baseline_engine: BaselineEngine | None = None,
        correlation_engine: CorrelationEngine | None = None,
    ) -> None:
        self.knowledge_base = knowledge_base or SecurityKnowledgeBase()
        self.prompt_builder = prompt_builder or SecurityPromptBuilder()
        self.backend = backend or self._default_backend()
        
        self.retriever = retriever or QdrantRetriever()
        
        self.baseline_engine = baseline_engine or BaselineEngine()
        
        self.correlation_engine = correlation_engine or CorrelationEngine()

    def _default_backend(self) -> SecurityModelBackend:
        heuristic = HeuristicSecurityBackend(self.knowledge_base)

        
        import os
        adapter_path = getenv("AGRUS_MODEL_PATH", "models/agrus-v1-final")
        if os.path.isdir(adapter_path) and os.path.exists(os.path.join(adapter_path, "adapter_config.json")):
            return FineTunedLlamaBackend(
                adapter_path=adapter_path,
                fallback=heuristic,
            )

        
        if getenv("SECURITY_AI_OLLAMA_BASE_URL"):
            return OllamaChatBackend(
                model=getenv("SECURITY_AI_OLLAMA_MODEL", "llama3.1"),
                base_url=getenv("SECURITY_AI_OLLAMA_BASE_URL"),
                fallback=heuristic,
            )

        
        return heuristic

    async def analyze_async(self, incident: IncidentContext) -> AIResult:
        
        entity_key = incident.asset_id or incident.host or "unknown"
        process = None
        dst_ip = None
        if hasattr(incident, 'labels') and incident.labels:
            for label in incident.labels:
                if label.startswith("process:"):
                    process = label.split(":", 1)[1]
                if label.startswith("dst_ip:"):
                    dst_ip = label.split(":", 1)[1]

        async with self._state_lock:
            self.baseline_engine.update(
                entity_id=entity_key,
                hour=incident.hour_of_day,
                process=process,
                ip=dst_ip,
                event_type=next((l for l in incident.labels if l in ("PROCESS_START", "FILE_ACCESS", "NETWORK_CONNECT")), None) if incident.labels else None,
            )

        deviation = self.baseline_engine.get_deviation(
            entity_id=entity_key,
            hour=incident.hour_of_day,
            process=process,
            ip=dst_ip,
        )

        
        retrieved_context = self.retriever.search(incident.summary, limit=3) or self.knowledge_base.retrieve(incident)
        prompt = self.prompt_builder.build(incident, retrieved_context)

        
        if deviation.get("has_baseline") and deviation.get("overall_deviation", 0) > 0.3:
            ueba_context = (
                f"\n[UEBA ALERT] Entity '{entity_key}' behavioral deviation: {deviation['overall_deviation']:.0%}. "
                f"Anomalies: {'; '.join(deviation.get('deviations', []))}. "
                f"Typical hours: {deviation.get('typical_hours', [])}. "
                f"Typical processes: {deviation.get('typical_processes', [])}."
            )
            prompt = prompt._replace(user_prompt=prompt.user_prompt + ueba_context)

        draft = await asyncio.to_thread(self.backend.generate, prompt, incident)
        ai_result = self._draft_to_ai_result(incident, draft, prompt)

        
        async with self._state_lock:
            correlated = self.correlation_engine.ingest(
                incident_id=incident.incident_id,
                host=incident.host,
                asset_id=incident.asset_id,
                mitre_techniques=ai_result.mitre_techniques,
                classification=ai_result.classification,
                action=ai_result.recommended_action,
            )

        
        if correlated:
            ai_result = AIResult(
                incident_id=ai_result.incident_id,
                classification=f"APT DETECTED: {correlated.summary}",
                confidence=min(ai_result.confidence + 0.15, 0.99),
                mitre_techniques=ai_result.mitre_techniques,
                recommended_action="isolate_host",
                escalate_to_human=True,
                reasoning=f"{ai_result.reasoning}; APT_CORRELATION: {correlated.severity} — {correlated.summary}",
            )

        
        if deviation.get("has_baseline") and deviation.get("overall_deviation", 0) > 0.3:
            ai_result = AIResult(
                incident_id=ai_result.incident_id,
                classification=ai_result.classification,
                confidence=min(ai_result.confidence + deviation["overall_deviation"] * 0.1, 0.99),
                mitre_techniques=ai_result.mitre_techniques,
                recommended_action=ai_result.recommended_action,
                escalate_to_human=ai_result.escalate_to_human,
                reasoning=f"{ai_result.reasoning}; UEBA_DEVIATION={deviation['overall_deviation']:.0%} [{'; '.join(deviation.get('deviations', []))}]",
            )

        return ai_result

    def analyze(self, incident: IncidentContext) -> AIResult:
        
        entity_key = incident.asset_id or incident.host or "unknown"
        process = None
        dst_ip = None
        if hasattr(incident, 'labels') and incident.labels:
            for label in incident.labels:
                if label.startswith("process:"):
                    process = label.split(":", 1)[1]
                if label.startswith("dst_ip:"):
                    dst_ip = label.split(":", 1)[1]

        with self._sync_lock:
            self.baseline_engine.update(
                entity_id=entity_key,
                hour=incident.hour_of_day,
                process=process,
                ip=dst_ip,
                event_type=next((l for l in incident.labels if l in ("PROCESS_START", "FILE_ACCESS", "NETWORK_CONNECT")), None) if incident.labels else None,
            )
            deviation = self.baseline_engine.get_deviation(
                entity_id=entity_key,
                hour=incident.hour_of_day,
                process=process,
                ip=dst_ip,
            )

        
        retrieved_context = self.retriever.search(incident.summary, limit=3) or self.knowledge_base.retrieve(incident)
        prompt = self.prompt_builder.build(incident, retrieved_context)

        
        if deviation.get("has_baseline") and deviation.get("overall_deviation", 0) > 0.3:
            ueba_context = (
                f"\n[UEBA ALERT] Entity '{entity_key}' behavioral deviation: {deviation['overall_deviation']:.0%}. "
                f"Anomalies: {'; '.join(deviation.get('deviations', []))}. "
                f"Typical hours: {deviation.get('typical_hours', [])}. "
                f"Typical processes: {deviation.get('typical_processes', [])}."
            )
            prompt = prompt._replace(user_prompt=prompt.user_prompt + ueba_context)

        draft = self.backend.generate(prompt, incident)
        ai_result = self._draft_to_ai_result(incident, draft, prompt)

        
        with self._sync_lock:
            correlated = self.correlation_engine.ingest(
                incident_id=incident.incident_id,
                host=incident.host,
                asset_id=incident.asset_id,
                mitre_techniques=ai_result.mitre_techniques,
                classification=ai_result.classification,
                action=ai_result.recommended_action,
            )

        
        if correlated:
            ai_result = AIResult(
                incident_id=ai_result.incident_id,
                classification=f"APT DETECTED: {correlated.summary}",
                confidence=min(ai_result.confidence + 0.15, 0.99),
                mitre_techniques=ai_result.mitre_techniques,
                recommended_action="isolate_host",
                escalate_to_human=True,
                reasoning=f"{ai_result.reasoning}; APT_CORRELATION: {correlated.severity} — {correlated.summary}",
            )

        
        if deviation.get("has_baseline") and deviation.get("overall_deviation", 0) > 0.3:
            ai_result = AIResult(
                incident_id=ai_result.incident_id,
                classification=ai_result.classification,
                confidence=min(ai_result.confidence + deviation["overall_deviation"] * 0.1, 0.99),
                mitre_techniques=ai_result.mitre_techniques,
                recommended_action=ai_result.recommended_action,
                escalate_to_human=ai_result.escalate_to_human,
                reasoning=f"{ai_result.reasoning}; UEBA_DEVIATION={deviation['overall_deviation']:.0%} [{'; '.join(deviation.get('deviations', []))}]",
            )

        return ai_result

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

    async def evaluate_async(self, incident: IncidentContext, constraints: CompanyConstraints) -> tuple[AIResult, Decision]:
        ai_result = await self.llm.analyze_async(incident)
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
        auto_execute = not requires_human_approval and enough_risk and enough_confidence and allowed_hour and asset_allowed and not blocked_by_criticality

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
