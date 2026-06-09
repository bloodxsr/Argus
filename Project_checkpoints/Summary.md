Project Checkpoints — Summary
=============================

Overview
--------
This file summarizes the work performed during the Security AI project conversation, lists completed items, partially completed work, and outstanding tasks prioritized for next steps.

Completed Work
--------------
- Core Python scaffold: dataclasses, engine, backends, prompts, retriever, validation, critic.
- Ollama-style layered prompt + backend integration with a `HeuristicSecurityBackend` fallback.
- Qdrant retriever scaffold with deterministic fallback embedding and in-memory KB.
- FastAPI demo endpoint and NATS subscriber example for integration.
- Validation and `CriticVerifier` to enforce policy before auto-execution.
- Product direction note added: [[Project Outcomes and Implementation Plan]].
- Three-repo plan confirmed: Test Website, Core Agent / Security AI, Report / Result Website.
- Model integrity review completed: the current AI path is coherent and tested, but it is not yet a trained custom model or live learning system.
- Fixed `train/fine_tune_lora.py` so the LoRA text conversion path imports `json`.
- Shared JSON contracts added under `contracts/`.
- Demo scenario fixtures added under `scenarios/`.
- Scenario loader, scenario API routes, and expanded evaluation cases added.
- Scenario replay pipeline added for CLI/API/demo use.
- Static prototype websites added:
  - `test-website/static-prototype.html`
  - `report-website/static-prototype.html`
- MERN website scaffolds added:
  - `test-website/` React/Vite + Express + MongoDB
  - `report-website/` React/Vite + Express + MongoDB
- Training skeletons:
  - `train/fine_tune_lora.py` converted to a runnable trainer skeleton (dry-run + training loop using `transformers`, `datasets`, `peft` guarded by imports).
  - `train/create_synthetic_dataset.py` and `train/dataset_schema.md` (dataset schema guidance).
- Qdrant CLI: `train/qdrant_cli.py` (create/delete/list) with safe fallbacks.
- `accelerate` support: `train/accelerate_config.yaml`, `train/run_accelerate.sh`, and `train/README.md` with quickstart commands.
- Unit tests passing on 2026-06-09: 17 tests OK.
- Live API smoke check passing on 2026-06-09:
  - `GET /scenarios` returns 5 scenarios.
  - `POST /scenarios/rce_c2_beacon/run` returns `kill_process` with `auto_execute=true`.

Partially Complete / In-Progress
--------------------------------
- Harden MITRE ingestion and dedupe: improved `train/ingest_mitre.py` exists but needs more robust STIX parsing, canonicalization of technique IDs, metadata enrichment (tactics, mitigations), chunking, and batching for upserts.

Outstanding / Not Started
-------------------------
- Production-grade LoRA training pipeline:
  - Full `accelerate` + `bitsandbytes` + `peft` training tested on target hardware.
  - Official training configs (hyperparams, gradient checkpointing, bf16 support) tuned for Mistral-7B.
- Full STIX MITRE ingestion hardening and enrichment (see above).
- CI/CD and reproducible artifact packaging for model adapters (LoRA adapters), evaluation harness, and deployment images.

Next Actions (recommended order)
--------------------------------
1. Finish MITRE ingestion hardening: add `stix2` parsing, dedupe by canonical MITRE IDs, and add metadata payloads for Qdrant.
2. Install Node.js/npm, run `npm install` in both website directories, and smoke-test the MERN apps.
3. Turn the MERN website scaffolds into separate repos when ready.
4. Validate fine-tune process on a small GPU instance: install `bitsandbytes`, `accelerate`, run `train/run_accelerate.sh` with a small dataset to verify end-to-end.
5. Add a Docker-compose recipe (Qdrant + service + MongoDB + websites) and CI job to run core unit tests and ingestion smoke tests.
6. Produce a production runbook for safe auto-execution, detailing CriticVerifier thresholds and human escalation procedures.

Quick run examples
------------------
Create an accelerate environment and run a dry training check (no GPU required):

```bash
pip install -U transformers datasets accelerate peft bitsandbytes
./train/run_accelerate.sh --model mistralai/mistral-7b-v0.1 --dataset ./data/synthetic_security_train.jsonl --output_dir ./outputs/mistral_lora --epochs 1 --batch_size 1
```

Create a Qdrant collection (local):

```bash
python train/qdrant_cli.py --host 127.0.0.1 --port 6333 create security-kb
```

Status provenance
-----------------
This summary was generated on 2026-06-09 from the in-repo conversation, test results, and recent edits to training and tooling files.
