# Event Bus

Communication backbone of AGRUS. All agents communicate exclusively through this layer. No agent calls another agent directly.

## Related Notes
- [[Monitoring Agent]]
- [[Investigation Agent]]
- [[01 - System Architecture]]

---

## Why This Matters

Direct agent communication creates tight coupling:

```text
Bad:
Monitoring → Investigation → Risk → Response
(if Investigation crashes, everything stops)

Good:
Monitoring → [Event Bus] → Investigation
                ↓
           [Event Bus] → Risk
                ↓
           [Event Bus] → Response
(any agent can crash and restart independently)
```

---

## Technology

### MVP: NATS

```bash
# Run NATS with JetStream (persistent messaging)
docker run -p 4222:4222 nats:latest -js
```

Fast, simple, handles millions of messages/sec on a single node. JetStream adds persistence — messages survive agent restarts.

### Production: Kafka / Redpanda

Redpanda is Kafka-compatible but written in C++ — lower latency, simpler ops (no ZooKeeper needed).

```bash
# Redpanda single-node
docker run -p 9092:9092 redpandadata/redpanda:latest
```

---

## Topic Structure

```text
telemetry.raw           ← raw events from sensors
incidents.new           ← flagged anomalies from Monitoring Agent
incidents.investigated  ← enriched by Investigation Agent
incidents.intel         ← enriched by Threat Intelligence Agent
incidents.scored        ← risk score added
incidents.decided       ← Decision Engine output
actions.pending         ← Response Agent queue
actions.completed       ← executed action results
review.pending          ← human review queue (Medium risk)
review.decisions        ← analyst approval/rejection
feedback.false_positive ← analyst corrections to Learning Agent
```

---

## Event Schema (Versioned)

```json
{
  "schema_version": "1.0",
  "event_id": "abc123",
  "incident_id": "inc_xyz",
  "timestamp": "2026-06-08T20:15:30Z",
  "event_type": "PROCESS_START",
  "host": "server01",
  "severity": "UNKNOWN",
  "source_agent": "monitoring",
  "payload": {}
}
```

Schema versioning is critical. When a new field is added, older consumers continue to work on the old schema version while being updated.

---

## Implementation

### Publishing (Rust)

```rust
use async_nats::Client;

async fn publish_incident(client: &Client, incident: &Incident) -> Result<()> {
    let payload = serde_json::to_vec(incident)?;
    client.publish("incidents.new", payload.into()).await?;
    Ok(())
}
```

### Subscribing with Queue Group (Rust)

```rust
// Queue group = load balanced — each message goes to exactly one instance
let mut sub = client
    .queue_subscribe("incidents.new", "investigation-workers")
    .await?;

while let Some(msg) = sub.next().await {
    let incident: Incident = serde_json::from_slice(&msg.payload)?;
    tokio::spawn(async move {
        process_incident(incident).await;
    });
}
```

---

## Scalability

| Scale | Setup |
|---|---|
| MVP | NATS single node, in-memory |
| 10k events/sec | NATS with JetStream (disk persistence) |
| 100k events/sec | Redpanda 3-node cluster |
| 1M+ events/sec | Kafka with 10+ partitions per topic, sharded by host_id |

### Partitioning Strategy (Kafka)

Partition by `host_id` — events from the same host always go to the same partition. This ensures ordering is preserved per host without global ordering overhead.

```python
# Kafka producer partition key
producer.send(
    topic="telemetry.raw",
    key=event.host_id.encode(),  # same host → same partition
    value=event.to_json()
)
```

### Backpressure

If Investigation Agent is slow, events pile up in the `incidents.new` topic. NATS JetStream / Kafka handle this natively — the queue buffers events until consumers catch up. Add more Investigation Agent instances to drain faster.
