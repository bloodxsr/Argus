from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from typing import Optional

from nats.aio.client import Client as NATS

from .core.engine import SecurityDecisionEngine
from .core.models import IncidentContext, CompanyConstraints


async def run_nats(nats_url: str = "nats://127.0.0.1:4222") -> None:
    nc = NATS()
    await nc.connect(nats_url)
    engine = SecurityDecisionEngine()

    async def handler(msg):
        try:
            payload = json.loads(msg.data.decode())
        except Exception:
            return

        # Map telemetry event dynamically to AI context
        incident = IncidentContext(
            incident_id=payload.get("event_id", payload.get("incident_id", "unknown")),
            summary=f"Event {payload.get('event_type')} on {payload.get('host')} involving {json.dumps(payload.get('payload', {}))}",
            risk_score=float(payload.get("risk_score", 8.0)), # High default priority for kernel events
            asset_id=payload.get("host_ip", "unknown"),
            host=payload.get("host", "unknown"),
            hour_of_day=int(payload.get("hour_of_day", 12)),
            labels=(payload.get("event_type", "telemetry"),),
            company=payload.get("environment", "default"),
        )
        constraints = CompanyConstraints()
        ai_result, decision = engine.evaluate(incident, constraints)
        
        # Publish live actions
        out = {"ai_result": asdict(ai_result), "decision": decision.to_dict()}
        await nc.publish("incidents.analyzed", json.dumps(out).encode())

    await nc.subscribe("incidents.scored", cb=handler)
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        await nc.drain()


def main() -> int:
    asyncio.run(run_nats())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
