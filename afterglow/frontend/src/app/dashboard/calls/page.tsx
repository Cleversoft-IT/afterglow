import Link from "next/link";

import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function CallsPage() {
  const calls = await api.listCalls({ limit: 50 }).catch(() => []);
  return (
    <div className="px-5 py-8 sm:px-8 sm:py-10">
      <header className="mb-8 flex flex-col gap-4 sm:mb-10 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ui-ink">Calls</h1>
          <p className="mt-1 max-w-xl text-sm leading-relaxed text-ui-subtle">
            Every audio call processed by Afterglow lands here.
          </p>
        </div>
        <Link
          href="/dialer/incoming/demo-restaurant-known"
          className="inline-flex w-fit items-center justify-center rounded-full bg-ui-accent px-4 py-2.5 text-sm font-medium text-ui-surface shadow-soft transition-[opacity,transform] hover:opacity-90 active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ui-mint/45 focus-visible:ring-offset-2 focus-visible:ring-offset-ui-canvas"
        >
          Trigger demo call
        </Link>
      </header>

      {calls.length === 0 ? (
        <div className="mx-auto max-w-lg rounded-2xl border border-ui-line bg-ui-surface p-10 text-center shadow-soft sm:p-12">
          <p className="text-sm leading-relaxed text-ui-subtle">
            No calls yet. Trigger a demo call to see the pipeline run.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-ui-line bg-ui-surface shadow-soft">
          <table className="w-full text-sm">
            <thead className="bg-ui-muted text-left text-xs font-medium uppercase tracking-wide text-ui-subtle">
              <tr>
                <th className="px-4 py-3 font-medium normal-case tracking-normal">Phone</th>
                <th className="px-4 py-3 font-medium normal-case tracking-normal">Status</th>
                <th className="px-4 py-3 font-medium normal-case tracking-normal">Language</th>
                <th className="px-4 py-3 font-medium normal-case tracking-normal">Created</th>
                <th className="px-4 py-3 text-right font-medium normal-case tracking-normal" />
              </tr>
            </thead>
            <tbody className="divide-y divide-ui-line">
              {calls.map((c) => (
                <tr key={c.id} className="transition-colors hover:bg-ui-muted/50">
                  <td className="px-4 py-3 font-mono text-ui-ink">{c.phone_e164}</td>
                  <td className="px-4 py-3 text-ui-ink">{c.status}</td>
                  <td className="px-4 py-3 text-ui-ink">{c.detected_language ?? "—"}</td>
                  <td className="px-4 py-3 text-ui-subtle">{c.created_at}</td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/dialer/post-call/${c.id}`}
                      className="font-medium text-ui-subtle transition-colors hover:text-ui-mint focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ui-mint/35 focus-visible:ring-offset-2 focus-visible:ring-offset-ui-surface focus-visible:rounded-md"
                    >
                      Open →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
