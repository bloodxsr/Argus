from __future__ import annotations

from dataclasses import asdict
from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .core.engine import SecurityDecisionEngine
from .core.models import CompanyConstraints, IncidentContext
from .replay import replay_scenario
from .scenarios import load_scenarios

app = FastAPI(title="AGRUS Security AI Service")
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


from .features.remediation import CodeRemediationEngine
from .features.scanners import scan_directory

remediation_engine = CodeRemediationEngine()

class ScanRequest(BaseModel):
    repo_path: str

class RemediateRequest(BaseModel):
    repo_path: str

@app.post("/scan")
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

@app.post("/remediate")
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

@app.get("/scenarios")
async def scenarios():
    return {"scenarios": [scenario.to_dict() for scenario in load_scenarios()]}

@app.post("/scenarios/{scenario_id}/run")
async def run_scenario(scenario_id: str):
    scenario = next((scenario for scenario in load_scenarios() if scenario.scenario_id == scenario_id), None)
    if scenario is None:
        return {"error": "scenario not found", "scenario_id": scenario_id}
    return replay_scenario(scenario, engine=engine)


# ── UEBA Baseline Endpoints ────────────────────────────────────

from .features.baselines import BaselineEngine

@app.get("/baselines")
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

@app.get("/baselines/{entity_id}")
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

@app.post("/baselines/deviation")
async def check_deviation(req: DeviationRequest):
    """Check how much a specific behavior deviates from an entity's baseline."""
    be = engine.llm.baseline_engine
    return be.get_deviation(req.entity_id, req.hour, req.process, req.ip)


# ── APT Correlation Endpoints ──────────────────────────────────

@app.get("/correlations")
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

@app.get("/timeline/{entity}")
async def get_timeline(entity: str):
    """Get the chronological attack timeline for an entity."""
    ce = engine.llm.correlation_engine
    timeline = ce.get_timeline(entity)
    return {
        "entity": entity,
        "event_count": len(timeline),
        "timeline": timeline,
    }


# ── Container Runtime Security Endpoints ───────────────────────

from .features.container import list_containers, quarantine_container, kill_container

@app.get("/containers")
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

@app.post("/containers/quarantine")
async def api_quarantine_container(req: ContainerActionRequest):
    """Quarantine a container: disconnect from all networks and pause."""
    return quarantine_container(req.container_id)

@app.post("/containers/kill")
async def api_kill_container(req: ContainerActionRequest):
    """Force-kill a running container."""
    return kill_container(req.container_id)

