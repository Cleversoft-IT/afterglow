import Link from "next/link";

import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function CallsPage() {
  const calls = await api.listCalls({ limit: 50 }).catch(() => []);
  return (
    <div className="px-8 py-10">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Calls</h1>
          <p className="text-sm text-zinc-600">
            Every audio call processed by Afterglow lands here.
          </p>
        </div>
        <Link
          href="/dialer/incoming/demo-restaurant-known"
          className="text-sm px-3 py-2 rounded bg-afterglow-700 text-white hover:bg-afterglow-800"
        >
          Trigger demo call
        </Link>
      </header>

      {calls.length === 0 ? (
        <div className="rounded-xl border bg-white p-10 text-center text-zinc-500">
          No calls yet. Trigger a demo call to see the pipeline run.
        </div>
      ) : (
        <table className="w-full text-sm bg-white rounded-xl border overflow-hidden">
          <thead className="bg-zinc-50 text-zinc-500">
            <tr>
              <th className="text-left px-4 py-2 font-medium">Phone</th>
              <th className="text-left px-4 py-2 font-medium">Status</th>
              <th className="text-left px-4 py-2 font-medium">Language</th>
              <th className="text-left px-4 py-2 font-medium">Created</th>
              <th className="text-right px-4 py-2 font-medium" />
            </tr>
          </thead>
          <tbody>
            {calls.map((c) => (
              <tr key={c.id} className="border-t hover:bg-zinc-50">
                <td className="px-4 py-2 font-mono">{c.phone_e164}</td>
                <td className="px-4 py-2">{c.status}</td>
                <td className="px-4 py-2">{c.detected_language ?? "—"}</td>
                <td className="px-4 py-2 text-zinc-500">{c.created_at}</td>
                <td className="px-4 py-2 text-right">
                  <Link
                    href={`/dialer/post-call/${c.id}`}
                    className="text-afterglow-700 hover:underline"
                  >
                    Open →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
