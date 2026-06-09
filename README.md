# Argus Security AI Service

This repository starts the Python Security AI layer for Argus.

## What it contains

- a structured Security AI output model
- a layered reasoning pipeline inspired by Ollama-style local model serving
- an Ollama-compatible chat backend for local LLM inference
- company constraints for per-tenant policy control
- an evaluation harness with test cases
- shared JSON contracts in `contracts/`
- demo scenario fixtures in `scenarios/`
- a tiny runner for local inspection

## Run the tests

```bash
/usr/bin/python -m unittest discover -s tests
```

## Run the demo

```bash
/usr/bin/python -m security_ai_service.runner
```

## Replay a scenario

```bash
/usr/bin/python -m security_ai_service.replay rce_c2_beacon
```

## Use the API

```bash
uvicorn security_ai_service.api:app --reload
```

Useful endpoints:

- `POST /analyze`
- `GET /scenarios`
- `POST /scenarios/{scenario_id}/run`

## Open the prototype websites

Start the API first, then open the standalone prototypes:

- `test-website/static-prototype.html`
- `report-website/static-prototype.html`

## MERN website scaffolds

The planned web stack is MERN. See `MERN_WEBSITE_PLAN.md`.

- `test-website/` contains a React/Vite + Express + MongoDB scenario launcher.
- `report-website/` contains a React/Vite + Express + MongoDB reporting app.

Node.js/npm are required to run the MERN apps.

## Run with Ollama

Set these environment variables before running the service:

```bash
export SECURITY_AI_OLLAMA_BASE_URL=http://localhost:11434
export SECURITY_AI_OLLAMA_MODEL=mistral
```

The service will use an Ollama chat endpoint when available and fall back to the deterministic local backend when it is not.

## Next step

Wire this service into the agent pipeline, add a real vector retrieval store, and train a security-tuned model on incident data.
