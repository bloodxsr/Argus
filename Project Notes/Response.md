# Autonomous Response

Defines the response tiers in AGRUS. Autonomous does not mean humans are removed — it means humans are removed from every alert that doesn't need them.

## Related Notes
- [[Response Agent]]
- [[Decision Engine]]

---

## Response Tiers

```
Low Risk (0–30)
      ↓
   Observe
   Log the event. Store for behavioral baseline.
   Human never sees it unless they audit logs.

Medium Risk (31–70)
      ↓
   Recommend
   AI generates a recommended action.
   Pushed to analyst dashboard as a card.
   Human approves → Response Agent executes.
   Human rejects → logged as false positive, fed to Learning Agent.

High Risk (71–100)
      ↓
   Automatic Action
   Response Agent executes immediately.
   Action is logged with full audit trail.
   Human receives notification and can audit / rollback within 24h.
```

---

## Why This Model Works for Enterprise

Full autonomy (no human involvement ever) is legally and compliance-wise unacceptable for most organizations. SOC 2, ISO 27001, and PCI-DSS all require documented human approval chains for significant security decisions.

This tier model satisfies those requirements:
- Medium risk: explicit human approval is on record
- High risk: immediate action + post-action human audit = documented accountability

The sales pitch is not "no humans." It is:

**"Your analysts spend zero time on low-risk noise and only make decisions that actually require human judgment."**

---

## Confidence Gate

Before any automated action executes, two gates must pass:

```
1. Risk Score > 70          (rule-based threshold)
2. AI Confidence > 0.85     (Security AI Agent certainty)
```

Both must be true for auto-execution. If AI confidence is low despite high risk score, the system escalates to Medium-tier human review instead of acting.

This prevents automated action on ambiguous high-risk signals.

---

## Human Override

Any automated action can be:
- Rolled back by an analyst within 24 hours
- Flagged as false positive (feeds Learning Agent)
- Escalated to senior analyst for review

The system learns from every override. Over time, false positive rate decreases and auto-action confidence increases.
