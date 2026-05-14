import Link from "next/link";

import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function TemplatesPage() {
  const templates = await api.listTemplates().catch(() => []);
  return (
    <div className="px-5 py-8 sm:px-8 sm:py-10">
      <header className="mb-8 flex flex-col gap-4 sm:mb-10 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ui-ink">Templates</h1>
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-ui-subtle">
            Templates define which fields to extract, which actions to run, and how
            the AI should classify the call.
          </p>
        </div>
        <Link
          href="/dashboard/templates/wizard"
          className="inline-flex w-fit items-center justify-center rounded-full bg-ui-accent px-4 py-2.5 text-sm font-medium text-ui-surface shadow-soft transition-[opacity,transform] hover:opacity-90 active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ui-mint/45 focus-visible:ring-offset-2 focus-visible:ring-offset-ui-canvas"
        >
          Build with AI →
        </Link>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {templates.map((t) => (
          <div
            key={t.id}
            className="rounded-2xl border border-ui-line bg-ui-surface p-5 shadow-soft transition-shadow hover:shadow-[0_2px_10px_rgba(13,13,13,0.06)]"
          >
            <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-ui-subtle">
              v{t.version}
            </div>
            <h3 className="mt-1 text-lg font-semibold tracking-tight text-ui-ink">{t.name}</h3>
            {t.description && (
              <p className="mt-2 text-sm leading-relaxed text-ui-subtle">{t.description}</p>
            )}
            <div className="mt-5 grid grid-cols-2 gap-3 border-t border-ui-line pt-4 text-[11px] text-ui-subtle">
              <div>
                <div className="text-sm font-semibold text-ui-ink">{t.fields_schema.length}</div>
                fields
              </div>
              <div>
                <div className="text-sm font-semibold text-ui-ink">{t.action_types.length}</div>
                actions
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
