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

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init.body && !(init.body instanceof FormData)
        ? { 'Content-Type': 'application/json' }
        : {}),
      ...(init.headers ?? {}),
    },
  });
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
