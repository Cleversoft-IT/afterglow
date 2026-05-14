import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function BusinessPage() {
  const businesses = await api.listBusinesses().catch(() => []);
  return (
    <div className="px-8 py-10 max-w-3xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Businesses</h1>
        <p className="text-sm text-zinc-600">
          Each business is a tenant with its own templates, customers, and Vector
          Store collection.
        </p>
      </header>

      <div className="grid gap-4">
        {businesses.map((b) => (
          <div key={b.id} className="rounded-xl border bg-white p-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">{b.name}</h3>
                <p className="text-xs text-zinc-500 uppercase tracking-wider">
                  {b.domain} · {b.default_language} · {b.timezone}
                </p>
              </div>
              <code className="text-[10px] text-zinc-400">{b.id.slice(0, 8)}</code>
            </div>
            {b.vultr_collection_id && (
              <div className="mt-3 text-xs text-zinc-500">
                Vultr collection:{" "}
                <code className="text-afterglow-700">{b.vultr_collection_id}</code>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
