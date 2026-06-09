import os
from tokenizers import Tokenizer, models, pre_tokenizers, trainers, decoders, processors

# gotta build our own tokenizer, standard ones butcher IPs and syslogs
def build_tokenizer(data_dir: str, out_path: str, vocab_size: int = 32000):
    print("spinning up tokenizer...")
    
    tok = Tokenizer(models.BPE(unk_token="<unk>"))
    
    # byte level is best for raw logs
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tok.decoder = decoders.ByteLevel()

    # special tokens for the pipeline
    specials = [
        "<unk>", "<s>", "</s>", "<pad>", 
        "<|telemetry|>", "<|investigation|>", "<|decision|>", "<|action|>",
        "<|user|>", "<|system|>"
    ]
    
    trainer = trainers.BpeTrainer(
        vocab_size=vocab_size,
        special_tokens=specials,
        show_progress=True,
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet()
    )

    files = []
    if os.path.exists(data_dir):
        for r, _, f in os.walk(data_dir):
            for file in f:
                if file.endswith((".txt", ".json", ".log")):
                    files.append(os.path.join(r, file))
    
    if not files:
        print(f"no files found in {data_dir}. creating dummy.")
        os.makedirs(data_dir, exist_ok=True)
        dummy = os.path.join(data_dir, "dummy_logs.txt")
        with open(dummy, "w") as f:
            f.write("192.168.1.50 - - [12/Oct/2026:14:32:00] 'POST /api/login HTTP/1.1' 200\n")
            f.write("eBPF sys_enter_execve: pid=1337 comm=bash filename=/bin/sh\n")
            f.write('{"classification": "Lateral Movement", "confidence": 0.95}\n')
        files.append(dummy)

    print(f"training on {len(files)} files")
    tok.train(files, trainer)

    # auto add <s> and </s>
    bos = tok.token_to_id("<s>")
    eos = tok.token_to_id("</s>")
    tok.post_processor = processors.TemplateProcessing(
        single="<s> $A </s>",
        pair="<s> $A </s> <s> $B </s>",
        special_tokens=[("<s>", bos), ("</s>", eos)],
    )

    tok.save(out_path)
    print(f"saved tokenizer to {out_path}")

if __name__ == "__main__":
    os.makedirs("models/custom-tokenizer", exist_ok=True)
    build_tokenizer("data/raw_corpus", "models/custom-tokenizer/tokenizer.json")
