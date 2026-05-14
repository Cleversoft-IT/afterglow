import Link from "next/link";

export default async function Landing() {
  return (
    <main className="min-h-screen flex flex-col">
      <header className="px-8 py-6 flex items-center justify-between border-b">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-afterglow-700 grid place-items-center text-white text-sm font-bold">
            A
          </div>
          <span className="font-semibold tracking-tight">Afterglow</span>
          <span className="text-xs text-zinc-500 hidden sm:inline">
            What remains after the call
          </span>
        </div>
        <nav className="flex items-center gap-6 text-sm">
          <Link href="/dashboard/calls" className="text-zinc-700 hover:text-afterglow-700">
            Dashboard
          </Link>
          <Link
            href="/dialer/incoming/demo-restaurant-known"
            className="text-zinc-700 hover:text-afterglow-700"
          >
            Demo dialer
          </Link>
        </nav>
      </header>

      <section className="flex-1 grid lg:grid-cols-2 gap-10 px-8 py-16 max-w-6xl mx-auto items-center">
        <div>
          <h1 className="text-5xl font-bold tracking-tight">
            The human talks.
            <br />
            <span className="text-afterglow-700">The AI remembers and acts.</span>
          </h1>
          <p className="mt-6 text-lg text-zinc-600 max-w-md">
            Afterglow listens to your booking calls, structures every detail,
            remembers your customers across calls, and autonomously executes the
            follow-ups — bookings, confirmations, profile updates. You stay in
            control via instant revert.
          </p>
          <div className="mt-8 flex gap-3">
            <Link
              href="/dialer/incoming/demo-restaurant-known"
              className="inline-flex items-center px-5 py-3 rounded-lg bg-afterglow-700 text-white font-medium hover:bg-afterglow-800"
            >
              Try the dialer
            </Link>
            <Link
              href="/dashboard/templates/wizard"
              className="inline-flex items-center px-5 py-3 rounded-lg border border-zinc-300 text-zinc-800 font-medium hover:bg-zinc-100"
            >
              Build a template with AI
            </Link>
          </div>

          <div className="mt-12 grid grid-cols-3 gap-4 text-xs text-zinc-500">
            <Stat label="Powered by Gemini" value="multimodal · ADK" />
            <Stat label="Deployed on Vultr" value="RAG · Vector Store" />
            <Stat label="Speech via" value="Speechmatics" />
          </div>
        </div>

        <PhoneMockup />
      </section>

      <footer className="px-8 py-6 border-t text-xs text-zinc-500 flex items-center justify-between">
        <span>
          MIT-licensed prototype for AI Agent Olympics @ Milan AI Week 2026.
        </span>
        <Link href="/dashboard/calls" className="hover:text-afterglow-700">
          Dashboard →
        </Link>
      </footer>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="uppercase tracking-wider text-[10px] text-zinc-400">{label}</div>
      <div className="font-medium text-zinc-700">{value}</div>
    </div>
  );
}

function PhoneMockup() {
  return (
    <div className="mx-auto phone-shell px-6 pt-12 pb-6 flex flex-col">
      <div className="text-[11px] uppercase tracking-widest text-zinc-300">
        Incoming call
      </div>
      <div className="mt-3 text-3xl font-semibold">+39 333 111 2233</div>
      <div className="mt-1 text-sm text-zinc-300">
        Marco Rossi · repeat · gluten-free
      </div>

      <div className="mt-6 rounded-xl bg-white/10 backdrop-blur-sm p-4 text-sm">
        <div className="text-zinc-300 text-xs uppercase tracking-widest mb-1">
          Memory
        </div>
        <p className="text-zinc-50">
          Cliente abituale, intollerante al glutine. Ultima prenotazione: 4 persone,
          tavolo tranquillo.
        </p>
      </div>

      <div className="flex-1" />

      <div className="grid grid-cols-3 gap-4 pt-6 pb-4 items-end">
        <ActionBubble color="bg-rose-500/90" label="Decline" />
        <ActionBubble color="bg-afterglow-600 blue-glow animate-pulse-soft" label="AI mode" big />
        <ActionBubble color="bg-emerald-500/90" label="Answer" />
      </div>
    </div>
  );
}

function ActionBubble({
  color,
  label,
  big,
}: {
  color: string;
  label: string;
  big?: boolean;
}) {
  return (
    <div className="flex flex-col items-center gap-2">
      <div
        className={`${color} rounded-full grid place-items-center text-white shadow-lg ${
          big ? "w-20 h-20 text-sm" : "w-14 h-14 text-xs"
        }`}
      >
        ●
      </div>
      <div className="text-xs text-zinc-300">{label}</div>
    </div>
  );
}
