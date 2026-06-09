from __future__ import annotations

import json
from dataclasses import asdict

from .evaluation import EvaluationHarness, default_evaluation_cases
from .engine import HeuristicSecurityLLM


def main() -> int:
    llm = HeuristicSecurityLLM()
    harness = EvaluationHarness()
    results = harness.run(default_evaluation_cases())
    print(json.dumps({
        "backend": getattr(llm.backend, "name", "unknown"),
        "summary": harness.summarize(results),
        "results": [
            {
                "case_name": result.case_name,
                "passed": result.passed,
                "decision": result.decision.to_dict(),
                "ai_result": asdict(result.ai_result),
                "issues": list(result.issues),
            }
            for result in results
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
