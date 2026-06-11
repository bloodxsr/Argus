# System Architecture

## Related Notes
- [[Deployment_and_Hosting_Guide]]
- [[Custom_3B_Model_Training_Guide]]
- [[Security_AI_Agent]]
- [[Decision_Engine]]

---

## The 4 Pillars of AGRUS (Finalized Architecture)

The system has been meticulously separated by language and concern to ensure maximum performance, security, and scalability in a B2B enterprise setting.

### 1. The Kernel Sensors (Rust)
*   **Linux Codebase:** `sensor/` & `ebpf/`
*   **Windows Codebase:** `windows-sensor/`
*   **Role:** Deployed on the client's servers. The Linux sensor natively compiles eBPF bytecode using `Aya` to hook `sys_enter_execve`, `sys_enter_openat`, and `sys_enter_connect` to extract exact process, file access, and networking events. The Windows sensor utilizes COM libraries to asynchronously query `Win32_ProcessStartTrace`, `Win32_Service`, and Registry changes over WMI. Both aggregate telemetry using a `tokio::sync::mpsc` channel.
*   **Why Rust?** Absolute memory safety and zero garbage collection overhead. Kernel telemetry extraction must be lightning-fast.

### 2. The API Gateway & Event Bus (Go)
*   **Codebase:** `gateway/`
*   **Role:** Acts as the high-throughput cloud ingestion point. It receives arrays of batched JSON events (`[]TelemetryEvent`) from the Rust sensors, decodes them dynamically, and fans them out using native `goroutines` to a **NATS Event Bus** queue (`incidents.scored`). 
*   **Why Go & NATS?** Go is incredibly fast at handling massive concurrent HTTP network requests, and NATS is an enterprise-grade message broker that prevents the AI from being DDOS'd by process spikes.

### 3. The AI Decision Engine (Python)
*   **Codebase:** `ai/` and `train/`
*   **Role:** The intelligence core. It consumes NATS queues and runs the **8-Billion Parameter Foundation Model** (Llama-3.1-8B-Instruct via QLoRA 4-bit) combined with advanced heuristic reasoning modules.
*   **Submodules:**
    *   **APT Correlation:** Tracks long-term sparse events mapped to the MITRE ATT&CK kill chain.
    *   **UEBA Baselines:** Generates behavioral deviations for entities.
    *   **Container Security:** Implements real-time quarantine and kill logic for Docker/K8s.
    *   **Code Remediation:** Uses AST parsing to find vulnerabilities and auto-submit PR patches via GitHub.
*   **Why Python?** The undisputed king of deep learning (PyTorch, HuggingFace, CUDA) and rapid ML framework integrations.

### 4. The Dashboards (MERN Stack)
*   **Codebase:** `dashboard/`
*   **Role:** The frontend interface for the SOC team. Built in React (Vite) and Node.js (Express), powered by MongoDB and direct REST connections to the Python FastAPI engine. 
*   **Design Language:** Strictly flat, minimalist, pure solid black UI (`#000000`) for maximum contrast and technical seriousness. No soft glassmorphism.
*   **Why MERN?** The industry standard for building extremely reactive, real-time web applications.

---

## Data Flow Pipeline

```text
[Client Infrastructure]
    │                 │
    ▼                 ▼
Linux (eBPF)      Windows (WMI)
(Syscalls)        (COM Library)
    │                 │
    ▼                 ▼
   MPSC Channel Batching (50 events/cycle)
           │
           ▼ HTTP POST (JSON Array)
           │
      Go Cloud Gateway
   (Goroutine Array Fanout)
           │
           ▼ NATS Publisher
           │
    NATS Message Broker (`incidents.scored`)
           │
           ▼ NATS Subscriber
           │
    Python PyTorch Engine & Fast API
    (8B Llama 3.1 + APT/UEBA/Containers)
           │
           ├───► Autonomous Remediation (Kill/Quarantine/PR)
           │
           ▼
    MongoDB Document Store
    (Incident Reports & Audit Trails)
           │
           ▼
      React Dashboard
    (Solid Black SOC Team Review UI)
```

---

## Production Scalability

*   **Agents (Rust):** Stateless. Scale out infinitely by deploying to more client nodes.
*   **Gateway (Go):** Stateless. Sit behind a Kubernetes LoadBalancer. Can scale to hundreds of pods to handle DDOS levels of telemetry.
*   **AI Engine (Python):** Scale vertically via multi-GPU instances (e.g., NVIDIA A100s) or horizontally using frameworks like vLLM. Training pipeline configured to push RTX 4060 limits (8GB VRAM) using sequence length 2048, LoRA rank 16, and gradient checkpointing.
*   **Database (Mongo):** Easily transitioned into a sharded MongoDB Atlas cluster.
