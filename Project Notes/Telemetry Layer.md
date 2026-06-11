# Telemetry Layer

Collects and normalizes raw data from all infrastructure sources into a unified event schema before publishing to the Event Bus.

## Sources
- [[eBPF]]
- [[OpenTelemetry]]
- Docker
- Kubernetes
- Auditd

Feeds data into [[Event Bus]].

---

## Responsibilities

- Collect from all sources simultaneously
- Normalize all events to the unified schema
- Attach host metadata (hostname, IP, environment tag)
- Apply initial timestamp normalization (UTC everywhere)
- Forward to Event Bus

---

## Unified Event Schema

Every event, regardless of source, arrives in this format:

```json
{
  "schema_version": "1.0",
  "event_id": "uuid-v4",
  "source": "ebpf | auditd | otel | docker | k8s",
  "event_type": "PROCESS_START | PROCESS_END | FILE_ACCESS | NET_CONNECT | LOGIN | ...",
  "timestamp": "2026-06-08T20:15:30.123456Z",
  "host": "prod-server-01",
  "host_ip": "10.0.0.5",
  "environment": "production",
  "pid": 1234,
  "uid": 33,
  "payload": { }
}
```

---

## Source-Specific Collectors

### eBPF Collector
See [[eBPF]] for full implementation.

Captures: process events, network events, file events, syscalls.

### Auditd Collector

```rust
// Parse auditd log lines into unified events
// /var/log/audit/audit.log
async fn parse_auditd(line: &str) -> Option<UnifiedEvent> {
    // type=EXECVE msg=audit(1234567890.123:456): ...
    // type=USER_LOGIN ...
    // type=PRIV_ESCALATION ...
    let parsed = auditd_parser::parse(line)?;
    Some(UnifiedEvent {
        source: "auditd".into(),
        event_type: map_auditd_type(&parsed.record_type),
        ..map_auditd_fields(parsed)
    })
}
```

### Docker Collector

```rust
// Docker Events API — real-time container lifecycle events
use bollard::Docker;
use bollard::system::EventsOptions;

let docker = Docker::connect_with_local_defaults()?;
let mut stream = docker.events(Some(EventsOptions::<String> {
    filters: HashMap::from([
        ("type".to_string(), vec!["container".to_string()])
    ]),
    ..Default::default()
}));

while let Some(event) = stream.next().await {
    let unified = map_docker_event(event?);
    nats.publish("telemetry.raw", unified.to_json()).await;
}
```

### Kubernetes Collector

```rust
// Watch pod events via Kubernetes API
use kube::{Api, Client};
use kube::runtime::watcher;
use k8s_openapi::api::core::v1::Pod;

let client = Client::try_default().await?;
let pods: Api<Pod> = Api::all(client);
let mut w = watcher(pods, Default::default()).boxed();

while let Some(event) = w.next().await {
    match event? {
        watcher::Event::Applied(pod) => {
            let unified = map_pod_event(&pod, "POD_START");
            nats.publish("telemetry.raw", unified.to_json()).await;
        }
        watcher::Event::Deleted(pod) => { ... }
        _ => {}
    }
}
```

### OpenTelemetry Collector

See [[OpenTelemetry]]. Receives spans via OTLP and maps them to the unified schema, focusing on anomalous API patterns (unusual endpoints, high error rates, unusual auth patterns).

---

## Scalability

- One Telemetry Layer process per host for host-level sources (eBPF, Auditd)
- One shared Telemetry Layer service per cluster for Kubernetes/Docker events
- Telemetry Layer is a thin normalizer — minimal CPU, mostly I/O
- Can buffer locally (SQLite) if NATS is temporarily unavailable, replay on reconnect
- At scale: eBPF sensors publish directly to NATS, Telemetry Layer handles normalization as a stream processor
