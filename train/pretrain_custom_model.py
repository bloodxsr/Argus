"""
Script to PRE-TRAIN a completely custom Foundation Model from scratch.
We define a highly optimized, scaled-down Transformer architecture (similar to Llama)
specifically designed to process cybersecurity telemetry extremely fast.
"""

import os
from transformers import (
    LlamaConfig,
    LlamaForCausalLM,
    PreTrainedTokenizerFast,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments
)
from datasets import load_dataset

def create_custom_architecture() -> LlamaForCausalLM:
    # We define a custom ~1.5 Billion Parameter Model
    # Big enough to reason about APTs, small enough to infer in milliseconds.
    config = LlamaConfig(
        vocab_size=32000,           # Matches our custom tokenizer
        hidden_size=2048,           # Width of the neural network
        intermediate_size=5504,     # MLP layer size
        num_hidden_layers=22,       # Depth of the network
        num_attention_heads=32,     
        num_key_value_heads=8,      # Grouped Query Attention for fast inference
        max_position_embeddings=4096, # 4K Context window for dense logs
        bos_token_id=1,
        eos_token_id=2,
    )
    
    print("Initializing custom model weights from scratch...")
    model = LlamaForCausalLM(config)
    print(f"Model Parameters: {model.num_parameters() / 1e6:.2f} Million")
    return model

def pretrain_model():
    tokenizer_path = "models/custom-tokenizer/tokenizer.json"
    if not os.path.exists(tokenizer_path):
        print(f"Error: Tokenizer not found at {tokenizer_path}. Run train_custom_tokenizer.py first.")
        return

    # Load our custom trained tokenizer
    tokenizer = PreTrainedTokenizerFast(tokenizer_file=tokenizer_path)
    tokenizer.pad_token = "<pad>"

    model = create_custom_architecture()

    # Load our massive pre-training corpus (raw logs, code, reports)
    # For demonstration, we use a dummy text dataset if a real one isn't present
    try:
        dataset = load_dataset("text", data_files={"train": ["data/raw_corpus/*.txt"]})
    except Exception:
        print("Using dummy dataset for demonstration...")
        # Create a tiny dummy dataset for the script to run without crashing
        os.makedirs("data/raw_corpus", exist_ok=True)
        with open("data/raw_corpus/dummy.txt", "w") as f:
            for _ in range(100):
                f.write("syslog sshd: Accepted publickey for root from 192.168.1.100 port 50123 ssh2\n")
        dataset = load_dataset("text", data_files={"train": ["data/raw_corpus/dummy.txt"]})

    # Tokenize the dataset
    def tokenize_function(examples):
        return tokenizer(examples["text"], truncation=True, max_length=1024)

    tokenized_datasets = dataset.map(tokenize_function, batched=True, remove_columns=["text"])

    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer, mlm=False
    )

    # Define training arguments (Configure for multi-GPU if available)
    training_args = TrainingArguments(
        output_dir="models/aisos-custom-v1",
        overwrite_output_dir=True,
        num_train_epochs=1,               # Set to much higher for real pre-training
        per_device_train_batch_size=4,
        gradient_accumulation_steps=8,
        save_steps=1000,
        save_total_limit=2,
        logging_steps=10,
        learning_rate=3e-4,
        weight_decay=0.1,
        fp16=True,                        # Use Mixed Precision for speed
        dataloader_num_workers=4,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets["train"],
        data_collator=data_collator,
    )

    print("Starting Pre-Training...")
    trainer.train()
    
    print("Pre-training complete. Saving final model...")
    trainer.save_model("models/aisos-custom-v1-final")
    tokenizer.save_pretrained("models/aisos-custom-v1-final")
    print("Custom model saved to models/aisos-custom-v1-final/")

if __name__ == "__main__":
    pretrain_model()
