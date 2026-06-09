# Market Analysis

## Related Notes
- [[00 - Project Vision]]
- [[Security AI Agent]]

---

## Competitors

| Company | What They Do | Key Weakness |
|---|---|---|
| CrowdStrike Falcon | EDR + threat hunting | Responses still require human approval in most deployments. No autonomous action. |
| SentinelOne | EDR + SOAR | Playbook-based automation — humans still write the playbooks. Not AI-native. |
| Wiz | Cloud security posture | Detection only. No response capability. No real-time runtime protection. |
| Splunk SOAR | Security orchestration | Playbook automation, not AI reasoning. Expensive. Complex to configure. |
| Palo Alto Cortex XSIAM | AI-driven SOC platform | General-purpose LLM integration. Not security-specialized AI. Priced for F500. |
| Falco (open source) | Container runtime security | Detection only. No response. No AI. |

---

## Where AISOS Wins

### 1. Autonomous Response with Human-on-the-Loop

CrowdStrike detects and alerts. AISOS detects, investigates, scores, decides, and acts — with a human auditing, not approving every action. This is a fundamentally different operational model.

### 2. Domain-Specialized Security AI

Every competitor uses either rule-based detection or a general-purpose LLM (GPT-4, Claude) bolted onto their existing pipeline. AISOS runs a fine-tuned security reasoning engine — trained exclusively on MITRE ATT&CK, CVE data, and real incident reports. It reasons like a senior analyst, not a chatbot.

This matters because:
- General LLMs have weak security priors
- General LLMs cost $0.03/1k tokens at scale — prohibitive
- General LLMs expose your incident data to third-party cloud providers
- A domain-specific model can be self-hosted, fast, cheap, and continuously improved on your own data

### 3. Full Stack: Telemetry → Response in One Platform

Wiz does posture. Falco does detection. SOAR does response. Customers buy all three, integrate them, and manage three vendors. AISOS is one platform from eBPF sensor to autonomous action. Fewer vendors, simpler architecture, lower total cost.

### 4. Open Architecture

Built on open standards: eBPF, OpenTelemetry, NATS/Kafka, OPA. Customers are not locked in to proprietary agents or data formats. Everything plugs into existing infrastructure.

---

## Target Market

**Initial wedge:** Startups and mid-market companies running Kubernetes. They have real security needs but cannot afford a 10-person SOC team. AISOS gives them autonomous protection with minimal headcount.

**Expansion:** Enterprise SOC augmentation. Large teams drowning in alerts. AISOS reduces analyst workload from 10,000 alerts/day to ~12 escalations/day.

---

## Positioning Statement

> AISOS is the only security platform with a domain-specialized AI reasoning engine — not a general LLM, not a playbook engine — that operates autonomously with human oversight at every tier.
