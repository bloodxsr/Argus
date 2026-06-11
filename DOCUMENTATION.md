# AGRUS: Autonomous AI Security Operating System

## 1. Overview

**AGRUS** is an AI-native autonomous SOAR (Security Orchestration, Automation, and Response) platform and EDR (Endpoint Detection and Response) system. It transforms enterprise cybersecurity by moving away from static, human-written playbooks and instead leveraging a domain-specialized AI reasoning engine.

### Core Goal
The fundamental leap is shifting the security paradigm from:
`Alert → Human → Decision → Action`
to:
`Detect → Investigate → Decide → Act → Human Audits`

### Target Market
AGRUS is explicitly designed as a **B2B Enterprise Platform** tailored for Cloud Infrastructure Providers, Managed Hosting Companies, and DevOps & SRE Teams managing large-scale server networks. It is built to protect web servers, databases, load balancers, and Kubernetes ingress nodes from threats like web-exploits, container escapes, and server-side lateral movement.

### Operating Model: Human-on-the-Loop
AGRUS operates on a tiered response model to satisfy stringent enterprise compliance (SOC 2, ISO 27001):
* **Low Risk (0–30):** System observes and logs. Human never sees it.
* **Medium Risk (31–70):** System recommends action. Human approves or rejects.
* **High Risk (71–100):** System acts immediately and autonomously. Human receives a notification and can audit/rollback within 24 hours.

---

## 2. Architecture

AGRUS is systematically separated by language and concern to ensure maximum performance, memory safety, and scalability.

### The 4 Pillars of AGRUS
1. **The Kernel Sensors (Rust):** Deployed on client servers. The Linux sensor hooks natively into the kernel using **eBPF** (Extended Berkeley Packet Filter) to trace syscalls (e.g., `sys_enter_execve`, `sys_enter_openat`, `sys_enter_connect`). The Windows sensor leverages native COM libraries and **WMI/ETW** to track process creations, service installations, and registry modifications. Telemetry extraction is lightning-fast and bypasses userspace evasion.
2. **The API Gateway & Event Bus (Go):** Acts as the high-throughput cloud ingestion point. Built in Go, it ingests batched JSON events from sensors, handles Bearer token authentication, and dynamically routes them to a **NATS Event Bus** (`incidents.scored`). This decoupled streaming protocol protects the AI from sudden telemetry spikes.
3. **The AI Decision Engine (Python):** The intelligence core powered by FastAPI and PyTorch. It consumes NATS queues and runs the customized Security Foundation Model (Llama-3.2-3B/8B architecture), augmented by heuristic reasoning modules and RAG (Retrieval-Augmented Generation) based on MITRE ATT&CK.
4. **The Dashboards (MERN Stack):** Built with React (Vite) and Node.js (Express), backed by MongoDB. A fully solid-dark, minimalist SOC UI (`#000000`) designed for maximum contrast. It provides real-time visibility into active incidents, APT correlations, UEBA baselines, and container statuses.

### Data Flow Pipeline
1. **Detection:** Rust sensors hook into the kernel and intercept raw system calls instantly.
2. **Transmission:** Secure HTTP POST payload is batched and sent to the Go Cloud Gateway.
3. **Ingestion:** The Go Gateway authenticates and fans out events into the NATS Message Broker.
4. **AI Processing:** The Python engine ingests the NATS stream. The event is mapped across Behavioral Baselines, Kill Chain correlations, and the primary LLM Decision Engine.
5. **Action:** The system generates a Risk Score and autonomously mitigates the threat (e.g., `kill_process` or `quarantine_container`) if constraints allow, publishing the audit trail back to the dashboard.

---

## 3. Core AI Features & Specialized Engines

AGRUS does not use general-purpose API chatbots. It utilizes a **Domain-Specialized Security Engine**, pre-trained and fine-tuned exclusively on cybersecurity datasets (CVEs, MITRE STIX, real incident reports, syslogs, and Kali Linux tool outputs).

### Specialized Modules (`ai/features/`)
* **APT Correlation Engine:** Tracks sparse alerts over long horizons (e.g., Initial Access → Execution → Credential Access), maps them to MITRE ATT&CK stages, and escalates when a full kill chain materializes.
* **UEBA Baseline Engine:** Establishes statistical and behavioral baselines (User & Entity Behavior Analytics) for specific hosts and identities, dynamically scoring behavioral deviations (e.g., unusual processes at 3:00 AM).
* **Container Runtime Security:** Interacts natively with the Docker socket (`/var/run/docker.sock`) to detect anomalous behavior within containers, supporting live, autonomous `quarantine` (network isolation) and `kill` capabilities.
* **Code Remediation Engine:** Uses AST parsing to statically scan codebases for vulnerabilities (SQLi, Command Injection, Secrets) and dynamically prompts the AI to open fully patched GitHub Pull Requests.
* **Threat Intelligence Integration:** Enriches incidents on-the-fly with fresh IOCs (Indicators of Compromise) from feeds like abuse.ch (ThreatFox, MalwareBazaar) and CISA KEV.

### The Risk & Decision Engines
* **Multiplicative Risk Formula:** `Risk = (Impact × Confidence × Exposure) / 10`. Normalizes to 0-100. This formulation prevents low-confidence signals from inflating the overall risk.
* **Policy Engine (OPA):** Policies are evaluated dynamically (Open Policy Agent) utilizing "Blast Radius" logic. If an asset is highly critical (e.g., `production`), the decision engine dynamically downgrades `auto_execute` capabilities to enforce human approval, maintaining absolute safety.

---

## 4. Deployment & Quickstart

AGRUS runs inside an orchestrated multi-container environment configured for absolute zero dependency conflict.

### Pre-Requisites
- Ensure Docker and Docker Compose are installed.
- For Windows/WSL2 or Linux environments with modern NVIDIA hardware, ensure the NVIDIA Container Toolkit is installed to allow GPU passthrough.

### Booting the Cloud SOC Platform
1. **Configure Environment Variables:**
   Create a `.env` file at the root by copying `.env.example`:
   ```bash
   cp .env.example .env
   # Ensure AGRUS_INTERNAL_TOKEN and AGRUS_SENSOR_TOKEN are set.
   ```
2. **Orchestrate the Stack:**
   Run the master Makefile command to build and launch the Go Gateway, Python AI Engine, MongoDB, and MERN Dashboards:
   ```bash
   make deploy
   ```
   *(Note: The `security-ai` container inherently uses `bfloat16` precision and BitsAndBytes `nf4` quantization tailored for RTX 40-Series/8GB VRAM limits).*
3. **Access the SOC Dashboard:** Open your browser to `http://localhost:4200`.
4. **Access the Attack Simulator:** Open your browser to `http://localhost:4100` to inject synthetic telemetry to test the pipeline natively.

### Sensor Deployment
For true kernel integration, compile the Rust agents:
* **Linux:** Navigate to `sensor/` and run `cargo build --release`. Deploy the binary as a background daemon (systemd).
* **Windows:** Navigate to `windows-sensor/` and compile the WMI tracer. Run via Windows Task Scheduler.

---

## 5. Future Roadmap

While the telemetry, messaging, and primary ML layers are successfully deployed, the platform targets continuous expansion in the following domains:

* **Container Runtime Isolation Expansion:**
  - Complete integration of Kubernetes `NetworkPolicy` APIs to automatically isolate and deny egress traffic for dynamically compromised K8s pods.
  - Plumb kernel `cgroup_id` telemetry deep into the eBPF tracepoints for 1-to-1 container identification.
* **Long-Term UEBA Memory:**
  - Build out the MongoDB Timeseries collections to persist granular event baselines (common IPs, standard execution hours) indefinitely.
  - Dynamically inject the deviation delta directly into the LLM prompt context to radically reduce false positives during anomalous-but-safe administrative work.
* **Advanced APT Graph Correlation:**
  - Transition from standard chronological correlations to full graph-based relationship linking (e.g., via Neo4j or Rust's `petgraph`), uncovering hidden lateral movements across entirely disparate server environments.
