from __future__ import annotations

from dataclasses import asdict
from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .engine import SecurityDecisionEngine
from .models import CompanyConstraints, IncidentContext
from .replay import replay_scenario
from .scenarios import load_scenarios

app = FastAPI(title="AISOS Security AI Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
engine = SecurityDecisionEngine()


class IncidentInput(BaseModel):
    incident_id: str
    summary: str
    risk_score: float
    asset_id: Optional[str] = "unknown"
    host: Optional[str] = "unknown"
    hour_of_day: Optional[int] = 12
    labels: Optional[List[str]] = None
    company: Optional[str] = "default"


@app.post("/analyze")
async def analyze(inc: IncidentInput):
    incident = IncidentContext(
        incident_id=inc.incident_id,
        summary=inc.summary,
        risk_score=inc.risk_score,
        asset_id=inc.asset_id or "unknown",
        host=inc.host or "unknown",
        hour_of_day=inc.hour_of_day or 12,
        labels=tuple(inc.labels or ()),
        company=inc.company or "default",
    )
    constraints = CompanyConstraints()
    ai_result, decision = engine.evaluate(incident, constraints)

    return {
        "ai_result": asdict(ai_result),
        "decision": decision.to_dict(),
    }


@app.get("/scenarios")
async def scenarios():
    return {"scenarios": [scenario.to_dict() for scenario in load_scenarios()]}


@app.post("/scenarios/{scenario_id}/run")
async def run_scenario(scenario_id: str):
    scenario = next((scenario for scenario in load_scenarios() if scenario.scenario_id == scenario_id), None)
    if scenario is None:
        return {"error": "scenario not found", "scenario_id": scenario_id}
    return replay_scenario(scenario, engine=engine)
