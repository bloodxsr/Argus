"""Create a small synthetic JSONL dataset from existing evaluation cases.

This script creates a `synthetic_security_train.jsonl` file suitable for quick fine-tune trials.
It is intentionally minimal: for real training you should expand and diversify examples.
"""
from __future__ import annotations

import json
from pathlib import Path

from security_ai_service.evaluation import default_evaluation_cases
from security_ai_service.knowledge import SecurityKnowledgeBase


OUT = Path("synthetic_security_train.jsonl")


def main() -> int:
    kb = SecurityKnowledgeBase()
    cases = default_evaluation_cases()
    with OUT.open("w", encoding="utf-8") as fh:
        for case in cases:
            incident = case.incident
            retrieved = kb.retrieve(incident)
            instruction = (
                f"Company: {incident.company}\nHost: {incident.host}\nAsset: {incident.asset_id}\n"
                f"Risk: {incident.risk_score}\nSummary: {incident.summary}\nRetrieved: "
                + "; ".join(s.title for s in retrieved)
            )
            response = {
                "classification": case.expected_classification or "Unknown",
                "confidence": case.expected_confidence_at_least,
                "mitre_techniques": [],
                "recommended_action": case.expected_action,
                "escalate_to_human": case.expected_requires_human_approval,
                "reasoning": "Synthetic training example derived from evaluation case",
            }
            fh.write(json.dumps({"instruction": instruction, "response": response}, ensure_ascii=False) + "\n")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
