# Implementation Blueprint

## Purpose

This note turns the project vision into a buildable structure. It defines the first concrete implementation surfaces:

- a Python Security AI / LLM service
- shared incident and action contracts
- evaluation test cases
- tenant/company constraints
- checkpointed progress in markdown

## Related Notes

- [[Shared_Contracts]]
- [[Project_checkpoints/0002_python_security_ai_scaffold]]
- [[Project Outcomes and Implementation Plan]]
- [[Project_checkpoints/0004_project_direction_and_model_integrity]]

## Repo Split

### 1. Test Website

Purpose: simulate attacks, visualize the pipeline, and demonstrate human review.

Responsibilities:
- generate synthetic telemetry
- replay known incidents
- render live incident flow
- show review, approve, reject, and rollback actions

### 2. Agent Repo

Purpose: run the core security workflow.

Responsibilities:
- telemetry ingestion
- monitoring and anomaly detection
- investigation and context building
- threat intelligence enrichment
- risk scoring
- Python-based Security AI / LLM decision service
- policy-driven decision engine
- response execution and audit logging

### 3. Report / Result Website

Purpose: provide the audit and reporting surface.

Responsibilities:
- incident history
- action history
- risk and decision visibility
- rollback tracking
- checkpoint timeline

## Shared Contracts

The project should define a single source of truth for these objects:

- UnifiedEvent
- Incident
- EnrichedIncident
- RiskScore
- AIResult
- Decision
- ActionRecord
- ReviewDecision
- CheckpointEntry

See [[Shared_Contracts]] for the canonical field definitions.

These contracts should be reused by every repo so the system does not drift.

## LLM / Security AI Shape

The Security AI component should be implemented in Python because it is the fastest path for:

- prompt orchestration
- retrieval augmented generation
- model evaluation
- fine-tuning experiments
- dataset preparation

The model should not directly own infrastructure actions. It should return a structured decision payload.

### Expected output

```json
{
  "classification": "Remote Code Execution + C2 Beaconing",
  "confidence": 0.93,
  "mitre_techniques": ["T1059.004", "T1071.001"],
  "recommended_action": "kill_process",
  "escalate_to_human": false,
  "reasoning": "..."
}
```

## Evaluation Harness

The LLM must be checked against fixed test cases before release.

### Test case categories

- known malicious incidents
- benign false positives
- ambiguous mixed-signal cases
- adversarial prompt injection attempts
- policy-boundary violations
- company-specific constraint cases

### Pass criteria

- structured JSON output is valid
- recommended action is allowed by policy
- confidence is calibrated against known labels
- escalations happen when confidence is low
- no out-of-scope action is suggested

## Company Constraint Layer

Each deployment must be able to restrict the bot without changing model code.

Examples:

- allowed response actions
- auto-response threshold
- risk threshold per environment
- asset-specific no-auto-response rules
- approved hours for automatic execution
- tenant-specific escalation chains

This layer should sit between model output and response execution.

## Checkpoint Discipline

Every meaningful implementation step should create a markdown checkpoint under Project_checkpoints.

Each checkpoint should record:

- what changed
- why it changed
- what file or note was touched
- what the next step is
- links to the relevant notes

## First Build Order

1. Define shared contracts.
2. Define the Security AI Python service interface.
3. Define evaluation test cases.
4. Define company constraints.
5. Create the first synthetic incident flow.
6. Add checkpoint entries after each milestone.
