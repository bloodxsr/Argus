# Decision Engine

Determines the next action based on risk score, Security AI reasoning, and policy rules.

## Related Notes
- [[Risk Engine]]
- [[Response Agent]]
- [[Security AI Agent]]
- [[Autonomous Response]]

---

## Inputs

- Risk score + level from Risk Assessment Agent
- Security AI Agent classification and recommended action
- Organizational policy (configured per environment)
- Asset context (is this a critical prod system?)
- Time context (is this during business hours? maintenance window?)

---

## Decision Logic

```text
Risk Score + AI Recommendation + Policy
              │
              ▼
      Policy Engine (OPA)
              │
         ┌────┴────┐
         ▼         ▼
      Autonomous  Human
       Response   Review
      (execute)  (recommend)
```

---

## Policy Engine — OPA (Open Policy Agent)

Policies are written in Rego (OPA's language) and loaded at runtime. This means response rules can be changed without redeploying the system.

```rego
# policy.rego
package aisos.response

# High risk → automatic action unless asset is flagged no-auto
default action = "observe"

action = "auto_respond" {
    input.risk_level == "High"
    input.ai_confidence >= 0.85
    not input.asset.no_auto_response
}

action = "recommend" {
    input.risk_level == "Medium"
}

action = "recommend" {
    input.risk_level == "High"
    input.asset.no_auto_response == true
}
```

### Why OPA

- Policies are files, not code — security team can change them without engineering
- Audit log of every policy decision is built-in
- Same policy engine used by Kubernetes and Terraform — battle-tested
- Enables per-tenant, per-environment policies at scale

---

## Implementation

```rust
async fn decide(
    risk: &RiskScore,
    ai_result: &AIResult,
    asset: &Asset,
    opa: &OpaClient,
) -> Decision {
    let input = json!({
        "risk_level": risk.level,
        "risk_score": risk.score,
        "ai_confidence": ai_result.confidence,
        "ai_action": ai_result.recommended_action,
        "asset": {
            "id": asset.id,
            "criticality": asset.criticality,
            "no_auto_response": asset.no_auto_response,
        }
    });

    let policy_result = opa.evaluate("aisos/response", &input).await;

    Decision {
        action: policy_result.action,
        confidence: ai_result.confidence,
        reasoning: ai_result.reasoning.clone(),
        requires_human: policy_result.action == "recommend",
        auto_execute: policy_result.action == "auto_respond",
    }
}
```

---

## Output Schema

```json
{
  "incident_id": "inc_abc123",
  "action": "kill_process",
  "confidence": 0.93,
  "requires_human_approval": false,
  "auto_execute": true,
  "reasoning": "Cobalt Strike C2 beaconing confirmed. High-confidence automated kill appropriate.",
  "fallback_action": "block_ip",
  "audit_trail": {
    "policy_version": "v1.3.2",
    "risk_score": 82.0,
    "ai_model_version": "aisos-security-7b-v2"
  }
}
```

---

## Human Review Queue

For Medium risk decisions, the Decision Engine writes to a human review queue:

```rust
// Publish to human review topic
nats.publish("review.pending", decision.to_json()).await;

// Dashboard polls this topic via WebSocket
// Analyst sees: incident summary, risk score, AI recommendation
// Analyst clicks: Approve / Reject / Escalate
```

Approved decisions execute immediately. Rejected decisions get logged as false positives and fed back to the Learning Agent.

---

## Scalability

- OPA runs as a sidecar container — co-located with Decision Engine instances
- Policy evaluation is CPU-only, sub-millisecond
- Decision Engine is stateless — all context is passed in as input
- Scale horizontally with NATS queue groups
- Policy files stored in Git, deployed via CI/CD — no restarts needed for policy changes
