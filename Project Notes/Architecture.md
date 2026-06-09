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
*   **Role:** Deployed on the client's servers. The Linux sensor natively compiles eBPF bytecode using `Aya` to hook `sys_enter_execve`, extracting string variables via `bpf_get_current_comm` into a high-performance `PerfEventArray`. The Windows sensor utilizes COM libraries to asynchronously query `Win32_ProcessStartTrace` over WMI. Both sensors aggregate telemetry using a `tokio::sync::mpsc` channel to batch network events.
*   **Why Rust?** Absolute memory safety and zero garbage collection overhead. Kernel telemetry extraction must be lightning-fast.

### 2. The API Gateway & Event Bus (Go)
*   **Codebase:** `gateway/`
*   **Role:** Acts as the high-throughput cloud ingestion point. It receives arrays of batched JSON events (`[]TelemetryEvent`) from the Rust sensors, decodes them dynamically, and fans them out using native `goroutines` to a **NATS Event Bus** queue (`incidents.scored`). 
*   **Why Go & NATS?** Go is incredibly fast at handling massive concurrent HTTP network requests, and NATS is an enterprise-grade message broker that prevents the AI from being DDOS'd by process spikes.

### 3. The AI Decision Engine (Python)
*   **Codebase:** `ai/` and `train/`
*   **Role:** Hosts the custom **8-Billion Parameter Foundation Model** (Llama-3.1-8B-Instruct via QLoRA 4-bit). It consumes from the NATS queue asynchronously, evaluates the telemetry, executes the Blast Radius business logic, and makes autonomous defense decisions.
*   **Why Python?** The undisputed king of deep learning (PyTorch, HuggingFace, CUDA).

### 4. The Dashboards (MERN Stack)
*   **Codebase:** `dashboard/`
*   **Role:** The frontend interface for the SOC team. Built in React (Vite) and Node.js (Express), powered by MongoDB. 
*   **Why MERN?** The industry standard for building extremely reactive, real-time web applications with dynamic UI/UX (glassmorphism, dark mode).

---

## Data Flow Pipeline

```text
[Client Infrastructure]
    │                 │
    ▼                 ▼
Linux (eBPF)      Windows (WMI)
(PerfEventArray)  (COM Library)
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
    Python PyTorch Engine
    (8B Parameter Llama 3.1 Inference)
           │
           ▼
    MongoDB Document Store
    (Incident Reports & Audit Trails)
           │
           ▼
      React Dashboard
    (SOC Team Review & UI)
```

---

## Production Scalability

*   **Agents (Rust):** Stateless. Scale out infinitely by deploying to more client nodes.
*   **Gateway (Go):** Stateless. Sit behind a Kubernetes LoadBalancer. Can scale to hundreds of pods to handle DDOS levels of telemetry.
*   **AI Engine (Python):** Scale vertically via multi-GPU instances (e.g., NVIDIA A100s) or horizontally using frameworks like vLLM.
*   **Database (Mongo):** Easily transitioned into a sharded MongoDB Atlas cluster.
