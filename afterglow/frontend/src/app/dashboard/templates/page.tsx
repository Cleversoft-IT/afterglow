import Link from "next/link";

import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function TemplatesPage() {
  const templates = await api.listTemplates().catch(() => []);
  return (
    <div className="px-8 py-10">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Templates</h1>
          <p className="text-sm text-zinc-600">
            Templates define which fields to extract, which actions to run, and how
            the AI should classify the call.
          </p>
        </div>
        <Link
          href="/dashboard/templates/wizard"
          className="text-sm px-3 py-2 rounded bg-afterglow-700 text-white hover:bg-afterglow-800"
        >
          Build with AI →
        </Link>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {templates.map((t) => (
          <div key={t.id} className="rounded-xl border bg-white p-5">
            <div className="text-[11px] uppercase tracking-widest text-zinc-500">
              v{t.version}
            </div>
            <h3 className="text-lg font-semibold mt-1">{t.name}</h3>
            {t.description && (
              <p className="text-sm text-zinc-600 mt-1">{t.description}</p>
            )}
            <div className="mt-4 grid grid-cols-2 gap-3 text-[11px] text-zinc-500">
              <div>
                <div className="font-medium text-zinc-700">{t.fields_schema.length}</div>
                fields
              </div>
              <div>
                <div className="font-medium text-zinc-700">{t.action_types.length}</div>
                actions
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
