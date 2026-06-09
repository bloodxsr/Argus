# Shared Contracts

## Purpose

This note defines the canonical objects that every repo will use. The goal is to prevent schema drift between the test website, the agent repo, and the report/result website.

## Related Notes

- [[Implementation Blueprint]]
- [[01 - System Architecture]]
- [[Event Bus]]
- [[Monitoring Agent]]
- [[Investigation Agent]]
- [[Threat Intelligence Agent]]
- [[Risk Assessment Agent]]
- [[Security AI Agent]]
- [[Decision Engine]]
- [[Response Agent]]
- [[Project_checkpoints/0001_kickoff]]
- [[Project_checkpoints/0002_python_security_ai_scaffold]]

---

## Core Objects

Canonical JSON schemas now live in `contracts/`.

### UnifiedEvent

Represents one normalized telemetry event from any source.

Fields:
- schema_version
- event_id
- source
- event_type
- timestamp
- host
- host_ip
- environment
- pid
- uid
- payload

### Incident

Represents a grouped suspicious activity record created from one or more events.

Fields:
- incident_id
- host
- start_time
- end_time
- severity
- summary
- events
- source_agent

### EnrichedIncident

Represents an incident after investigation and threat intel enrichment.

Fields:
- incident_id
- process_tree
- timeline
- network_events
- file_events
- threat_matches
- mitre_techniques
- context_graph

### RiskScore

Represents the final risk calculation.

Fields:
- incident_id
- score
- level
- impact
- confidence
- exposure
- breakdown
- recommended_action
- escalate

### AIResult

Represents the Python Security AI output.

Fields:
- incident_id
- classification
- confidence
- mitre_techniques
- recommended_action
- escalate_to_human
- reasoning

### Decision

Represents the policy-checked final action choice.

Fields:
- incident_id
- action
- confidence
- requires_human_approval
- auto_execute
- reasoning
- fallback_action
- audit_trail

### ActionRecord

Represents one executed or attempted response action.

Fields:
- action_id
- incident_id
- action_type
- target
- host
- executed_by
- approved_by
- command
- result
- rollback_cmd
- rolled_back
- timestamp

### ReviewDecision

Represents a human analyst approval or rejection.

Fields:
- incident_id
- review_id
- analyst
- decision
- notes
- timestamp

### CheckpointEntry

Represents one markdown checkpoint in the project history.

Fields:
- checkpoint_id
- title
- status
- changed_files
- related_notes
- next_step
- timestamp

### Scenario

Represents a replayable demo/test fixture for the test website and evaluation harness.

Fields:
- scenario_id
- title
- description
- incident
- expected_outcome
- events

## Rules

- Every repo must serialize and deserialize the same object shapes.
- The Security AI may only return structured fields defined in AIResult.
- The Decision Engine may only execute actions allowed by policy and company constraints.
- Checkpoints must link back to the notes that justified them.
- Scenario fixtures must use the same UnifiedEvent and IncidentContext fields as the service.
