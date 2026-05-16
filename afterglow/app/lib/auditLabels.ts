// Friendly labels for audit_log rows. Keeps the production-shape `agent_name` /
// `step_type` strings intact in the DB while making the Audit tab readable.
//
// Falls back to "agent_name · step_type" when there is no mapping.

const AGENT_LABELS: Record<string, string> = {
  speechmatics: 'Speechmatics transcription',
  pre_classifier: 'Pre-classifier',
  memory_lookup: 'Memory lookup',
  call_analyzer: 'Call analyzer',
  pii_sanitizer: 'PII observer',
  action_planner: 'Action planner',
  action_executor: 'Action executor',
  memory_updater: 'Memory write-back',
  memory_summarizer_bilingual: 'Bilingual summary',
};

const STEP_LABELS: Record<string, string> = {
  tool_call: 'Tool call',
  llm_call: 'LLM call',
  agent_loop: 'Agent reasoning loop',
  action_exec: 'Action executed',
  pii_policy_applied: 'PII observed',
  rejected: 'Rejected',
  rag_semantic: 'RAG (semantic)',
  structured_history: 'Structured history',
  pre_classify: 'Pre-classify',
  revert: 'Revert',
  undo: 'Undo',
  redo: 'Redo',
};

export function friendlyAgentLabel(agentName: string): string {
  return AGENT_LABELS[agentName] ?? agentName;
}

export function friendlyStepLabel(stepType: string): string {
  return STEP_LABELS[stepType] ?? stepType;
}

export function friendlyAuditLabel(agentName: string, stepType: string): string {
  return `${friendlyAgentLabel(agentName)} · ${friendlyStepLabel(stepType)}`;
}

// Read a human-friendly explanation out of the audit row payload. We honor
// an explicit `human_label` key (set by the orchestrator on skip / degraded
// steps) and otherwise fall back to a short rendering of the `reason` key.
export function humanLabelFromPayload(payload?: Record<string, unknown> | null): string | null {
  if (!payload) return null;
  const human = payload['human_label'];
  if (typeof human === 'string' && human.trim().length > 0) return human;
  const reason = payload['reason'];
  if (typeof reason === 'string' && reason.trim().length > 0) {
    return reason.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase());
  }
  return null;
}
