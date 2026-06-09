# Checkpoint 0003 - Ollama-Style Layered Security AI

## Status

Added a layered Security AI path that can use an Ollama-compatible local model backend and fall back to deterministic heuristics.

## What Changed

- Added a security knowledge base for retrieval-style context.
- Added a prompt builder that formats Ollama-style chat messages.
- Added a backend abstraction with a local heuristic fallback and an Ollama chat client.
- Updated the Security AI engine to run layered inference and record reasoning layers in the audit trail.
- Expanded tests to cover prompt construction and retrieved security context.
- Updated the README and Security AI design note to reflect the Ollama-style architecture.

## Why It Changed

The service needed a more realistic path toward a deep security model with layered reasoning, while keeping the offline test harness stable.

## Relevant Notes

- [[Implementation Blueprint]]
- [[Shared_Contracts]]
- [[Security_AI_Agent]]
- [[Decision Engine]]
- [[Project_checkpoints/0002_python_security_ai_scaffold]]

## Relevant Code

- `security_ai_service/knowledge.py`
- `security_ai_service/prompts.py`
- `security_ai_service/backends.py`
- `security_ai_service/engine.py`
- `security_ai_service/runner.py`
- `tests/test_engine.py`
- `README.md`

## Validation

- Passed on 2026-06-09:

```text
python -m unittest discover -s tests
Ran 11 tests
OK
```

## Next Step

Replace the heuristic fallback with a real fine-tuned security model and a persistent retrieval store.
