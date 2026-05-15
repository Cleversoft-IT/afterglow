// Thin fetch wrapper. Talks to the Next.js BFF rewrites (so no CORS in the browser).
// On the server (RSC) rewrites don't apply, so use an absolute URL from NEXT_PUBLIC_API_BASE.

const BASE =
  typeof window === "undefined" ? process.env.NEXT_PUBLIC_API_BASE ?? "" : "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    cache: "no-store",
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status} on ${path}: ${text || res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  // The single-tenant entry point. UIs not tied to the multi-domain demo
  // dialer should call this and forget about business_id selection.
  getCurrentBusiness: () =>
    request<import("./types").Business>("/api/v1/businesses/current"),

  // Kept for the multi-domain demo dialer at /dialer/incoming/[callId], which
  // routes by domain. Not used by the dashboard.
  listBusinesses: () => request<import("./types").Business[]>("/api/v1/businesses"),
  getBusiness: (id: string) => request<import("./types").Business>(`/api/v1/businesses/${id}`),

  listCalls: (params?: { business_id?: string; customer_id?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.business_id) qs.set("business_id", params.business_id);
    if (params?.customer_id) qs.set("customer_id", params.customer_id);
    if (params?.limit) qs.set("limit", String(params.limit));
    const q = qs.toString();
    return request<import("./types").CallDetail[]>(`/api/v1/calls${q ? `?${q}` : ""}`);
  },
  getCall: (id: string) => request<import("./types").CallDetail>(`/api/v1/calls/${id}`),
  submitAudio: async (formData: FormData) => {
    const res = await fetch("/api/v1/calls", { method: "POST", body: formData });
    if (!res.ok) throw new Error(`upload failed: ${res.status}`);
    return (await res.json()) as { call_id: string; status: string };
  },

  getCustomerByPhone: (phone: string, business_id: string) =>
    request<import("./types").CustomerCard | null>(
      `/api/v1/customers/by-phone/${encodeURIComponent(phone)}?business_id=${business_id}`,
    ),
  getCustomer: (id: string) => request<import("./types").CustomerCard>(`/api/v1/customers/${id}`),

  listTemplates: (business_id?: string) =>
    request<import("./types").TemplateView[]>(
      `/api/v1/templates${business_id ? `?business_id=${business_id}` : ""}`,
    ),
  templateWizard: (body: { business_id: string; description: string; language?: string }) =>
    request<import("./types").WizardResponse>("/api/v1/templates/wizard", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  revertAction: (action_id: string) =>
    request<import("./types").CallAction>(`/api/v1/actions/${action_id}/revert`, { method: "POST" }),

  listAudit: (call_id?: string) =>
    request<import("./types").AuditEntry[]>(
      `/api/v1/audit${call_id ? `?call_id=${call_id}` : ""}`,
    ),
};
