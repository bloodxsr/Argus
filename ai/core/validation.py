from __future__ import annotations

from typing import List, Optional


class ValidationError(ValueError):
    pass


class AIResultModel:
    def __init__(self, incident_id: str, classification: str, confidence: float, mitre_techniques: List[str], recommended_action: str, escalate_to_human: bool, reasoning: str) -> None:
        if not isinstance(incident_id, str) or not incident_id:
            raise ValidationError("incident_id must be a non-empty string")
        if not isinstance(classification, str) or not classification:
            raise ValidationError("classification must be a non-empty string")
        try:
            confidence = float(confidence)
        except Exception:
            raise ValidationError("confidence must be a number")
        if not (0.0 <= confidence <= 1.0):
            raise ValidationError("confidence must be between 0.0 and 1.0")
        if mitre_techniques is None:
            mitre_techniques = []
        if not isinstance(mitre_techniques, (list, tuple)):
            raise ValidationError("mitre_techniques must be a list of strings")
        if not isinstance(recommended_action, str) or not recommended_action:
            raise ValidationError("recommended_action must be a non-empty string")
        if not isinstance(escalate_to_human, bool):
            raise ValidationError("escalate_to_human must be a boolean")
        if not isinstance(reasoning, str):
            raise ValidationError("reasoning must be a string")

        self.incident_id = incident_id
        self.classification = classification
        self.confidence = confidence
        self.mitre_techniques = list(mitre_techniques)
        self.recommended_action = recommended_action
        self.escalate_to_human = escalate_to_human
        self.reasoning = reasoning


class DecisionModel:
    def __init__(self, incident_id: str, action: str, confidence: float, requires_human_approval: bool, auto_execute: bool, reasoning: str, fallback_action: Optional[str], audit_trail: dict) -> None:
        if not isinstance(incident_id, str) or not incident_id:
            raise ValidationError("incident_id must be a non-empty string")
        if not isinstance(action, str) or not action:
            raise ValidationError("action must be a non-empty string")
        try:
            confidence = float(confidence)
        except Exception:
            raise ValidationError("confidence must be a number")
        if not (0.0 <= confidence <= 1.0):
            raise ValidationError("confidence must be between 0.0 and 1.0")
        if not isinstance(requires_human_approval, bool):
            raise ValidationError("requires_human_approval must be a boolean")
        if not isinstance(auto_execute, bool):
            raise ValidationError("auto_execute must be a boolean")
        if not isinstance(reasoning, str):
            raise ValidationError("reasoning must be a string")
        if fallback_action is not None and not isinstance(fallback_action, str):
            raise ValidationError("fallback_action must be a string or None")
        if not isinstance(audit_trail, dict):
            raise ValidationError("audit_trail must be a dict")

        self.incident_id = incident_id
        self.action = action
        self.confidence = confidence
        self.requires_human_approval = requires_human_approval
        self.auto_execute = auto_execute
        self.reasoning = reasoning
        self.fallback_action = fallback_action
        self.audit_trail = audit_trail


def validate_ai_result(payload: dict) -> AIResultModel:
    try:
        return AIResultModel(
            incident_id=payload["incident_id"],
            classification=payload["classification"],
            confidence=payload["confidence"],
            mitre_techniques=payload.get("mitre_techniques", []),
            recommended_action=payload["recommended_action"],
            escalate_to_human=payload["escalate_to_human"],
            reasoning=payload["reasoning"],
        )
    except KeyError as e:
        raise ValidationError(f"missing field: {e}") from e


def validate_decision(payload: dict) -> DecisionModel:
    try:
        return DecisionModel(
            incident_id=payload["incident_id"],
            action=payload["action"],
            confidence=payload["confidence"],
            requires_human_approval=payload["requires_human_approval"],
            auto_execute=payload["auto_execute"],
            reasoning=payload["reasoning"],
            fallback_action=payload.get("fallback_action"),
            audit_trail=payload["audit_trail"],
        )
    except KeyError as e:
        raise ValidationError(f"missing field: {e}") from e
