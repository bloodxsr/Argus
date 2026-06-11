export type ReplayReport = {
  scenario: {
    scenario_id: string;
    title: string;
    description: string;
    incident: {
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
  };
  event_count: number;
  ai_result: {
    classification: string;
    confidence: number;
    mitre_techniques: string[];
    reasoning: string;
  };
  decision: {
    incident_id: string;
    action: string;
    confidence: number;
    requires_human_approval: boolean;
    auto_execute: boolean;
    reasoning: string;
    audit_trail: Record<string, unknown>;
  };
  action_record: {
    action_id: string;
    action_type: string;
    result: string;
    rollback_cmd: string | null;
  };
  review_decision: Record<string, unknown> | null;
};
