# Checkpoint 0006 - Scenario Replay Pipeline

## Status

Added a reusable scenario replay path for demos, API calls, and future website integration.

## What Changed

- Added `security_ai_service/replay.py`.
- Added CLI usage:
  - `python -m security_ai_service.replay`
  - `python -m security_ai_service.replay rce_c2_beacon`
- Reused replay logic from the API route `POST /scenarios/{scenario_id}/run`.
- Added replay tests for:
  - high-risk auto-execution simulation
  - medium-risk human review creation
- Updated README.

## Why It Changed

The Test Website and Report / Result Website need a deterministic way to run the same scenario and get the same incident, AI result, decision, action record, and review payloads.

## Validation

Passed on 2026-06-09:

```text
python -m unittest discover -s tests
Ran 17 tests
OK
```

CLI smoke check passed:

```text
python -m security_ai_service.replay rce_c2_beacon --compact
action: kill_process
auto_execute: true
```

## Relevant Notes

- [[Project Outcomes and Implementation Plan]]
- [[Shared_Contracts]]
- [[Project_checkpoints/0005_shared_contracts_and_scenarios]]

## Relevant Code

- `security_ai_service/replay.py`
- `security_ai_service/api.py`
- `tests/test_replay.py`
- `README.md`

## Next Step

Build the first website surface around these replay endpoints: scenario launcher, live pipeline view, and report view.
