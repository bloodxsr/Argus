Fine-tune with Accelerate
=========================

Quickstart
----------

1. Install requirements (example):

```bash
pip install -U transformers datasets accelerate peft bitsandbytes
```

2. Review `accelerate_config.yaml` and adjust `num_processes` / `mixed_precision`.

3. Prepare a JSONL dataset where each line contains `{"instruction": "...", "response": {...}}`.

4. Run training (example single-node single-GPU):

```bash
./train/run_accelerate.sh --model mistralai/mistral-7b-v0.1 --dataset ./data/synthetic_security_train.jsonl --output_dir ./outputs/mistral_lora --epochs 3 --batch_size 4
```

Notes
-----
- This wrapper uses `accelerate launch` to start the training script `train/fine_tune_lora.py`.
- If you do not have GPUs, set `use_cpu: true` in `accelerate_config.yaml`, but training large LLMs on CPU is impractical.
- Adjust `mixed_precision` (`fp16`/`bf16`) according to your hardware.
