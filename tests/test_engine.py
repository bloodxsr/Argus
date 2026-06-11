from unittest import TestCase

from ai import SecurityDecisionEngine, SecurityKnowledgeBase, SecurityPromptBuilder
from ai.evaluation import EvaluationHarness, default_evaluation_cases


class SecurityDecisionEngineTests(TestCase):
    def test_all_default_evaluation_cases_pass(self) -> None:
        harness = EvaluationHarness(SecurityDecisionEngine())
        results = harness.run(default_evaluation_cases())
        self.assertTrue(all(result.passed for result in results), results)

    def test_company_constraints_block_disallowed_auto_action(self) -> None:
        engine = SecurityDecisionEngine()
        case = next(case for case in default_evaluation_cases() if case.name == "policy_blocked_kill")
        ai_result, decision = engine.evaluate(case.incident, case.constraints)
        self.assertEqual(ai_result.classification, "Remote Code Execution + C2 Beaconing")
        self.assertEqual(decision.action, "observe")
        self.assertFalse(decision.auto_execute)
        self.assertTrue(decision.requires_human_approval)

    def test_prompt_injection_is_forced_to_review(self) -> None:
        engine = SecurityDecisionEngine()
        case = next(case for case in default_evaluation_cases() if case.name == "prompt_injection")
        ai_result, decision = engine.evaluate(case.incident, case.constraints)
        self.assertEqual(ai_result.classification, "Prompt Injection Attempt")
        self.assertTrue(ai_result.escalate_to_human)
        self.assertTrue(decision.requires_human_approval)
        self.assertFalse(decision.auto_execute)

    def test_prompt_builder_includes_retrieved_security_context(self) -> None:
        case = next(case for case in default_evaluation_cases() if case.name == "high_confidence_rce")
        knowledge_base = SecurityKnowledgeBase()
        prompt = SecurityPromptBuilder().build(case.incident, knowledge_base.retrieve(case.incident))

        self.assertIn("Return only valid JSON", prompt.user_prompt)
        self.assertIn("Web shell and remote execution", prompt.user_prompt)
        self.assertEqual(prompt.messages[0]["role"], "system")
        self.assertIn("Do not reveal hidden chain-of-thought", prompt.system_prompt)
