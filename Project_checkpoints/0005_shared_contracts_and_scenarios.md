# Checkpoint 0005 - Shared Contracts and Scenarios

## Status

Implemented the first concrete foundation for splitting Argus into the Test Website, Core Agent, and Report / Result Website.

## What Changed

- Added shared JSON schemas under `contracts/`.
- Added replayable demo fixtures under `scenarios/`.
- Added shared dataclasses for:
  - UnifiedEvent
  - Incident
  - RiskScore
  - ActionRecord
  - ReviewDecision
  - Scenario
- Added scenario loading helpers in `security_ai_service/scenarios.py`.
- Expanded evaluation coverage for container, UEBA, and APT-style cases.
- Added scenario API routes:
  - `GET /scenarios`
  - `POST /scenarios/{scenario_id}/run`
- Cleaned the older FastAPI integration example to use `CompanyConstraints`.
- Added tests for scenario loading, scenario evaluation, schema JSON validity, and new contract serialization.
- Updated README and [[Shared_Contracts]].

## Why It Changed

The next project phase needs stable contracts and demo data before separate repos can be safely created.

## Validation

Passed on 2026-06-09:

```text
python -m unittest discover -s tests
Ran 15 tests
OK
```

## Relevant Notes

- [[Project Outcomes and Implementation Plan]]
- [[Shared_Contracts]]
- [[Implementation Blueprint]]
- [[Project_checkpoints/0004_project_direction_and_model_integrity]]

## Relevant Code

- `contracts/*.schema.json`
- `scenarios/*.json`
- `security_ai_service/models.py`
- `security_ai_service/scenarios.py`
- `security_ai_service/evaluation.py`
- `security_ai_service/api.py`
- `tests/test_scenarios.py`
- `tests/test_schema_validation.py`

## Next Step

Add a small front-end demo or CLI replay command that streams scenario events through the pipeline in order.
