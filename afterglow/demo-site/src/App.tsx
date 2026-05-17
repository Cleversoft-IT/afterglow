import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Bot, Zap, Brain, Layers, Play, ArrowRight, ExternalLink,
  Sun, Moon, Monitor, Maximize2,
  type LucideIcon,
} from 'lucide-react';
import { useTheme, type ThemeMode } from '@/lib/theme';

const APP_URL = import.meta.env.VITE_APP_URL ?? 'https://app.95-179-245-107.sslip.io';

const steps = [
  {
    n: '01',
    title: 'Pick a sector template',
    body: 'Restaurant, dentist, or body shop — each preset comes with its own fields, actions, and ASR dictionary.',
  },
  {
    n: '02',
    title: 'Press the blue button',
    body: 'One tap triggers the post-call pipeline on a real recording. No PBX, no test numbers — the demo is the app.',
  },
  {
    n: '03',
    title: 'Watch the call get structured',
    body: 'Speechmatics transcribes, Gemini extracts and classifies in a single structured pass, autonomous actions fire.',
  },
  {
    n: '04',
    title: 'Memory of returning callers',
    body: 'Every call enriches a Vultr Vector Store. The next ring pre-fetches caller history via RAG so the operator opens the call already briefed.',
  },
];

const features: { icon: LucideIcon; title: string; body: string }[] = [
  {
    icon: Bot,
    title: 'Autonomous, not a copilot',
    body: 'Actions execute themselves — bookings confirmed, WhatsApp messages sent, customer profiles updated. Every action is logged and can be individually reverted.',
  },
  {
    icon: Zap,
    title: 'Zero AI in the live call',
    body: "The pipeline runs entirely post-call. The operator's screen updates in the background while they're still saying goodbye. Postgres latency, not model latency.",
  },
  {
    icon: Brain,
    title: 'Caller memory',
    body: 'Every call enriches a Vector Store. At the next ring, prior history is pre-fetched via RAG so the operator greets the caller already knowing their preferences.',
  },
  {
    icon: Layers,
    title: 'Any vertical in minutes',
    body: 'A 4-step wizard turns a plain-language description into a typed extraction schema with fields, actions, and PII rules — no code required.',
  },
];

const team = [
  { name: 'Stefano Gheza',      photo: '/team/stefano_gheza.jpg' },
  { name: 'Gio Marco Baglioni', photo: '/team/gio_marco_baglioni.jpg' },
  { name: 'Daniele Chiminelli', photo: '/team/daniele_chiminelli.jpg' },
  { name: 'Nicola Gheza',       photo: '/team/nicola_gheza.webp' },
];

const partners = [
  {
    name: 'Vultr',
    pills: ['Managed Postgres', 'Vector Store', 'Cloud Compute', 'IAM'],
    description:
      'System of record for calls, actions, customer profiles, and audit log. Vector Store powers the RAG memory loop in production.',
  },
  {
    name: 'Google Gemini + ADK',
    pills: ['Gemini 2.0 Flash', 'Structured output', 'ADK agentic loop'],
    description:
      'A single Gemini structured-output call extracts every field, classifies intent, and plans actions. Google ADK drives the autonomous action planner.',
  },
  {
    name: 'Speechmatics',
    pills: ['Batch STT', 'Diarization', 'Language detect', 'TTS'],
    description:
      'Transcribes every recording with speaker labels and automatic language detection. Demo audio files were generated with Speechmatics TTS preview voices.',
  },
];

/* ─── Theme toggle (Auto / Light / Dark) ────────────────── */
function ThemeToggle() {
  const { mode, setMode } = useTheme();
  const options: { value: ThemeMode; label: string; icon: LucideIcon }[] = [
    { value: 'auto',  label: 'Auto',  icon: Monitor },
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'dark',  label: 'Dark',  icon: Moon },
  ];
  return (
    <div
      role="group"
      aria-label="Theme"
      className="inline-flex items-center gap-0.5 rounded-full border border-border/60 bg-card/60 p-0.5"
    >
      {options.map(({ value, label, icon: Icon }) => {
        const active = mode === value;
        return (
          <button
            key={value}
            type="button"
            aria-pressed={active}
            aria-label={`${label} theme`}
            onClick={() => setMode(value)}
            className={
              'flex h-7 w-7 items-center justify-center rounded-full transition-colors ' +
              (active
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:text-foreground')
            }
          >
            <Icon className="w-3.5 h-3.5" />
          </button>
        );
      })}
    </div>
  );
}

/* ─── Navbar ────────────────────────────────────────────── */
function Navbar() {
  return (
    <nav className="border-b border-border/50 bg-background/80 backdrop-blur-md">
      <div className="mx-auto max-w-5xl px-6 h-14 flex items-center justify-between gap-3">
        <span className="font-extrabold text-base tracking-tight text-foreground">
          after<span className="text-primary">glow</span>
        </span>
        <div className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
          <a href="#why" className="hover:text-foreground transition-colors">Why</a>
          <a href="#how" className="hover:text-foreground transition-colors">How it works</a>
          <a href="#demo" className="hover:text-foreground transition-colors">Live demo</a>
          <a href="#features" className="hover:text-foreground transition-colors">Features</a>
          <a href="#built-on" className="hover:text-foreground transition-colors">Tech stack</a>
        </div>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <Button asChild size="sm" className="rounded-full hidden md:flex">
            <a href="#demo">Try it live</a>
          </Button>
        </div>
      </div>
    </nav>
  );
}

/* ─── Section label ─────────────────────────────────────── */
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] font-bold uppercase tracking-[4px] text-primary mb-4">
      {children}
    </p>
  );
}

/* ─── Phone scale hook ──────────────────────────────────────
   Mirrors the CSS formula in .phone-stage so the page can show
   a "Scaled to N%" badge when (and only when) the phone is not
   at full logical size. */
const PHONE_H = 845;
const PHONE_FLOOR = 0.45;
const DEMO_CHROME = 48;

function usePhoneScale(): number {
  const [scale, setScale] = useState(1);
  useEffect(() => {
    const compute = () => {
      const vh = window.innerHeight;
      const raw = (vh - DEMO_CHROME) / PHONE_H;
      setScale(Math.min(1, Math.max(PHONE_FLOOR, raw)));
    };
    compute();
    window.addEventListener('resize', compute);
    return () => window.removeEventListener('resize', compute);
  }, []);
  return scale;
}

/* ─── Demo section ──────────────────────────────────────────
   Side-by-side: copy/CTAs on the left, full-viewport-height phone
   on the right. On narrow viewports the iframe is hidden and the
   page shows a single "Open the live app" CTA card instead. */
function DemoSection() {
  const scale = usePhoneScale();
  const scaledDown = scale < 0.999;
  const pct = Math.round(scale * 100);

  return (
    <section
      id="demo"
      className="border-t border-border/40 -mx-6 px-6 md:min-h-dvh md:flex md:items-center py-16 md:py-0"
    >
      <div className="w-full grid grid-cols-1 md:grid-cols-[minmax(260px,1fr)_auto] md:gap-12 lg:gap-16 items-center">
        {/* Left column: copy + CTAs (sits next to the phone) */}
        <div className="flex flex-col gap-6 max-w-md">
          <div>
            <SectionLabel>02 — Try it now</SectionLabel>
            <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-3">
              Live demo
            </h2>
            <div className="text-muted-foreground text-sm leading-relaxed space-y-3">
              <p>
                <span className="text-foreground font-medium">Not a mockup.</span>{' '}
                The phone runs the actual Afterglow app — same Expo / React Native
                build that ships in production — embedded as a live iframe against
                our backend on Vultr.
              </p>
              <p>
                Your first visit opens a{' '}
                <span className="text-foreground font-medium">welcome dialog</span>{' '}
                on Templates: pick one of the three seed presets — restaurant,
                dentist, body shop — for the fastest demo path, or describe your
                own business and let the wizard agent draft a template with you.
              </p>
              <p>
                Activating a template lands you on Home with seeded call history.
                From there, open <span className="text-foreground font-medium">
                Test simulator</span> in the drawer to run an incoming call,
                watch Afterglow analyze it, and inspect the extracted fields and
                actions in the call detail.
              </p>
            </div>
          </div>

          <div className="hidden md:flex flex-wrap items-center gap-3">
            <Button asChild className="rounded-full gap-2">
              <a href={APP_URL} target="_blank" rel="noopener noreferrer">
                Open in a new tab
                <ExternalLink className="w-4 h-4" />
              </a>
            </Button>
          </div>

          {/* Mobile: single CTA, no iframe-in-phone-in-phone */}
          <div className="md:hidden flex flex-col items-center gap-4 rounded-2xl border border-border/60 bg-card/60 p-8 mt-2">
            <p className="text-sm text-muted-foreground text-center leading-relaxed max-w-xs">
              The embedded preview is hidden on mobile — open the real app full-screen instead.
            </p>
            <Button asChild size="lg" className="rounded-full gap-2 w-full sm:w-auto">
              <a href={APP_URL} target="_blank" rel="noopener noreferrer">
                Open the live app
                <ExternalLink className="w-4 h-4" />
              </a>
            </Button>
          </div>
        </div>

        {/* Right column: phone */}
        <div className="hidden md:flex justify-center md:justify-end">
          <div className="phone-stage">
            <div className="demo-phone-glow" aria-hidden="true" />
            {scaledDown && (
              <div className="phone-scale-badge" aria-live="polite" title="The embedded phone is scaled to fit your viewport. Open in a new tab for full size.">
                <Maximize2 className="w-3 h-3" aria-hidden="true" />
                Scaled · {pct}%
              </div>
            )}
            <div className="phone-frame">
              <iframe
                title="Afterglow live demo"
                src={APP_URL}
                allow="autoplay; clipboard-write"
                loading="lazy"
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── App ───────────────────────────────────────────────── */
export default function App() {
  return (
    <div className="min-h-screen bg-background text-foreground antialiased">
      <Navbar />

      {/* ── Hero — full-viewport width so bg bleeds edge-to-edge */}
      <section className="relative overflow-hidden">
        <div className="hero-glow" aria-hidden="true" />
        <div className="dot-grid" aria-hidden="true" />
        <div className="hero-bottom-fade" aria-hidden="true" />

        <div className="relative mx-auto max-w-5xl px-6 pt-12 md:pt-20 pb-20 md:pb-24 grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
          <div className="flex flex-col items-start gap-7">
            <h1 className="text-5xl md:text-[62px] font-extrabold leading-[1.05] tracking-tight">
              AI for what happens
              <br />
              <span className="gradient-text">after</span> the call.
            </h1>

            <p className="text-muted-foreground text-lg leading-relaxed max-w-[440px]">
              The phone keeps ringing. The operator keeps answering. Afterglow listens to the
              recording, extracts the booking, updates the customer profile, and fires the
              follow-ups — all in the seconds after the caller hangs up.
            </p>

            <div className="flex flex-wrap gap-3">
              <Button asChild size="lg" className="rounded-full gap-2">
                <a href="#demo">
                  Live demo <ArrowRight className="w-4 h-4" />
                </a>
              </Button>
              <Button asChild variant="outline" size="lg" className="rounded-full">
                <a href="#how">How it works</a>
              </Button>
              <Button asChild variant="outline" size="lg" className="rounded-full">
                <a href="#built-on">Tech stack</a>
              </Button>
            </div>
          </div>

          <div className="relative flex justify-center items-center">
            <div className="phone-glow" aria-hidden="true" />
            <div className="relative phone-frame hero-phone">
              <div className="video-placeholder">
                <div className="play-icon">
                  <Play className="w-5 h-5" fill="currentColor" />
                </div>
                <p>Demo video coming soon</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-5xl px-6">

        {/* ── Problem / Solution ────────────────────────── */}
        <section id="why" className="py-20 md:py-24">
          <SectionLabel>Why it exists</SectionLabel>
          <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-6 items-stretch">
            <div className="rounded-xl border border-border/60 p-8 bg-card/60">
              <p className="text-xs font-bold uppercase tracking-[3px] text-muted-foreground mb-5">
                The problem
              </p>
              <p className="text-muted-foreground text-sm leading-relaxed mb-3">
                Operators take dozens of calls every day. Each one ends the same way: a
                handwritten note, a tab switch, a follow-up they might forget. The more calls,
                the more that falls through the cracks.
              </p>
              <p className="text-muted-foreground text-sm leading-relaxed">
                Booking software doesn't listen. CRMs don't pick up the phone. The human in
                the middle has to do all the translation — and they're already on the next call.
              </p>
            </div>

            <div className="hidden md:flex flex-col items-center justify-center gap-2 px-2">
              <div className="flex-1 w-px bg-border" />
              <ArrowRight className="w-5 h-5 text-primary" />
              <div className="flex-1 w-px bg-border" />
            </div>

            <div className="rounded-xl border border-primary/30 p-8 bg-primary/5 relative overflow-hidden">
              <div className="solution-shimmer" aria-hidden="true" />
              <p className="text-xs font-bold uppercase tracking-[3px] text-primary mb-5">
                The insight
              </p>
              <p className="text-muted-foreground text-sm leading-relaxed mb-3">
                AI shouldn't interrupt the call — that's a distraction. It should wait until
                the caller hangs up, then do everything the operator would have done manually:
                structure the conversation, update the profile, fire the actions.
              </p>
              <p className="text-sm leading-relaxed text-foreground/80">
                The operator's screen is ready{' '}
                <span className="font-semibold text-foreground">before</span> they even reach
                for the keyboard. That's the afterglow.
              </p>
            </div>
          </div>
        </section>

        {/* ── How it works ──────────────────────────────── */}
        <section id="how" className="py-20 md:py-24 border-t border-border/40">
          <SectionLabel>01 — The pipeline</SectionLabel>
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-10">
            How it works
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {steps.map((s) => (
              <div
                key={s.n}
                className="relative rounded-xl border border-border/60 bg-card p-6 pl-8 overflow-hidden hover:border-border transition-colors group"
              >
                <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-primary/30 group-hover:bg-primary transition-colors rounded-l-xl" />
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-bold uppercase tracking-[3px] text-primary mb-2">
                      Step {s.n}
                    </p>
                    <h3 className="font-semibold text-sm mb-2 text-foreground">{s.title}</h3>
                    <p className="text-muted-foreground text-sm leading-relaxed">{s.body}</p>
                  </div>
                  <span className="flex-shrink-0 text-5xl font-black leading-none text-border select-none pt-1">
                    {s.n}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── Live demo ─────────────────────────────────── */}
        <DemoSection />


        {/* ── What makes it different ───────────────────── */}
        <section id="features" className="py-20 md:py-24 border-t border-border/40">
          <SectionLabel>03 — Differentiators</SectionLabel>
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-12">
            What makes it different
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {features.map((f) => (
              <Card
                key={f.title}
                className="border-border/60 bg-card/80 hover:border-primary/40 hover:bg-card transition-all group feature-card-accent"
              >
                <CardHeader>
                  <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary/10 mb-3 group-hover:bg-primary/20 transition-colors">
                    <f.icon className="w-5 h-5 text-primary" />
                  </div>
                  <CardTitle className="text-base">{f.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground text-sm leading-relaxed">{f.body}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* ── Built on ──────────────────────────────────── */}
        <section id="built-on" className="py-20 md:py-24 border-t border-border/40">
          <SectionLabel>04 — The stack</SectionLabel>
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-12">
            Built on
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {partners.map((p) => (
              <div
                key={p.name}
                className="rounded-xl border border-border/60 bg-card/60 p-6 hover:border-border transition-colors"
              >
                <h3 className="font-bold text-sm mb-3 text-foreground">{p.name}</h3>
                <div className="flex flex-wrap gap-1.5 mb-4">
                  {p.pills.map((pill) => (
                    <span
                      key={pill}
                      className="inline-flex items-center px-2 py-0.5 rounded-md bg-secondary text-secondary-foreground text-[11px] font-medium border border-border/60"
                    >
                      {pill}
                    </span>
                  ))}
                </div>
                <p className="text-muted-foreground text-xs leading-relaxed">{p.description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── Team ──────────────────────────────────────── */}
        <section className="py-20 md:py-24 border-t border-border/40">
          <SectionLabel>05 — The team</SectionLabel>
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-12">
            Team Claudio Opuscoli
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
            {team.map((member) => (
              <div key={member.name} className="flex flex-col items-center gap-3 group">
                <div className="relative w-24 h-24 rounded-full overflow-hidden border-2 border-border/60 group-hover:border-primary/60 transition-colors">
                  <img
                    src={member.photo}
                    alt={member.name}
                    className="w-full h-full object-cover object-top"
                  />
                </div>
                <p className="text-sm font-semibold text-center text-foreground leading-snug">
                  {member.name}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* ── Footer ────────────────────────────────────── */}
        <footer className="py-12 md:py-14 border-t border-border/40 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted-foreground">
          <span className="font-bold text-sm text-foreground/70 tracking-tight">
            after<span className="text-primary">glow</span>
          </span>
          <p>MIT licensed · AI Hackathon by lablab.ai · Milano AI Week 2026</p>
        </footer>
      </div>
    </div>
  );
}
