Project Checkpoint 0017 - Final Integration & AI Expansion
======================================================
Date: 2026-06-11

## Architecture Refactor
- The original messy `ai/` folder was restructured into a clear separation of concerns:
  - `ai/core/`: Contains the fundamental reasoning logic, heuristics backends, LLM wrappers, critic verifiers, and RAG retrievers.
  - `ai/features/`: Contains the modular security domains: `baselines.py` (UEBA), `correlation.py` (APT Kill Chains), `container.py` (Runtime Container Security), and `remediation.py` (Code Scanners and PR automation).
- Circular import loops between `core` and `features` were identified and cleanly resolved.

## New Autonomous AI Features
- **APT Correlation Engine (`correlation.py`)**: Built to track sparse alerts over long horizons (e.g. initial access → execution → credential access), map them to MITRE ATT&CK stages, and escalate if a full kill chain is materializing.
- **UEBA Baseline Engine (`baselines.py`)**: Establishes behavioral baselines for specific hosts/identities and tracks deviation.
- **Container Runtime Security (`container.py`)**: Detects malicious behavior inside Docker/Kubernetes boundaries, supporting real-time autonomous isolation (`quarantine`) and termination (`kill`).
- **Code Remediation Engine (`remediation.py` & `scanners.py`)**: Statically scans codebases via AST, detects vulnerabilities (SQLi, Command Injection, Secrets), prompts the AI to generate a fix, and automatically opens a GitHub Pull Request.

## Multi-Platform Sensor Telemetry
- **Linux eBPF Sensor (`ebpf/` & `sensor/`)**: Added kernel tracepoints for file access (`sys_enter_openat`) and network connections (`sys_enter_connect`). It extracts IPs and filenames and ships them into the NATS event bus.
- **Windows WMI Sensor (`windows-sensor/`)**: Added WMI subscriptions to detect service installations (`Win32_Service`) and registry persistence (`RegistryValueChangeEvent` on `Run` keys).

## Real-Time SOC Dashboard (`dashboard/`)
- Stripped away the placeholder glassmorphism and soft colors.
- Implemented a strictly utilitarian, solid flat black, minimalist UI (`#000000` background, `#0a0a0a` panels).
- Added live API hooks directly to the FastAPI engine (`http://127.0.0.1:9000`) for:
  - APT Correlations Tab
  - UEBA Baselines Tab
  - Active Containers Tab (with live actionable "Quarantine" and "Kill" buttons)
- Integrated with the Node.js MongoDB backend (`http://127.0.0.1:4200`) to pull Historical/Active Incident Reports.

## QLoRA Hardware Maximization
- Tuned `train/train.py` specifically for an **RTX 4060 with 8GB VRAM**.
- Pushed limits: Max sequence length increased from 1024 to **2048**, LoRA rank (`r`) pushed from 8 to **16**, Effective batch size set to **8** (2 physical * 4 gradient accumulation), and explicitly enabled **Gradient Checkpointing** to prevent OOM errors with the Llama-3.1-8B model. Training set to 3 epochs.

## Conclusion
The stack is fully interconnected: Low-level kernel events trigger NATS messages, which pass through the Go Gateway into the Python AI Engine, generating autonomous responses and mapping complex correlations, which are then immediately visible on the React Dashboard. The architectural vision of a playbook-less autonomous SOAR is now realized in code.
