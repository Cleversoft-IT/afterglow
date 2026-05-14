"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { CallAction, CallDetail } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  callId: string;
}

export function PostCallActions({ callId }: Props) {
  const [call, setCall] = useState<CallDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let attempts = 0;

    async function poll() {
      try {
        const data = await api.getCall(callId);
        if (cancelled) return;
        setCall(data);
        if (data.status !== "completed" && data.status !== "failed" && attempts < 40) {
          attempts += 1;
          setTimeout(poll, 1500);
        }
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : String(e));
      }
    }
    poll();
    return () => {
      cancelled = true;
    };
  }, [callId]);

  async function onRevert(action: CallAction) {
    try {
      const updated = await api.revertAction(action.id);
      setCall((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          executed_actions: prev.executed_actions.map((a) =>
            a.id === updated.id ? updated : a,
          ),
        };
      });
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  if (err) return <p className="p-6 text-rose-600">{err}</p>;
  if (!call) return <p className="p-6 text-zinc-500">Loading call…</p>;

  return (
    <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <div className="text-xs uppercase tracking-widest text-zinc-500">
            Call · {call.detected_language ?? "—"} · {call.status}
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">{call.phone_e164}</h1>
        </div>
        <a href="/dashboard/calls" className="text-sm text-afterglow-700 hover:underline">
          ← Back to dashboard
        </a>
      </header>

      {call.extracted && (
        <section className="rounded-xl border bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-zinc-500 mb-3">
            Extracted fields
          </h2>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
            {Object.entries(call.extracted.fields ?? {}).map(([k, v]) => (
              <div key={k}>
                <dt className="text-zinc-500 text-xs uppercase tracking-wider">{k}</dt>
                <dd className="font-medium text-zinc-900">
                  {Array.isArray(v) ? v.join(", ") : String(v ?? "—")}
                  {call.extracted?.confidence?.[k] != null && (
                    <span className="ml-2 text-[11px] text-zinc-400">
                      ({(call.extracted.confidence[k] * 100).toFixed(0)}%)
                    </span>
                  )}
                </dd>
                {call.extracted?.evidence?.[k] && (
                  <p className="text-[11px] italic text-zinc-500 mt-0.5">
                    “{call.extracted.evidence[k]}”
                  </p>
                )}
              </div>
            ))}
          </dl>
        </section>
      )}

      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-zinc-500">
          Executed actions
        </h2>
        {call.executed_actions.length === 0 ? (
          <p className="text-sm text-zinc-500">
            No actions yet. The agent is still working — or no actions matched.
          </p>
        ) : (
          <ul className="space-y-3">
            {call.executed_actions.map((a) => (
              <ActionCard key={a.id} action={a} onRevert={() => onRevert(a)} />
            ))}
          </ul>
        )}
      </section>

      {call.raw_transcript?.text && (
        <section className="rounded-xl border bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-zinc-500 mb-2">
            Transcript
          </h2>
          <p className="text-sm leading-relaxed text-zinc-700 whitespace-pre-line">
            {call.raw_transcript.text}
          </p>
        </section>
      )}
    </div>
  );
}

function ActionCard({
  action,
  onRevert,
}: {
  action: CallAction;
  onRevert: () => void;
}) {
  const reverted = action.status === "reverted";
  const manual = action.status === "manual_required";
  return (
    <li
      className={cn(
        "rounded-xl border bg-white p-4 shadow-sm",
        reverted && "opacity-60 line-through",
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] uppercase tracking-widest text-afterglow-700">
              {action.action_type}
            </span>
            {manual && (
              <span className="rounded-full bg-amber-100 text-amber-700 text-[10px] uppercase tracking-wider px-2 py-0.5">
                manual required
              </span>
            )}
            {!manual && !reverted && (
              <span className="rounded-full bg-emerald-100 text-emerald-700 text-[10px] uppercase tracking-wider px-2 py-0.5">
                executed
              </span>
            )}
            {reverted && (
              <span className="rounded-full bg-zinc-200 text-zinc-700 text-[10px] uppercase tracking-wider px-2 py-0.5">
                reverted
              </span>
            )}
          </div>
          <h3 className="text-base font-semibold text-zinc-900 mt-1">
            {action.title}
          </h3>
          {action.summary && (
            <p className="text-sm text-zinc-600">{action.summary}</p>
          )}
          {action.confidence != null && (
            <p className="text-[11px] text-zinc-400 mt-1">
              confidence {(action.confidence * 100).toFixed(0)}%
            </p>
          )}
        </div>
        {action.status === "executed" && (
          <button
            onClick={onRevert}
            className="text-xs px-3 py-1.5 rounded border border-zinc-300 hover:bg-zinc-100"
          >
            Revert
          </button>
        )}
      </div>
    </li>
  );
}
