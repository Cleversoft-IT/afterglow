import type { ReactNode } from "react";
import Link from "next/link";
import { Cloud, Mic, Phone, PhoneOff, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

export default async function Landing() {
  return (
    <main className="landing-root relative flex min-h-dvh flex-col bg-ui-canvas text-ui-ink">
      <header className="sticky top-0 z-20 border-b border-ui-line bg-ui-surface/90 shadow-soft backdrop-blur-md">
        <div className="relative z-10 mx-auto flex max-w-6xl flex-col gap-5 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-8 sm:py-5">
          <div className="flex flex-wrap items-center gap-3">
            <div
              className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-ui-accent text-sm font-semibold text-ui-surface shadow-soft"
              aria-hidden
            >
              A
            </div>
            <div className="flex min-w-0 flex-col gap-0.5 sm:flex-row sm:items-baseline sm:gap-3">
              <span className="text-[15px] font-medium tracking-tight text-ui-ink">
                Afterglow
              </span>
              <span className="hidden text-[13px] text-ui-subtle sm:inline">
                What remains after the call
              </span>
            </div>
          </div>
          <nav
            className="flex flex-wrap items-center gap-7 text-sm sm:gap-8"
            aria-label="Primary"
          >
            <Link href="/dashboard/calls" className={navLinkClass}>
              Dashboard
            </Link>
            <Link
              href="/dialer/incoming/demo-restaurant-known"
              className={navLinkClass}
            >
              Demo dialer
            </Link>
          </nav>
        </div>
      </header>

      <section className="relative z-10 flex-1">
        <div className="relative z-10 mx-auto grid max-w-6xl items-center gap-12 px-5 py-14 sm:gap-16 sm:px-8 sm:py-16 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,400px)] lg:gap-20 lg:py-24 xl:px-10">
          <div className="min-w-0 max-w-xl flex-1 lg:max-w-none">
            <h1 className="text-balance text-[2.5rem] font-normal leading-[1.06] tracking-[-0.035em] text-ui-ink sm:text-5xl md:text-[3.2rem] md:leading-[1.05]">
              The human talks.
              <br />
              <span className="text-ui-subtle">The AI remembers and acts.</span>
            </h1>
            <p className="mt-8 max-w-[34rem] text-[16px] leading-7 text-ui-subtle sm:mt-10 sm:text-[17px] sm:leading-8">
              Afterglow listens to your booking calls, structures every detail,
              remembers your customers across calls, and autonomously executes the
              follow-ups — bookings, confirmations, profile updates. You stay in
              control via instant revert.
            </p>
            <div className="mt-10 flex flex-col gap-2.5 sm:flex-row sm:flex-wrap sm:items-center sm:gap-3">
              <Link
                href="/dialer/incoming/demo-restaurant-known"
                className={buttonPrimaryClass}
              >
                Try the dialer
              </Link>
              <Link
                href="/dashboard/templates/wizard"
                className={buttonSecondaryClass}
              >
                Build a template with AI
              </Link>
            </div>

            <div className="mt-16 border-t border-ui-line pt-10 sm:mt-20 sm:pt-12">
              <div className="grid gap-3 sm:grid-cols-3 sm:gap-4">
                <Stat
                  icon={<Sparkles className="h-4 w-4" strokeWidth={2} aria-hidden />}
                  label="Powered by Gemini"
                  value="multimodal · ADK"
                />
                <Stat
                  icon={<Cloud className="h-4 w-4" strokeWidth={2} aria-hidden />}
                  label="Deployed on Vultr"
                  value="RAG · Vector Store"
                />
                <Stat
                  icon={<Mic className="h-4 w-4" strokeWidth={2} aria-hidden />}
                  label="Speech via"
                  value="Speechmatics"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-center lg:justify-end">
            <PhoneMockup />
          </div>
        </div>
      </section>

      <footer className="relative z-10 mt-auto border-t border-ui-line bg-ui-surface/85 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-5 py-7 text-xs text-ui-subtle sm:flex-row sm:items-center sm:justify-between sm:px-8 sm:py-8">
          <span className="max-w-prose leading-relaxed">
            MIT-licensed prototype for AI Agent Olympics @ Milan AI Week 2026.
          </span>
          <Link
            href="/dashboard/calls"
            className={footerLinkClass}
          >
            Dashboard
            <span className="text-ui-line" aria-hidden>
              →
            </span>
          </Link>
        </div>
      </footer>
    </main>
  );
}

const navLinkClass = cn(
  "font-medium text-ui-subtle transition-colors hover:text-ui-ink",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ui-mint/35 focus-visible:ring-offset-2 focus-visible:ring-offset-ui-canvas focus-visible:rounded-md",
);

const buttonPrimaryClass = cn(
  "inline-flex min-h-10 min-w-[8.5rem] items-center justify-center rounded-full bg-ui-accent px-6 text-sm font-medium text-ui-surface",
  "shadow-soft transition-[opacity,transform] hover:opacity-90 active:scale-[0.99] active:opacity-95",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ui-mint/45 focus-visible:ring-offset-2 focus-visible:ring-offset-ui-canvas",
);

const buttonSecondaryClass = cn(
  "inline-flex min-h-10 min-w-[8.5rem] items-center justify-center rounded-full border border-ui-line bg-ui-surface px-6 text-sm font-medium text-ui-ink",
  "shadow-soft transition-colors hover:bg-ui-muted",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ui-mint/35 focus-visible:ring-offset-2 focus-visible:ring-offset-ui-canvas",
);

const footerLinkClass = cn(
  "inline-flex w-fit items-center gap-1.5 text-sm font-medium text-ui-subtle transition-colors hover:text-ui-mint",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ui-mint/35 focus-visible:ring-offset-2 focus-visible:ring-offset-ui-surface focus-visible:rounded-md",
);

function Stat({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="group flex gap-3 rounded-2xl border border-ui-line bg-ui-surface p-4 shadow-soft transition-shadow hover:shadow-[0_2px_8px_rgba(13,13,13,0.06)]">
      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-ui-line bg-ui-muted text-ui-subtle transition-colors group-hover:text-ui-mint">
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-ui-subtle">
          {label}
        </div>
        <div className="mt-1.5 text-[13px] font-medium leading-snug text-ui-ink">
          {value}
        </div>
      </div>
    </div>
  );
}

function PhoneMockup() {
  return (
    <div
      className="phone-shell mx-auto flex w-full max-w-[375px] flex-col px-6 pb-7 pt-11 sm:px-7"
      role="img"
      aria-label="Preview of incoming call screen with customer memory"
    >
      <div className="text-[11px] font-medium uppercase tracking-[0.2em] text-zinc-400">
        Incoming call
      </div>
      <div className="mt-3 text-[1.65rem] font-semibold tracking-tight text-white sm:text-3xl">
        +39 333 111 2233
      </div>
      <div className="mt-1.5 text-sm text-zinc-400">
        Marco Rossi · repeat · gluten-free
      </div>

      <div className="mt-7 rounded-2xl border border-white/10 bg-white/[0.06] p-4 backdrop-blur-sm">
        <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-500">
          Memory
        </div>
        <p className="mt-2 text-sm leading-relaxed text-zinc-100">
          Cliente abituale, intollerante al glutine. Ultima prenotazione: 4 persone,
          tavolo tranquillo.
        </p>
      </div>

      <div className="flex-1 min-h-[4rem]" />

      <div className="grid grid-cols-3 items-end gap-5 pb-2 pt-6">
        <ActionBubble
          icon={<PhoneOff className="h-5 w-5" strokeWidth={2} aria-hidden />}
          color="bg-rose-500/90 ring-1 ring-white/15"
          label="Decline"
        />
        <ActionBubble
          icon={<Sparkles className="h-6 w-6" strokeWidth={2} aria-hidden />}
          color="bg-afterglow-600 ring-1 ring-white/20 blue-glow"
          label="AI mode"
          big
          bubbleClassName="animate-pulse-soft"
        />
        <ActionBubble
          icon={<Phone className="h-5 w-5" strokeWidth={2} aria-hidden />}
          color="bg-emerald-500/90 ring-1 ring-white/15"
          label="Answer"
        />
      </div>
    </div>
  );
}

function ActionBubble({
  color,
  label,
  icon,
  big,
  bubbleClassName,
}: {
  color: string;
  label: string;
  icon: ReactNode;
  big?: boolean;
  bubbleClassName?: string;
}) {
  return (
    <div className="flex flex-col items-center gap-2.5">
      <div
        className={cn(
          "grid place-items-center rounded-full text-white shadow-[0_8px_24px_-12px_rgba(0,0,0,0.45)] transition-transform duration-200 hover:scale-[1.02]",
          color,
          big ? "h-[4.5rem] w-[4.5rem]" : "h-14 w-14",
          bubbleClassName,
        )}
      >
        {icon}
      </div>
      <div className="text-center text-[11px] font-medium text-zinc-400">{label}</div>
    </div>
  );
}
