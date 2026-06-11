from unittest import TestCase

from ai.core.validation import (
    AIResultModel,
    DecisionModel,
    validate_ai_result,
    validate_decision,
)
from ai.core.models import ActionRecord, ReviewDecision, UnifiedEvent


class SchemaValidationTests(TestCase):
    def test_valid_ai_result_passes_validation(self) -> None:
        payload = {
            "incident_id": "inc-1",
            "classification": "RCE",
            "confidence": 0.93,
            "mitre_techniques": ["T1059.004"],
            "recommended_action": "kill_process",
            "escalate_to_human": False,
            "reasoning": "evidence here",
        }
        model = validate_ai_result(payload)
        self.assertIsInstance(model, AIResultModel)

    def test_invalid_confidence_raises(self) -> None:
        payload = {
            "incident_id": "inc-1",
            "classification": "RCE",
            "confidence": 1.5,
            "mitre_techniques": [],
            "recommended_action": "kill_process",
            "escalate_to_human": False,
            "reasoning": "evidence here",
        }
        with self.assertRaises(Exception):
            validate_ai_result(payload)

    def test_valid_decision_passes(self) -> None:
        payload = {
            "incident_id": "inc-1",
            "action": "observe",
            "confidence": 0.5,
            "requires_human_approval": True,
            "auto_execute": False,
            "reasoning": "some reasoning",
            "fallback_action": "observe",
            "audit_trail": {"company": "default"},
        }
        model = validate_decision(payload)
        self.assertIsInstance(model, DecisionModel)

    def test_missing_field_in_decision_raises(self) -> None:
        payload = {
            "incident_id": "inc-1",
            "confidence": 0.5,
            "requires_human_approval": True,
            "auto_execute": False,
            "reasoning": "some reasoning",
            "fallback_action": "observe",
            "audit_trail": {},
        }
        with self.assertRaises(Exception):
            validate_decision(payload)

    def test_new_shared_contracts_serialize(self) -> None:
        event = UnifiedEvent(
            schema_version="1.0",
            event_id="evt-1",
            source="test",
            event_type="process_spawn",
            timestamp="2026-06-09T00:00:00Z",
            host="web-01",
            payload={"process": "bash"},
        )
        action = ActionRecord(
            action_id="act-1",
            incident_id="inc-1",
            action_type="kill_process_simulated",
            target="web-01",
            host="web-01",
            executed_by="agrus-demo",
            approved_by=None,
            command="simulate:kill_process",
            result="simulated",
            rollback_cmd="simulate:rollback:kill_process",
            rolled_back=False,
        )
        review = ReviewDecision(
            incident_id="inc-1",
            review_id="rev-1",
            analyst="pending",
            decision="pending",
            notes="needs review",
        )

        self.assertEqual(event.to_dict()["event_id"], "evt-1")
        self.assertEqual(action.to_dict()["action_type"], "kill_process_simulated")
        self.assertEqual(review.to_dict()["decision"], "pending")
