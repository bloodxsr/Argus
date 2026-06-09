# Security AI Agent

The core reasoning brain of AISOS. A domain-specialized AI that thinks like a senior security analyst — not a general-purpose chatbot.

## Related Notes
- [[Decision Engine]]
- [[Investigation Agent]]
- [[Threat Intelligence Agent]]
- [[Risk Assessment Agent]]
- [[Implementation Blueprint]]

---

## What It Is

A fine-tuned language model trained exclusively on security data, combined with a retrieval system over live threat intelligence. It does not know how to write poetry, summarize articles, or help with code. It only knows security.

This is the key architectural difference from competitors who use GPT-4 or Claude directly. A general LLM reasons from generic priors. This agent reasons from:

- Every MITRE ATT&CK tactic, technique, and sub-technique
- 200,000+ CVE entries with CVSS scores and exploit context
- Real-world incident reports (DFIR reports, threat actor TTPs)
- Historical AISOS incidents and analyst decisions
- Live threat intelligence feeds (abuse.ch, OTX, VirusTotal)

---

## Architecture

```text
Incident Context
      │
      ▼
    Layered Retrieval
    (MITRE + CVE + past incidents + policy context)
      │
      ▼
    Local LLM Backend
    (Ollama-compatible chat server or self-hosted vLLM)
      │
      ▼
    Critique / Policy Layer
    (internal safety pass + company constraints)
      │
      ▼
  Structured Output
  (JSON — action, confidence, reasoning)
```

### Why RAG + Fine-tune (not just one or the other)

Fine-tuning alone gives security reasoning but stale knowledge. Retrieval alone gives current data but poor reasoning quality. Combined: good reasoning + always-current threat context.

The current Python implementation mirrors Ollama's local-serving style:

- a prompt builder that packages system + user messages
- a chat backend that can call `http://localhost:11434/api/chat`
- a deterministic fallback backend for offline evaluation
- a policy-aware decision engine that sits after model inference

---

## Training Data Sources

| Source | What It Provides |
|---|---|
| MITRE ATT&CK STIX bundle | Tactics, techniques, mitigations |
| NVD / CVE JSON feeds | Vulnerability context, CVSS scores |
| CISA KEV catalog | Actively exploited vulnerabilities |
| abuse.ch datasets | Live malware IOCs |
| Mandiant / CrowdStrike threat reports (public) | Real APT TTPs |
| AISOS incident history | Platform-specific learned context |

---

## Implementation Plan

### Step 1 — Base Model

Start with `mistral-7b-instruct` or `phi-3-mini` (smaller, faster, enough for structured classification).

### Step 2 — Dataset Construction

```python
# Format: instruction-response pairs
{
  "instruction": "Process /tmp/x.sh spawned by nginx. Connected to 185.x.x.x. Parent PID is www-data.",
  "response": {
    "classification": "Webshell execution",
    "mitre_technique": "T1059.004",
    "confidence": 0.91,
    "recommended_action": "kill_process + block_ip + isolate_container",
    "reasoning": "Nginx spawning shell scripts is abnormal. External IP contact post-execution indicates C2 beaconing."
  }
}
```

Construct 10,000+ such pairs from MITRE ATT&CK examples, public DFIR reports, and synthetic generation.

### Step 3 — Fine-tuning

```bash
# Using LLaMA-Factory or Axolotl
axolotl train security_finetune.yaml

# LoRA fine-tune — keeps compute cost low
# Target: 4-bit quantized, runs on single A10G
```

### Step 4 — RAG Layer

```python
# Embed MITRE ATT&CK + CVE data into vector store
# Pinecone or Qdrant
# On each incident, retrieve top-5 relevant techniques
# Inject into model prompt as context
```

### Step 5 — Inference Server

```bash
# Self-hosted via vLLM
vllm serve aisos-security-7b --quantization awq --max-model-len 4096

# Or for MVP: call Mistral API with system prompt built from security KB
```

---

## Input / Output Schema

### Input

```json
{
  "incident_id": "inc_abc123",
  "event_summary": "Process /tmp/malware spawned by bash. Connected to known C2 IP.",
  "risk_score": 82,
  "timeline": [...],
  "retrieved_techniques": ["T1059", "T1071.001"],
  "asset_context": {
    "host": "prod-server-01",
    "role": "web_server",
    "criticality": "high"
  }
}
```

### Output

```json
{
  "classification": "Remote Code Execution + C2 Beaconing",
  "confidence": 0.93,
  "mitre_techniques": ["T1059.004", "T1071.001"],
  "recommended_action": "kill_process",
  "escalate_to_human": false,
  "reasoning": "Execution from /tmp is a known evasion pattern. C2 IP matches Cobalt Strike infrastructure. High-confidence automated kill appropriate."
}
```

---

## Why Not Just Use GPT-4

| Criteria | GPT-4 | Security AI Agent |
|---|---|---|
| Security reasoning depth | Generic | Expert-level |
| Inference cost | $0.03/1k tokens | Near-zero (self-hosted) |
| Data privacy | Cloud, your incidents leave your network | Fully on-prem |
| Latency | 2-5 seconds | <500ms (local GPU) |
| Customizable | No | Full control |
| Learns from your incidents | No | Yes (continuous fine-tune) |

---

## Scalability

For MVP: call Mistral API with a structured security system prompt. Cheap, fast enough.

For production: self-hosted vLLM on a single A10G GPU handles ~200 concurrent requests. Multiple GPU nodes behind a load balancer handles enterprise scale.

Fine-tune cadence: retrain monthly on new AISOS incident data + analyst corrections. This is the feedback loop that makes the model smarter over time on your specific infrastructure.

---

## Integration Examples

Two clean integration patterns are supported: a FastAPI HTTP endpoint (quick demo) and a NATS subscriber (production/event-bus).

### FastAPI (Demo)

Run a small HTTP service that accepts `POST /analyze` and returns the structured JSON output. Example (Python):

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class IncidentInput(BaseModel):
  incident_id: str
  summary: str
  risk_score: float

@app.post("/analyze")
async def analyze(inc: IncidentInput):
  # construct IncidentContext and call SecurityDecisionEngine.evaluate
  # return {"ai_result": ..., "decision": ...}
  pass
```

Run with `uvicorn security_ai_service.api:app --reload --port 8000` and point the Rust Decision Engine to `http://security-ai:8000/analyze` for synchronous analysis in demos.

### NATS (Production / Event Bus)

Subscribe to `incidents.scored` and publish results to `incidents.analyzed`. This keeps the AI agent decoupled and resilient.

Example (Python async subscriber):

```python
import asyncio
import json
from nats.aio.client import Client as NATS

async def handler(msg):
  incident = json.loads(msg.data)
  # call engine.evaluate and publish to incidents.analyzed

async def main():
  nc = NATS()
  await nc.connect("nats://127.0.0.1:4222")
  await nc.subscribe("incidents.scored", cb=handler)
  await asyncio.Event().wait()

asyncio.run(main())
```

This approach ensures events queue if the Python service is down and aligns with the project's event-driven architecture.

