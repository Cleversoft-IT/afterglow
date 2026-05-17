// Thin fetch wrapper. Every call is absolute against EXPO_PUBLIC_API_BASE —
// Expo's static web build has no BFF, so relative paths would 404.

import type {
  ActionCatalogEntry,
  AuditLogEntry,
  BookingListItem,
  CallDetailView,
  CallListItem,
  CallSubmittedResponse,
  CreateTemplateRequest,
  CustomerCard,
  TemplateView,
  TemplateWizardRequest,
  TemplateWizardResponse,
  UpdateTemplateRequest,
  ValidationReport,
  WizardChatRequest,
  WizardChatResponse,
} from './types';

const BASE = (process.env.EXPO_PUBLIC_API_BASE ?? 'http://localhost:8000').replace(/\/$/, '');

// Demo iframe sandbox: every visitor of demo.* is identified by an opaque
// UUID stamped on every demo-side write so concurrent judges do not collide.
// The token lives in localStorage; first request sends the literal "new" and
// the backend echoes a freshly-minted uuid in the response header, which we
// persist for every subsequent fetch. Native / non-browser builds (no
// localStorage) fall back to in-memory storage — fine because the only path
// that needs isolation is the web iframe demo.
//
// Race protection: the app fires several parallel fetches at boot (root layout
// primes templates, tab index lists calls, etc). Without a singleton promise
// they would all send "new" simultaneously and the server would mint N
// disconnected sessions; whichever response landed last would win
// `memorySessionId` and the other N-1 sessions become orphan rows. The
// `sessionPromise` below serializes the first mint so every subsequent fetch
// waits and reuses the same uuid.
const SESSION_HEADER = 'X-Demo-Session';
const BYPASS_HEADER = 'X-Demo-Bypass-Token';
const STORAGE_KEY = 'afterglow.demo_session_id';
const BYPASS_TOKEN = process.env.EXPO_PUBLIC_DEMO_BYPASS_TOKEN ?? '';

let memorySessionId: string | null = null;
let sessionPromise: Promise<string> | null = null;

function readStoredSession(): string | null {
  if (memorySessionId) return memorySessionId;
  try {
    if (typeof localStorage === 'undefined') return null;
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeStoredSession(value: string): void {
  memorySessionId = value;
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, value);
    }
  } catch {
    /* private mode / native runtime / partitioned storage — ignore;
       memorySessionId still holds the value for the rest of the page. */
  }
}

/**
 * Pitch-day escape hatch: appending `?bypass=<token>` to the app URL flips the
 * client into "production tenant" mode for the rest of the session. The server
 * matches the same token from the DEMO_BYPASS_TOKEN env var.
 */
function detectBypassFromUrl(): void {
  if (typeof window === 'undefined' || !window.location) return;
  try {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('bypass');
    if (token && token === BYPASS_TOKEN) {
      writeStoredSession('bypass');
    }
  } catch {
    /* SSR / non-browser — ignore */
  }
}

detectBypassFromUrl();

async function primeSession(): Promise<string> {
  // Lightweight handshake: hit an endpoint that runs through
  // get_session_context so the server mints a DemoSession row and echoes the
  // uuid via X-Demo-Session. Templates list is fine — it is the cheapest
  // sandbox-aware GET.
  try {
    const res = await fetch(`${BASE}/api/v1/templates`, {
      headers: {
        Accept: 'application/json',
        [SESSION_HEADER]: 'new',
      },
    });
    const minted = res.headers.get(SESSION_HEADER);
    if (minted && minted !== 'new') {
      writeStoredSession(minted);
      return minted;
    }
  } catch {
    /* network blip — fall through to 'new' so the caller keeps going */
  }
  return 'new';
}

async function ensureSession(): Promise<string> {
  if (memorySessionId) return memorySessionId;
  const stored = readStoredSession();
  if (stored) {
    memorySessionId = stored;
    return stored;
  }
  if (!sessionPromise) {
    sessionPromise = primeSession().finally(() => {
      sessionPromise = null;
    });
  }
  return sessionPromise;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const sessionValue = await ensureSession();
  const sessionHeaders: Record<string, string> = {
    [SESSION_HEADER]: sessionValue,
  };
  if (sessionValue === 'bypass' && BYPASS_TOKEN) {
    sessionHeaders[BYPASS_HEADER] = BYPASS_TOKEN;
  }

  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init.body && !(init.body instanceof FormData)
        ? { 'Content-Type': 'application/json' }
        : {}),
      ...sessionHeaders,
      ...(init.headers ?? {}),
    },
  });

  const minted = res.headers.get(SESSION_HEADER);
  if (minted && minted !== sessionValue && minted !== 'bypass') {
    writeStoredSession(minted);
  }

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new ApiError(res.status, text || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(`HTTP ${status}: ${message}`);
    this.status = status;
  }
}

/**
 * `true` whenever the client is talking to the backend as a per-visitor demo
 * sandbox. `false` only when the user has flipped into bypass mode via
 * `?bypass=<token>` (i.e. the live production tenant during a pitch).
 *
 * UI bits that only make sense for visitors (e.g. the "Reset demo" button,
 * the "pick a template" bootstrap redirect) should be guarded behind this.
 */
export function isDemoMode(): boolean {
  return readStoredSession() !== 'bypass';
}

export const api = {
  listTemplates: () => request<TemplateView[]>('/api/v1/templates'),
  // Returns `null` when the visitor has no active template yet (fresh access
  // or post-reset): the backend responds 204 which our request() helper maps
  // to `undefined`; we normalize to `null` here so callers can rely on a
  // `=== null` check.
  getActiveTemplate: async (): Promise<TemplateView | null> => {
    const result = await request<TemplateView | undefined>(
      '/api/v1/templates/active',
    );
    return result ?? null;
  },
  resetDemo: () =>
    request<{ ok: boolean; session_id: string }>('/api/v1/demo/reset', {
      method: 'POST',
    }),
  getTemplate: (id: string) => request<TemplateView>(`/api/v1/templates/${id}`),
  setActiveTemplate: (template_id: string) =>
    request<TemplateView>('/api/v1/templates/active', {
      method: 'PUT',
      body: JSON.stringify({ template_id }),
    }),
  runWizard: (payload: TemplateWizardRequest) =>
    request<TemplateWizardResponse>('/api/v1/templates/wizard', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  runWizardChat: (payload: WizardChatRequest) =>
    request<WizardChatResponse>('/api/v1/templates/wizard/chat', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  validateDraft: (template: TemplateWizardResponse) =>
    request<ValidationReport>('/api/v1/templates/validate', {
      method: 'POST',
      body: JSON.stringify({ template }),
    }),
  createTemplate: (payload: CreateTemplateRequest) =>
    request<TemplateView>('/api/v1/templates', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateTemplate: (id: string, payload: UpdateTemplateRequest) =>
    request<TemplateView>(`/api/v1/templates/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  listCalls: (params?: { customer_id?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.customer_id) qs.set('customer_id', params.customer_id);
    if (params?.limit) qs.set('limit', String(params.limit));
    const suffix = qs.toString() ? `?${qs}` : '';
    return request<CallListItem[]>(`/api/v1/calls${suffix}`);
  },
  getCall: (id: string) => request<CallDetailView>(`/api/v1/calls/${id}`),

  submitAudio: async (audio: Blob, phone_e164: string, filename = 'audio.mp3') => {
    const fd = new FormData();
    fd.append('audio', audio as unknown as Blob, filename);
    fd.append('phone_e164', phone_e164);
    return request<CallSubmittedResponse>('/api/v1/calls', {
      method: 'POST',
      body: fd,
    });
  },

  listCustomers: (params?: { q?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.q) qs.set('q', params.q);
    if (params?.limit) qs.set('limit', String(params.limit));
    const suffix = qs.toString() ? `?${qs}` : '';
    return request<CustomerCard[]>(`/api/v1/customers${suffix}`);
  },
  getCustomerByPhone: (phone: string) =>
    request<CustomerCard | null>(`/api/v1/customers/by-phone/${encodeURIComponent(phone)}`),
  getCustomer: (id: string) => request<CustomerCard>(`/api/v1/customers/${id}`),

  listBookings: (params?: { limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.limit) qs.set('limit', String(params.limit));
    const suffix = qs.toString() ? `?${qs}` : '';
    return request<BookingListItem[]>(`/api/v1/bookings${suffix}`);
  },

  listAudit: (params?: { call_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.call_id) qs.set('call_id', params.call_id);
    const suffix = qs.toString() ? `?${qs}` : '';
    return request<AuditLogEntry[]>(`/api/v1/audit${suffix}`);
  },

  // Back-compat alias for the historical endpoint name; new code should
  // call undoAction / redoAction instead.
  revertAction: (action_id: string) =>
    request<void>(`/api/v1/actions/${action_id}/undo`, { method: 'POST' }),
  undoAction: (action_id: string) =>
    request<void>(`/api/v1/actions/${action_id}/undo`, { method: 'POST' }),
  redoAction: (action_id: string) =>
    request<void>(`/api/v1/actions/${action_id}/redo`, { method: 'POST' }),
  listActionCatalog: () =>
    request<ActionCatalogEntry[]>(`/api/v1/actions/catalog`),

  generateSimulationScript: (template_id: string) =>
    request<TemplateView>(`/api/v1/templates/${template_id}/simulation/script`, {
      method: 'POST',
    }),
  generateSimulationAudio: (template_id: string) =>
    request<TemplateView>(
      `/api/v1/templates/${template_id}/simulation/generate-audio`,
      { method: 'POST' },
    ),
  uploadSimulationAudio: async (template_id: string, file: Blob, filename = 'audio.wav') => {
    const fd = new FormData();
    fd.append('audio', file as unknown as Blob, filename);
    return request<TemplateView>(
      `/api/v1/templates/${template_id}/simulation/upload-audio`,
      { method: 'POST', body: fd },
    );
  },
  // Fetched as a Blob (not a plain <audio src=URL>) because the endpoint is
  // session-scoped and cross-origin: HTMLAudioElement cannot send custom
  // headers, so the caller is expected to convert the blob into an object
  // URL via URL.createObjectURL() before feeding it to <audio>.
  fetchSimulationAudio: async (
    template_id: string,
    mode: 'existing' | 'new' = 'existing',
  ): Promise<Blob> => {
    const sessionValue = await ensureSession();
    const headers: Record<string, string> = {
      [SESSION_HEADER]: sessionValue,
    };
    if (sessionValue === 'bypass' && BYPASS_TOKEN) {
      headers[BYPASS_HEADER] = BYPASS_TOKEN;
    }
    const res = await fetch(
      `${BASE}/api/v1/templates/${template_id}/simulation/audio?mode=${mode}`,
      { headers },
    );
    const minted = res.headers.get(SESSION_HEADER);
    if (minted && minted !== sessionValue && minted !== 'bypass') {
      writeStoredSession(minted);
    }
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new ApiError(res.status, text || res.statusText);
    }
    return res.blob();
  },
};
