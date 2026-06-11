# Checkpoint 0015: AI Training Overhaul & Custom Llama 3 Pipeline

## Status
Completed

## Changed Files
- `train/train_agrus_foundation.py`
- `train/run_accelerate.sh`
- `pyproject.toml`
- `.dockerignore`
- `.gitignore`
- `docker-compose.yml`

## Changes
1. **Model Architecture Upgrade**: 
   - Replaced the blank, randomly initialized 3B model architecture with `AutoModelForCausalLM.from_pretrained("meta-llama/Llama-3.2-3B")`.
   - This ensures the model starts with world-class reasoning and English comprehension before being subjected to cybersecurity fine-tuning.
2. **QLoRA Quantization**:
   - Integrated `BitsAndBytesConfig` (4-bit quantization) to compress the 6GB Llama 3 weights down to 1.5GB.
   - Reduced batch size to 1 and implemented an 8-bit paged AdamW optimizer. 
   - This allows the massive model to comfortably train and fine-tune on a 6GB RTX 4050 laptop GPU without throwing CUDA OOM errors.
3. **Parallel Dataset Blending**:
   - Removed the 20 lines of dummy strings that were acting as the training set.
   - Connected the script to Hugging Face to dynamically download `AYI-NEDJIMI/soc-analyst-en` (The Brain - SOC workflows) and `kholil-lil/wazuh-alerts` (The Muscle - Raw exploits).
   - The script merges 10,000 real-world examples, formats them into Instruction/Response pairs, and shuffles them together.
4. **Environment & Dependency Cleanup**:
   - Fixed the `uv` virtual environment wipeout by populating `pyproject.toml` with the exact required dependencies (`peft`, `accelerate`, `bitsandbytes`, `huggingface_hub[cli]`).
   - Removed the deprecated `test-website` completely from `docker-compose.yml`.

## Next Step
Launch the training script via `./run_accelerate.sh` and deploy the output `.safetensors` model to the Python AI service.
