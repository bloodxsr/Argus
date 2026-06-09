# Risk Assessment Agent

Calculates risk scores and prioritizes threats.

## Related Notes
- [[Risk Engine]]
- [[Response Agent]]
- [[Security AI Agent]]

---

## Inputs

- Investigation Agent output (context, timeline, process tree)
- Threat Intelligence Agent output (IOC matches, MITRE techniques)
- Asset database (criticality of the affected host)
- Historical incident data (has this happened before?)

---

## Risk Formula

See [[Risk Engine]] for formula.

```
Risk = (Impact × Confidence × Exposure) / 10

Output: 0–100

0–30   → Low
31–70  → Medium
71–100 → High
```

---

## Scoring Each Factor

### Impact (0–10)

How bad is it if this incident is real?

```
+3  Asset is production / customer-facing
+2  Asset contains sensitive data (PII, secrets, credentials)
+2  Threat technique maps to data exfiltration or ransomware
+2  Known malware family confirmed by Threat Intel
+1  Lateral movement indicators present
```

### Confidence (0–10)

How sure are we this is actually malicious?

```
+3  IOC matched known threat feed with >90% confidence
+2  Process tree is a textbook attack pattern
+2  Multiple independent signals agree
+2  Security AI Agent confidence > 0.85
+1  Anomaly score is high
```

### Exposure (0–10)

How accessible is this asset to an attacker?

```
+3  Asset is internet-facing
+2  Outbound connection to external IP confirmed
+2  Running as root or privileged user
+2  No network segmentation (flat network)
+1  Container with host network mode
```

---

## Implementation

```rust
fn calculate_risk(impact: f32, confidence: f32, exposure: f32) -> f32 {
    (impact * confidence * exposure) / 10.0
}

fn risk_level(score: f32) -> RiskLevel {
    match score as u32 {
        0..=30  => RiskLevel::Low,
        31..=70 => RiskLevel::Medium,
        _       => RiskLevel::High,
    }
}

async fn score_incident(incident: &EnrichedIncident, db: &PgPool) -> RiskScore {
    let impact     = calculate_impact(incident, db).await;
    let confidence = calculate_confidence(incident);
    let exposure   = calculate_exposure(incident, db).await;
    let score      = calculate_risk(impact, confidence, exposure);

    RiskScore {
        score,
        level: risk_level(score),
        impact,
        confidence,
        exposure,
        breakdown: generate_breakdown(impact, confidence, exposure),
    }
}
```

---

## Security AI Integration

After rule-based scoring, the Security AI Agent reviews the incident and can adjust confidence:

```rust
// AI can raise or lower confidence based on deep reasoning
let ai_result = security_ai.analyze(&incident).await;

// Weighted blend: 70% rule-based, 30% AI adjustment
let final_confidence = (confidence * 0.7) + (ai_result.confidence * 10.0 * 0.3);
```

This prevents the AI from being the sole decision-maker while still capturing its reasoning.

---

## Output Schema

```json
{
  "incident_id": "inc_abc123",
  "risk_score": 64.8,
  "risk_level": "Medium",
  "impact": 9.0,
  "confidence": 8.0,
  "exposure": 9.0,
  "breakdown": {
    "impact_reasons": ["production asset", "known malware family"],
    "confidence_reasons": ["IOC matched ThreatFox at 95%", "AI confidence 0.91"],
    "exposure_reasons": ["internet-facing", "outbound C2 connection confirmed"]
  },
  "recommended_action": "recommend_human_review",
  "escalate": true
}
```

---

## Scalability

- Stateless computation — no shared mutable state
- Asset criticality cached in Redis (TTL 5 minutes)
- Historical incident lookup via indexed PostgreSQL queries
- Can run 100+ concurrent scoring operations without issue
- At scale: fan-out scoring across multiple instances, NATS queue group handles distribution
