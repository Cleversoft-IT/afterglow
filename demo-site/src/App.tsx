import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Bot, Zap, Brain, Layers, ArrowRight, ExternalLink,
  Sun, Moon, Monitor, Maximize2, Sparkles, ChevronDown,
  type LucideIcon,
} from 'lucide-react';
import { DemoGuide } from './components/DemoGuide';

const REPO_URL = 'https://github.com/Cleversoft-IT/afterglow';

function GithubIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
      className={className}
    >
      <path d="M12 .5C5.73.5.5 5.73.5 12c0 5.08 3.29 9.39 7.86 10.91.58.11.79-.25.79-.56v-2c-3.2.7-3.87-1.37-3.87-1.37-.52-1.33-1.27-1.69-1.27-1.69-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.76 2.69 1.25 3.34.96.1-.75.4-1.25.73-1.54-2.55-.29-5.23-1.28-5.23-5.69 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.46.11-3.04 0 0 .97-.31 3.18 1.18a11.05 11.05 0 0 1 5.8 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.58.23 2.75.12 3.04.74.81 1.18 1.84 1.18 3.1 0 4.42-2.69 5.39-5.25 5.68.41.36.78 1.05.78 2.12v3.14c0 .31.21.67.79.56C20.21 21.39 23.5 17.08 23.5 12c0-6.27-5.23-11.5-11.5-11.5z" />
    </svg>
  );
}
import { useTheme, type ThemeMode } from '@/lib/theme';

const APP_URL = import.meta.env.VITE_APP_URL ?? 'https://app.afterglow.cleversoft.it';

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
    title: 'Vultr is the system of record',
    body: 'Calls, customers, audit log on Managed Postgres; caller memory on Vultr Vector Store. In production every call enriches the Vector Store; in the public demo the Vector Store is pre-seeded read-only, so the first ring of a known caller already retrieves real prior facts — judges see the RAG audit step succeed on day 1, not on call number two.',
  },
];

const features: { icon: LucideIcon; title: string; body: string }[] = [
  {
    icon: Bot,
    title: 'Autonomous, not a copilot',
    body: 'Bookings confirmed, WhatsApp messages sent, profiles updated — without a human in the loop. Every action is audit-logged with the evidence that triggered it, and any single one can be reverted from the call detail. Autonomy with a rollback.',
  },
  {
    icon: Zap,
    title: 'Zero AI in the live call',
    body: "The pipeline runs entirely post-call. The operator's screen updates in the background while they're still saying goodbye. Postgres latency, not model latency.",
  },
  {
    icon: Brain,
    title: 'Caller memory',
    body: 'Every production call enriches a Vector Store; at the next ring the prior history is pre-fetched via RAG so the operator greets the caller already knowing their preferences. The public demo runs the same retrieval read-only against a pre-seeded collection, so judges can watch the RAG audit step land on the very first call.',
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
    pills: ['Gemini 3.1 Flash Lite', 'Structured output', 'ADK agentic loop', 'Typed tool calls'],
    description:
      'A single Gemini/ADK agent runs the post-call loop turn by turn — on-demand Vultr RAG, transcript search, action execution with self-correction on failures — up to 12 turns. The final finalize_call returns the full structured analysis (fields, intent, sentiment, briefing) in one shot.',
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
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub repository"
            className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-border/60 bg-card/60 text-muted-foreground hover:text-foreground hover:border-border transition-colors"
          >
            <GithubIcon className="w-4 h-4" />
          </a>
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
   Copy-only section. The live phone now lives in the app shell's
   fixed right rail (see `AppShellPhone`), so this section is just
   the click-path narrative + the disclosures. On mobile the rail
   is hidden — the section still shows an "Open the live app" CTA
   card so the visitor isn't stuck. */
function DemoSection() {
  const [guideOpen, setGuideOpen] = useState(false);

  return (
    <section
      id="demo"
      className="border-t border-border/40 -mx-6 px-6 py-16"
    >
      <div className="w-full">
        <div className="flex flex-col gap-6 max-w-2xl">
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

          <Button
            variant="default"
            size="lg"
            className="rounded-full gap-2 w-fit"
            onClick={() => setGuideOpen(true)}
          >
            <Sparkles className="w-4 h-4" />
            How to get the most out of this demo
          </Button>
          <DemoGuide
            open={guideOpen}
            onOpenChange={setGuideOpen}
            appUrl={APP_URL}
          />

          <details className="demo-disclosure group">
            <summary className="demo-disclosure-summary">
              <span className="demo-disclosure-icon" aria-hidden="true">
                <Sparkles className="w-3.5 h-3.5" />
              </span>
              <span className="flex-1">
                <span className="demo-disclosure-eyebrow">Behind the scenes</span>
                <span className="demo-disclosure-title">
                  How a single-tenant product runs a public, multi-visitor demo
                </span>
              </span>
              <ChevronDown
                className="demo-disclosure-chevron w-4 h-4 flex-shrink-0"
                aria-hidden="true"
              />
            </summary>

            <div className="demo-disclosure-body">
              <p>
                Afterglow is{' '}
                <span className="text-foreground font-medium">
                  single-tenant by design
                </span>{' '}
                — one installation, one customer. The right shape for a small
                business buying the product, the wrong one for a public live
                demo. So we wrapped the same backend in a thin per-visitor
                sandbox:{' '}
                <span className="text-foreground font-medium">
                  the app inside the iframe is the real Afterglow build
                </span>
                , scoped to your private slice of the database.
              </p>

              <ol className="demo-disclosure-list">
                <li>
                  <span className="demo-disclosure-step">1</span>
                  <div>
                    <strong>Per-visitor sandbox.</strong> Your first visit mints
                    an opaque session id, persisted client-side and stamped on
                    every write. A single dependency in the API injects it into
                    every query, so two visitors share the schema but never the
                    rows — same Postgres, separate worlds.
                  </div>
                </li>
                <li>
                  <span className="demo-disclosure-step">2</span>
                  <div>
                    <strong>Shared seeds, private writes.</strong> The preset
                    templates and demo callers are read-only and visible to
                    everyone. Anything you create through the wizard, the call
                    simulator, or the autonomous action layer stays inside your
                    sandbox.
                  </div>
                </li>
                <li>
                  <span className="demo-disclosure-step">3</span>
                  <div>
                    <strong>Self-cleaning, with a pitch escape hatch.</strong>{' '}
                    Idle sandboxes are wiped after 24h; a reset endpoint clears
                    yours on demand. For our live presentation, a signed
                    bypass flips the same client into the production tenant —
                    same UX, single shared dataset.
                  </div>
                </li>
              </ol>

              <p className="demo-disclosure-footer">
                Same code path as production. The demo isn't a fork — it's the
                product with one extra column carrying the boundary.
              </p>
            </div>
          </details>

          <div className="flex flex-wrap items-center gap-3">
            <Button asChild className="rounded-full gap-2">
              <a href={APP_URL} target="_blank" rel="noopener noreferrer">
                Open in a new tab
                <ExternalLink className="w-4 h-4" />
              </a>
            </Button>
          </div>

          {/* Mobile fallback — the right-rail phone is hidden under
              1024 px, so we still need a CTA for phones / tablets. */}
          <div className="lg:hidden flex flex-col items-center gap-4 rounded-2xl border border-border/60 bg-card/60 p-8 mt-2">
            <p className="text-sm text-muted-foreground text-center leading-relaxed max-w-xs">
              The embedded preview is hidden on smaller screens — open the real app full-screen instead.
            </p>
            <Button asChild size="lg" className="rounded-full gap-2 w-full sm:w-auto">
              <a href={APP_URL} target="_blank" rel="noopener noreferrer">
                Open the live app
                <ExternalLink className="w-4 h-4" />
              </a>
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── Fixed right-rail demo phone (desktop only) ─────────
   Mounts the live iframe once at the App root and pins it to the
   right edge of the viewport, full-height. On scroll the content
   column slides past on the left; the phone stays visible the whole
   time. Hidden under 1024 px — mobile falls back to the "Open the
   live app" CTA card already present in the Live demo section.

   The iframe is mounted exactly once and never re-mounted, so the
   visitor's in-app state survives any cross-section scroll/jump
   between landing-page anchors. */
function AppShellPhone() {
  const scale = usePhoneScale();
  const scaledDown = scale < 0.999;
  const pct = Math.round(scale * 100);
  return (
    <aside className="app-shell__phone" aria-label="Live demo app">
      <div className="phone-stage">
        <div className="demo-phone-glow" aria-hidden="true" />
        {scaledDown && (
          <div
            className="phone-scale-badge"
            aria-live="polite"
            title="The embedded phone is scaled to fit your viewport. Open in a new tab for full size."
          >
            <Maximize2 className="w-3 h-3" aria-hidden="true" />
            Scaled · {pct}%
          </div>
        )}
        <div className="phone-frame">
          <iframe
            title="Afterglow live demo"
            src={APP_URL}
            allow="autoplay; clipboard-write"
            loading="eager"
          />
        </div>
      </div>
    </aside>
  );
}

/* ─── App ───────────────────────────────────────────────── */
export default function App() {
  return (
    <div className="app-shell min-h-screen bg-background text-foreground antialiased">
      <Navbar />

      <main className="app-shell__content">
      {/* ── Hero — full-viewport width so bg bleeds edge-to-edge */}
      <section className="relative overflow-hidden">
        <div className="hero-glow" aria-hidden="true" />
        <div className="dot-grid" aria-hidden="true" />
        <div className="hero-bottom-fade" aria-hidden="true" />

        <div className="relative mx-auto max-w-2xl px-6 pt-12 md:pt-20 pb-20 md:pb-24">
          <div className="flex flex-col items-start gap-7">
            <h1 className="text-5xl md:text-[62px] font-extrabold leading-[1.05] tracking-tight">
              Stay in the moment.
              <br />
              We handle the <span className="gradient-text">after</span>.
            </h1>

            <p className="text-muted-foreground text-lg leading-relaxed max-w-[440px]">
              The phone keeps ringing. The operator keeps answering. Afterglow listens to the
              recording, extracts the booking, updates the customer profile, and fires the
              follow-ups — all in the seconds after the caller hangs up.
            </p>

            <p className="inline-flex items-center gap-2 text-sm text-muted-foreground app-shell__hint">
              <ArrowRight className="w-4 h-4 text-primary" aria-hidden="true" />
              Try it now — the real app is running on the right.
            </p>

            <div className="flex flex-wrap gap-3">
              <Button asChild size="lg" className="rounded-full gap-2">
                <a href="#demo">
                  How to drive it <ArrowRight className="w-4 h-4" />
                </a>
              </Button>
              <Button asChild variant="outline" size="lg" className="rounded-full">
                <a href="#how">How it works</a>
              </Button>
              <Button asChild variant="outline" size="lg" className="rounded-full">
                <a href="#built-on">Tech stack</a>
              </Button>
            </div>

            <p className="inline-flex items-center gap-2 text-xs text-muted-foreground -mt-1">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0" />
              For service businesses where every call is a booking
            </p>
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
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-3">
            Team Claudio Opuscoli
          </h2>
          <p className="text-muted-foreground text-sm mb-12">
            Based in Italy · On-site at Milan AI Week 2026
          </p>
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
          <div className="flex flex-col sm:flex-row items-center gap-3 sm:gap-5">
            <p>MIT licensed · AI Hackathon by lablab.ai · Milano AI Week 2026</p>
            <a
              href={REPO_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 hover:text-foreground transition-colors"
            >
              <GithubIcon className="w-3.5 h-3.5" />
              GitHub
            </a>
          </div>
        </footer>
      </div>
      </main>

      {/* The phone is mounted exactly once at the App root so its
          iframe state survives all in-page scrolling and anchor jumps. */}
      <AppShellPhone />
    </div>
  );
}
