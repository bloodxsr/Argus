# AGRUS: Master System Overview & Setup Guide

This document serves as the complete, ground-up explanation of the AGRUS platform. It explains what the project is, how it works, what each module does, and exactly how to deploy it in a real-world distributed environment.

---

## 1. The Core Concept

**AGRUS** is an AI-native autonomous SOAR (Security Orchestration, Automation, and Response) platform and EDR (Endpoint Detection and Response) system. 

Traditional security systems rely on humans writing static "if-this-then-that" rules (playbooks) to react to threats. AGRUS eliminates playbooks. Instead, it deploys lightweight **Sensors** to your computers (Endpoints) which monitor kernel-level system activity. This activity is streamed to a central **Security Operations Center (SOC)**, where a fine-tuned Artificial Intelligence (Llama-3.1 LLM) acts as an autonomous security analyst—reading the data, understanding the context, correlating multi-stage attacks, and automatically taking action to kill the threat.

---

## 2. How Data Flows (The Architecture)

The system is split into two halves: **The Endpoints** (the victim computers being protected) and **The Server** (the SOC where the AI lives).

1. **Detection:** A user on an Endpoint PC executes a malicious script. The **Rust Sensor** running in the background detects the kernel-level process creation.
2. **Transmission:** The sensor securely packages this event into JSON and sends it via an HTTP POST request over the network to the **Go Gateway** running on the Server.
3. **Ingestion & Queuing:** The Go Gateway authenticates the sensor. Once verified, it drops the event into the **NATS Event Bus** (a lightning-fast message queue capable of handling millions of events).
4. **Processing & Storage:** The **React Dashboard Server** acts as the central orchestrator on the Server. It continuously listens to the NATS queue. When an event arrives, it saves a draft to **MongoDB** and immediately forwards the event to the **Python AI Engine**.
5. **AI Analysis:** The Python AI Engine runs the event through:
    - **UEBA Baseline Engine:** Checks if this behavior deviates from the user's normal routine.
    - **APT Correlation Engine:** Checks if this event is part of a larger multi-stage kill chain.
    - **Decision Engine (LLM):** The Llama-3.1 model reads the context, maps it to MITRE ATT&CK frameworks, calculates a confidence score, and determines an action (e.g., `kill_process`).
6. **Response:** The AI's decision is sent back to the Dashboard Server, stored in the database, and rendered live on the analyst's screen. If autonomous execution is enabled, the system automatically isolates the host or kills the malicious container.

---

## 3. Module Breakdown

### 1. `sensor/` (Linux eBPF Sensor)
Written in Rust. It hooks directly into the Linux kernel using eBPF (Extended Berkeley Packet Filter). It intercepts system calls (like `sys_enter_openat` for file access and `sys_enter_connect` for network traffic) before they even reach user space. Highly performant and practically invisible to malware.

### 2. `windows-sensor/` (Windows WMI Sensor)
Written in Rust. Uses Windows Management Instrumentation (WMI) and Event Tracing to silently monitor Process Creations, Service Installations, and Registry modifications (persistence mechanisms) on Windows machines.

### 3. `gateway/` (Go API Gateway)
Written in Go for extreme concurrency. It acts as the shield for your SOC. It handles authentication (`AGRUS_SENSOR_TOKEN`), rate-limiting, and direct bridging from HTTP requests into the NATS streaming protocol.

### 4. `ai/` (Python Security Engine)
The brain of the operation, powered by FastAPI and customized LLM wrappers. 
- **`core/`:** Contains the base logic. Handles routing, LLM backend communication (Fine-Tuned Llama, Ollama, or Heuristic fallback), and RAG (Retrieval-Augmented Generation) to inject threat intelligence into prompts.
- **`features/`:** Contains the specialized security modules:
  - `correlation.py`: Groups sparse events across long time horizons to detect Advanced Persistent Threats (APTs).
  - `baselines.py`: User and Entity Behavior Analytics (UEBA). Learns what "normal" looks like to detect anomalies.
  - `container.py`: Interacts with the host Docker socket to quarantine or kill compromised containers.
  - `remediation.py`: Analyzes local codebases for vulnerabilities via AST, prompts the AI to write a patch, and automatically opens a GitHub Pull Request to fix it.

### 5. `dashboard/` (React / Express SOC UI)
A fully solid-dark, minimalist dashboard. The React frontend provides real-time visibility into Active Incidents, APT Correlations, UEBA Baselines, and Container Statuses. The Node.js/Express backend serves as the bridge between MongoDB, NATS, and the AI Engine.

---

## 4. Master Setup & Deployment Guide

### Phase 1: The Central Server (SOC)
This is the machine that hosts the AI, the database, and the dashboard.

1. **Configure Environment:** Create a `.env` file at the root of the project by copying `.env.example`. Set your secure tokens:
   ```env
   AGRUS_INTERNAL_TOKEN=super-secret-internal
   AGRUS_SENSOR_TOKEN=super-secret-sensor
   AGRUS_GATEWAY_URL=http://<YOUR_SERVER_IP>:8080/api/v1/telemetry
   ```
2. **Start the Stack:**
   ```bash
   docker compose up -d --build
   ```
   *This launches MongoDB, NATS, the Go Gateway, the Python AI Engine (with RTX GPU passthrough automatically enabled for Windows WSL2), and the Dashboard.*
3. **Train the AI (Optional):**
   If you wish to fine-tune the Llama model on your dataset, run `uv run python train/train.py`. The resulting `.safetensors` files will be saved in `models/` and instantly recognized by the AI container.

### Phase 2: Distributed Endpoints (The "Deep Root" Installation)
To protect external computers, you must install the compiled sensors deep into their operating systems so they run silently on boot.

#### On Linux Endpoints
1. Copy the compiled `agrus-sensor` binary to `/usr/local/bin/agrus-sensor`.
2. Create a persistent systemd service at `/etc/systemd/system/agrus-sensor.service`:
   ```ini
   [Unit]
   Description=AGRUS eBPF Security Sensor
   After=network.target

   [Service]
   Type=simple
   # Set the environment variables directly in the service configuration
   Environment="AGRUS_GATEWAY_URL=http://<YOUR_SERVER_IP>:8080/api/v1/telemetry"
   Environment="AGRUS_SENSOR_TOKEN=super-secret-sensor"
   Environment="RUST_LOG=info"

   ExecStart=/usr/local/bin/agrus-sensor
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
3. Enable and start the silent background guardian:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now agrus-sensor
   ```

#### On Windows Endpoints
1. Copy `agrus-windows-sensor.exe` to a secure directory (e.g., `C:\Program Files\AGRUS\`).
2. Set "Machine-level" System Environment Variables using an Administrator PowerShell. This bakes the configuration into the Windows Registry so any background service can access it:
   ```powershell
   [Environment]::SetEnvironmentVariable("AGRUS_GATEWAY_URL", "http://<YOUR_SERVER_IP>:8080/api/v1/telemetry", "Machine")
   [Environment]::SetEnvironmentVariable("AGRUS_SENSOR_TOKEN", "super-secret-sensor", "Machine")
   [Environment]::SetEnvironmentVariable("RUST_LOG", "info", "Machine")
   ```
3. Configure `agrus-windows-sensor.exe` to run via the Windows Task Scheduler on `SYSTEM STARTUP`, running as the `SYSTEM` user. It will silently stream telemetry to your SOC.

---
*End of Guide.*
