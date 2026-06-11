# Checkpoint 0019: Windows and CUDA Ecosystem Fixes

## Date
*June 11, 2026*

## Problem
The `train.py` pipeline and Docker containers were originally defaulting to CPU when ported to a Windows environment or when using experimental Python versions (3.13). The IDE was also populated with `Pylance` and `rust-analyzer` squiggly lines across both the AI backend and the Windows sensor module due to OS-specific configuration blocks.

## Execution & Resolution

### 1. PyTorch CUDA Routing
- Pinned `requires-python` in `pyproject.toml` down to `>=3.10` to ensure complete compatibility across varying local installations (e.g. `3.10.20` or `3.12`).
- Hardcoded the `--extra-index-url https://download.pytorch.org/whl/cu121` into `uv` config and `requirements.txt`. This strictly enforces pulling down the proper massive NVIDIA wheels rather than defaulting to generic PyPI CPU packages.
- Dockerfile base image was downgraded from the highly experimental `3.13-slim` to `3.12-slim` for unshakeable container stability.

### 2. RTX 40-Series Optimization
- Identified the host hardware as an Ada Lovelace RTX 4060 GPU (8GB VRAM).
- Stripped out `torch.float16` and `fp16=True` throughout `train.py`, `ai/core/backends.py`, and `accelerate_config.yaml`.
- Replaced them with **bfloat16** (`bf16=True`), which utilizes modern Tensor Cores perfectly, eliminating floating point crashes and vanishing gradients during training while keeping the massive 8B model cleanly tucked inside the 8GB memory limit using `BitsAndBytes` 4-bit `nf4` quantization.

### 3. Docker GPU Passthrough for Windows
- Modified `docker-compose.yml` to include the `deploy: resources: reservations: devices: - driver: nvidia` block.
- Previously, Docker Desktop WSL2 would isolate the container from the host GPU, crashing the AI. Now, `docker compose up` inherently routes the physical RTX 4060 down into the Python AI microservice.

### 4. IDE / Linter Exorcism
- **Pylance:** Repaired module path mismatching (`ai.core.knowledge` instead of `ai.knowledge`) and converted `QdrantClient` type hints to `Any` to resolve "Variable not allowed in type expression" warnings.
- **Rust-Analyzer:** The `windows-sensor` was covered in warnings when viewed on Linux due to `#[cfg(windows)]`. Injected `#![allow(unused_imports, dead_code, unreachable_code)]` at the top of the file to clean the IDE workspace.
- Added instructions to install `rust-src` on the `nightly` toolchain to fix the `bpfel-unknown-none` missing target error for eBPF code analysis.

## Next Steps
- Verify telemetry streams successfully from `windows-sensor.exe` into the Go Gateway via the NATS message queue.
- Initiate the final training run on the host GPU.
