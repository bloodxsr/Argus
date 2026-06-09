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

# ~1.5B params. Good balance of speed and smarts for EDR.
def get_model() -> LlamaForCausalLM:
    cfg = LlamaConfig(
        vocab_size=32000,           
        hidden_size=2048,           
        intermediate_size=5504,     
        num_hidden_layers=22,       
        num_attention_heads=32,     
        num_key_value_heads=8,      # GQA for the win
        max_position_embeddings=4096, 
        bos_token_id=1,
        eos_token_id=2,
    )
    
    print("init weights...")
    model = LlamaForCausalLM(cfg)
    print(f"Params: {model.num_parameters() / 1e6:.2f}M")
    return model

def pretrain():
    tok_path = "models/custom-tokenizer/tokenizer.json"
    if not os.path.exists(tok_path):
        print("tokenizer missing. run train_custom_tokenizer.py first")
        return

    tokenizer = PreTrainedTokenizerFast(tokenizer_file=tok_path)
    tokenizer.pad_token = "<pad>"

    model = get_model()

    try:
        ds = load_dataset("text", data_files={"train": ["data/raw_corpus/*.txt"]})
    except Exception:
        print("falling back to dummy dataset...")
        os.makedirs("data/raw_corpus", exist_ok=True)
        with open("data/raw_corpus/dummy.txt", "w") as f:
            for _ in range(100):
                f.write("syslog sshd: Accepted publickey for root from 192.168.1.100 port 50123 ssh2\n")
        ds = load_dataset("text", data_files={"train": ["data/raw_corpus/dummy.txt"]})

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=1024)

    tokenized = ds.map(tokenize, batched=True, remove_columns=["text"])
    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    args = TrainingArguments(
        output_dir="models/agrus-v1",
        overwrite_output_dir=True,
        num_train_epochs=1, # TODO: bump this for actual training
        per_device_train_batch_size=4,
        gradient_accumulation_steps=8,
        save_steps=1000,
        save_total_limit=2,
        logging_steps=10,
        learning_rate=3e-4,
        weight_decay=0.1,
        fp16=True, # gotta go fast
        dataloader_num_workers=4,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized["train"],
        data_collator=collator,
    )

    print("training...")
    trainer.train()
    
    print("saving final model")
    trainer.save_model("models/agrus-v1-final")
    tokenizer.save_pretrained("models/agrus-v1-final")

if __name__ == "__main__":
    pretrain()
