"""APT Detection — Multi-stage attack correlation engine.

Catches slow, multi-stage Advanced Persistent Threats by stitching
isolated events into coherent attack timelines using MITRE ATT&CK
kill chain progression analysis.

Events are stored in a sliding window (default 7 days).  When a new
event arrives, the engine checks whether it, combined with recent
events on the same host/entity, forms a kill chain progression.
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple



MITRE_KILL_CHAIN: List[Tuple[str, List[str]]] = [
    ("reconnaissance",        ["T1595", "T1592", "T1589", "T1590", "T1046"]),
    ("initial_access",        ["T1566", "T1190", "T1133", "T1078", "T1105"]),
    ("execution",             ["T1059", "T1059.001", "T1059.004", "T1204", "T1053", "T1053.003"]),
    ("persistence",           ["T1053.003", "T1543", "T1547", "T1136", "T1222.002"]),
    ("privilege_escalation",  ["T1548", "T1068", "T1055"]),
    ("defense_evasion",       ["T1140", "T1562", "T1562.004", "T1222", "T1222.002"]),
    ("credential_access",     ["T1003", "T1003.001", "T1003.002", "T1110"]),
    ("lateral_movement",      ["T1021", "T1021.004", "T1570"]),
    ("exfiltration",          ["T1041", "T1048", "T1567"]),
    ("impact",                ["T1486", "T1490", "T1489"]),
]


_TECHNIQUE_TO_STAGE: Dict[str, str] = {}
for stage_name, techniques in MITRE_KILL_CHAIN:
    for t in techniques:
        _TECHNIQUE_TO_STAGE[t] = stage_name


@dataclass
class StoredEvent:
    incident_id: str
    host: str
    asset_id: str
    mitre_techniques: Tuple[str, ...]
    classification: str
    action: str
    timestamp: float
    kill_chain_stages: List[str] = field(default_factory=list)


@dataclass
class CorrelatedIncident:
    """A multi-stage attack detected by correlating multiple events."""
    correlation_id: str
    entity: str
    events: List[StoredEvent]
    kill_chain_stages_hit: List[str]
    kill_chain_coverage: float      
    time_span_hours: float
    severity: str                   
    summary: str


class CorrelationEngine:
    """Sliding-window event correlation with MITRE kill chain analysis."""

    def __init__(self, window_days: int = 7) -> None:
        self._window_seconds = window_days * 86400
        
        self._events_by_entity: Dict[str, List[StoredEvent]] = defaultdict(list)

    def ingest(
        self,
        incident_id: str,
        host: str,
        asset_id: str,
        mitre_techniques: Tuple[str, ...],
        classification: str,
        action: str,
        timestamp: Optional[float] = None,
    ) -> Optional[CorrelatedIncident]:
        """Store an event and immediately check for kill chain progression.

        Returns a CorrelatedIncident if the new event completes a
        multi-stage attack pattern.  Returns None otherwise.
        """
        now = timestamp or time.time()

        
        stages = list(dict.fromkeys(
            _TECHNIQUE_TO_STAGE[t]
            for t in mitre_techniques
            if t in _TECHNIQUE_TO_STAGE
        ))

        event = StoredEvent(
            incident_id=incident_id,
            host=host,
            asset_id=asset_id,
            mitre_techniques=mitre_techniques,
            classification=classification,
            action=action,
            timestamp=now,
            kill_chain_stages=stages,
        )

        
        for key in {host, asset_id}:
            if key and key != "unknown":
                self._events_by_entity[key].append(event)

        
        self._prune(now)

        
        for key in {host, asset_id}:
            if key and key != "unknown":
                correlated = self._check_correlation(key, now)
                if correlated:
                    return correlated

        return None

    def get_timeline(self, entity: str) -> List[dict]:
        """Return a chronological timeline of all events for an entity."""
        events = sorted(self._events_by_entity.get(entity, []), key=lambda e: e.timestamp)
        timeline = []
        for e in events:
            timeline.append({
                "incident_id": e.incident_id,
                "timestamp": e.timestamp,
                "classification": e.classification,
                "mitre_techniques": list(e.mitre_techniques),
                "kill_chain_stages": e.kill_chain_stages,
                "action": e.action,
            })
        return timeline

    def get_active_correlations(self) -> List[CorrelatedIncident]:
        """Scan all entities and return any that have multi-stage activity."""
        now = time.time()
        self._prune(now)
        results = []
        seen = set()
        for entity in list(self._events_by_entity.keys()):
            if entity in seen:
                continue
            seen.add(entity)
            correlated = self._check_correlation(entity, now)
            if correlated:
                results.append(correlated)
        return results

    

    def _prune(self, now: float) -> None:
        """Remove events older than the sliding window."""
        cutoff = now - self._window_seconds
        for key in list(self._events_by_entity.keys()):
            self._events_by_entity[key] = [
                e for e in self._events_by_entity[key]
                if e.timestamp >= cutoff
            ]
            if not self._events_by_entity[key]:
                del self._events_by_entity[key]

    def _check_correlation(self, entity: str, now: float) -> Optional[CorrelatedIncident]:
        """Check if events for this entity form a kill chain progression."""
        events = self._events_by_entity.get(entity, [])
        if len(events) < 2:
            return None

        
        all_stages = set()
        for e in events:
            all_stages.update(e.kill_chain_stages)

        if len(all_stages) < 2:
            return None

        
        stage_order = [name for name, _ in MITRE_KILL_CHAIN]
        hit_ordered = [s for s in stage_order if s in all_stages]

        coverage = len(hit_ordered) / len(stage_order)

        
        if len(hit_ordered) >= 2:
            sorted_events = sorted(events, key=lambda e: e.timestamp)
            time_span = (sorted_events[-1].timestamp - sorted_events[0].timestamp) / 3600

            if coverage >= 0.5:
                severity = "CRITICAL"
            elif coverage >= 0.3:
                severity = "HIGH"
            else:
                severity = "MEDIUM"

            summary_parts = [
                f"Multi-stage attack detected on entity '{entity}'.",
                f"Kill chain stages: {' → '.join(hit_ordered)}.",
                f"Coverage: {coverage:.0%} of MITRE ATT&CK kill chain.",
                f"Time span: {time_span:.1f} hours across {len(sorted_events)} events.",
            ]

            return CorrelatedIncident(
                correlation_id=f"corr-{entity}-{int(now)}",
                entity=entity,
                events=sorted_events,
                kill_chain_stages_hit=hit_ordered,
                kill_chain_coverage=round(coverage, 2),
                time_span_hours=round(time_span, 1),
                severity=severity,
                summary=" ".join(summary_parts),
            )

        return None
