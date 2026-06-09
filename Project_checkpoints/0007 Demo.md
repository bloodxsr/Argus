# Checkpoint 0007 - Static Demo Websites

## Status

Added first static website surfaces for the Test Website and Report / Result Website plan.

## What Changed

- Added `test-website/index.html`.
- Added `report-website/index.html`.
- The test website can list API scenarios, launch a replay, show pipeline status, and inspect the replay payload.
- The report website can generate an audit-style report from the same replay endpoint.
- Enabled API CORS for local static demo pages.
- Updated README with website entry points.

## Why It Changed

The project needed visible surfaces around the core service so the hackathon MVP can demonstrate the full loop: scenario trigger, AI decision, response simulation, and audit report.

## Validation

Passed on 2026-06-09:

```text
python -m unittest discover -s tests
Ran 17 tests
OK
```

API smoke check passed:

```text
GET /scenarios -> 5 scenarios
POST /scenarios/rce_c2_beacon/run -> action kill_process, auto_execute true
```

Local API server started:

```text
http://127.0.0.1:8000
```

## Relevant Notes

- [[Project Outcomes and Implementation Plan]]
- [[Shared_Contracts]]
- [[Project_checkpoints/0006_scenario_replay_pipeline]]

## Relevant Files

- `test-website/index.html`
- `report-website/index.html`
- `security_ai_service/api.py`
- `security_ai_service/replay.py`

## Next Step

Turn the static websites into separate repos or a proper Vite/Next app when the demo flow needs richer routing and persistent state.
