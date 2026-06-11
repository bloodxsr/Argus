# AGRUS: Autonomous Security Orchestration & Response

AGRUS is an AI-native autonomous SOAR (Security Orchestration, Automation, and Response) platform. Unlike traditional SOARs that rely on static, human-written playbooks, AGRUS uses an active reasoning engine powered by a fine-tuned LLM to dynamically infer context, establish baselines, correlate APT attack chains, and execute immediate autonomous remediation at the kernel level.

## Features

- **Autonomous SOAR**: Eliminates static playbooks. The reasoning engine evaluates raw telemetry and autonomous executes blast-radius-aware mitigations.
- **eBPF Endpoint Detection & Response (EDR)**: Kernel-level visibility into file accesses, network connections, and process executions using Rust and eBPF.
- **Windows WMI Sensor**: Service installation and registry monitoring on Windows endpoints.
- **APT Correlation Engine**: Correlates sparse multi-stage events across the MITRE ATT&CK kill chain over long time horizons.
- **UEBA Baseline Engine**: Tracks entity behavior and flags deviations from normal operational baselines.
- **Container Runtime Security**: Detects and automatically isolates or kills malicious container workloads in real-time.
- **Code Remediation Engine**: AST-based vulnerability scanning and automated patch generation via the AI engine, complete with GitHub PR automation.
- **High-Performance Go Gateway**: Enterprise-grade API gateway and NATS event bus publisher built in Go.
- **Real-Time SOC Dashboard**: A minimalistic, fully solid dark-themed React dashboard for live threat monitoring and autonomous action oversight.

## Architecture

```text
.
├── ai/                # Core AI Reasoning & Features (Python)
│   ├── core/          # Backends, Critic Verifier, Decision Engine, Models, RAG Retriever
│   └── features/      # Baselines, Container Security, APT Correlation, Code Remediation
├── dashboard/         # React/Vite SOC Dashboard (Solid Dark Theme)
├── ebpf/              # eBPF C programs for kernel telemetry
├── gateway/           # Go API Gateway & NATS event router
├── sensor/            # Rust user-space eBPF sensor and NATS publisher
├── windows-sensor/    # Rust Windows WMI and Registry sensor
└── train/             # Llama-3.1-8B QLoRA fine-tuning scripts
```

## Running the Stack

Before running any services or `docker compose up`, please copy `.env.example` to `.env` and fill in the required tokens.

### 1. NATS Event Bus
Ensure a NATS server is running locally on port `4222` to broker telemetry.
```bash
nats-server -p 4222
```

### 2. AI Decision Engine (FastAPI)
The central intelligence node. Uses `uv` for fast package management.
```bash
uv run uvicorn ai.api:app --host 127.0.0.1 --port 9000
```
*Key Endpoints: `/analyze`, `/baselines`, `/correlations`, `/containers`, `/scan`, `/remediate`*

### 3. NATS AI Subscriber Agent
NATS subscription and AI analysis happen automatically when the dashboard server (`dashboard/server/index.js`) starts — it connects to NATS, listens on `incidents.scored`, calls `/analyze`, and stores results in MongoDB. No separate process to run.

### 4. Go API Gateway
Provides authentication, rate-limiting, and routes telemetry directly to NATS.
```bash
cd gateway
go run main.go
```

### 5. SOC Dashboard
The real-time monitoring interface for analysts.
```bash
cd dashboard
npm install
npm run dev
```

### 6. eBPF Sensor (Linux)
Compile and attach the eBPF programs. Requires root privileges to load into the kernel.
```bash
cd ebpf
RUSTC_BOOTSTRAP=1 cargo build -Z build-std=core
cd ../sensor
cargo run
```

## AI Model Fine-Tuning

The platform utilizes a customized Llama-3.1-8B model trained on SOC analyst workflows and raw Wazuh alerts. To run the QLoRA fine-tuning pipeline (optimized for 8GB VRAM RTX 4060):

```bash
uv run python train/train.py
```
*Note: This utilizes 4-bit quantization, gradient checkpointing, a max sequence length of 2048, and effective batch size of 8.*

## API Examples

**View Active APT Correlations:**
```bash
curl http://127.0.0.1:9000/correlations
```

**Quarantine a Malicious Container:**
```bash
curl -X POST http://127.0.0.1:9000/containers/quarantine \
     -H "Content-Type: application/json" \
     -d '{"container_id": "malicious-pod-1"}'
```

**Scan & Remediate a Codebase:**
```bash
curl -X POST http://127.0.0.1:9000/remediate \
     -H "Content-Type: application/json" \
     -d '{"repo_path": "/path/to/vulnerable/code"}'
```
