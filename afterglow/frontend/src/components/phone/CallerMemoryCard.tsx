import type { CustomerCard } from "@/lib/types";

interface Props {
  customer?: CustomerCard | null;
  phone: string;
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

  return (
    <div className="rounded-xl bg-white/10 backdrop-blur-sm p-4 text-sm">
      <div className="text-zinc-300 text-[11px] uppercase tracking-widest">
        Caller memory
      </div>
      <div className="mt-1 text-zinc-50 text-base font-semibold">
        {customer.display_name ?? phone}
      </div>
      <div className="text-zinc-300 text-xs">
        {phone} · {customer.total_calls} prior call{customer.total_calls === 1 ? "" : "s"}
      </div>

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
        <p className="mt-3 text-zinc-100 leading-snug">
          {customer.memory_summary}
        </p>
      )}
    </div>
  );
}
