# Checkpoint 0016: Production Telemetry Architecture

## Summary
The AGRUS telemetry framework has been fully migrated from a demonstration/live-mock state into a robust, production-grade endpoint detection suite. All simulated loops have been deleted. The sensors now rely exclusively on real OS telemetry, and network operations have been decoupled to prevent bottlenecking.

## Key Upgrades

### 1. Linux eBPF Sensor (`ebpf` and `sensor`)
- **Native Memory Probing:** Replaced the `aya_log` shortcut with a genuine `PerfEventArray`. The eBPF kernel program pushes a C-struct (`ProcessExecEvent`) directly to the ring buffer.
- **Contextual Enrichment:** Added `bpf_get_current_comm` to the eBPF tracepoint to extract the 16-byte raw process string natively from the kernel, granting the AI immediate insight into the executing command (e.g., `bash`, `nmap`).
- **Memory Fix:** Addressed a critical `BytesMut` buffer exhaustion bug by explicitly clearing cursors in the `read_events` asynchronous loop.
- **PID Accuracy:** Fixed the `bpf_get_current_pid_tgid()` bitwise extraction to properly segregate the TGID (User-space PID) from the TID (Kernel Thread ID).

### 2. Windows WMI Sensor (`windows-sensor`)
- **True WMI Tracing:** Stripped out the fake ETW loop and implemented a real COM library connection leveraging `wmi`.
- **Process Creation:** The sensor natively subscribes to `Win32_ProcessStartTrace` events via `exec_notification_query_async`, pulling true telemetry (PID, parent PID, command strings) directly from the OS.

### 3. Network Architecture & Gateway
- **Asynchronous Batching:** Both sensors now feature a decoupled network architecture. Kernel streams push to a `tokio::sync::mpsc` channel, while a dedicated worker aggregates events into batches of 50.
- **High-Throughput Ingestion:** Rewrote the Go Gateway (`gateway/main.go`) to natively unmarshal `[]TelemetryEvent` JSON arrays, dramatically reducing HTTP connection overhead and ensuring the `incidents.scored` NATS topic can handle process spikes during malware detonation.
