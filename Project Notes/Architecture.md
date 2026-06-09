# System Architecture

## Related Notes
- [[Deployment_and_Hosting_Guide]]
- [[Custom_3B_Model_Training_Guide]]
- [[Security_AI_Agent]]
- [[Decision_Engine]]

---

## The 4 Pillars of AGRUS (Finalized Architecture)

The system has been meticulously separated by language and concern to ensure maximum performance, security, and scalability in a B2B enterprise setting.

### 1. The Kernel Sensor (Rust)
*   **Codebase:** `agrus-sensor/`
*   **Role:** Deployed on the client's servers. Uses eBPF (`Aya`) to hook directly into the Linux Kernel (e.g., `sys_enter_execve`).
*   **Why Rust?** Absolute memory safety and zero garbage collection overhead. A crash in the sensor must never crash the client's production server.

### 2. The API Gateway & Event Bus (Go)
*   **Codebase:** `agrus-gateway/`
*   **Role:** Acts as the high-throughput cloud ingestion point. It receives millions of JSON events from the Rust sensors and uses native `goroutines` to queue and fan-out the telemetry to the AI engine asynchronously. 
*   **Why Go?** Dominates cloud-native architectures (Kubernetes, NATS). It is incredibly fast at handling massive concurrent network requests.

### 3. The AI Decision Engine (Python)
*   **Codebase:** `security_ai_service/` and `train/`
*   **Role:** Hosts the custom **3-Billion Parameter Foundation Model**. Exposes a single `/analyze` endpoint for the Go Gateway. It evaluates telemetry, executes the Blast Radius business logic, and makes autonomous decisions.
*   **Why Python?** The undisputed king of deep learning (PyTorch, HuggingFace, CUDA).

### 4. The Dashboards (MERN Stack)
*   **Codebase:** `report-website/` and `test-website/`
*   **Role:** The frontend interfaces for the SOC team. Built in React (Vite) and Node.js (Express), powered by MongoDB. 
*   **Why MERN?** The industry standard for building extremely reactive, real-time web applications with dynamic UI/UX (glassmorphism, dark mode).

---

## Data Flow Pipeline

```text
[Client Infrastructure]
        │
        ▼
   Rust eBPF Sensor
   (Zero-overhead telemetry)
        │
        ▼ HTTP POST (Sub-millisecond)
        │
   Go Cloud Gateway
   (Goroutine Fanout / Reverse Proxy)
        │
        ▼
   Python PyTorch Engine
   (3B Parameter Inference + Blast Radius Logic)
        │
        ▼
   MongoDB Document Store
   (Incident Reports & Audit Trails)
        │
        ▼
   React Dashboards
   (SOC Team Review & Simulation)
```

---

## Production Scalability

*   **Agents (Rust):** Stateless. Scale out infinitely by deploying to more client nodes.
*   **Gateway (Go):** Stateless. Sit behind a Kubernetes LoadBalancer. Can scale to hundreds of pods to handle DDOS levels of telemetry.
*   **AI Engine (Python):** Scale vertically via multi-GPU instances (e.g., NVIDIA A100s) or horizontally using frameworks like vLLM.
*   **Database (Mongo):** Easily transitioned into a sharded MongoDB Atlas cluster.
