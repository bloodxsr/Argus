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

## Implementation Plan (Custom Foundation Model)

We have pivoted away from fine-tuning generic models (like Mistral-7B). The system now runs on a completely custom, proprietary **~3 Billion Parameter Foundation Model** built from scratch in PyTorch.

### Step 1 — Custom Tokenizer
Standard tokenizers destroy IP addresses and hex codes. We train a Custom Byte-Level BPE Tokenizer (`train/train_custom_tokenizer.py`) strictly on server logs, eBPF traces, and JSON. 

### Step 2 — Custom 3B Architecture
We implemented a highly scalable Decoder-Only Transformer (`train/custom_transformer.py`) featuring:
- **Flash Attention 2**: O(N) memory scaling to handle 8192-token context windows (massive server logs).
- **Grouped Query Attention (GQA)**: For sub-500ms inference times.
- **Rotary Position Embeddings (RoPE)**: For seamless length extrapolation.

### Step 3 — Pre-Training
The model is pre-trained from scratch on terabytes of raw unstructured cybersecurity data (Nginx logs, PCAPs, Windows Events, DFIR reports). It does not learn generic English; it only learns the physics of cyber attacks.

### Step 4 — Alignment (SFT)
Once the foundation is solid, the model is Supervised Fine-Tuned (SFT) using the `IncidentReport` history from our MongoDB database to output the exact JSON schemas expected by the `SecurityDecisionEngine`.

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

