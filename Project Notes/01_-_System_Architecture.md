# System Architecture

## Related Notes
- [[Telemetry Layer]]
- [[Event Bus]]
- [[Monitoring Agent]]
- [[Risk Assessment Agent]]
- [[Response Agent]]
- [[Security AI Agent]]
- [[Implementation Blueprint]]
- [[Shared_Contracts]]
- [[Project_checkpoints/0001_kickoff]]

---

## Full Pipeline

```text
Infrastructure (servers, containers, VMs)
            │
            ▼
    Telemetry Sensors
    (eBPF + Auditd + OTel)
            │
            ▼
        Event Bus
        (NATS → Kafka at scale)
            │
            ▼
    Monitoring Agent
    (normalize, deduplicate, anomaly flag)
            │
            ▼
  Investigation Agent
  (timeline, process tree, context graph)
            │
            ▼
Threat Intelligence Agent
(MITRE ATT&CK lookup, IP reputation, IOC match)
            │
            ▼
      Risk Agent
      (Impact × Confidence × Exposure / 10)
            │
            ▼
  Security AI Agent ← the custom brain
  (domain-specific reasoning, not a generic LLM)
            │
            ▼
    Decision Engine
    (policy + confidence → action)
            │
       ┌────┴────┐
       ▼         ▼
   Autonomous  Human
    Response   Review
   (High Risk) (Medium Risk)
            │
            ▼
     Learning Agent
     (feedback loop, false positive tracking)
            │
            ▼
      Memory System
      (PostgreSQL + ClickHouse)
```

---

## Scalability Architecture

### Phase 1 — MVP (Single Node)

```text
1 server
NATS (single node)
PostgreSQL (single instance)
Rust services (1 process per agent)
```

### Phase 2 — Production (Horizontal Scale)

```text
Agents       → stateless Rust binaries, scale via Docker replicas
Event Bus    → Kafka with partitioning by host_id
Telemetry DB → ClickHouse cluster (sharded by date + host)
Metadata DB  → PostgreSQL with read replicas
Security AI  → GPU inference server (vLLM or TGI), load balanced
Dashboard    → CDN-served Next.js, WebSocket via NATS JetStream
```

### Scaling Rule

Each agent is stateless. All state lives in:
- PostgreSQL (incidents, assets, policies, users)
- ClickHouse (event history, raw telemetry)
- Redis (short-term behavioral cache, session state)

This means any agent can die and restart without data loss. New instances pick up from the event bus where the previous one left off.

---

## Technology Stack

| Layer | MVP | Production |
|---|---|---|
| Agent runtime | Rust (tokio) | Rust (tokio) |
| Event bus | NATS | Kafka / Redpanda |
| Metadata store | PostgreSQL | PostgreSQL + read replicas |
| Telemetry store | PostgreSQL | ClickHouse cluster |
| Cache | — | Redis |
| AI inference | API call (Mistral) | Self-hosted vLLM |
| Dashboard | Axum + HTMX | Next.js + WebSocket |
| Deployment | Docker Compose | Kubernetes + Helm |

---

## Data Isolation

Each agent reads from and writes to specific topics only.

No agent calls another agent directly. All communication through the event bus.

This makes the system:
- Debuggable (replay any event stream)
- Testable (mock any agent by publishing fake events)
- Scalable (add consumers without changing producers)
