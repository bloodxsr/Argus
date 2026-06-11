"""UEBA — User & Entity Behavior Analytics baseline engine.

Maintains rolling behavioral profiles for every entity (user, host, IP,
asset) observed in the telemetry stream.  When a new event arrives, the
engine calculates how far it deviates from "normal" for that entity and
injects the deviation context into the AI prompt.

Persistence: baselines are stored as a JSON file on disk so they survive
restarts without requiring MongoDB.
"""
from __future__ import annotations

import json
import math
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


@dataclass
class EntityBaseline:
    entity_id: str
    hour_histogram: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    process_freq: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    ip_freq: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    event_types: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    event_count: int = 0
    first_seen: float = 0.0
    last_seen: float = 0.0


class BaselineEngine:
    """In-memory behavioral baseline store with JSON file persistence."""

    def __init__(self, persistence_path: str = "models/baselines.json") -> None:
        self._baselines: Dict[str, EntityBaseline] = {}
        self._persistence_path = persistence_path
        self._load()

    # ── Public API ──────────────────────────────────────────────

    def update(
        self,
        entity_id: str,
        hour: int,
        process: Optional[str] = None,
        ip: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> None:
        """Ingest a new event and update the entity's rolling baseline."""
        now = time.time()

        if entity_id not in self._baselines:
            self._baselines[entity_id] = EntityBaseline(
                entity_id=entity_id,
                first_seen=now,
            )

        b = self._baselines[entity_id]
        b.hour_histogram[hour] = b.hour_histogram.get(hour, 0) + 1
        if process:
            b.process_freq[process] = b.process_freq.get(process, 0) + 1
        if ip:
            b.ip_freq[ip] = b.ip_freq.get(ip, 0) + 1
        if event_type:
            b.event_types[event_type] = b.event_types.get(event_type, 0) + 1
        b.event_count += 1
        b.last_seen = now

        # Auto-save every 100 events
        if b.event_count % 100 == 0:
            self._save()

    def get_baseline(self, entity_id: str) -> Optional[EntityBaseline]:
        return self._baselines.get(entity_id)

    def get_deviation(
        self,
        entity_id: str,
        hour: int,
        process: Optional[str] = None,
        ip: Optional[str] = None,
    ) -> Dict:
        """Calculate how much the current event deviates from this entity's baseline.

        Returns a dict with deviation scores and human-readable explanations.
        """
        b = self._baselines.get(entity_id)
        if b is None or b.event_count < 5:
            return {
                "entity_id": entity_id,
                "has_baseline": False,
                "reason": "Insufficient data (fewer than 5 events observed)",
                "overall_deviation": 0.0,
            }

        deviations = []
        explanations = []
        total = b.event_count

        # ── Hour deviation ──
        hour_count = b.hour_histogram.get(hour, 0)
        hour_ratio = hour_count / total if total > 0 else 0
        if hour_ratio < 0.02:
            deviations.append(0.9)
            explanations.append(f"hour={hour} is RARE (seen {hour_count}/{total} times, {hour_ratio:.1%})")
        elif hour_ratio < 0.05:
            deviations.append(0.5)
            explanations.append(f"hour={hour} is UNCOMMON ({hour_ratio:.1%})")
        else:
            deviations.append(0.0)

        # Detect off-hours: if >80% of events are during business hours but this one is not
        business_hours_count = sum(b.hour_histogram.get(h, 0) for h in range(8, 19))
        business_ratio = business_hours_count / total if total > 0 else 0
        if business_ratio > 0.8 and (hour < 6 or hour > 22):
            deviations.append(0.85)
            explanations.append(f"Entity is {business_ratio:.0%} business-hours active, but current event is at {hour}:00")

        # ── Process deviation ──
        if process:
            proc_count = b.process_freq.get(process, 0)
            if proc_count == 0:
                deviations.append(0.7)
                explanations.append(f"process='{process}' has NEVER been seen for this entity")
            else:
                proc_ratio = proc_count / total
                if proc_ratio < 0.01:
                    deviations.append(0.5)
                    explanations.append(f"process='{process}' is rare ({proc_ratio:.2%})")

        # ── IP deviation ──
        if ip:
            ip_count = b.ip_freq.get(ip, 0)
            if ip_count == 0:
                deviations.append(0.6)
                explanations.append(f"dst_ip='{ip}' has NEVER been contacted by this entity")
            else:
                ip_ratio = ip_count / total
                if ip_ratio < 0.01:
                    deviations.append(0.4)
                    explanations.append(f"dst_ip='{ip}' is rarely contacted ({ip_ratio:.2%})")

        overall = max(deviations) if deviations else 0.0

        # Build typical behavior summary
        top_hours = sorted(b.hour_histogram.items(), key=lambda x: -x[1])[:3]
        top_procs = sorted(b.process_freq.items(), key=lambda x: -x[1])[:5]

        return {
            "entity_id": entity_id,
            "has_baseline": True,
            "event_count": total,
            "days_observed": round((b.last_seen - b.first_seen) / 86400, 1),
            "overall_deviation": round(overall, 2),
            "deviations": explanations,
            "typical_hours": [h for h, _ in top_hours],
            "typical_processes": [p for p, _ in top_procs],
        }

    def list_entities(self) -> List[str]:
        return list(self._baselines.keys())

    def save(self) -> None:
        self._save()

    # ── Persistence ─────────────────────────────────────────────

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._persistence_path) or ".", exist_ok=True)
        data = {}
        for eid, b in self._baselines.items():
            data[eid] = {
                "entity_id": b.entity_id,
                "hour_histogram": dict(b.hour_histogram),
                "process_freq": dict(b.process_freq),
                "ip_freq": dict(b.ip_freq),
                "event_types": dict(b.event_types),
                "event_count": b.event_count,
                "first_seen": b.first_seen,
                "last_seen": b.last_seen,
            }
        with open(self._persistence_path, "w") as f:
            json.dump(data, f)

    def _load(self) -> None:
        if not os.path.exists(self._persistence_path):
            return
        try:
            with open(self._persistence_path, "r") as f:
                data = json.load(f)
            for eid, entry in data.items():
                self._baselines[eid] = EntityBaseline(
                    entity_id=entry["entity_id"],
                    hour_histogram=defaultdict(int, {int(k): v for k, v in entry.get("hour_histogram", {}).items()}),
                    process_freq=defaultdict(int, entry.get("process_freq", {})),
                    ip_freq=defaultdict(int, entry.get("ip_freq", {})),
                    event_types=defaultdict(int, entry.get("event_types", {})),
                    event_count=entry.get("event_count", 0),
                    first_seen=entry.get("first_seen", 0.0),
                    last_seen=entry.get("last_seen", 0.0),
                )
        except (json.JSONDecodeError, KeyError):
            self._baselines = {}
