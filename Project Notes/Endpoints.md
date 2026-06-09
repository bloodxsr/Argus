# Endpoint Deployment Architecture & Data Flow

This document outlines the exact deployment model and data flow from the smallest individual server endpoint to the centralized AI engine.

## 1. The Decentralized Endpoint (The "Smallest Server")
The only component installed on individual production servers (web servers, databases, laptops) is the **Sensor**. 
- The Sensor is a lightweight Rust daemon (`agrus-sensor` for Linux, `agrus-windows-sensor` for Windows).
- It consumes negligible RAM and CPU, ensuring no performance degradation to the host.

## 2. Deep Kernel Hooking (eBPF & ETW)
The sensor does not poll user-space logs. Instead, it hooks directly into the core Operating System kernel:
- **Linux:** Uses `eBPF` to attach to tracepoints (e.g., `sys_enter_execve`).
- **Windows:** Subscribes to `Event Tracing for Windows (ETW)` (e.g., `Microsoft-Windows-Kernel-Process`).
Because these hooks sit at the kernel level, malicious actors cannot bypass detection by deleting logs or using user-space rootkits to hide their processes. The kernel sees every raw execution.

## 3. Microsecond Event Trigger
When an event occurs (e.g., an attacker attempts to spawn a reverse shell via `bash -i`), the kernel intercepts the syscall and instantly triggers the sensor's probe. 

## 4. Secure Telemetry Dispatch
The Rust sensor packages the raw syscall data (PID, Parent Process, File Path, Hostname, Timestamp) into a lightweight JSON `TelemetryEvent`. It appends a cryptographic `Bearer Token` to the HTTP headers and transmits the payload across the network to the central Gateway. Once dispatched, the endpoint's job is done.

## 5. The Centralized Brain (SOC / Cloud)
The rest of the AGRUS stack runs in a centralized cluster, physically separated from the endpoints:
1. **The Gateway:** Authenticates the incoming telemetry via the Bearer Token and publishes it to the central NATS Message Bus.
2. **NATS Message Bus:** Distributes the high-velocity telemetry streams.
3. **The Web Backend / AI Engine:** The Node.js server ingests the live NATS stream, enriches the data, and POSTs it to the Python Security AI Engine. 
4. **HitL Decision Engine:** The AI scores the risk and maps it to MITRE ATT&CK. If an active mitigation is required, it enforces the "Daddy" Rule (Human-in-the-Loop) and flags it for review rather than auto-executing.
5. **Live SOC Dashboard:** The flagged incident immediately flashes onto the React dashboard for the human analyst to review and authorize.
