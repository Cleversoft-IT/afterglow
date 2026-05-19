// Backend DTOs mirrored on the client. Keep in sync with afterglow/backend/app/schemas.

export type ExtractorHint = 'regex' | 'freeform' | 'enum' | 'llm_only';
export type ExecutionMode = 'auto' | 'manual-only';

export type FieldDefinition = {
  key: string;
  type: string;
  label: string;
  required?: boolean;
  options?: string[];
  description?: string | null;

  confidence_threshold?: number | null;
  extractor_hint?: ExtractorHint;
  depends_on?: string[];
};

// `mock_target` / `mutates` / `integration_kind` / `can_undo` live in
// `ActionCatalogEntry` (sourced from backend/app/integrations/action_catalog.py),
// not on the per-template action definition.
export type ActionDefinition = {
  key: string;
  label: string;
  execution_mode: ExecutionMode;
  description?: string | null;

  preconditions?: string[];
  confidence_threshold?: number;
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

// Per-template simulator config. Both seeded and wizard-built templates
// emit a `scenarios` map keyed by CallerMode (as of 2026-05-18). The
// legacy flat fields (caller_name/script_turns/audio_url at the top
// level) are kept as a fallback for custom templates generated before
// that date — those will be migrated the next time their script is
// regenerated.
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
  prompt_hints?: PromptHintRule[] | null;
  is_active: boolean;
  is_seed?: boolean;
  session_id?: string | null;
  // Internal/demo-only — drives the Simulator screen, never exposed in the
  // template editor surface.
  simulation_config?: SimulationConfig | null;
  created_at: string;
};

// --- Wizard / validation ----------------------------------------------------

export type ValidationIssue = {
  field_path: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
};

export type ValidationReport = {
  issues: ValidationIssue[];
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
  prompt_hints: PromptHintRule[];
  validation?: ValidationReport | null;
};

export type CreateTemplateRequest = {
  template: TemplateWizardResponse;
  set_active?: boolean;
  parent_seed_id?: string | null;
};

// --- Integrations marketplace ------------------------------------------------

// One row in the read-only Integrations drawer screen — derived from the
// backend's CATALOG via `aggregate_integrations`. `kind === 'live'` means
// the bucket runs against real records (today only `customer_profile`);
// every other bucket is a simulated external system.
export type IntegrationSummary = {
  key: string;
  label: string;
  kind: 'simulated' | 'live';
  action_count: number;
};

export type UpdateTemplateRequest = {
  name?: string | null;
  description?: string | null;
  domain_hint?: string | null;
  fields_schema?: FieldDefinition[];
  action_types?: ActionDefinition[];
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

export type BookingListItem = {
  id: string;
  call_id: string;
  customer_id?: string | null;
  action_type: string;
  title: string;
  summary?: string | null;
  payload: Record<string, unknown>;
  status: string;
  created_at: string;
  customer_display_name?: string | null;
  customer_phone_e164?: string | null;
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
  mutates: boolean;
  default_payload_schema?: Record<string, unknown> | null;
  compatible_domains: string[];
};

export type FieldDefinitionLite = {
  key: string;
  label: string;
  type: string;
};

export type CallExtractedView = {
  fields: Record<string, unknown>;
  confidence: Record<string, number>;
  evidence: Record<string, string>;
  intent?: string | null;
  sentiment?: string | null;
  urgency?: string | null;
  field_definitions?: FieldDefinitionLite[];
  briefing?: string | null;
};

// Server-computed discriminator for `status === 'failed'`. Distinguishes
// a real missed/empty call from a technical pipeline crash. Mirrors
// `backend/app/schemas/calls.py:FailureKind`.
export type FailureKind = 'missed' | 'pipeline_error';

// Surfaced on calls when the agentic pipeline asked for human review:
// either `flagged_by="agent"` (the agent called `flag_for_review`) or
// `flagged_by="system"` (orchestrator set it after max_turns without finalize).
// Mirrors `backend/app/schemas/calls.py:ReviewFlag`.
export type ReviewFlag = {
  reason: string;
  severity: 'low' | 'medium' | 'high';
  turn_count?: number | null;
  flagged_by: 'agent' | 'system';
};

export type CallDetailView = {
  id: string;
  customer_id?: string | null;
  customer?: CustomerCard | null;
  template_id: string;
  phone_e164: string;
  detected_language?: string | null;
  raw_transcript?: { text: string; speakers?: unknown[]; language?: string } | null;
  status:
    | 'pending'
    | 'transcribing'
    | 'analyzing'
    | 'completed'
    | 'needs_review'
    | 'failed'
    | string;
  error?: string | null;
  failure_kind?: FailureKind | null;
  review_flag?: ReviewFlag | null;
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
  customer_tags?: string[];
  template_id: string;
  status: string;
  failure_kind?: FailureKind | null;
  review_flag?: ReviewFlag | null;
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
  call_phone_e164?: string | null;
  call_display_name?: string | null;
  call_status?: string | null;
};
