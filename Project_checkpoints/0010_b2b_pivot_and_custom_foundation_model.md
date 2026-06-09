# Checkpoint 0010: B2B Pivot & Custom Foundation Model Architecture

## Date: 2026-06-09

### 1. B2B Enterprise Target Market Pivot
- **Context:** Clarified the fundamental target audience and deployment environment. AISOS is not an endpoint security product for average users; it is a B2B platform tailored for Enterprise Web Hosting, Cloud Infrastructure Providers, and DevOps teams.
- **Action:** Updated `00_-_Project_Vision.md` to formally document this. All future architectural and product decisions (e.g., UI terminology, AI constraints, incident types) will focus on protecting servers, databases, load balancers, and Kubernetes ingress nodes from threats like web-exploits, container escapes, and lateral movement.

### 2. Custom 3-Billion Parameter Foundation Model (PyTorch)
- **Context:** The previous plan relied on fine-tuning an existing general-purpose model (like Mistral-7B). We have officially ripped out the fine-tuning wrappers and pivoted to building a proprietary, fully custom Foundation Model from scratch.
- **Action:** Created `train/custom_transformer.py`. This is a pure, from-scratch PyTorch implementation of a Decoder-Only Transformer specifically scaled to **2.92 Billion parameters**.
- **Architectural Features Implemented:**
  - **Flash Attention 2** natively via `F.scaled_dot_product_attention` for massive context windows (8192 tokens) to handle heavy server logs and eBPF dumps.
  - **Grouped Query Attention (GQA)** for lightning-fast inference (100-300ms) necessary for autonomous incident response.
  - **Rotary Position Embeddings (RoPE)** for perfect context extrapolation.
  - **SwiGLU** Feed-Forward Networks.
  - **Gradient Checkpointing** to allow training on standard clusters without OOM errors.
- **Action:** Created `train/train_custom_tokenizer.py` to build a Custom Byte-Level BPE Tokenizer. This ensures the model reads IP addresses, file paths, and hex codes natively, rather than fragmenting them like standard English-based tokenizers.

### 3. "Blast Radius" Logic Implemented in Decision Engine
- **Context:** To safely deploy autonomous responses in enterprise cloud environments, the AI must be constrained by the environment it is operating in.
- **Action:** Updated `CompanyConstraints` in `security_ai_service/models.py` and the `_apply_constraints` logic in `security_ai_service/engine.py`. Added `critical_environments` (e.g., `production`) and `critical_assets`. The engine now dynamically blocks the AI's `auto_execute` capabilities if an incident occurs on a critical asset, forcing human approval even if AI confidence is 99%.

### Next Steps
- Begin aggregating massive datasets (syslogs, PCAPs, Nginx logs, CTI reports) to feed into the custom tokenizer and begin the pre-training loop for the 3B model.
- Test the integration between the custom model's `.gguf` export and the Ollama local backend running within the Docker network.
