from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from security_ai_service.engine import SecurityDecisionEngine
from security_ai_service.models import CompanyConstraints, IncidentContext

app = FastAPI(title="AISOS Security AI Service")
engine = SecurityDecisionEngine()


class IncidentInput(BaseModel):
    incident_id: str
    summary: str
    risk_score: float
    asset_id: str | None = None
    host: str | None = None
    labels: list[str] | None = None
    hour_of_day: int | None = 12
    company: str | None = "default"


@app.post("/analyze")
async def analyze(incident: IncidentInput) -> Any:
    ctx = IncidentContext(
        incident_id=incident.incident_id,
        summary=incident.summary,
        risk_score=incident.risk_score,
        asset_id=incident.asset_id or "unknown",
        host=incident.host or "unknown",
        hour_of_day=incident.hour_of_day or 12,
        labels=tuple(incident.labels or ()),
        company=incident.company or "default",
    )
    ai_result, decision = engine.evaluate(ctx, CompanyConstraints())
    # Return structured JSON
    return {
        "ai_result": ai_result.__dict__ if hasattr(ai_result, "__dict__") else ai_result,
        "decision": decision.to_dict() if hasattr(decision, "to_dict") else decision,
    }
