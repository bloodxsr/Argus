# Project Outcomes and Implementation Plan

## Purpose

This note converts the current AISOS notes into concrete project directions and a build plan for the three-repo structure:

- Test Website
- Core Agent / Security AI Service
- Report and Result Website

## Related Notes

- [[00 - Project Vision]]
- [[01 - System Architecture]]
- [[Implementation Blueprint]]
- [[Shared_Contracts]]
- [[Security AI Agent]]
- [[Risk Engine]]
- [[Decision Engine]]
- [[Autonomous Response]]
- [[Market Analysis]]
- [[Project_checkpoints/0004_project_direction_and_model_integrity]]

---

## What We Are Making

AISOS is an AI-native cybersecurity risk management and response platform.

The core promise is:

```text
Detect -> Investigate -> Risk Score -> Decide -> Respond -> Learn -> Human Audit
```

The system reduces repetitive human review by letting the AI triage and act within policy. Humans remain on the loop for audit, approvals, escalation, and correction.

## Best Project Framing

The strongest hackathon framing is:

> An autonomous SOAR and endpoint/container response platform that uses AI reasoning, behavioral memory, risk scoring, and policy gates to reduce SOC analyst workload.

This is stronger than saying only "cybersecurity AI" because it names the buyer pain:

- too many alerts
- slow human response
- static playbooks
- alert fatigue
- fragmented endpoint, container, and cloud telemetry
- weak auditability for automated actions

## Possible Project Outcomes

### Outcome 1 - Hackathon Demo MVP

Build a polished demo where a test website generates simulated attacks, the AI service decides what to do, and a report site shows the audit trail.

Best for:
- hackathon judging
- investor-style demo
- proving the workflow

Core features:
- synthetic attack generator
- incident pipeline visualization
- AI classification
- risk score
- policy-safe decision
- human approval for medium risk
- automatic response for high risk
- final report timeline

### Outcome 2 - AI-Native SOAR

Position AISOS as a replacement for static SOAR playbooks.

Best for:
- enterprise security operations
- SOC teams
- automation buyers

Core features:
- event bus
- incident grouping
- investigation timeline
- model-generated action recommendation
- policy engine
- response execution
- rollback/audit system

Main differentiator:
- the AI infers the playbook instead of requiring humans to write every playbook manually.

### Outcome 3 - Lightweight EDR Prototype

Focus the project around endpoint visibility and response.

Best for:
- technical credibility
- systems/security engineering demo
- Rust/eBPF roadmap

Core features:
- process telemetry
- syscall/file/network signals
- process tree reconstruction
- suspicious behavior detection
- kill process / isolate host actions

Main differentiator:
- kernel-level visibility plus AI-decided response.

### Outcome 4 - Container Runtime Security

Focus on Docker/Kubernetes workloads.

Best for:
- cloud-native teams
- DevSecOps use cases
- demos with visible isolation actions

Core features:
- container behavior monitoring
- namespace/pod metadata
- anomalous process detection
- quarantine container
- kill malicious process
- report blast radius

Main differentiator:
- tools like Falco detect; AISOS can reason and act within policy.

### Outcome 5 - UEBA and Behavioral Risk Engine

Focus on baselining users, services, hosts, and containers.

Best for:
- long-term product moat
- anomaly detection
- reducing false positives

Core features:
- normal login/process/network profiles
- deviation scoring
- entity risk memory
- feedback from human corrections
- drift detection

Main differentiator:
- behavior memory is built into the response pipeline, not bolted on afterward.

### Outcome 6 - APT Investigation Assistant

Focus on catching slow, multi-stage attacks.

Best for:
- advanced threat hunting
- high-end security positioning
- demos using multi-step incident replay

Core features:
- long incident timelines
- MITRE ATT&CK mapping
- lateral movement detection
- historical incident memory
- cross-host context graph

Main differentiator:
- memory plus timeline reasoning gives the AI a better chance of catching slow attacks.

### Outcome 7 - Compliance and Audit Automation

Focus on explainable security decisions.

Best for:
- regulated companies
- conservative enterprise adoption
- report/result website differentiation

Core features:
- why the AI acted
- policy constraints applied
- human approvals
- rollback trail
- incident export
- compliance-ready evidence

Main differentiator:
- autonomy is paired with accountability.

## Recommended Outcome

For the current stage, build Outcome 1 first, while designing it so it naturally grows into Outcome 2.

That means:

- demo like a complete product
- implement only the minimum real automation needed
- keep schemas stable
- make every action auditable
- make the AI explainable through structured fields, not hidden chain-of-thought

This gives the strongest near-term result without pretending the full eBPF/EDR/APT product is already complete.

---

## Three-Repo Plan

The three-repo split is good if shared contracts are treated as sacred.

### Repo 1 - Test Website

Purpose:
- simulate attacks and benign activity
- let judges/users trigger scenarios
- visualize the pipeline as events move through the system

Recommended stack:
- MERN: MongoDB, Express, React, Node.js
- Vite React client
- Express API wrapper around the Python Security AI service
- MongoDB for replay sessions
- WebSocket/SSE connection to live pipeline later
- scenario fixtures stored as JSON

Major screens:
- attack scenario launcher
- live pipeline view
- incident detail view
- human review queue

### Repo 2 - Core Agent / Security AI

Purpose:
- own the real workflow and decision logic
- receive telemetry
- create incidents
- enrich context
- calculate risk
- call the Security AI
- apply company constraints
- emit response/audit records

Current repo already contains:
- Python Security AI service
- structured AIResult and Decision models
- Ollama-compatible backend path
- heuristic fallback
- retrieval fallback
- evaluation harness
- critic verifier
- FastAPI/NATS integration examples
- training skeleton

Future production pieces:
- Rust telemetry agents
- eBPF sensors
- event bus workers
- persistent stores
- response executor
- learning/memory system

### Repo 3 - Report / Result Website

Purpose:
- show what happened
- prove why the AI acted
- expose audit, approvals, and rollback history

Recommended stack:
- MERN: MongoDB, Express, React, Node.js
- Vite React client
- Express API wrapper around the Python Security AI service
- MongoDB for generated report snapshots
- exportable incident reports

Major screens:
- incident history
- risk breakdown
- AI decision explanation
- action history
- human approvals/rejections
- rollback status
- project checkpoint timeline

---

## Shared Contract Strategy

Create a shared package or generated schema used by all repos.

Recommended options:

1. JSON Schema as the source of truth
2. Python dataclasses / Pydantic models generated from schema
3. TypeScript types generated from schema
4. Rust structs generated or manually mirrored with contract tests

Minimum shared objects:
- UnifiedEvent
- Incident
- EnrichedIncident
- RiskScore
- AIResult
- Decision
- ActionRecord
- ReviewDecision
- CheckpointEntry

See [[Shared_Contracts]].

---

## Model Integrity Check

Current state:

- The core Security AI pipeline is internally coherent.
- Unit tests pass.
- The service produces structured outputs.
- The decision engine applies company constraints before auto-response.
- A critic verifier checks schema and simple safety consistency.
- Retrieval has a Qdrant path and a deterministic fallback.
- Ollama can be used when configured; otherwise the heuristic backend keeps demos stable.

Verified on 2026-06-09:

```text
python -m unittest discover -s tests
Ran 11 tests
OK
```

Important limitation:

- The current model is not yet a trained custom security model.
- The heuristic backend is fast and deterministic, but it does not truly learn.
- The LoRA training script is a scaffold, not a fully validated production training pipeline.
- There is no online learning loop that updates behavior from analyst feedback yet.
- "Huge thinking capability" currently comes from prompt structure, retrieval, and layered evaluation, not from a larger reasoning model.

Small integrity fix made:

- `train/fine_tune_lora.py` now imports `json`, which is required by the training text conversion path.

## Model Roadmap

### Phase 1 - Stable Reasoning Shell

Keep the current deterministic shell:
- schema validation
- policy constraints
- critic verifier
- evaluation cases
- retrieval context
- audit trail

This makes the AI safe enough to demo.

### Phase 2 - Strong Local LLM

Use Ollama or vLLM with a security prompt profile.

Target behavior:
- valid JSON every time
- no hidden chain-of-thought leakage
- calibrated confidence
- safe escalation on ambiguity
- MITRE mapping accuracy

### Phase 3 - Retrieval-Augmented Security Memory

Back retrieval with Qdrant.

Data sources:
- MITRE ATT&CK
- CVE/NVD summaries
- internal incident reports
- company policies
- past human corrections

### Phase 4 - Fine-Tuned Security Model

Fine-tune a base model with LoRA on:
- synthetic incident cases
- labeled attack scenarios
- benign operations
- policy-boundary examples
- prompt injection examples
- analyst correction examples

### Phase 5 - Learning Agent

Add learning without unsafe live self-modification:
- store analyst corrections
- update entity baselines
- update retrieval memory
- add failed cases to evaluation suite
- retrain/fine-tune only through controlled release cycles

---

## Implementation Plan

### Milestone 1 - Contracts and Repo Boundaries

Deliverables:
- finalize JSON schemas for shared contracts
- generate TypeScript types for websites
- align Python dataclasses with schemas
- add contract tests

Done when:
- test website, agent, and report website agree on event and decision shapes.

### Milestone 2 - Synthetic Scenario Engine

Deliverables:
- create attack fixtures
- create benign activity fixtures
- create mixed/ambiguous fixtures
- replay fixtures into the agent pipeline

Scenarios:
- RCE + C2 beaconing
- benign backup
- suspicious container process
- impossible travel login
- lateral movement across hosts
- prompt injection attempt
- ransomware-like file behavior

### Milestone 3 - Core Agent Pipeline

Deliverables:
- API endpoint to accept UnifiedEvent
- incident grouping
- risk score calculation
- Security AI analysis
- decision engine result
- action record emission

Pipeline:

```text
UnifiedEvent -> Incident -> EnrichedIncident -> RiskScore -> AIResult -> Decision -> ActionRecord
```

### Milestone 4 - Response Simulator

Deliverables:
- safe simulated actions first
- no destructive host actions in demo mode
- rollback metadata
- approval gates

Actions:
- observe
- recommend
- block_ip_simulated
- kill_process_simulated
- quarantine_container_simulated
- isolate_host_simulated

### Milestone 5 - Test Website

Deliverables:
- scenario launcher
- live event feed
- pipeline visualization
- human review UI
- approve/reject controls

Demo goal:
- user triggers an attack and sees the AI decide/respond in seconds.

### Milestone 6 - Report Website

Deliverables:
- incident report page
- risk and confidence breakdown
- action history
- human review history
- rollback state
- checkpoint timeline from markdown metadata

Demo goal:
- after the attack, the result site explains exactly what happened.

### Milestone 7 - Memory and Learning

Deliverables:
- feedback records from human review
- entity behavior baseline table
- retrieval ingestion for corrections
- evaluation case generation from mistakes

Safety rule:
- learning updates memory and future evaluations first, not live model weights.

### Milestone 8 - Real Telemetry Track

Deliverables:
- Rust/eBPF proof of concept
- process tree events
- container metadata
- OpenTelemetry support
- local NATS topic integration

This can run in parallel after the hackathon MVP is stable.

---

## Build Order for the Current Repo

1. Add JSON schemas for shared contracts. Done in [[Project_checkpoints/0005_shared_contracts_and_scenarios]].
2. Add an API route that accepts a synthetic incident and returns AIResult + Decision. Done.
3. Expand evaluation cases to include containers, UEBA, APT, and prompt injection. Done.
4. Add sample scenario JSON files for the test website. Done.
5. Add report-friendly ActionRecord and ReviewDecision objects. Done.
6. Add a markdown checkpoint after each meaningful change. Ongoing.

## Immediate Next Step

Add a small front-end demo or CLI replay command that streams scenario events through the pipeline in order.
