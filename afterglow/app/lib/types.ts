// Backend DTOs mirrored on the client. Keep in sync with afterglow/backend/app/schemas.

export type PiiClass = 'none' | 'contact' | 'health' | 'financial' | 'identity';
export type ExtractorHint = 'regex' | 'freeform' | 'enum' | 'llm_only';
export type ExecutionMode = 'auto' | 'manual-only';

export type FieldDefinition = {
  key: string;
  type: string;
  label: string;
  required?: boolean;
  sensitive?: boolean;
  options?: string[];
  description?: string | null;

  // v2 additions
  pii_class?: PiiClass;
  confidence_threshold?: number | null;
  extractor_hint?: ExtractorHint;
  depends_on?: string[];
};

export type ActionDefinition = {
  key: string;
  label: string;
  execution_mode: ExecutionMode;
  mock_target?: string;
  description?: string | null;

  // v2 additions
  preconditions?: string[];
  confidence_threshold?: number;
  mutates?: boolean;
  evidence_required?: boolean;
  payload_schema?: Record<string, unknown> | null;
};

export type PromptHintRule = {
  when: string;
  then: string;
};

export type SimulationScenario = {
  caller_name?: string | null;
  caller_phone_e164?: string | null;
  script_turns?: { speaker: string; voice: string; text: string }[];
  audio_url?: string | null;
  audio_status?: 'pending' | 'ready' | 'failed' | null;
  audio_generated_at?: string | null;
  audio_source?: 'tts_generated' | 'user_uploaded' | 'bundled' | null;
};

// Per-template simulator config. New seeded templates emit a `scenarios`
// map keyed by CallerMode; custom wizard-built templates still ship the
// legacy flat fields (caller_name/script_turns/audio_url at the top
// level) and are served back through the API with the same shape until
// the wizard is upgraded to render two recordings.
export type SimulationConfig = SimulationScenario & {
  scenarios?: {
    existing?: SimulationScenario | null;
    new?: SimulationScenario | null;
  } | null;
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
  prompt_hints?: PromptHintRule[] | null;
  is_active: boolean;
  is_seed?: boolean;
  session_id?: string | null;
  simulation_config?: SimulationConfig | null;
  created_at: string;
};

// --- Wizard / validation ----------------------------------------------------

export type ValidationIssue = {
  field_path: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
};

export type ProposedMock = {
  action_key: string;
  suggested_mock_target: string;
  rationale: string;
};

export type ValidationReport = {
  issues: ValidationIssue[];
  proposed_mocks: ProposedMock[];
};

export type TemplateWizardRequest = {
  description: string;
  language?: string;
};

export type WizardChatTurn = {
  role: 'user' | 'assistant';
  content: string;
};

export type WizardChatRequest = {
  messages: WizardChatTurn[];
  draft_partial?: TemplateWizardResponse | null;
  slots_filled?: Record<string, unknown>;
  language?: string;
};

export type WizardChatResponse = {
  assistant_message: string;
  slots_filled: Record<string, unknown>;
  confidence: number;
  ready: boolean;
  draft_partial?: TemplateWizardResponse | null;
  validation?: ValidationReport | null;
  proposed_actions_from_catalog: string[];
};

export type TemplateWizardResponse = {
  name: string;
  description: string;
  domain_hint?: string;
  fields_schema: FieldDefinition[];
  action_types: ActionDefinition[];
  custom_dictionary: string[];
  prompt_hints: PromptHintRule[];
  validation?: ValidationReport | null;
};

export type CreateTemplateRequest = {
  template: TemplateWizardResponse;
  set_active?: boolean;
  parent_seed_id?: string | null;
};

export type UpdateTemplateRequest = {
  description?: string | null;
  domain_hint?: string | null;
  fields_schema?: FieldDefinition[];
  action_types?: ActionDefinition[];
  custom_dictionary?: string[];
  prompt_hints?: PromptHintRule[];
};

// --- Calls / customers / audit (unchanged) ---------------------------------

export type CustomerCard = {
  id: string;
  phone_e164: string;
  display_name?: string | null;
  preferred_language?: string | null;
  tags: string[];
  profile_facts?: Record<string, unknown>;
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
  execution_mode: ExecutionMode;
  status: string;
  reverted_at?: string | null;
  created_at: string;
  is_simulated?: boolean;
  can_undo?: boolean;
};

export type ActionCatalogEntry = {
  key: string;
  label: string;
  description: string;
  integration_kind: 'mock_external' | 'internal_real';
  mock_target?: string | null;
  internal_handler?: string | null;
  can_undo: boolean;
  default_payload_schema?: Record<string, unknown> | null;
  compatible_domains: string[];
};

export type FieldDefinitionLite = {
  key: string;
  label: string;
  type: string;
  pii_class: PiiClass | string;
};

export type CallExtractedView = {
  fields: Record<string, unknown>;
  confidence: Record<string, number>;
  evidence: Record<string, string>;
  intent?: string | null;
  sentiment?: string | null;
  urgency?: string | null;
  field_definitions?: FieldDefinitionLite[];
};

export type CallDetailView = {
  id: string;
  customer_id?: string | null;
  customer?: CustomerCard | null;
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
  customer_display_name?: string | null;
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
  payload?: Record<string, unknown> | null;
  status: string;
  error?: string | null;
  created_at: string;
};
