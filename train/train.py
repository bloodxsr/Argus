import os
import random
import torch
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments
)
from peft import get_peft_model, LoraConfig, TaskType
from datasets import load_dataset, concatenate_datasets

def get_unified_dataset() -> list:
    """
    Downloads and perfectly blends two datasets:
    1. SOC Analyst Workflow (High-level reasoning & reporting)
    2. Wazuh Alerts (Raw kernel payloads, database attacks, network scans)
    """
    print("Downloading SOC Analyst Dataset (The Brain)...")
    soc_dataset = load_dataset("AYI-NEDJIMI/soc-analyst-en", split="train")
    soc_sample = soc_dataset.select(range(min(5000, len(soc_dataset))))
    
    print("Downloading Raw Threat/Alert Dataset (The Muscle)...")
    raw_threat_dataset = load_dataset("kholil-lil/wazuh-alerts", split="train")

    print(f"Dataset columns: {raw_threat_dataset.column_names}")
    if 'input' not in raw_threat_dataset.column_names or 'output' not in raw_threat_dataset.column_names:
        raise ValueError(f"Expected 'input' and 'output' columns, but got: {raw_threat_dataset.column_names}")

    threat_sample = raw_threat_dataset.select(range(min(5000, len(raw_threat_dataset))))
    
    formatted_corpus = []
    
    
    for row in soc_sample:
        instruction = f"Analyze the following security event and provide a SOC assessment:\n{row.get('instruction', '')}"
        response = f"Assessment:\n{row.get('output', '')}"
        formatted_corpus.append(f"Instruction: {instruction}\n{response}")

    
    for row in threat_sample:
        
        
        instruction = f"Analyze the following raw endpoint telemetry and identify the threat:\n{row.get('input', '')}"
        response = f"Classification:\n{row.get('output', 'Malicious Payload Detected')}"
        formatted_corpus.append(f"Instruction: {instruction}\n{response}")
        
    print(f"Successfully blended {len(formatted_corpus)} training examples from parallel datasets!")
    random.shuffle(formatted_corpus)
    return formatted_corpus

def train_foundation_model():
    """The master function that handles the entire fine-tuning pipeline using Llama-3.1-8B-Instruct."""
    os.makedirs("models/agrus-v1-final", exist_ok=True)
    
    
    corpus = get_unified_dataset()
    
    
    print("Loading Pre-Trained Llama-3.1-8B Tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B-Instruct")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        
    
    print("Tokenizing unified dataset...")
    raw_dataset = Dataset.from_dict({"text": corpus})
    
    def tokenize_fn(batch):
        return tokenizer(batch["text"], truncation=True, max_length=2048)

    tokenized_dataset = raw_dataset.map(tokenize_fn, batched=True, remove_columns=["text"])
    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    
    print("Loading Pre-Trained Llama-3.1-8B Brain in 4-bit mode for RTX 4060 (8GB VRAM)...")
    
    from transformers import BitsAndBytesConfig
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    model = AutoModelForCausalLM.from_pretrained(
        "meta-llama/Llama-3.1-8B-Instruct",
        quantization_config=bnb_config,
        device_map="auto"
    )
    
    print("Injecting LoRA Adapters for fast CyberSecurity fine-tuning...")
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=16, 
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"] 
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    
    args = TrainingArguments(
        output_dir="models/agrus-v1",
        overwrite_output_dir=True,
        num_train_epochs=3, 
        per_device_train_batch_size=2, 
        gradient_accumulation_steps=4, 
        gradient_checkpointing=True, 
        save_steps=500,
        logging_steps=10,
        learning_rate=2e-4, 
        bf16=True, 
        optim="paged_adamw_8bit" 
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized_dataset,
        data_collator=collator,
    )

    print("Beginning Deep Learning Fine-Tuning Loop...")
    trainer.train()

    
    print("Saving final AGRUS Llama-3.1-8B Fine-Tune...")
    trainer.model.save_pretrained("models/agrus-v1-final")
    tokenizer.save_pretrained("models/agrus-v1-final")
    print("Training complete. Model is ready for deployment!")

if __name__ == "__main__":
    train_foundation_model()
