from __future__ import annotations

import os
import secrets
from dataclasses import asdict
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from .core.engine import SecurityDecisionEngine
from .core.models import CompanyConstraints, IncidentContext
from .replay import replay_scenario
from .scenarios import load_scenarios

app = FastAPI(title="AGRUS Security AI Service")

allowed_origins_env = os.environ.get("AGRUS_ALLOWED_ORIGINS")
if allowed_origins_env:
    allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
else:
    allowed_origins = ["http://localhost:4200"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
engine = SecurityDecisionEngine()

security = HTTPBearer(auto_error=False)

def verify_token(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    expected_token = os.environ.get("AGRUS_INTERNAL_TOKEN")
    if (
        not expected_token
        or credentials is None
        or not credentials.credentials
        or not secrets.compare_digest(credentials.credentials, expected_token)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing authentication token"
        )
    return credentials.credentials



class ConstraintsInput(BaseModel):
    auto_response_threshold: Optional[float] = None
    minimum_risk_for_auto_response: Optional[float] = None
    approved_hours: Optional[List[int]] = None
    critical_environments: Optional[List[str]] = None
    critical_assets: Optional[List[str]] = None
    allowed_actions: Optional[List[str]] = None
    escalation_channel: Optional[str] = None


class IncidentInput(BaseModel):
    incident_id: str
    summary: str
    risk_score: float
    asset_id: Optional[str] = "unknown"
    host: Optional[str] = "unknown"
    hour_of_day: Optional[int] = 12
    labels: Optional[List[str]] = None
    company: Optional[str] = "default"
    constraints: Optional[ConstraintsInput] = None


@app.post("/analyze", dependencies=[Depends(verify_token)])
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
    constraints = _build_constraints(inc.constraints)
    ai_result, decision = await engine.evaluate_async(incident, constraints)

    return {
        "ai_result": asdict(ai_result),
        "decision": decision.to_dict(),
    }


def _build_constraints(payload: ConstraintsInput | None) -> CompanyConstraints:
    if payload is None:
        return CompanyConstraints()

    defaults = CompanyConstraints()
    data = payload.dict(exclude_none=True)
    if "approved_hours" in data:
        data["approved_hours"] = tuple(data["approved_hours"])
    if "critical_environments" in data:
        data["critical_environments"] = frozenset(data["critical_environments"])
    if "critical_assets" in data:
        data["critical_assets"] = frozenset(data["critical_assets"])
    if "allowed_actions" in data:
        data["allowed_actions"] = tuple(data["allowed_actions"])

    return CompanyConstraints(
        allowed_actions=data.get("allowed_actions", defaults.allowed_actions),
        auto_response_threshold=data.get("auto_response_threshold", defaults.auto_response_threshold),
        minimum_risk_for_auto_response=data.get("minimum_risk_for_auto_response", defaults.minimum_risk_for_auto_response),
        critical_environments=data.get("critical_environments", defaults.critical_environments),
        critical_assets=data.get("critical_assets", defaults.critical_assets),
        approved_hours=data.get("approved_hours", defaults.approved_hours),
        escalation_channel=data.get("escalation_channel", defaults.escalation_channel),
    )


from .features.remediation import CodeRemediationEngine
from .features.scanners import scan_directory

remediation_engine = CodeRemediationEngine()

class ScanRequest(BaseModel):
    repo_path: str

class RemediateRequest(BaseModel):
    repo_path: str

@app.post("/scan", dependencies=[Depends(verify_token)])
async def scan(req: ScanRequest):
    findings = scan_directory(req.repo_path)
    return {
        "repo_path": req.repo_path,
        "findings": [
            {
                "file_path": f.file_path,
                "line_number": f.line_number,
                "vulnerability_type": f.vulnerability_type,
                "severity": f.severity,
                "code_snippet": f.code_snippet
            } for f in findings
        ]
    }

@app.post("/remediate", dependencies=[Depends(verify_token)])
async def remediate(req: RemediateRequest):
    findings = scan_directory(req.repo_path)
    if not findings:
        return {"status": "success", "message": "No vulnerabilities found.", "pr_url": None}
    
    result = remediation_engine.create_pull_request(req.repo_path, findings)
    
    return {
        "status": "success",
        "message": "Remediation process completed.",
        "findings_count": len(findings),
        "result": result
    }

@app.get("/scenarios", dependencies=[Depends(verify_token)])
async def scenarios():
    return {"scenarios": [scenario.to_dict() for scenario in load_scenarios()]}

@app.post("/scenarios/{scenario_id}/run", dependencies=[Depends(verify_token)])
async def run_scenario(scenario_id: str):
    scenario = next((scenario for scenario in load_scenarios() if scenario.scenario_id == scenario_id), None)
    if scenario is None:
        return {"error": "scenario not found", "scenario_id": scenario_id}
    return replay_scenario(scenario, engine=engine)




from .features.baselines import BaselineEngine

@app.get("/baselines", dependencies=[Depends(verify_token)])
async def list_baselines():
    """List all entities with behavioral baselines."""
    be = engine.llm.baseline_engine
    entities = be.list_entities()
    return {
        "entity_count": len(entities),
        "entities": [
            {
                "entity_id": eid,
                "event_count": be.get_baseline(eid).event_count if be.get_baseline(eid) else 0,
            }
            for eid in entities
        ]
    }

@app.get("/baselines/{entity_id}", dependencies=[Depends(verify_token)])
async def get_baseline(entity_id: str):
    """Get the full behavioral baseline for an entity."""
    be = engine.llm.baseline_engine
    b = be.get_baseline(entity_id)
    if b is None:
        return {"error": "No baseline found", "entity_id": entity_id}
    return {
        "entity_id": b.entity_id,
        "event_count": b.event_count,
        "days_observed": round((b.last_seen - b.first_seen) / 86400, 1) if b.last_seen > b.first_seen else 0,
        "hour_histogram": dict(b.hour_histogram),
        "top_processes": dict(sorted(b.process_freq.items(), key=lambda x: -x[1])[:10]),
        "top_ips": dict(sorted(b.ip_freq.items(), key=lambda x: -x[1])[:10]),
        "event_types": dict(b.event_types),
    }

class DeviationRequest(BaseModel):
    entity_id: str
    hour: int
    process: Optional[str] = None
    ip: Optional[str] = None

@app.post("/baselines/deviation", dependencies=[Depends(verify_token)])
async def check_deviation(req: DeviationRequest):
    """Check how much a specific behavior deviates from an entity's baseline."""
    be = engine.llm.baseline_engine
    return be.get_deviation(req.entity_id, req.hour, req.process, req.ip)




@app.get("/correlations", dependencies=[Depends(verify_token)])
async def get_correlations():
    """Get all active multi-stage attack correlations."""
    ce = engine.llm.correlation_engine
    correlations = ce.get_active_correlations()
    return {
        "active_correlations": len(correlations),
        "correlations": [
            {
                "correlation_id": c.correlation_id,
                "entity": c.entity,
                "severity": c.severity,
                "kill_chain_stages": c.kill_chain_stages_hit,
                "kill_chain_coverage": c.kill_chain_coverage,
                "time_span_hours": c.time_span_hours,
                "event_count": len(c.events),
                "summary": c.summary,
            }
            for c in correlations
        ]
    }

@app.get("/timeline/{entity}", dependencies=[Depends(verify_token)])
async def get_timeline(entity: str):
    """Get the chronological attack timeline for an entity."""
    ce = engine.llm.correlation_engine
    timeline = ce.get_timeline(entity)
    return {
        "entity": entity,
        "event_count": len(timeline),
        "timeline": timeline,
    }




from .features.container import list_containers, quarantine_container, kill_container

@app.get("/containers", dependencies=[Depends(verify_token)])
async def get_containers():
    """List all running containers on this host."""
    containers = list_containers()
    return {
        "container_count": len(containers),
        "containers": [
            {
                "id": c.container_id,
                "name": c.name,
                "image": c.image,
                "status": c.status,
                "pid": c.pid,
            }
            for c in containers
        ]
    }

class ContainerActionRequest(BaseModel):
    container_id: str

@app.post("/containers/quarantine", dependencies=[Depends(verify_token)])
async def api_quarantine_container(req: ContainerActionRequest):
    """Quarantine a container: disconnect from all networks and pause."""
    return quarantine_container(req.container_id)

@app.post("/containers/kill", dependencies=[Depends(verify_token)])
async def api_kill_container(req: ContainerActionRequest):
    """Force-kill a running container."""
    return kill_container(req.container_id)

