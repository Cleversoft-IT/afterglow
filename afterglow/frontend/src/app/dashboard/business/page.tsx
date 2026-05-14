import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function BusinessPage() {
  const businesses = await api.listBusinesses().catch(() => []);
  return (
    <div className="max-w-3xl space-y-8 px-5 py-8 sm:px-8 sm:py-10">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-ui-ink">Businesses</h1>
        <p className="mt-1 max-w-2xl text-sm leading-relaxed text-ui-subtle">
          Each business is a tenant with its own templates, customers, and Vector
          Store collection.
        </p>
      </header>

      <div className="grid gap-4">
        {businesses.map((b) => (
          <div
            key={b.id}
            className="rounded-2xl border border-ui-line bg-ui-surface p-5 shadow-soft transition-shadow hover:shadow-[0_2px_10px_rgba(13,13,13,0.06)]"
          >
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <h3 className="text-lg font-semibold tracking-tight text-ui-ink">{b.name}</h3>
                <p className="mt-1 text-xs font-medium uppercase tracking-[0.12em] text-ui-subtle">
                  {b.domain} · {b.default_language} · {b.timezone}
                </p>
              </div>
              <code className="shrink-0 text-[10px] text-ui-subtle">{b.id.slice(0, 8)}</code>
            </div>
            {b.vultr_collection_id && (
              <div className="mt-4 border-t border-ui-line pt-3 text-xs text-ui-subtle">
                Vultr collection:{" "}
                <code className="rounded-md bg-ui-muted px-1.5 py-0.5 font-mono text-ui-ink">
                  {b.vultr_collection_id}
                </code>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
