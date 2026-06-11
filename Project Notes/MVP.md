# MVP Scope

What gets built for the hackathon demo. Every item here must be demoable live in front of judges.

## Related Notes
- [[Monitoring Agent]]
- [[Investigation Agent]]
- [[Risk Assessment Agent]]
- [[Response Agent]]
- [[Security AI Agent]]

---

## MVP Feature Set

1. Synthetic attack event generator (replaces real eBPF for demo)
2. NATS event bus with defined topic structure
3. Monitoring Agent (Rust) — normalize, deduplicate, flag anomalies
4. Investigation Agent (Rust) — process tree, timeline, basic context
5. Risk scoring engine — formula-based, no AI for MVP
6. Security AI Agent — MVP uses Mistral API with security system prompt
7. Response Agent — simulated actions (log "would kill PID X" for safety)
8. Real-time dashboard — WebSocket, shows live pipeline firing
9. Human review queue — analyst approval UI for Medium-risk incidents
10. Audit log — every action recorded

---

## What Is Explicitly Out of Scope for MVP

- Real eBPF kernel probes (use synthetic generator)
- Real process kill / IP block (simulate in logs)
- ClickHouse (use PostgreSQL for everything)
- Fine-tuned model (use Mistral API with security prompt)
- Kubernetes integration (Docker only)
- Learning Agent / feedback loop
- Multi-host deployment

---

## Demo Scenario (Run This Live)

One scripted attack sequence. 90 seconds. Judges see the full pipeline fire.

```
T+0s   Synthetic generator starts
T+3s   nginx spawns /bin/bash  [Monitoring Agent flags: parent anomaly]
T+5s   bash spawns /tmp/x.sh   [Investigation Agent: builds process tree]
T+8s   x.sh reads /etc/passwd  [Threat Intel: file access + process anomaly]
T+12s  x.sh connects to 185.x.x.x:4444  [TI Agent: IOC match — known C2 IP]
T+15s  Risk score computed: 82 → HIGH
T+16s  Security AI: "Cobalt Strike C2 beacon, T1071.001, confidence 0.93"
T+17s  Decision Engine: auto_respond
T+18s  Response Agent: "KILLED PID 1002 on demo-server" [appears in dashboard]
T+20s  Dashboard shows: incident card, timeline, risk score, action taken
T+25s  Generate a MEDIUM risk event → analyst review card appears
T+30s  Presenter clicks APPROVE → action executes
       Presenter clicks REJECT → false positive logged
```

Dashboard shows everything live as it happens.

---

## Build Plan (4 Days)

### Day 1
- NATS setup + Docker Compose
- Unified event schema (Rust structs + serde)
- Synthetic event generator (Python script)
- PostgreSQL schema: incidents, assets, action_log

### Day 2
- Monitoring Agent (Rust)
- Investigation Agent (Rust)
- Threat Intelligence Agent — hardcode 5 known-bad IOCs for demo

### Day 3
- Risk Assessment Agent (Rust)
- Security AI integration (Mistral API, security system prompt)
- Decision Engine (OPA + Rust glue)
- Response Agent (simulate actions, write to DB)

### Day 4
- Dashboard (Next.js or Axum + HTMX)
- WebSocket real-time pipeline visualization
- Human review queue UI
- End-to-end demo scenario testing
- Polish

---

## Presenting to Judges

### The Pitch (60 seconds)

> "SOC analysts deal with 10,000 alerts a day. They miss real threats. AGRUS reduces that to 12 decisions per day — only the ones that actually need human judgment. Everything else is handled autonomously with a domain-specialized security AI. Not GPT-4. Not rules. A model trained to think like a senior security analyst."

### The Demo (90 seconds)

Run the scripted attack scenario live. Point to the dashboard:

1. "This is the event pipeline — watch it fire in real time."
2. "An anomaly is detected. Our Investigation Agent reconstructs the attack chain automatically."
3. "Threat intel confirms this IP is Cobalt Strike infrastructure."
4. "Risk score: 82. Our security AI confirms the classification at 93% confidence."
5. "System acts autonomously. Process killed. Logged. Human can audit or rollback."
6. "Here's a medium-risk event — analyst reviews, approves, action executes."

### Likely Judge Questions

**"How is this different from CrowdStrike?"**
> CrowdStrike detects and pages a human. AGRUS detects, investigates, decides, and acts. The human audits, not approves. Different operational model entirely.

**"Isn't full automation dangerous?"**
> That's why we have three tiers. High risk acts autonomously with a post-action audit trail. Medium risk requires human approval. Low risk is silent. Compliance requirements are met. Legal accountability is preserved.

**"What's your Security AI trained on?"**
> MITRE ATT&CK, 200,000 CVEs, real incident reports, and Cobalt Strike/APT TTPs. It's not a chatbot — it's a security analyst in a model. For MVP we use Mistral with a structured security prompt. Production ships a fine-tuned 7B model that runs on-prem.

**"Can it handle false positives?"**
> Yes. Every analyst rejection feeds back to the learning agent. The model improves on your specific infrastructure over time. Day 1 it's generic. Month 6 it knows your normal.
