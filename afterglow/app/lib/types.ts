// Backend DTOs mirrored on the client. Keep in sync with afterglow/backend/app/schemas.

export type FieldDefinition = {
  key: string;
  type: string;
  label: string;
  required?: boolean;
  sensitive?: boolean;
  options?: string[];
  description?: string;
};

export type ActionDefinition = {
  key: string;
  label: string;
  execution_mode: 'auto' | 'manual-only';
  mock_target?: string;
  description?: string;
};

export type TemplateView = {
  id: string;
  name: string;
  version: number;
  description?: string | null;
  domain_hint: 'restaurant' | 'dentist' | 'bodyshop' | string;
  fields_schema: FieldDefinition[];
  action_types: ActionDefinition[];
  custom_dictionary: string[];
  prompt_hints?: string | null;
  is_active: boolean;
  created_at: string;
};

export type CustomerCard = {
  id: string;
  phone_e164: string;
  display_name?: string | null;
  preferred_language?: string | null;
  tags: string[];
  memory_summary?: string | null;
  total_calls: number;
  last_call_at?: string | null;
};

export type CallActionView = {
  id: string;
  action_type: string;
  title: string;
  summary?: string | null;
  payload: Record<string, unknown>;
  result?: Record<string, unknown> | null;
  confidence?: number | null;
  evidence?: string[] | null;
  execution_mode: 'auto' | 'manual-only';
  status: string;
  reverted_at?: string | null;
  created_at: string;
};

export type CallExtractedView = {
  fields: Record<string, unknown>;
  confidence: Record<string, number>;
  evidence: Record<string, string>;
  intent?: string | null;
  sentiment?: string | null;
  urgency?: string | null;
};

export type CallDetailView = {
  id: string;
  customer_id?: string | null;
  template_id: string;
  phone_e164: string;
  detected_language?: string | null;
  raw_transcript?: { text: string; speakers?: unknown[]; language?: string } | null;
  status: 'pending' | 'transcribing' | 'analyzing' | 'completed' | 'failed' | string;
  error?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  extracted?: CallExtractedView | null;
  executed_actions: CallActionView[];
};

export type CallListItem = {
  id: string;
  phone_e164: string;
  customer_id?: string | null;
  template_id: string;
  status: string;
  detected_language?: string | null;
  created_at: string;
};

export type CallSubmittedResponse = {
  call_id: string;
  status: string;
};

export type AuditLogEntry = {
  id: string;
  call_id?: string | null;
  agent_name: string;
  step_type: string;
  model?: string | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  duration_ms?: number | null;
  status: string;
  error?: string | null;
  created_at: string;
};
