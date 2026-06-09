import json
from pathlib import Path
from unittest import TestCase

from security_ai_service.engine import SecurityDecisionEngine
from security_ai_service.evaluation import EvaluationHarness
from security_ai_service.scenarios import evaluation_cases_from_scenarios, load_scenarios


class ScenarioFixtureTests(TestCase):
    def test_scenarios_load(self) -> None:
        scenarios = load_scenarios()
        self.assertGreaterEqual(len(scenarios), 5)
        self.assertTrue(all(scenario.scenario_id for scenario in scenarios))
        self.assertTrue(all(scenario.incident.incident_id for scenario in scenarios))

    def test_scenario_evaluation_cases_pass(self) -> None:
        cases = evaluation_cases_from_scenarios(load_scenarios())
        results = EvaluationHarness(SecurityDecisionEngine()).run(cases)
        self.assertTrue(all(result.passed for result in results), results)

    def test_contract_schema_files_are_valid_json(self) -> None:
        contract_dir = Path(__file__).resolve().parent.parent / "contracts"
        schemas = sorted(contract_dir.glob("*.schema.json"))
        self.assertGreaterEqual(len(schemas), 6)
        for schema in schemas:
            payload = json.loads(schema.read_text(encoding="utf-8"))
            self.assertEqual(payload["type"], "object")
            self.assertIn("title", payload)
            self.assertIn("required", payload)
