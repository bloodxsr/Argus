from __future__ import annotations

from typing import Dict, List, Tuple

from .validation import validate_ai_result, validate_decision, ValidationError


class CriticVerifier:
    """Lightweight critic that validates model outputs and checks simple consistency rules.

    Does NOT call external models. For production you can optionally add a model-based
    secondary verifier that re-prompts the model and checks agreement.
    """

    def __init__(self) -> None:
        pass

    def verify(self, ai_result: Dict, decision: Dict) -> Tuple[bool, List[str]]:
        """Return (is_valid, issues).

        Basic checks:
        - Schema validation (required fields, types, ranges)
        - Confidence/auto_execute consistency
        - If recommended_action is high-impact (kill_process, isolate_host) require confidence >= 0.85
        - If escalate_to_human is True then auto_execute must be False
        """
        issues: List[str] = []
        try:
            validate_ai_result(ai_result)
        except ValidationError as e:
            issues.append(f"ai_result schema: {e}")

        try:
            validate_decision(decision)
        except ValidationError as e:
            issues.append(f"decision schema: {e}")

        
        rec_action = ai_result.get("recommended_action")
        confidence = float(ai_result.get("confidence", 0.0))
        escalate = bool(ai_result.get("escalate_to_human", False))
        auto_exec = bool(decision.get("auto_execute", False))

        high_impact = {"kill_process", "isolate_host", "quarantine_container", "block_ip"}
        if rec_action in high_impact and confidence < 0.85:
            issues.append("high-impact action with low confidence")

        if escalate and auto_exec:
            issues.append("escalate_to_human is True but decision.auto_execute is True")



        if auto_exec and confidence < 0.7:
            issues.append("auto_execute requested with insufficient model confidence")

        is_valid = not issues
        return is_valid, issues
