from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from .core.engine import SecurityDecisionEngine
from .core.models import ActionRecord, CompanyConstraints, ReviewDecision, Scenario
from .scenarios import load_scenarios


def replay_scenario(scenario: Scenario, engine: SecurityDecisionEngine | None = None) -> dict[str, Any]:
    decision_engine = engine or SecurityDecisionEngine()
    ai_result, decision = decision_engine.evaluate(scenario.incident, CompanyConstraints())
    action_record = _build_action_record(scenario, decision)
    review_decision = _build_review_decision(scenario) if decision.requires_human_approval else None
    return {
        "scenario": scenario.to_dict(),
        "event_count": len(scenario.events),
        "pipeline": [
            "UnifiedEvent",
            "IncidentContext",
            "AIResult",
            "Decision",
            "ActionRecord",
            "ReviewDecision" if review_decision else "HumanAudit",
        ],
        "events": [event.to_dict() for event in scenario.events],
        "ai_result": asdict(ai_result),
        "decision": decision.to_dict(),
        "action_record": action_record.to_dict(),
        "review_decision": review_decision.to_dict() if review_decision else None,
    }


def replay_scenario_by_id(scenario_id: str, engine: SecurityDecisionEngine | None = None) -> dict[str, Any]:
    for scenario in load_scenarios():
        if scenario.scenario_id == scenario_id:
            return replay_scenario(scenario, engine=engine)
    raise ValueError(f"unknown scenario_id: {scenario_id}")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Replay an AGRUS demo scenario.")
    parser.add_argument("scenario_id", nargs="?", help="Scenario ID to replay. Lists scenarios when omitted.")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON.")
    args = parser.parse_args(argv)

    if not args.scenario_id:
        print(json.dumps({"scenarios": [scenario.scenario_id for scenario in load_scenarios()]}, indent=2))
        return 0

    result = replay_scenario_by_id(args.scenario_id)
    print(json.dumps(result, indent=None if args.compact else 2, sort_keys=True))
    return 0


def _build_action_record(scenario: Scenario, decision) -> ActionRecord:
    if decision.auto_execute:
        action_type = f"{decision.action}_simulated"
        result = "simulated"
        rollback_cmd = f"simulate:rollback:{decision.action}"
    elif decision.requires_human_approval:
        action_type = "pending_review"
        result = "not_executed"
        rollback_cmd = None
    else:
        action_type = decision.action
        result = "observed"
        rollback_cmd = None

    return ActionRecord(
        action_id=f"act-{scenario.incident.incident_id}",
        incident_id=scenario.incident.incident_id,
        action_type=action_type,
        target=scenario.incident.asset_id,
        host=scenario.incident.host,
        executed_by="agrus-demo",
        approved_by=None,
        command=f"simulate:{decision.action}",
        result=result,
        rollback_cmd=rollback_cmd,
        rolled_back=False,
    )


def _build_review_decision(scenario: Scenario) -> ReviewDecision:
    return ReviewDecision(
        incident_id=scenario.incident.incident_id,
        review_id=f"rev-{scenario.incident.incident_id}",
        analyst="pending",
        decision="pending",
        notes="Decision requires human approval before response execution.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
