// Frontend mirror of the Pydantic schemas exposed by the backend.

export interface Business {
  id: string;
  name: string;
  domain: "restaurant" | "dentist" | "bodyshop" | string;
  default_language: string;
  timezone: string;
  settings?: Record<string, unknown>;
  vultr_collection_id?: string | null;
}

export interface CustomerCard {
  id: string;
  phone_e164: string;
  display_name?: string | null;
  preferred_language?: string | null;
  tags: string[];
  memory_summary?: string | null;
  total_calls: number;
  last_call_at?: string | null;
}

export interface CallAction {
  id: string;
  action_type: string;
  title: string;
  summary?: string | null;
  payload: Record<string, unknown>;
  result?: Record<string, unknown> | null;
  confidence?: number | null;
  evidence?: string[] | null;
  execution_mode: "auto" | "manual-only" | string;
  status: "executed" | "manual_required" | "reverted" | "failed" | string;
  reverted_at?: string | null;
  created_at: string;
}

export interface CallExtracted {
  fields: Record<string, unknown>;
  confidence: Record<string, number>;
  evidence: Record<string, string>;
  intent?: string | null;
  sentiment?: string | null;
  urgency?: string | null;
}

export interface CallDetail {
  id: string;
  business_id: string;
  customer_id?: string | null;
  template_id: string;
  phone_e164: string;
  detected_language?: string | null;
  raw_transcript?: {
    text?: string;
    speakers?: Array<{ id: string; label: string }>;
    language?: string;
  } | null;
  status: string;
  error?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  extracted?: CallExtracted | null;
  executed_actions: CallAction[];
}

export interface AuditEntry {
  id: string;
  call_id?: string | null;
  agent_name: string;
  step_type: string;
  model?: string | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  duration_ms?: number | null;
  payload?: Record<string, unknown> | null;
  status: string;
  error?: string | null;
  created_at: string;
}

export interface TemplateField {
  key: string;
  type: string;
  label: string;
  required?: boolean;
  sensitive?: boolean;
  options?: string[];
  description?: string;
}

export interface TemplateAction {
  key: string;
  label: string;
  execution_mode: "auto" | "manual-only" | string;
  mock_target: string;
  description?: string;
}

export interface TemplateView {
  id: string;
  business_id: string;
  name: string;
  version: number;
  description?: string | null;
  fields_schema: TemplateField[];
  action_types: TemplateAction[];
  custom_dictionary: string[];
  prompt_hints?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface WizardResponse {
  name: string;
  description: string;
  fields_schema: TemplateField[];
  action_types: TemplateAction[];
  custom_dictionary: string[];
  prompt_hints: string;
}
