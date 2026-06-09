# Monitoring Agent

## Inputs
- [[Telemetry Layer]]
- [[eBPF]]
- [[OpenTelemetry]]

## Outputs
- [[Investigation Agent]] (via Event Bus)

Responsible for observing all system activity continuously and flagging anomalies.

---

## Responsibilities

- Event normalization (all sources → unified schema)
- Deduplication (same event from multiple sensors → one event)
- Baseline comparison (is this normal for this host?)
- Initial anomaly flagging
- Publishing incidents to the Event Bus

---

## Implementation

### Runtime

```toml
# Cargo.toml
[dependencies]
tokio = { version = "1", features = ["full"] }
axum = "0.7"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
sqlx = { version = "0.7", features = ["postgres", "runtime-tokio"] }
async-nats = "0.33"
tracing = "0.1"
tracing-subscriber = "0.3"
```

### Core Processing Loop

```rust
// Simplified flow
async fn process_event(event: RawEvent, db: &Pool, nats: &Client) {
    // 1. Normalize to unified schema
    let normalized = normalize(event);

    // 2. Deduplicate — check Redis or in-memory bloom filter
    if is_duplicate(&normalized).await { return; }

    // 3. Compare against behavioral baseline
    let baseline = get_baseline(&normalized.host, &normalized.process).await;
    let anomaly_score = score_anomaly(&normalized, &baseline);

    // 4. If anomaly detected, publish incident
    if anomaly_score > THRESHOLD {
        let incident = build_incident(normalized, anomaly_score);
        nats.publish("incidents.new", incident.to_json()).await;
    }

    // 5. Always store raw event in ClickHouse
    store_event(&normalized, db).await;
}
```

### Deduplication Strategy

Events from eBPF and Auditd can overlap. Use a 30-second deduplication window per `(host, event_type, pid)` tuple.

```rust
// Bloom filter — fast, memory-efficient
use bloomfilter::Bloom;
let mut dedup_filter: Bloom<String> = Bloom::new_for_fp_rate(100_000, 0.01);

fn is_duplicate(event: &NormalizedEvent) -> bool {
    let key = format!("{}:{}:{}", event.host, event.event_type, event.pid);
    if dedup_filter.check(&key) {
        return true;
    }
    dedup_filter.set(&key);
    false
}
```

### Anomaly Detection (Statistical Baseline)

For MVP: compare event against a rolling 7-day baseline per host.

```rust
// Baseline stored in PostgreSQL
// Schema: host, process_name, avg_cpu, avg_net, typical_parents[]
// Alert if: process spawns from unexpected parent
//           process connects to external IP it never has before
//           process runs at unusual hour
```

For production: replace statistical baseline with a behavioral ML model (isolation forest or autoencoder) running per-host.

---

## NATS Topic Schema

```text
Publish to:  incidents.new
Subscribe to: telemetry.raw
```

---

## Scalability

- Agent is stateless — all state is in PostgreSQL + Redis
- Multiple Monitoring Agent instances can subscribe to the same NATS subject with a queue group
- NATS queue group ensures each event is processed by exactly one instance

```rust
// Queue group subscription — built-in load balancing
let sub = nats.queue_subscribe("telemetry.raw", "monitoring-workers").await?;
```

- Scale: add more instances behind the same queue group. NATS distributes load automatically.
- At 100k events/sec: partition by host_id prefix, run 10 instances each handling a slice.
