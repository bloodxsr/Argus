# Threat Intelligence Agent

## Depends On
- [[Investigation Agent]]

## Sends Data To
- [[Risk Assessment Agent]]

## Related Notes
- [[Security AI Agent]]
- [[Implementation Blueprint]]
- [[Shared_Contracts]]
- [[Project_checkpoints/0002_python_security_ai_scaffold]]

Enriches every incident with external threat context. Answers: is any part of this incident already known to the security world?

---

## What It Checks

- Is this IP address known malicious infrastructure?
- Is this file hash associated with known malware?
- Is this domain used for C2 (command and control)?
- Does this technique match a known APT group?
- Is this CVE being actively exploited in the wild?

---

## Data Sources

| Feed | What It Provides | Update Frequency |
|---|---|---|
| abuse.ch MalwareBazaar | Malware file hashes | Real-time |
| abuse.ch ThreatFox | IPs, domains, URLs | Real-time |
| CISA KEV | Actively exploited CVEs | Weekly |
| OTX AlienVault | IP/domain reputation, threat pulses | Hourly |
| VirusTotal API | File hash, IP, domain reputation | On-demand |
| MITRE ATT&CK STIX | Technique → group → malware mapping | Monthly |
| Feodo Tracker | Botnet C2 IPs | Real-time |

---

## Implementation

### Feed Ingestion Service

```rust
// Periodic job — runs on schedule via tokio-cron or similar
async fn ingest_feeds(db: &PgPool) {
    // Fetch abuse.ch ThreatFox
    let iocs = fetch_threatfox().await;
    bulk_upsert_iocs(&db, iocs).await;

    // Fetch CISA KEV
    let kev = fetch_cisa_kev().await;
    bulk_upsert_kev(&db, kev).await;
}

async fn fetch_threatfox() -> Vec<IOC> {
    let client = reqwest::Client::new();
    let resp = client
        .post("https://threatfox-api.abuse.ch/api/v1/")
        .json(&json!({ "query": "get_iocs", "days": 1 }))
        .send().await.unwrap();

    resp.json::<ThreatFoxResponse>().await.unwrap().data
}
```

### PostgreSQL Schema for IOC Storage

```sql
CREATE TABLE iocs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type        VARCHAR(20),   -- ip, domain, hash, url
    value       TEXT NOT NULL,
    threat_type VARCHAR(50),   -- ransomware, c2, botnet
    malware     VARCHAR(100),
    confidence  INT,           -- 0-100
    source      VARCHAR(50),
    first_seen  TIMESTAMPTZ,
    last_seen   TIMESTAMPTZ,
    UNIQUE(type, value)
);

CREATE INDEX idx_iocs_value ON iocs(value);
CREATE INDEX idx_iocs_type_value ON iocs(type, value);
```

### Lookup at Incident Time

```rust
async fn enrich_incident(incident: &mut Incident, db: &PgPool) {
    // Check all IPs in the incident
    for ip in &incident.network_events {
        if let Some(ioc) = lookup_ioc("ip", &ip.dst_ip, db).await {
            incident.threat_matches.push(ThreatMatch {
                indicator: ip.dst_ip.clone(),
                threat_type: ioc.threat_type,
                malware: ioc.malware,
                confidence: ioc.confidence,
                source: ioc.source,
            });
        }
    }

    // Check file hashes
    for file in &incident.file_events {
        if let Some(hash) = &file.sha256 {
            if let Some(ioc) = lookup_ioc("hash", hash, db).await {
                incident.threat_matches.push(...);
            }
        }
    }
}
```

### VirusTotal On-Demand (for novel indicators)

```rust
// Only call VT for indicators not found in local DB
// Respects rate limits — free tier is 4 requests/min
async fn vt_lookup(indicator: &str, api_key: &str) -> Option<VTResult> {
    let client = reqwest::Client::new();
    let resp = client
        .get(format!("https://www.virustotal.com/api/v3/ip_addresses/{}", indicator))
        .header("x-apikey", api_key)
        .send().await.ok()?;

    resp.json::<VTResult>().await.ok()
}
```

---

## Output to Risk Agent

```json
{
  "incident_id": "inc_abc123",
  "threat_matches": [
    {
      "indicator": "185.x.x.x",
      "type": "ip",
      "threat_type": "c2",
      "malware": "Cobalt Strike",
      "confidence": 95,
      "source": "abuse.ch ThreatFox"
    }
  ],
  "mitre_techniques": ["T1071.001", "T1059.004"],
  "threat_actor_hint": "APT29 uses this infrastructure",
  "intelligence_confidence": 0.95
}
```

---

## Scalability

- IOC database lives in PostgreSQL — indexed on `(type, value)` for sub-millisecond lookups
- At scale: move to Redis for hot IOCs (last 30 days), PostgreSQL for historical
- Feed ingestion is a separate service — can be scheduled via Kubernetes CronJob
- VirusTotal rate limits managed via a token bucket in Redis
- For enterprise: add commercial feeds (Recorded Future, Intel 471) via same ingestion interface
