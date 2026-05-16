import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Bot, Zap, Brain, Layers, Play, ArrowRight, type LucideIcon } from 'lucide-react';

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

/* ─── Navbar ────────────────────────────────────────────── */
function Navbar() {
  return (
    <nav className="fixed top-9 inset-x-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-md">
      <div className="mx-auto max-w-5xl px-6 h-14 flex items-center justify-between">
        <span className="font-extrabold text-base tracking-tight text-foreground">
          after<span className="text-primary">glow</span>
        </span>
        <div className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
          <a href="#how" className="hover:text-foreground transition-colors">How it works</a>
          <a href="#demo" className="hover:text-foreground transition-colors">Live demo</a>
          <a href="#built-on" className="hover:text-foreground transition-colors">Tech stack</a>
        </div>
        <Button asChild size="sm" className="rounded-full hidden md:flex">
          <a href="#demo">Try it live</a>
        </Button>
      </div>
    </nav>
  );
}

/* ─── Hackathon banner ──────────────────────────────────── */
function HackathonBanner() {
  return (
    <div className="fixed top-0 inset-x-0 z-[60] bg-primary/10 border-b border-primary/20 backdrop-blur-sm">
      <div className="mx-auto max-w-5xl px-6 py-2 flex items-center justify-center gap-2 text-center">
        <span className="text-primary text-[11px] font-bold">⚡</span>
        <p className="text-xs text-foreground/80 leading-snug">
          <span className="font-semibold text-foreground">Team Claudio Opuscoli</span>
          {' '}· built entirely during the{' '}
          <span className="font-semibold text-foreground">lablab.ai Milano AI Week Hackathon</span>
          {' '}· every line of code written during the hackathon days.
        </p>
      </div>
    </div>
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

/* ─── App ───────────────────────────────────────────────── */
export default function App() {
  return (
    <div className="min-h-screen bg-background text-foreground antialiased">
      <HackathonBanner />
      <Navbar />

      {/* ── Hero — full-viewport width so bg bleeds edge-to-edge */}
      <section className="relative overflow-hidden">
        <div className="hero-glow" aria-hidden="true" />
        <div className="dot-grid" aria-hidden="true" />
        <div className="hero-bottom-fade" aria-hidden="true" />

        <div className="relative mx-auto max-w-5xl px-6 pt-[112px] pb-24 grid grid-cols-1 md:grid-cols-2 gap-12 items-center min-h-dvh">
          <div className="flex flex-col items-start gap-7">
            <Badge
              variant="outline"
              className="uppercase tracking-[4px] text-[11px] font-bold text-primary border-primary/40 bg-primary/10"
            >
              Afterglow · AI Hackathon 2026
            </Badge>

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
        <section className="py-16">
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
        <section id="how" className="py-16 border-t border-border/40">
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
        <section id="demo" className="py-16 border-t border-border/40">
          <SectionLabel>02 — Try it now</SectionLabel>
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-3">
            Live demo
          </h2>
          <p className="text-muted-foreground text-sm mb-14 max-w-xl leading-relaxed">
            The phone below is the real Afterglow app, running against the production backend
            on Vultr. Activate a template, tap the blue button, and inspect the call.
          </p>
          <div className="flex justify-center">
            <div className="relative">
              <div className="demo-phone-glow" aria-hidden="true" />
              <div className="relative phone-frame">
                <iframe
                  title="Afterglow live demo"
                  src={APP_URL}
                  allow="autoplay; clipboard-write"
                  loading="lazy"
                />
              </div>
            </div>
          </div>
        </section>

        {/* ── What makes it different ───────────────────── */}
        <section className="py-16 border-t border-border/40">
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
        <section id="built-on" className="py-16 border-t border-border/40">
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
        <section className="py-16 border-t border-border/40">
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
        <footer className="py-10 border-t border-border/40 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted-foreground">
          <span className="font-bold text-sm text-foreground/70 tracking-tight">
            after<span className="text-primary">glow</span>
          </span>
          <p>MIT licensed · AI Hackathon by lablab.ai · Milano AI Week 2026</p>
        </footer>
      </div>
    </div>
  );
}
