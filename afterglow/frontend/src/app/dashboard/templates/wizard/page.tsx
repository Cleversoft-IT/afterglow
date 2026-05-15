"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { Business, WizardResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

const fieldBaseClass = cn(
  "w-full rounded-2xl border border-ui-line bg-ui-surface px-4 py-3 text-sm text-ui-ink shadow-soft",
  "placeholder:text-ui-subtle/70",
  "transition-[border-color,box-shadow] duration-150",
  "focus:border-ui-mint focus:outline-none focus:ring-2 focus:ring-ui-mint/25 focus:ring-offset-2 focus:ring-offset-ui-canvas",
  "disabled:cursor-not-allowed disabled:opacity-40",
);

const controlClass = cn(fieldBaseClass, "mt-2");

const primaryBtnClass = cn(
  "inline-flex min-h-10 items-center justify-center rounded-full bg-ui-accent px-5 py-2.5 text-sm font-medium text-ui-surface shadow-soft",
  "transition-[opacity,transform] hover:opacity-90 active:scale-[0.99] disabled:pointer-events-none disabled:opacity-40",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ui-mint/45 focus-visible:ring-offset-2 focus-visible:ring-offset-ui-canvas",
);

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
    <div className="max-w-4xl px-5 py-8 sm:px-8 sm:py-10">
      <header className="mb-8 sm:mb-10">
        <h1 className="text-2xl font-semibold tracking-tight text-ui-ink">Template wizard</h1>
        <p className="mt-1 max-w-2xl text-sm leading-relaxed text-ui-subtle">
          Describe your phone intake in plain language. The AI proposes a
          structured template you can edit and save.
        </p>
        {business && (
          <p className="mt-3 text-xs text-ui-subtle">
            Target:{" "}
            <span className="font-medium text-ui-ink">{business.name}</span>{" "}
            ({business.domain})
          </p>
        )}
      </header>

      <form onSubmit={generate} className="max-w-2xl space-y-6">
        <label className="block text-sm font-medium text-ui-ink">
          Description
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={8}
            placeholder="I run a barbershop. Customers call to book a cut or a beard trim. I want to know their preferred barber and send a confirmation SMS."
            className={cn(controlClass, "min-h-[11rem] resize-y leading-relaxed")}
          />
        </label>

        <button
          type="submit"
          disabled={busy || description.length < 20 || !business}
          className={primaryBtnClass}
        >
          {busy ? "Generating…" : "Generate template"}
        </button>

        {err && (
          <p className="rounded-2xl border border-red-200/80 bg-red-50 px-4 py-3 text-sm text-red-800">
            {err}
          </p>
        )}
      </form>

      {result && (
        <section className="mt-10 space-y-6">
          <div className="rounded-2xl border border-ui-line bg-ui-surface p-6 shadow-soft">
            <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-ui-subtle">
              Generated template
            </div>
            <h2 className="mt-2 text-xl font-semibold tracking-tight text-ui-ink">{result.name}</h2>
            <p className="mt-2 text-sm leading-relaxed text-ui-subtle">{result.description}</p>
          </div>

          <div className="rounded-2xl border border-ui-line bg-ui-surface p-6 shadow-soft">
            <h3 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.14em] text-ui-subtle">
              Fields ({result.fields_schema.length})
            </h3>
            <ul className="space-y-2 text-sm">
              {result.fields_schema.map((f) => (
                <li
                  key={f.key}
                  className="flex items-center justify-between gap-3 rounded-xl border border-ui-line bg-ui-muted/40 px-3 py-2"
                >
                  <span>
                    <code className="font-mono text-ui-ink">{f.key}</code>{" "}
                    <span className="text-ui-subtle">{f.type}</span>
                  </span>
                  {f.required && (
                    <span className="text-[10px] font-medium uppercase tracking-wider text-red-700">
                      required
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-2xl border border-ui-line bg-ui-surface p-6 shadow-soft">
            <h3 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.14em] text-ui-subtle">
              Actions ({result.action_types.length})
            </h3>
            <ul className="space-y-2 text-sm">
              {result.action_types.map((a) => (
                <li
                  key={a.key}
                  className="flex items-center justify-between gap-3 rounded-xl border border-ui-line bg-ui-muted/40 px-3 py-2"
                >
                  <span>
                    <code className="font-mono text-ui-ink">{a.key}</code>{" "}
                    <span className="text-ui-subtle">{a.label}</span>
                  </span>
                  <span
                    className={
                      a.execution_mode === "manual-only"
                        ? "text-[10px] font-medium uppercase tracking-wider text-amber-800"
                        : "text-[10px] font-medium uppercase tracking-wider text-emerald-800"
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
