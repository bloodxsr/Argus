from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class IncidentContext:
    incident_id: str
    summary: str
    risk_score: float
    asset_id: str = "unknown"
    host: str = "unknown"
    environment: str = "unknown"
    hour_of_day: int = 12
    labels: tuple[str, ...] = ()
    company: str = "default"


@dataclass(frozen=True, slots=True)
class UnifiedEvent:
    schema_version: str
    event_id: str
    source: str
    event_type: str
    timestamp: str
    host: str
    host_ip: str = "unknown"
    environment: str = "unknown"
    pid: int | None = None
    uid: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Incident:
    incident_id: str
    host: str
    start_time: str
    end_time: str
    severity: str
    summary: str
    events: tuple[UnifiedEvent, ...] = ()
    source_agent: str = "scenario"

    def to_context(self, risk_score: float, asset_id: str = "unknown", hour_of_day: int = 12, labels: tuple[str, ...] = (), company: str = "default") -> IncidentContext:
        return IncidentContext(
            incident_id=self.incident_id,
            summary=self.summary,
            risk_score=risk_score,
            asset_id=asset_id,
            host=self.host,
            environment=self.events[0].environment if self.events else "unknown",
            hour_of_day=hour_of_day,
            labels=labels,
            company=company,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "events": [event.to_dict() for event in self.events],
        }


@dataclass(frozen=True, slots=True)
class RiskScore:
    incident_id: str
    score: float
    level: str
    impact: float
    confidence: float
    exposure: float
    breakdown: dict[str, Any] = field(default_factory=dict)
    recommended_action: str = "observe"
    escalate: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIResult:
    incident_id: str
    classification: str
    confidence: float
    mitre_techniques: tuple[str, ...]
    recommended_action: str
    escalate_to_human: bool
    reasoning: str


@dataclass(frozen=True, slots=True)
class CompanyConstraints:
    allowed_actions: tuple[str, ...] = (
        "observe",
        "recommend",
        "kill_process",
        "block_ip",
        "isolate_host",
        "quarantine_container",
    )
    auto_response_threshold: float = 0.85
    minimum_risk_for_auto_response: float = 70.0
    no_auto_response_assets: frozenset[str] = frozenset()
    critical_environments: frozenset[str] = frozenset({"production", "pci-data-layer"})
    critical_assets: frozenset[str] = frozenset({"ceo-laptop", "auth-server-01"})
    approved_hours: tuple[int, ...] = tuple(range(24))
    escalation_channel: str = "soc-tier-1"

    def allows_action(self, action: str) -> bool:
        return action in self.allowed_actions

    def is_hour_allowed(self, hour_of_day: int) -> bool:
        return hour_of_day in self.approved_hours

    def asset_is_blocked(self, asset_id: str) -> bool:
        return asset_id in self.no_auto_response_assets


@dataclass(frozen=True, slots=True)
class Decision:
    incident_id: str
    action: str
    confidence: float
    requires_human_approval: bool
    auto_execute: bool
    reasoning: str
    fallback_action: str = "observe"
    audit_trail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ActionRecord:
    action_id: str
    incident_id: str
    action_type: str
    target: str
    host: str
    executed_by: str
    approved_by: str | None
    command: str
    result: str
    rollback_cmd: str | None
    rolled_back: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    incident_id: str
    review_id: str
    analyst: str
    decision: str
    notes: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Scenario:
    scenario_id: str
    title: str
    description: str
    incident: IncidentContext
    expected_outcome: dict[str, Any] = field(default_factory=dict)
    events: tuple[UnifiedEvent, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "description": self.description,
            "incident": asdict(self.incident),
            "expected_outcome": self.expected_outcome,
            "events": [event.to_dict() for event in self.events],
        }


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    name: str
    incident: IncidentContext
    constraints: CompanyConstraints
    expected_action: str
    expected_auto_execute: bool
    expected_requires_human_approval: bool
    expected_classification: str | None = None
    expected_reason_contains: str | None = None
    expected_confidence_at_least: float = 0.0


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    case_name: str
    passed: bool
    decision: Decision
    ai_result: AIResult
    issues: tuple[str, ...] = ()
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
