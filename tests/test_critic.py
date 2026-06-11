from unittest import TestCase

from ai.core.critic import CriticVerifier


class CriticTests(TestCase):
    def test_valid_result_passes(self) -> None:
        ai = {
            "incident_id": "inc-1",
            "classification": "RCE",
            "confidence": 0.9,
            "mitre_techniques": ["T1059.004"],
            "recommended_action": "observe",
            "escalate_to_human": False,
            "reasoning": "evidence",
        }
        decision = {
            "incident_id": "inc-1",
            "action": "observe",
            "confidence": 0.9,
            "requires_human_approval": False,
            "auto_execute": True,
            "reasoning": "authed",
            "fallback_action": "observe",
            "audit_trail": {},
        }
        ok, issues = CriticVerifier().verify(ai, decision)
        self.assertTrue(ok)
        self.assertEqual(issues, [])

    def test_high_impact_auto_execute_passes(self) -> None:
        ai = {
            "incident_id": "inc-1",
            "classification": "RCE",
            "confidence": 0.9,
            "mitre_techniques": ["T1059.004"],
            "recommended_action": "kill_process",
            "escalate_to_human": False,
            "reasoning": "evidence",
        }
        decision = {
            "incident_id": "inc-1",
            "action": "kill_process",
            "confidence": 0.9,
            "requires_human_approval": False,
            "auto_execute": True,
            "reasoning": "authed",
            "fallback_action": "observe",
            "audit_trail": {},
        }
        ok, issues = CriticVerifier().verify(ai, decision)
        self.assertTrue(ok)
        self.assertEqual(issues, [])

    def test_high_impact_low_confidence_fails(self) -> None:
        ai = {
            "incident_id": "inc-2",
            "classification": "RCE",
            "confidence": 0.6,
            "mitre_techniques": ["T1059.004"],
            "recommended_action": "kill_process",
            "escalate_to_human": False,
            "reasoning": "uncertain",
        }
        decision = {
            "incident_id": "inc-2",
            "action": "kill_process",
            "confidence": 0.6,
            "requires_human_approval": True,
            "auto_execute": True,
            "reasoning": "authed",
            "fallback_action": "observe",
            "audit_trail": {},
        }
        ok, issues = CriticVerifier().verify(ai, decision)
        self.assertFalse(ok)
        self.assertTrue(any("high-impact" in s for s in issues))
