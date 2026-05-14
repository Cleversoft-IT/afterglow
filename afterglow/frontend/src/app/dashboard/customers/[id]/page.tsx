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
    <div className="px-8 py-10 space-y-6 max-w-3xl">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">
          {customer.display_name ?? customer.phone_e164}
        </h1>
        <p className="text-sm text-zinc-600 font-mono">{customer.phone_e164}</p>
      </header>

      {customer.memory_summary && (
        <section className="rounded-xl border bg-white p-5">
          <h2 className="text-xs uppercase tracking-widest text-zinc-500 mb-2">
            Memory
          </h2>
          <p className="text-sm leading-relaxed text-zinc-800">
            {customer.memory_summary}
          </p>
        </section>
      )}

      <section className="rounded-xl border bg-white p-5">
        <h2 className="text-xs uppercase tracking-widest text-zinc-500 mb-2">
          Tags
        </h2>
        <div className="flex flex-wrap gap-1.5">
          {customer.tags.length === 0 ? (
            <span className="text-sm text-zinc-500">No tags yet.</span>
          ) : (
            customer.tags.map((t) => (
              <span
                key={t}
                className="rounded-full bg-afterglow-50 text-afterglow-700 text-xs px-2 py-0.5"
              >
                {t}
              </span>
            ))
          )}
        </div>
      </section>

      <section className="rounded-xl border bg-white p-5 text-sm text-zinc-500">
        Total calls: {customer.total_calls} · Last call: {customer.last_call_at ?? "—"}
      </section>
    </div>
  );
}
