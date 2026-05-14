import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AuditPage() {
  const entries = await api.listAudit().catch(() => []);
  return (
    <div className="px-8 py-10">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Audit log</h1>
        <p className="text-sm text-zinc-600">
          Every step every agent takes is written here — production-shape, queryable,
          ready for compliance review.
        </p>
      </header>

      {entries.length === 0 ? (
        <div className="rounded-xl border bg-white p-10 text-center text-zinc-500">
          Audit empty. Trigger a call to populate.
        </div>
      ) : (
        <table className="w-full text-xs bg-white rounded-xl border overflow-hidden">
          <thead className="bg-zinc-50 text-zinc-500">
            <tr>
              <th className="text-left px-3 py-2 font-medium">Agent</th>
              <th className="text-left px-3 py-2 font-medium">Step</th>
              <th className="text-left px-3 py-2 font-medium">Model</th>
              <th className="text-right px-3 py-2 font-medium">Duration</th>
              <th className="text-left px-3 py-2 font-medium">Status</th>
              <th className="text-left px-3 py-2 font-medium">Created</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.id} className="border-t hover:bg-zinc-50">
                <td className="px-3 py-2 font-mono">{e.agent_name}</td>
                <td className="px-3 py-2">{e.step_type}</td>
                <td className="px-3 py-2 text-zinc-500">{e.model ?? "—"}</td>
                <td className="px-3 py-2 text-right font-mono">{e.duration_ms ?? "—"} ms</td>
                <td className="px-3 py-2">{e.status}</td>
                <td className="px-3 py-2 text-zinc-400">{e.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
