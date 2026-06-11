# Phase 2: B2B Pivot and Enterprise Architecture

## Overview
The project pivoted from a general-purpose security tool to a B2B enterprise platform targeting cloud infrastructure and DevOps teams. The architecture evolved into a multi-language, high-performance ecosystem, moving from static mock data to real live telemetry.

## Key Milestones

### 1. B2B Enterprise Target Market Pivot
- Formalized the focus on protecting servers, databases, and Kubernetes nodes.
- Replaced fine-tuning wrappers with a custom PyTorch 3-Billion Parameter Foundation Model framework, natively incorporating Flash Attention 2, Grouped Query Attention, and Rotary Position Embeddings.
- Created a Custom Byte-Level BPE Tokenizer for native processing of IP addresses, file paths, and hex codes.
- Introduced "Blast Radius" logic into the Decision Engine to constrain AI `auto_execute` actions in critical environments (e.g., forcing human approval for production systems).

### 2. Multi-Language Microservices
- **Rust Sensors:** Initialized memory-safe, zero-overhead kernel telemetry agents using eBPF for Linux and ETW/WMI for Windows.
- **Go API Gateway:** Replaced the Python FastAPI gateway with a highly concurrent Go microservice (`agrus-gateway`) acting as a reverse proxy, unmarshaling JSON arrays to handle high-throughput telemetry ingestion.
- **Python Engine:** Maintained the Python AI backend for PyTorch inference and decision logic.
- **MERN Dashboard:** The React/Vite dashboard was overhauled with a live feed design, connecting to a NATS backend to process raw kernel events in real-time.

### 3. Security Hardening and Deployment
- Hardened the `agrus-gateway` with Bearer token authentication to prevent unauthenticated telemetry ingestion.
- Refactored the Human-in-the-Loop (HitL) decision engine to force approval on any action other than "observe".
- Finalized production-ready Docker Compose orchestration, transitioning the Python engine to `uvicorn` and implementing universal `.dockerignore` files.
- Executed a global project rename to **AGRUS**.

### 4. AI Training Pipeline Overhaul
- Transitioned to a unified script leveraging `AutoModelForCausalLM.from_pretrained("meta-llama/Llama-3.2-3B")` as a base.
- Integrated QLoRA (4-bit quantization, 8-bit paged AdamW) to compress weights and enable training on consumer GPUs without OOM errors.
- Blended real-world SOC workflows and raw exploit datasets dynamically from Hugging Face for fine-tuning.
