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
    threat_sample = raw_threat_dataset.select(range(min(5000, len(raw_threat_dataset))))
    
    formatted_corpus = []
    
    # Process SOC Dataset
    for row in soc_sample:
        instruction = f"Analyze the following security event and provide a SOC assessment:\n{row.get('instruction', '')}"
        response = f"Assessment:\n{row.get('output', '')}"
        formatted_corpus.append(f"Instruction: {instruction}\n{response}")

    # Process Raw Threat Dataset
    for row in threat_sample:
        # Wazuh dataset has different columns, typically 'alert' and 'classification'
        # We mold it into the exact same prompt structure so the AI learns to treat raw payloads as SOC events.
        instruction = f"Analyze the following raw endpoint telemetry and identify the threat:\n{row.get('text', '')}"
        response = f"Classification:\n{row.get('label', 'Malicious Payload Detected')}"
        formatted_corpus.append(f"Instruction: {instruction}\n{response}")
        
    print(f"Successfully blended {len(formatted_corpus)} training examples from parallel datasets!")
    random.shuffle(formatted_corpus)
    return formatted_corpus

def train_foundation_model():
    """The master function that handles the entire fine-tuning pipeline using Llama-3.1-8B-Instruct."""
    os.makedirs("models/agrus-v1-final", exist_ok=True)
    
    # 1. Generate Unified Data
    corpus = get_unified_dataset()
    
    # 2. Load Pre-trained Tokenizer
    print("Loading Pre-Trained Llama-3.1-8B Tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B-Instruct")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        
    # 3. Prepare HuggingFace Dataset
    print("Tokenizing unified dataset...")
    raw_dataset = Dataset.from_dict({"text": corpus})
    
    def tokenize_fn(batch):
        return tokenizer(batch["text"], truncation=True, max_length=1024)

    tokenized_dataset = raw_dataset.map(tokenize_fn, batched=True, remove_columns=["text"])
    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    # 4. Initialize Pre-trained Llama-3-8B Model with QLoRA (4-bit)
    print("Loading Pre-Trained Llama-3.1-8B Brain in 4-bit mode for RTX 4050...")
    
    from transformers import BitsAndBytesConfig
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16
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
        r=8, # Reduced back to 8 because 8B model eats up way more VRAM
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"] # Target all attention layers
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    # 5. Execute Training Loop
    args = TrainingArguments(
        output_dir="models/agrus-v1",
        overwrite_output_dir=True,
        num_train_epochs=1,
        per_device_train_batch_size=1, # Reduced to 1 to fit in 6GB VRAM
        gradient_accumulation_steps=8, # Compensate for small batch size
        save_steps=500,
        logging_steps=10,
        learning_rate=2e-4, 
        fp16=True, 
        optim="paged_adamw_8bit" # 8-bit optimizer to save even more VRAM
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized_dataset,
        data_collator=collator,
    )

    print("Beginning Deep Learning Fine-Tuning Loop...")
    trainer.train()

    # 6. Save Artifacts
    print("Saving final AGRUS Llama-3.1-8B Fine-Tune...")
    trainer.model.save_pretrained("models/agrus-v1-final")
    tokenizer.save_pretrained("models/agrus-v1-final")
    print("Training complete. Model is ready for deployment!")

if __name__ == "__main__":
    train_foundation_model()
