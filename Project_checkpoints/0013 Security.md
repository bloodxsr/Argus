# Checkpoint 0013: Security Hardening & Sensor Alignment

## Status
Completed

## Changed Files
- `agrus-sensor/Cargo.toml`
- `agrus-sensor/src/main.rs`
- `agrus-gateway/main.go`
- `security_ai_service/engine.py`
- `agrus-windows-sensor/Cargo.toml` (new)
- `agrus-windows-sensor/src/main.rs` (new)
- `agrus-ebpf/Cargo.toml` (new)
- `agrus-ebpf/src/main.rs` (new)
- `agrus-ebpf/.cargo/config.toml` (new)

## Related Notes
- [[Telemetry Layer]]
- [[Shared Contracts]]
- [[Decision Engine]]

## Changes
1. **Sensor Alignment**:
   - Updated the generated telemetry payload in the eBPF and ETW sensors to strictly follow the JSON schema detailed in `Project Notes/Telemetry_Layer.md` and `Project Notes/Shared_Contracts.md`. Specifically aligned the `source` to `"ebpf"` and `"etw"`, and `event_type` to `"PROCESS_START"`.
2. **Infrastructure Security (Gateway)**:
   - Implemented rigorous Bearer token authentication logic within `agrus-gateway/main.go` to reject unauthenticated telemetry ingestion, stopping spoofing and DoS attacks against the NATS bus and AI engine.
3. **True Kernel Integration**:
   - Replaced commented-out dummy code in `agrus-sensor` with the actual Aya loader and added the foundational `agrus-ebpf` kernel-space source crate so it successfully targets `bpfel-unknown-none`.
   - Created `agrus-windows-sensor` implementing analogous low-level kernel introspection natively using ETW (Event Tracing for Windows) for Windows deployments.
4. **HitL Decision Engine Refactor**:
   - Ripped out autonomous mitigation logic bypassing in `security_ai_service/engine.py`. Hard-coded a rule stating `if action != "observe": requires_human_approval = True`. This guarantees the highest level of security remains completely Human-in-the-Loop, preventing runaway AI mitigations.

## Next Step
Fully train the internal classification models, implement the mTLS framework if Bearer tokens are deemed insufficient for zero-trust, and build out the reporting UI for the human decision-makers.
