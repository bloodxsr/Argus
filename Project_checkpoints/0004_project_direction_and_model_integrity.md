# Checkpoint 0004 - Project Direction and Model Integrity

## Status

Converted the project notes and current code state into a concrete product direction, possible outcomes, and implementation plan.

## What Changed

- Added [[Project Outcomes and Implementation Plan]].
- Confirmed the three-repo split is appropriate if shared contracts stay canonical.
- Documented possible product outcomes:
  - hackathon demo MVP
  - AI-native SOAR
  - lightweight EDR prototype
  - container runtime security
  - UEBA and behavioral risk
  - APT investigation assistant
  - compliance and audit automation
- Checked the Security AI model/service path.
- Ran the unit test suite.
- Fixed a training scaffold integrity issue in `train/fine_tune_lora.py`.

## Why It Changed

The project needed a clearer bridge from broad cybersecurity ambition to an implementable hackathon and product roadmap.

## Model Integrity Notes

- Current AI path is structurally coherent and testable.
- Current backend is a heuristic/Ollama-compatible reasoning shell, not yet a trained custom model.
- Retrieval and evaluation exist, but persistent memory and analyst-feedback learning are not implemented yet.
- Fine-tuning is scaffolded; full training still needs validation on target hardware.

## Validation

```text
python -m unittest discover -s tests
Ran 11 tests in 0.002s
OK
```

## Relevant Notes

- [[00 - Project Vision]]
- [[01 - System Architecture]]
- [[Implementation Blueprint]]
- [[Shared_Contracts]]
- [[Security AI Agent]]
- [[Project Outcomes and Implementation Plan]]
- [[Project_checkpoints/0003_ollama_style_layered_security_ai]]

## Relevant Code

- `security_ai_service/engine.py`
- `security_ai_service/backends.py`
- `security_ai_service/models.py`
- `security_ai_service/evaluation.py`
- `security_ai_service/critic.py`
- `security_ai_service/retriever.py`
- `train/fine_tune_lora.py`

## Next Step

Create shared JSON schemas and scenario fixtures so the Test Website, Core Agent, and Report Website can be split into separate repos without contract drift.
