# Telemetry Layer

The Telemetry Layer collects, normalizes, and contextualizes raw data from all infrastructure sources into a unified event schema before publishing to the Event Bus. It bridges the gap between infrastructure-level kernel data and application-level behavior.

## Core Responsibilities
- Collect from all sources simultaneously (eBPF, OpenTelemetry, Docker, Kubernetes, Auditd).
- Normalize all events to a `Unified Event Schema`.
- Attach host metadata (hostname, IP, environment tag).
- Apply initial timestamp normalization.

---

## Unified Event Schema
Regardless of the source, every event arrives in a standardized format:
```json
{
  "schema_version": "1.0",
  "event_id": "uuid-v4",
  "source": "ebpf | auditd | otel | docker | k8s",
  "event_type": "PROCESS_START | FILE_ACCESS | TCP_CONNECT | API_ANOMALY | ...",
  "timestamp": "2026-06-08T20:15:30.123456Z",
  "host": "prod-server-01",
  "payload": { }
}
```

---

## Source Integrations

### 1. eBPF (Kernel Observability)
eBPF captures kernel-level ground truth without modifying application code or relying on userspace logging that attackers can evade.
- **Capabilities:** Captures every process created/terminated, file accessed, network connection, and syscall made.
- **Implementation:** Built using the `Aya` Rust library. Uses `kprobe` on syscalls like `execve` and `tcp_connect`, reading events from the kernel ring buffer into userspace.
- **Why eBPF?** Unlike Auditd or LD_PRELOAD hooks, eBPF is highly performant (<3% CPU overhead) and cannot be bypassed by attackers operating in userspace.

### 2. OpenTelemetry (Application Observability)
While eBPF sees OS-level calls, OpenTelemetry (OTel) sees application-level semantics, which is critical for detecting SQL injection, API abuse, and other application-layer attacks.
- **Capabilities:** Collects traces, metrics, and logs from applications. E.g., mapping a raw TCP connection to a specific SQL query (`SELECT * FROM users WHERE id=1 OR 1=1`).
- **Implementation:** Utilizes an OTEL Collector with filter processors to forward only security-relevant spans to AGRUS. The Telemetry Layer processes incoming OTel spans to flag anomalous HTTP patterns, SQL-like injection patterns, or unusual authentication failures.

### 3. Additional Collectors
- **Docker:** Hooks into the Docker Events API to stream real-time container lifecycle events.
- **Kubernetes:** Watches pod events via the Kubernetes API.
- **Auditd:** Parses `audit.log` lines into unified events.

---

## Scalability
- **Host-level:** One lightweight Telemetry Layer process per host for eBPF and Auditd.
- **Cluster-level:** A shared Telemetry Layer service per cluster for Docker/Kubernetes/OTel.
- **Buffering:** Buffers locally (SQLite) if NATS is temporarily unavailable to prevent data loss.
