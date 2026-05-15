"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { Business, WizardResponse } from "@/lib/types";

export default function WizardPage() {
  const [business, setBusiness] = useState<Business | null>(null);
  const [description, setDescription] = useState<string>("");
  const [result, setResult] = useState<WizardResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.getCurrentBusiness().then(setBusiness).catch(() => setBusiness(null));
  }, []);

  async function generate(e: React.FormEvent) {
    e.preventDefault();
    if (!business) {
      setErr("No business provisioned. Run the seed first.");
      return;
    }
    setBusy(true);
    setErr(null);
    setResult(null);
    try {
      const out = await api.templateWizard({
        business_id: business.id,
        description,
      });
      setResult(out);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="px-8 py-10 max-w-4xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Template wizard</h1>
        <p className="text-sm text-zinc-600">
          Describe your phone intake in plain language. The AI proposes a
          structured template you can edit and save.
        </p>
        {business && (
          <p className="mt-2 text-xs text-zinc-500">
            Target: <span className="font-medium text-zinc-700">{business.name}</span>{" "}
            ({business.domain})
          </p>
        )}
      </header>

      <form onSubmit={generate} className="space-y-4 max-w-2xl">
        <label className="block text-sm">
          <span className="text-zinc-700">Description</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={6}
            placeholder="I run a barbershop. Customers call to book a cut or a beard trim. I want to know their preferred barber and send a confirmation SMS."
            className="mt-1 w-full rounded border px-3 py-2 font-sans"
          />
        </label>

        <button
          type="submit"
          disabled={busy || description.length < 20 || !business}
          className="px-4 py-2 rounded bg-afterglow-700 text-white text-sm hover:bg-afterglow-800 disabled:opacity-50"
        >
          {busy ? "Generating…" : "Generate template"}
        </button>

        {err && <p className="text-rose-600 text-sm">{err}</p>}
      </form>

      {result && (
        <section className="mt-8 space-y-6">
          <div className="rounded-xl border bg-white p-5">
            <div className="text-[11px] uppercase tracking-widest text-zinc-500">
              Generated template
            </div>
            <h2 className="text-xl font-semibold mt-1">{result.name}</h2>
            <p className="text-sm text-zinc-600 mt-1">{result.description}</p>
          </div>

          <div className="rounded-xl border bg-white p-5">
            <h3 className="text-sm font-semibold uppercase tracking-widest text-zinc-500 mb-3">
              Fields ({result.fields_schema.length})
            </h3>
            <ul className="space-y-1 text-sm">
              {result.fields_schema.map((f) => (
                <li key={f.key} className="flex items-center justify-between">
                  <span>
                    <code className="text-afterglow-700">{f.key}</code>{" "}
                    <span className="text-zinc-500">{f.type}</span>
                  </span>
                  {f.required && (
                    <span className="text-[10px] uppercase tracking-wider text-rose-600">
                      required
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-xl border bg-white p-5">
            <h3 className="text-sm font-semibold uppercase tracking-widest text-zinc-500 mb-3">
              Actions ({result.action_types.length})
            </h3>
            <ul className="space-y-1 text-sm">
              {result.action_types.map((a) => (
                <li key={a.key} className="flex items-center justify-between">
                  <span>
                    <code className="text-afterglow-700">{a.key}</code>{" "}
                    <span className="text-zinc-500">{a.label}</span>
                  </span>
                  <span
                    className={
                      a.execution_mode === "manual-only"
                        ? "text-[10px] uppercase tracking-wider text-amber-600"
                        : "text-[10px] uppercase tracking-wider text-emerald-600"
                    }
                  >
                    {a.execution_mode}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}
    </div>
  );
}
