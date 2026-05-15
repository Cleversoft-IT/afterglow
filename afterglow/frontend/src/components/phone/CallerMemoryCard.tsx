import type { CustomerCard } from "@/lib/types";

interface Props {
  customer?: CustomerCard | null;
  phone: string;
}

const DATE_FMT = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

function formatLastCall(iso?: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return DATE_FMT.format(d);
}

export function CallerMemoryCard({ customer, phone }: Props) {
  if (!customer) {
    return (
      <div className="rounded-xl bg-white/10 backdrop-blur-sm p-4 text-sm">
        <div className="text-zinc-300 text-xs uppercase tracking-widest">
          New caller
        </div>
        <p className="text-zinc-50 mt-1">{phone}</p>
        <p className="text-zinc-300 text-xs mt-2">
          No prior calls in memory. Activate AI mode to start a profile.
        </p>
      </div>
    );
  }

  const lastCall = formatLastCall(customer.last_call_at);
  const callCount = customer.total_calls;

  return (
    <div className="rounded-xl bg-white/10 backdrop-blur-sm p-4 text-sm">
      <div className="text-zinc-300 text-[11px] uppercase tracking-widest">
        Caller memory
      </div>
      <div className="mt-1 text-zinc-50 text-base font-semibold">
        {customer.display_name ?? phone}
      </div>
      <div className="text-zinc-300 text-xs">{phone}</div>

      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
        <dt className="text-zinc-400">Prior calls</dt>
        <dd className="text-zinc-100">{callCount}</dd>
        {lastCall && (
          <>
            <dt className="text-zinc-400">Last call</dt>
            <dd className="text-zinc-100">{lastCall}</dd>
          </>
        )}
      </dl>

      {customer.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {customer.tags.map((t) => (
            <span
              key={t}
              className="rounded-full bg-afterglow-700/40 px-2 py-0.5 text-[11px] tracking-wide"
            >
              {t}
            </span>
          ))}
        </div>
      )}

      {customer.memory_summary && (
        <div className="mt-3 border-t border-white/10 pt-3">
          <div className="text-zinc-400 text-[10px] uppercase tracking-widest mb-1">
            Next-call briefing
          </div>
          <p className="text-zinc-100 leading-snug">{customer.memory_summary}</p>
        </div>
      )}
    </div>
  );
}
