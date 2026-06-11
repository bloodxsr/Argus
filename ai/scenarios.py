from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .core.models import IncidentContext, Scenario, UnifiedEvent


def default_scenario_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "scenarios"


def load_scenario(path: str | Path) -> Scenario:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return scenario_from_dict(data)


def load_scenarios(directory: str | Path | None = None) -> tuple[Scenario, ...]:
    scenario_dir = Path(directory) if directory else default_scenario_dir()
    if not scenario_dir.exists():
        return ()
    return tuple(load_scenario(path) for path in sorted(scenario_dir.glob("*.json")))


def scenario_from_dict(data: dict) -> Scenario:
    incident_data = data["incident"]
    events = tuple(_event_from_dict(event) for event in data.get("events", ()))
    return Scenario(
        scenario_id=str(data["scenario_id"]),
        title=str(data["title"]),
        description=str(data.get("description", "")),
        incident=IncidentContext(
            incident_id=str(incident_data["incident_id"]),
            summary=str(incident_data["summary"]),
            risk_score=float(incident_data["risk_score"]),
            asset_id=str(incident_data.get("asset_id", "unknown")),
            host=str(incident_data.get("host", "unknown")),
            environment=str(incident_data.get("environment", "unknown")),
            hour_of_day=int(incident_data.get("hour_of_day", 12)),
            labels=tuple(str(label) for label in incident_data.get("labels", ())),
            company=str(incident_data.get("company", "default")),
        ),
        expected_outcome=dict(data.get("expected_outcome", {})),
        events=events,
    )


def evaluation_cases_from_scenarios(scenarios: Iterable[Scenario]):
    from .core.models import CompanyConstraints, EvaluationCase

    cases = []
    for scenario in scenarios:
        expected = scenario.expected_outcome
        if not expected:
            continue
        cases.append(
            EvaluationCase(
                name=scenario.scenario_id,
                incident=scenario.incident,
                constraints=CompanyConstraints(),
                expected_action=str(expected["action"]),
                expected_auto_execute=bool(expected["auto_execute"]),
                expected_requires_human_approval=bool(expected["requires_human_approval"]),
                expected_classification=expected.get("classification"),
                expected_confidence_at_least=float(expected.get("confidence_at_least", 0.0)),
            )
        )
    return tuple(cases)


def _event_from_dict(data: dict) -> UnifiedEvent:
    return UnifiedEvent(
        schema_version=str(data.get("schema_version", "1.0")),
        event_id=str(data["event_id"]),
        source=str(data["source"]),
        event_type=str(data["event_type"]),
        timestamp=str(data["timestamp"]),
        host=str(data.get("host", "unknown")),
        host_ip=str(data.get("host_ip", "unknown")),
        environment=str(data.get("environment", "unknown")),
        pid=data.get("pid"),
        uid=data.get("uid"),
        payload=dict(data.get("payload", {})),
    )
