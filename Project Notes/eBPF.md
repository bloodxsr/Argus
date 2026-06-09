# eBPF

Kernel-level observability technology. Captures what's happening inside the OS without modifying application code.

Feeds data into [[Telemetry Layer]].

---

## What It Captures

- Every process created and terminated (with full parent chain)
- Every file opened, read, written, deleted
- Every network connection opened or closed
- Every syscall made by any process
- Memory maps and executable loading

This is ground truth. Applications cannot hide from eBPF because it runs in the kernel, not in userspace.

---

## Why eBPF Over Alternatives

| Method | Can Be Evaded? | Performance Cost |
|---|---|---|
| Auditd | Yes (high noise, can be disabled) | High |
| ptrace | Yes (anti-debug tricks) | Very high |
| LD_PRELOAD hooks | Yes (static binaries bypass) | Medium |
| eBPF | No (kernel-level, always-on) | Very low (<3% CPU) |

---

## Implementation: Aya (Rust)

Aya is a Rust library for writing eBPF programs. Safe, no C required, integrates with tokio.

```toml
# Cargo.toml — eBPF sensor crate
[dependencies]
aya = "0.12"
aya-log = "0.2"
tokio = { version = "1", features = ["full"] }
async-nats = "0.33"
```

### Process Probe (kprobe on execve)

```rust
// eBPF program — attached to execve syscall
// Captures every process creation
use aya::programs::KProbe;

let prog: &mut KProbe = bpf.program_mut("trace_execve").unwrap().try_into()?;
prog.load()?;
prog.attach("__x64_sys_execve", 0)?;
```

### Network Probe (kprobe on tcp_connect)

```rust
let prog: &mut KProbe = bpf.program_mut("trace_tcp_connect").unwrap().try_into()?;
prog.load()?;
prog.attach("tcp_connect", 0)?;
```

### Reading Events from Kernel Ring Buffer

```rust
// eBPF → userspace via perf event array or ring buffer
use aya::maps::perf::AsyncPerfEventArray;

let mut perf_array = AsyncPerfEventArray::try_from(bpf.take_map("EVENTS").unwrap())?;

for cpu_id in online_cpus()? {
    let mut buf = perf_array.open(cpu_id, None)?;
    tokio::spawn(async move {
        let mut bufs = (0..10)
            .map(|_| BytesMut::with_capacity(1024))
            .collect::<Vec<_>>();

        loop {
            let events = buf.read_events(&mut bufs).await.unwrap();
            for i in 0..events.read {
                let event = parse_event(&bufs[i]);
                publish_to_nats(&event).await;
            }
        }
    });
}
```

---

## Output Event Schema

```json
{
  "event_type": "PROCESS_START",
  "timestamp": "2026-06-08T20:15:30.123456Z",
  "pid": 2346,
  "ppid": 2345,
  "binary": "/tmp/x.sh",
  "args": ["/tmp/x.sh", "--silent"],
  "uid": 33,
  "gid": 33,
  "cwd": "/var/www/html",
  "host": "prod-server-01"
}
```

```json
{
  "event_type": "TCP_CONNECT",
  "pid": 2346,
  "src_ip": "10.0.0.5",
  "src_port": 49152,
  "dst_ip": "185.x.x.x",
  "dst_port": 4444,
  "host": "prod-server-01"
}
```

---

## MVP Alternative (If eBPF Is Too Complex for Hackathon)

For hackathon MVP: ship a **synthetic event generator** that emits the same JSON schema.

```python
# event_simulator.py
# Generates a realistic attack sequence
import asyncio, nats, json, time

ATTACK_SEQUENCE = [
    {"event_type": "PROCESS_START", "binary": "/usr/sbin/nginx", "pid": 1000},
    {"event_type": "PROCESS_START", "binary": "/bin/bash", "pid": 1001, "ppid": 1000},
    {"event_type": "PROCESS_START", "binary": "/tmp/x.sh", "pid": 1002, "ppid": 1001},
    {"event_type": "FILE_ACCESS",   "path": "/etc/passwd", "pid": 1002, "op": "READ"},
    {"event_type": "TCP_CONNECT",   "dst_ip": "185.x.x.x", "dst_port": 4444, "pid": 1002},
]

async def simulate():
    nc = await nats.connect("nats://localhost:4222")
    for event in ATTACK_SEQUENCE:
        event["timestamp"] = time.time()
        event["host"] = "demo-server"
        await nc.publish("telemetry.raw", json.dumps(event).encode())
        await asyncio.sleep(1)  # 1 second between events

asyncio.run(simulate())
```

Judges care about the pipeline, not the kernel module. Ship the simulator for demo, ship real eBPF for production.

---

## Scalability

- eBPF sensor is per-host — one lightweight sensor process per server
- CPU overhead: <3% on modern kernels
- Each sensor connects to nearest NATS node and publishes events
- At 1000-host scale: 1000 sensors publishing to NATS cluster — NATS handles this easily
- Sensor crash: Linux restarts it via systemd, eBPF probes auto-reattach on startup
