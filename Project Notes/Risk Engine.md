# Risk Engine

Risk = (Impact × Confidence × Exposure) / 10

All three factors scored 0–10. Output normalized to 0–100.

Used by [[Risk Assessment Agent]].

---

## Factor Definitions

- **Impact** — How damaging is this if the threat is real? (data loss, service down, privilege escalation)
- **Confidence** — How certain is the detection? (IOC match quality, AI confidence, signal count)
- **Exposure** — How accessible is the affected asset? (internet-facing, running as root, flat network)

---

## Scale

```
0–30   Low     → Log and observe
31–70  Medium  → Recommend to human
71–100 High    → Autonomous response
```

---

## Why Multiplicative (Not Additive)

Additive scoring inflates risk for medium-quality signals.

Example: Impact=9, Confidence=2, Exposure=9
- Additive: (9+2+9)/3 × 10 = 66 → Medium (would send alert)
- Multiplicative: (9×2×9)/10 = 16 → Low (correctly ignored — confidence is too low)

Multiplicative forces all three factors to be high before risk score escalates. Low confidence suppresses a high-impact finding. This is correct security behavior — don't act on weak signals.
