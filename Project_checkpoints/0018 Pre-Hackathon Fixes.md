Project Checkpoint 0018 - Pre-Hackathon Pipeline Fixes & Tuning
======================================================
Date: 2026-06-11

## Overview
A comprehensive audit and cleanup of the end-to-end AGRUS pipeline was performed right before the hackathon, ensuring stable integration between the AI backend, the React dashboard, the Go gateway, and the Rust sensors. All local systems were properly spun down and verified.

## 1. Code Remediation Automation Safety
- **Issue:** The `remediation.py` engine would aggressively commit and push `"# Manual review required"` placeholder strings to the origin repository whenever the default fallback `HeuristicSecurityBackend` was active.
- **Fix:** Added guards inside `generate_fix()` to return an empty string for non-LLM backends, bypassing the PR creation process. 
- **Safety Switch:** Enforced a new `AGRUS_REMEDIATION_AUTO_PUSH=true` environment variable requirement to prevent unintended destructive git pushes to `origin`. It now defaults to safe local commits.

## 2. Container Orchestration within Docker
- **Issue:** The `security-ai` container, tasked with real-time incident isolation, could not access or interact with Docker because it lacked the CLI and socket permissions.
- **Fix:** Installed `docker.io` inside `Dockerfile.security-ai` and mapped the host's `/var/run/docker.sock` directly into the container via `docker-compose.yml`, successfully granting the AI control over peer containers for the demo.

## 3. Real-Time Dashboard Integration
- **Issue:** The `dashboard/src/main.jsx` frontend components requested API routes (`/api/correlations`, `/api/baselines`, `/api/containers`, etc.) that were never exposed by the Express backend.
- **Fix:** Appended eight fully functioning proxy routes into `dashboard/server/index.js` that authenticate and forward SPA traffic directly down into the `security-ai` API, bridging the data pipeline.

## 4. Multi-Platform Sensor Config
- **Issue:** The `windows-sensor` was dropping payloads because it lacked an `AGRUS_SENSOR_TOKEN` environment variable reader and hardcoded the gateway URL.
- **Fix:** Refactored `windows-sensor/src/main.rs` to use `dotenvy`, rigidly enforcing token existence (exiting on failure) and routing telemetry directly to the dynamic `AGRUS_GATEWAY_URL`.

## 5. Startup & Workspace Management
- **Documentation:** Modernized `README.md` and `scripts/dev_all.sh` to correctly reflect that NATS incident routing happens internally within `dashboard/server/index.js` rather than a deprecated `nats_agent.py`.
- **Environment Parity:** Created a standardized `.env.example` defining core tokens (`AGRUS_INTERNAL_TOKEN`, `AGRUS_SENSOR_TOKEN`, `AGRUS_GATEWAY_URL`) for instant onboarding.
- **Git State:** Added `security_ai_service.egg-info/` to `.gitignore` and enforced volume mounts for the `models/` directory inside Docker Compose so that hot-swapping trained AI weights requires zero container rebuilds.

## Conclusion
The stack is fully locked down. Background processes were purged with `docker compose down`. The system is prepared for instantaneous Llama-3.1 LLM integration once training completes.
