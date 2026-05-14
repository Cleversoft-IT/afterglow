import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AuditPage() {
  const entries = await api.listAudit().catch(() => []);
  return (
    <div className="px-5 py-8 sm:px-8 sm:py-10">
      <header className="mb-8 sm:mb-10">
        <h1 className="text-2xl font-semibold tracking-tight text-ui-ink">Audit log</h1>
        <p className="mt-1 max-w-2xl text-sm leading-relaxed text-ui-subtle">
          Every step every agent takes is written here — production-shape, queryable,
          ready for compliance review.
        </p>
      </header>

      {entries.length === 0 ? (
        <div className="mx-auto max-w-lg rounded-2xl border border-ui-line bg-ui-surface p-10 text-center shadow-soft sm:p-12">
          <p className="text-sm leading-relaxed text-ui-subtle">
            Audit empty. Trigger a call to populate.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-ui-line bg-ui-surface shadow-soft">
          <table className="w-full text-xs">
            <thead className="bg-ui-muted text-left font-medium uppercase tracking-wide text-ui-subtle">
              <tr>
                <th className="px-3 py-3 font-medium normal-case tracking-normal">Agent</th>
                <th className="px-3 py-3 font-medium normal-case tracking-normal">Step</th>
                <th className="px-3 py-3 font-medium normal-case tracking-normal">Model</th>
                <th className="px-3 py-3 text-right font-medium normal-case tracking-normal">Duration</th>
                <th className="px-3 py-3 font-medium normal-case tracking-normal">Status</th>
                <th className="px-3 py-3 font-medium normal-case tracking-normal">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ui-line">
              {entries.map((e) => (
                <tr key={e.id} className="transition-colors hover:bg-ui-muted/50">
                  <td className="px-3 py-2.5 font-mono text-ui-ink">{e.agent_name}</td>
                  <td className="px-3 py-2.5 text-ui-ink">{e.step_type}</td>
                  <td className="px-3 py-2.5 text-ui-subtle">{e.model ?? "—"}</td>
                  <td className="px-3 py-2.5 text-right font-mono text-ui-ink">
                    {e.duration_ms ?? "—"} ms
                  </td>
                  <td className="px-3 py-2.5 text-ui-ink">{e.status}</td>
                  <td className="px-3 py-2.5 text-ui-subtle">{e.created_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
