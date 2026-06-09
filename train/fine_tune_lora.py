"""Skeleton script to fine-tune a base model with LoRA (PEFT).

This script is a starting point. It assumes you have GPU access and relevant packages
installed: `transformers`, `accelerate`, `peft`, `datasets`, and `bitsandbytes` for 4-bit.

Adjust `model_name`, `dataset_path`, and training hyperparams before running.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="mistralai/mistral-7b-v0.1", help="HF model repo to fine-tune")
    p.add_argument("--dataset", default="synthetic_security_train.jsonl", help="JSONL dataset path")
    p.add_argument("--output_dir", default="security_mistral_lora", help="Where to save the LoRA adapter")
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch_size", type=int, default=8)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print("Dataset not found. Run train/create_synthetic_dataset.py first or provide a dataset.")
        return 2

    # Note: full training implementation omitted for brevity.
    # This file outlines the recommended libraries and steps.

    print("Fine-tune skeleton: follow README and update this script to your infra.")
    print(f"Model: {args.model}")
    print(f"Dataset: {dataset_path}")
    print(f"Output dir: {args.output_dir}")
    # Try to import training libs; if missing, run a dry-run check
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
        from datasets import load_dataset
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        import torch
    except Exception as e:
        print("Training dependencies are not installed or environment not ready for full training.")
        print("Dry-run info:")
        print(f"Model: {args.model}")
        print(f"Dataset: {dataset_path}")
        print(f"Output dir: {args.output_dir}")
        print("Install transformers, datasets, accelerate, peft, bitsandbytes to run full training.")
        return 0

    # Load dataset (assumes JSONL with instruction/response pairs)
    ds = load_dataset("json", data_files=str(dataset_path))
    # Map to prompt/completion structure (simple example)
    def to_text(example):
        instr = example.get("instruction", "")
        resp = example.get("response", {})
        completion = json.dumps(resp, ensure_ascii=False)
        prompt = instr + "\n\nResponse:\n"
        return {"text": prompt + completion}

    ds = ds.map(lambda ex: to_text(ex), remove_columns=ds.column_names[0])

    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    tokenizer.pad_token = tokenizer.eos_token

    def tokenize_fn(ex):
        return tokenizer(ex["text"], truncation=True, max_length=1024)

    tokenized = ds.map(tokenize_fn, batched=True)

    model = AutoModelForCausalLM.from_pretrained(args.model, load_in_4bit=True, device_map="auto")
    model = prepare_model_for_kbit_training(model)
    lora_config = LoraConfig(r=8, lora_alpha=32, target_modules=["q_proj", "v_proj"], lora_dropout=0.1, bias="none")
    model = get_peft_model(model, lora_config)

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        logging_steps=10,
        save_strategy="epoch",
    )

    trainer = Trainer(model=model, args=training_args, train_dataset=tokenized["train"]) if "train" in tokenized else Trainer(model=model, args=training_args, train_dataset=tokenized)
    trainer.train()
    model.save_pretrained(args.output_dir)
    print("Training finished; LoRA adapter saved to", args.output_dir)
    return 0

    # Example commands (run in shell after installing requirements):
    # python -m venv .venv && source .venv/bin/activate
    # pip install -r requirements.txt
    # python train/create_synthetic_dataset.py
    # python train/fine_tune_lora.py --model mistralai/mistral-7b-v0.1 --dataset synthetic_security_train.jsonl --output_dir ./security_mistral_lora --epochs 3


    return 0


if __name__ == "__main__":
    raise SystemExit(main())
