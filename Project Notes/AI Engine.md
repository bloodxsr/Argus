# AI Engine

The AI Engine is the core reasoning brain and decision-making center of AGRUS. It functions not as a generic chatbot, but as a domain-specialized AI that thinks like a senior security analyst. It evaluates risk, investigates anomalies, and executes autonomous remediation.

## Core Capabilities
- **Risk Assessment:** Calculates risk scores and prioritizes threats based on impact, confidence, and exposure.
- **Decision Engine:** Determines the next action based on risk score, Security AI reasoning, and organizational policy (via Open Policy Agent).
- **Autonomous Response:** Executes defensive actions such as isolating containers, killing malicious processes, or automatically fixing vulnerable code.
- **Code Remediation:** Scans repositories for vulnerabilities, generates patches using the LLM, and creates GitHub PRs automatically when configured.

---

## Architecture & Workflows

### AI Agent & Foundation Model
The AI Agent is powered by a proprietary Llama-3.1-8B-Instruct foundation model, fine-tuned specifically for cybersecurity using QLoRA (4-bit quantization). 
- **Training Data:** The model is trained on a perfectly blended dataset comprising high-level SOC Analyst Workflows and raw Wazuh Alerts (kernel payloads, network scans).
- **Hardware Profile:** The 8B model fits into an 8GB VRAM footprint (RTX 4060) utilizing `nf4` compute types, `bfloat16`, LoRA rank 16, and gradient checkpointing.
- **RAG Integration:** The model leverages Layered Retrieval (MITRE ATT&CK, CVE feeds, past incidents) before inference to maintain current threat context.

### Risk Assessment
Risk is calculated multiplicatively to suppress weak signals:
`Risk = (Impact × Confidence × Exposure) / 10`

- **Impact (0-10):** Measures potential damage (e.g., data loss, production asset).
- **Confidence (0-10):** Measures certainty (e.g., Threat intel IOC match, AI confidence).
- **Exposure (0-10):** Measures accessibility (e.g., internet-facing, root privileges).

Scores translate to tiers:
- **Low (0-30):** Log and observe.
- **Medium (31-70):** Recommend action for human review.
- **High (71-100):** Automatic action with post-action human audit.

### Decision Engine
Decisions are governed by an Open Policy Agent (OPA) that evaluates the risk score, AI recommendation, and company constraints.
- Policies are written in Rego and loaded at runtime.
- Evaluates asset context (e.g., `no_auto_response` flags for critical systems) before executing actions.

### Response & Remediation
The Response Agent executes actions determined by the Decision Engine. It operates on a Human-on-the-Loop model.

**Action Categories:**
1. **Process/Network Actions:** Kill processes, block IPs via `iptables`, or disable accounts.
2. **Container Isolation:** Maps host PIDs to containers via `/proc/<pid>/cgroup`. Isolates compromised containers by disconnecting them from all networks and pausing them, or executing a force-kill.
3. **Code Remediation:** Scans codebase for vulnerabilities, generates patches using the HeuristicSecurityLLM, and automates git branch creation, commits, and GitHub PR creation via the API.

Every automated action is logged with a rollback command to preserve accountability.
