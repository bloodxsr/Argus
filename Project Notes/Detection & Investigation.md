# Detection & Investigation

The Detection and Investigation layer is responsible for observing system activity, flagging anomalies, constructing context around suspicious events, and enriching them with global threat intelligence.

## 1. Monitoring Agent
The Monitoring Agent continuously observes telemetry data and publishes initial incidents.
- **Responsibilities:**
  - Normalizes events to the unified schema.
  - Deduplicates overlapping events (e.g., from eBPF and Auditd) using a Bloom filter with a sliding window.
  - Compares events against behavioral baselines (e.g., spotting a process spawning from an unexpected parent or connecting to a novel IP).
  - Flags anomalies and publishes incidents to the Event Bus (`incidents.new`).
- **Scalability:** Stateless design utilizing PostgreSQL and Redis. Leverages NATS queue groups to distribute load across multiple instances.

## 2. Investigation Agent
When an incident is flagged, the Investigation Agent performs deep contextual analysis to answer the *who, what, when, where, and how*.
- **Responsibilities:**
  - **Process Tree Reconstruction:** Queries the database (ClickHouse/PostgreSQL) to build the complete parent-child process chain.
  - **Timeline Construction:** Collects all related events (file access, network connections) within a time window of the incident.
  - **Graph Correlation:** Analyzes the "blast radius" to find related anomalies.
- **Output:** Outputs a highly enriched JSON schema mapping the process tree, network events, file operations, and MITRE ATT&CK hints.

## 3. Threat Intelligence Agent
The Threat Intelligence Agent enriches every incident by checking artifacts against external intelligence feeds.
- **Capabilities:**
  - Identifies malicious IPs, known malware hashes, C2 domains, and actively exploited CVEs.
  - Automatically fetches and updates indicators of compromise (IOCs) from feeds like abuse.ch (ThreatFox, MalwareBazaar), CISA KEV, OTX AlienVault, and VirusTotal.
- **Implementation:**
  - Operates a Feed Ingestion Service to bulk-upsert IOCs into an indexed PostgreSQL database.
  - Checks every file hash and network IP in the incident against the local database for sub-millisecond lookups.
  - Queries VirusTotal on-demand for novel indicators, respecting API rate limits via a Redis token bucket.
- **Output:** Injects threat matches (e.g., Cobalt Strike C2, APT29 attribution) and intelligence confidence scores into the incident payload for the Risk Assessment Agent.
