# Investigation Agent

## Depends On
- [[Monitoring Agent]]
- [[Threat Intelligence Agent]]

## Sends Data To
- [[Risk Assessment Agent]] (via Event Bus)

Performs deep contextual analysis of suspicious events. Answers who, what, when, where, and how for every incident.

---

## Core Questions It Answers

For any flagged incident:

1. What process triggered this?
2. What spawned that process? (full parent chain)
3. Did it touch the filesystem? Which files?
4. Did it make network connections? To what?
5. What was the user context?
6. Has this pattern occurred before on this host?
7. Does this match any known attack technique?

---

## Implementation

### Process Tree Reconstruction

```rust
// Query process history from ClickHouse
// Build parent-child chain from pid → ppid
async fn build_process_tree(pid: u32, host: &str, db: &ClickhouseClient) -> ProcessTree {
    let mut chain = vec![];
    let mut current_pid = pid;

    loop {
        let row = db.query(
            "SELECT pid, ppid, binary, args, user, started_at
             FROM process_events
             WHERE host = ? AND pid = ?
             ORDER BY started_at DESC LIMIT 1",
            (host, current_pid)
        ).await;

        match row {
            Some(proc) => {
                chain.push(proc.clone());
                if proc.ppid == 1 { break; } // reached init
                current_pid = proc.ppid;
            }
            None => break,
        }
    }
    ProcessTree { chain }
}
```

### Timeline Builder

```rust
// Collect all events related to this incident within a time window
async fn build_timeline(incident: &Incident, db: &ClickhouseClient) -> Vec<TimelineEvent> {
    db.query(
        "SELECT timestamp, event_type, details
         FROM events
         WHERE host = ?
           AND timestamp BETWEEN ? AND ?
           AND (pid = ? OR related_pid = ?)
         ORDER BY timestamp ASC",
        (incident.host, incident.start - 300, incident.start + 300,
         incident.pid, incident.pid)
    ).await
}
```

### Graph-Based Correlation

For production: store the investigation graph in Neo4j or use `petgraph` in Rust for in-memory graph analysis.

```rust
// petgraph — Rust graph library
use petgraph::graph::DiGraph;

// Nodes: processes, files, network connections, users
// Edges: spawned_by, accessed, connected_to, ran_as
// Walk the graph to find blast radius of an incident
```

---

## Output Schema

```json
{
  "incident_id": "inc_abc123",
  "verdict": "suspicious",
  "confidence": 0.88,
  "summary": "nginx spawned bash which executed /tmp/x.sh and contacted external IP",
  "process_tree": [
    { "pid": 1, "binary": "/usr/sbin/nginx", "user": "www-data" },
    { "pid": 2345, "binary": "/bin/bash", "parent_pid": 1 },
    { "pid": 2346, "binary": "/tmp/x.sh", "parent_pid": 2345 }
  ],
  "network_events": [
    { "dst_ip": "185.x.x.x", "dst_port": 4444, "protocol": "TCP" }
  ],
  "file_events": [
    { "path": "/etc/passwd", "operation": "READ" },
    { "path": "/tmp/x.sh", "operation": "EXECUTE" }
  ],
  "timeline": [...],
  "mitre_hint": "T1059.004"
}
```

---

## Scalability

- Agent is stateless — reads from ClickHouse, writes enriched incident to PostgreSQL
- Can run as many parallel instances as needed
- For high-volume: partition investigations by host — each instance handles a subset of hosts
- ClickHouse handles billion-row event history queries at sub-second latency
- Cache recent process trees in Redis (TTL 60s) — most investigations re-query the same recent processes
