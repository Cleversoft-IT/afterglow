// Thin fetch wrapper. Every call is absolute against EXPO_PUBLIC_API_BASE —
// Expo's static web build has no BFF, so relative paths would 404.

import type {
  AuditLogEntry,
  CallDetailView,
  CallListItem,
  CallSubmittedResponse,
  CustomerCard,
  TemplateView,
} from './types';

const BASE = (process.env.EXPO_PUBLIC_API_BASE ?? 'http://localhost:8000').replace(/\/$/, '');

// Demo iframe sandbox: every visitor of demo.* is identified by an opaque
// UUID stamped on every demo-side write so concurrent judges do not collide.
// The token lives in localStorage; first request sends the literal "new" and
// the backend echoes a freshly-minted uuid in the response header, which we
// persist for every subsequent fetch. Native / non-browser builds (no
// localStorage) fall back to in-memory storage — fine because the only path
// that needs isolation is the web iframe demo.
const SESSION_HEADER = 'X-Demo-Session';
const BYPASS_HEADER = 'X-Demo-Bypass-Token';
const STORAGE_KEY = 'afterglow.demo_session_id';
const BYPASS_TOKEN = process.env.EXPO_PUBLIC_DEMO_BYPASS_TOKEN ?? '';

let memorySessionId: string | null = null;

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
    /* private mode / native runtime — ignore */
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

function currentSessionHeader(): string {
  return readStoredSession() ?? 'new';
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const sessionValue = currentSessionHeader();
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

export const api = {
  listTemplates: () => request<TemplateView[]>('/api/v1/templates'),
  getActiveTemplate: () => request<TemplateView>('/api/v1/templates/active'),
  setActiveTemplate: (template_id: string) =>
    request<TemplateView>('/api/v1/templates/active', {
      method: 'PUT',
      body: JSON.stringify({ template_id }),
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

  getCustomerByPhone: (phone: string) =>
    request<CustomerCard | null>(`/api/v1/customers/by-phone/${encodeURIComponent(phone)}`),
  getCustomer: (id: string) => request<CustomerCard>(`/api/v1/customers/${id}`),

  listAudit: (params?: { call_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.call_id) qs.set('call_id', params.call_id);
    const suffix = qs.toString() ? `?${qs}` : '';
    return request<AuditLogEntry[]>(`/api/v1/audit${suffix}`);
  },

  revertAction: (action_id: string) =>
    request<void>(`/api/v1/actions/${action_id}/revert`, { method: 'POST' }),
};
