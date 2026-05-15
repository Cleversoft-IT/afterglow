import { notFound } from "next/navigation";

import { api } from "@/lib/api";

export default async function CustomerProfilePage({
  params,
}: {
  params: { id: string };
}) {
  const customer = await api.getCustomer(params.id).catch(() => null);
  if (!customer) notFound();
  return (
    <div className="max-w-3xl space-y-6 px-5 py-8 sm:px-8 sm:py-10">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-ui-ink">
          {customer.display_name ?? customer.phone_e164}
        </h1>
        <p className="mt-1 text-sm text-ui-subtle font-mono">{customer.phone_e164}</p>
      </header>

      {customer.memory_summary && (
        <section className="rounded-2xl border border-ui-line bg-ui-surface p-6 shadow-soft">
          <h2 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-ui-subtle">
            Memory
          </h2>
          <p className="text-sm leading-relaxed text-ui-ink">{customer.memory_summary}</p>
        </section>
      )}

      <section className="rounded-2xl border border-ui-line bg-ui-surface p-6 shadow-soft">
        <h2 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-ui-subtle">
          Tags
        </h2>
        <div className="flex flex-wrap gap-2">
          {customer.tags.length === 0 ? (
            <span className="text-sm text-ui-subtle">No tags yet.</span>
          ) : (
            customer.tags.map((t) => (
              <span
                key={t}
                className="rounded-full border border-ui-line bg-ui-muted px-2.5 py-1 text-xs font-medium text-ui-ink"
              >
                {t}
              </span>
            ))
          )}
        </div>
      </section>

      <section className="rounded-2xl border border-ui-line bg-ui-surface p-6 text-sm text-ui-subtle shadow-soft">
        Total calls: {customer.total_calls} · Last call: {customer.last_call_at ?? "—"}
      </section>
    </div>
  );
}
