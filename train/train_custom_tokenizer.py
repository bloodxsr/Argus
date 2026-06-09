"""
Script to train a custom Tokenizer strictly for Cybersecurity.
Standard tokenizers (like OpenAI's or LLaMA's) split IP addresses, file paths, and hex codes inefficiently.
By training our own BPE tokenizer on raw logs, eBPF traces, and JSON schemas,
the model will learn to read security telemetry natively.
"""

import os
from tokenizers import Tokenizer, models, pre_tokenizers, trainers, decoders, processors

def train_security_tokenizer(corpus_dir: str, output_path: str, vocab_size: int = 32000):
    print(f"Initializing custom BPE tokenizer...")
    
    # Initialize a Byte-Pair Encoding Tokenizer
    tokenizer = Tokenizer(models.BPE(unk_token="<unk>"))
    
    # We use ByteLevel pre-tokenizer to handle all raw bytes, spaces, and weird characters in logs perfectly
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tokenizer.decoder = decoders.ByteLevel()

    # Define special tokens specific to our SOAR/EDR architecture
    special_tokens = [
        "<unk>", "<s>", "</s>", "<pad>", 
        "<|telemetry|>", "<|investigation|>", "<|decision|>", "<|action|>",
        "<|user|>", "<|system|>"
    ]
    
    trainer = trainers.BpeTrainer(
        vocab_size=vocab_size,
        special_tokens=special_tokens,
        show_progress=True,
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet()
    )

    # Gather all raw text files, logs, and JSONs for training
    files = []
    if os.path.exists(corpus_dir):
        for root, _, filenames in os.walk(corpus_dir):
            for filename in filenames:
                if filename.endswith(".txt") or filename.endswith(".json") or filename.endswith(".log"):
                    files.append(os.path.join(root, filename))
    
    if not files:
        print(f"Warning: No training files found in {corpus_dir}. Create a dummy file for demonstration.")
        os.makedirs(corpus_dir, exist_ok=True)
        dummy_file = os.path.join(corpus_dir, "dummy_logs.txt")
        with open(dummy_file, "w") as f:
            f.write("192.168.1.50 - - [12/Oct/2026:14:32:00] 'POST /api/login HTTP/1.1' 200\n")
            f.write("eBPF sys_enter_execve: pid=1337 comm=bash filename=/bin/sh\n")
            f.write('{"classification": "Lateral Movement", "confidence": 0.95}\n')
        files.append(dummy_file)

    print(f"Training custom tokenizer on {len(files)} files...")
    tokenizer.train(files, trainer)

    # Add post-processor to automatically add <s> and </s> to sequences
    bos_token_id = tokenizer.token_to_id("<s>")
    eos_token_id = tokenizer.token_to_id("</s>")
    tokenizer.post_processor = processors.TemplateProcessing(
        single="<s> $A </s>",
        pair="<s> $A </s> <s> $B </s>",
        special_tokens=[("<s>", bos_token_id), ("</s>", eos_token_id)],
    )

    # Save the tokenizer
    tokenizer.save(output_path)
    print(f"Custom Cybersecurity Tokenizer saved to: {output_path}")

if __name__ == "__main__":
    os.makedirs("models/custom-tokenizer", exist_ok=True)
    train_security_tokenizer("data/raw_corpus", "models/custom-tokenizer/tokenizer.json")
