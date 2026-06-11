# Architecture & Blueprint

This document defines the finalized architectural structure and implementation blueprint for AGRUS. It translates the project vision into a concrete, buildable structure distributed across languages for maximum performance and security.

## The 4 Pillars of AGRUS Architecture

The system is separated by language and concern to ensure maximum performance, security, and scalability in a B2B enterprise setting.

### 1. The Kernel Sensors (Rust)
- **Role:** Deployed on client servers to capture ground truth telemetry.
- **Linux (`sensor/` & `ebpf/`):** Natively compiles eBPF bytecode using `Aya` to hook `sys_enter_execve`, `sys_enter_openat`, and `sys_enter_connect`.
- **Windows (`windows-sensor/`):** Utilizes COM libraries to asynchronously query `Win32_ProcessStartTrace`, `Win32_Service`, and Registry changes over WMI.
- **Why Rust?** Absolute memory safety and zero garbage collection overhead. Kernel telemetry extraction must be lightning-fast.

### 2. The API Gateway & Event Bus (Go)
- **Role:** High-throughput cloud ingestion point (`gateway/`).
- **Functionality:** Receives arrays of batched JSON events from Rust sensors, decodes them dynamically, and fans them out using native `goroutines` to a NATS Event Bus queue (`incidents.scored`).
- **Why Go & NATS?** Go excels at handling massive concurrent HTTP network requests. NATS provides an enterprise-grade message broker that prevents the AI from being DDOS'd by process spikes.

### 3. The AI Decision Engine (Python)
- **Role:** The intelligence core (`ai/` and `train/`).
- **Functionality:** Consumes NATS queues and runs the proprietary Llama-3.1-8B-Instruct foundation model combined with heuristic reasoning modules.
- **Key Modules:** APT Correlation, UEBA Baselines, Container Security, Code Remediation.
- **Why Python?** The undisputed king of deep learning and rapid ML framework integrations.

### 4. The Dashboards (MERN Stack)
- **Role:** The frontend interface for the SOC team (`dashboard/`).
- **Functionality:** Built in React (Vite) and Node.js (Express), powered by MongoDB and direct REST connections to the Python FastAPI engine. Features a minimalist, pure solid black UI (`#000000`).

---

## Data Flow Pipeline
```text
[Client Infrastructure] -> Linux (eBPF) / Windows (WMI)
      |
      v
MPSC Channel Batching
      |
      v
Go Cloud Gateway -> NATS Event Bus (`incidents.scored`)
      |
      v
Python PyTorch Engine & FastAPI (Llama 3.1 + Security Heuristics)
      |
      +---> Autonomous Remediation (Kill/Quarantine/PR)
      |
      v
MongoDB Document Store
      |
      v
React Dashboard (Solid Black SOC UI)
```

---

## Implementation Blueprint & Repo Split

The implementation is split into defined repositories and domains:

1. **Test Website:** Simulates attacks, generates synthetic telemetry, and demonstrates human review.
2. **Agent Repo:** Runs the core security workflow, handling telemetry ingestion, anomaly detection, threat intelligence, and the Python Security AI decision service.
3. **Report / Result Website:** Provides the audit and reporting surface for incident and action history.

### Shared Contracts
The system utilizes a single source of truth for core objects across all repositories to prevent drift:
- UnifiedEvent, Incident, EnrichedIncident
- RiskScore, AIResult, Decision, ActionRecord

### Company Constraint Layer & Checkpoint Discipline
Each deployment implements a constraint layer to restrict the bot without changing model code (e.g., allowed response actions, auto-response thresholds). Meaningful implementation steps are recorded as markdown checkpoints under `Project_checkpoints/`.

### Evaluation Harness
The LLM is rigorously tested against fixed test cases before release:
- Known malicious incidents and benign false positives.
- Ambiguous mixed-signal cases and adversarial prompt injections.
- Policy-boundary violations and company-specific constraint cases.
