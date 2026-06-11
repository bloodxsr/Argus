# Strategy, Vision & Market

AGRUS is an autonomous B2B cybersecurity platform designed to protect cloud infrastructure, managed hosting environments, and large-scale Kubernetes clusters. It monitors, investigates, responds, and learns from security incidents in real time.

## Core Vision
AGRUS transforms enterprise cybersecurity from a reactive `Alert → Human → Decision → Action` pipeline into an autonomous `Detect → Investigate → Decide → Act → Human Audits` flow.
By utilizing a proprietary, domain-specialized Security AI reasoning engine, AGRUS collapses the traditional alert volume from 10,000+ daily alerts to a handful of high-confidence escalations. 

### Operating Model: Human-on-the-Loop
AGRUS removes humans from every alert, but preserves them for critical oversight:
- **Low Risk:** System observes and logs. Analyst is not interrupted.
- **Medium Risk:** System recommends action. Human approves or rejects.
- **High Risk:** System acts immediately (e.g., isolates container, blocks IP). Human audits post-action.

This ensures that legal accountability and compliance (SOC 2, ISO 27001) are strictly maintained while unlocking the speed of autonomous defense.

---

## Market Positioning

AGRUS targets Cloud Infrastructure Providers, DevOps, and SRE teams managing extensive server networks.

**Why AGRUS Wins:**
1. **Autonomous Response with Human-on-the-Loop:** Unlike CrowdStrike or SentinelOne, which predominantly detect and require humans to execute playbooks, AGRUS detects, scores, decides, and acts autonomously with built-in audit trails.
2. **Domain-Specialized Security AI:** Competitors rely on generic LLMs (GPT-4) which are costly and have weak security priors. AGRUS utilizes a fine-tuned, on-prem Llama-3.1-8B foundation model trained exclusively on MITRE ATT&CK, CVE data, and real incident reports.
3. **Full Stack Architecture:** From kernel-level eBPF telemetry to automated code remediation PRs, AGRUS consolidates detection, posture, and response into a single, open-standards platform (NATS, OPA, OpenTelemetry).

**Target Market Expansion:**
- **Initial Wedge:** Startups and mid-market companies utilizing Kubernetes that cannot afford a large SOC team.
- **Enterprise Expansion:** SOC augmentation for large enterprises drowning in alert fatigue.

---

## Minimum Viable Product (MVP) Scope

For initial hackathon and demonstration purposes, the MVP implements the core pipeline:
1. **Synthetic Telemetry:** A synthetic attack event generator simulates a live attack in 90 seconds (replaces full eBPF for fast demoing).
2. **Core Pipeline:** The NATS event bus orchestrates the Monitoring Agent, Investigation Agent, and Risk Assessment Engine.
3. **AI Integration:** The Security AI Agent utilizes an API-based LLM with a highly structured security system prompt to classify the attack.
4. **Demonstrable Response:** The Response Agent simulates actions (logging its intent to kill or isolate), which appear live on the MERN real-time dashboard.
5. **Human Review Queue:** Demonstrates the Analyst UI for medium-risk incidents, feeding decisions back into the pipeline.

**Out of Scope for MVP:** Real eBPF kernel probes, live process killing, custom foundation model deployment, and multi-host deployment. These are reserved for the production enterprise rollout.
