from unittest import TestCase

from ai.replay import replay_scenario_by_id


class ScenarioReplayTests(TestCase):
    def test_high_risk_scenario_replay_auto_executes_simulated_action(self) -> None:
        result = replay_scenario_by_id("rce_c2_beacon")

        self.assertEqual(result["decision"]["action"], "kill_process")
        self.assertFalse(result["decision"]["auto_execute"])
        self.assertEqual(result["action_record"]["action_type"], "pending_review")
        self.assertEqual(result["review_decision"]["decision"], "pending")

    def test_review_scenario_replay_creates_pending_review(self) -> None:
        result = replay_scenario_by_id("ueba_impossible_travel")

        self.assertEqual(result["decision"]["action"], "recommend")
        self.assertTrue(result["decision"]["requires_human_approval"])
        self.assertEqual(result["action_record"]["action_type"], "pending_review")
        self.assertEqual(result["review_decision"]["decision"], "pending")
