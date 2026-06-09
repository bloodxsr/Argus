export type UnifiedEvent = {
  schema_version: string;
  event_id: string;
  source: string;
  event_type: string;
  timestamp: string;
  host: string;
  host_ip: string;
  environment: string;
  pid: number | null;
  uid: number | null;
  payload: Record<string, unknown>;
};

export type IncidentContext = {
  incident_id: string;
  summary: string;
  risk_score: number;
  asset_id: string;
  host: string;
  environment: string;
  hour_of_day: number;
  labels: string[];
  company: string;
};

export type Scenario = {
  scenario_id: string;
  title: string;
  description: string;
  incident: IncidentContext;
  expected_outcome: Record<string, unknown>;
  events: UnifiedEvent[];
};

export type ReplayResult = {
  scenario: Scenario;
  event_count: number;
  pipeline: string[];
  events: UnifiedEvent[];
  ai_result: {
    incident_id: string;
    classification: string;
    confidence: number;
    mitre_techniques: string[];
    recommended_action: string;
    escalate_to_human: boolean;
    reasoning: string;
  };
  decision: {
    incident_id: string;
    action: string;
    confidence: number;
    requires_human_approval: boolean;
    auto_execute: boolean;
    reasoning: string;
    fallback_action: string;
    audit_trail: Record<string, unknown>;
  };
  action_record: Record<string, unknown>;
  review_decision: Record<string, unknown> | null;
};
