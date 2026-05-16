const APP_URL =
  import.meta.env.VITE_APP_URL ?? 'https://app.95-179-245-107.sslip.io';

export default function App() {
  return (
    <div className="page">

      {/* ── Hero (2-col: text left, video placeholder right) ─ */}
      <header className="hero">
        <div className="hero-text">
          <span className="eyebrow">Afterglow</span>
          <h1>
            AI for what happens
            <br />
            <em>after</em> the call.
          </h1>
          <p className="lede">
            The phone keeps ringing. The operator keeps answering. Afterglow listens to the
            recording, extracts the booking, updates the customer profile, and fires the
            follow-ups — all in the seconds after the caller hangs up.
          </p>
          <div className="cta-row">
            <a className="primary" href="#demo">Live demo</a>
            <a className="secondary" href="#how">How it works</a>
            <a className="secondary" href="#built-on">Tech stack</a>
          </div>
        </div>

        <div className="hero-demo">
          <div className="phone-frame">
            <div className="video-placeholder">
              <div className="play-icon" aria-hidden="true">▶</div>
              <p>Demo video coming soon</p>
            </div>
          </div>
        </div>
      </header>

      {/* ── Insight (problem / solution) ─────────────────── */}
      <section className="insight">
        <div className="insight-grid">
          <div className="insight-block problem">
            <span className="insight-label">The problem</span>
            <p>
              Operators take dozens of calls every day. Each one ends the same way: a
              handwritten note, a tab switch, a follow-up they might forget. The more
              calls, the more that falls through the cracks.
            </p>
            <p>
              Booking software doesn't listen. CRMs don't pick up the phone. The
              human in the middle has to do all the translation — and they're already
              on the next call.
            </p>
          </div>
          <div className="insight-divider" aria-hidden="true">→</div>
          <div className="insight-block solution">
            <span className="insight-label">The insight</span>
            <p>
              AI shouldn't interrupt the call — that's a distraction. It should wait
              until the caller hangs up, then do everything the operator would have
              done manually: structure the conversation, update the profile, fire the
              actions.
            </p>
            <p>
              The operator's screen is ready <em>before</em> they even reach for the
              keyboard. That's the afterglow.
            </p>
          </div>
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────── */}
      <section id="how" className="how">
        <h2>How it works</h2>
        <ol className="steps">
          <Step
            n={1}
            title="Pick a sector template"
            body="Restaurant, dentist, or body shop — each preset comes with its own fields, actions, and ASR dictionary."
          />
          <Step
            n={2}
            title="Press the blue button"
            body="One tap triggers the post-call pipeline on a real recording. No PBX, no test numbers — the demo is the app."
          />
          <Step
            n={3}
            title="Watch the call get structured"
            body="Speechmatics transcribes, Gemini extracts and classifies in a single structured pass, autonomous actions fire (and can be reverted)."
          />
          <Step
            n={4}
            title="Memory of returning callers"
            body="In production every call enriches a Vultr Vector Store collection. The next ring pre-fetches the caller's history via RAG so the operator opens the call already briefed."
          />
        </ol>
      </section>

      {/* ── Live demo ─────────────────────────────────────── */}
      <section id="demo" className="demo">
        <h2>Live demo</h2>
        <p className="demo-help">
          The phone below is the real Afterglow app, running against the production backend on
          Vultr. Activate a template, tap the blue button, and inspect the call.
        </p>
        <div className="phone-wrap">
          <div className="phone-frame">
            <iframe
              title="Afterglow live demo"
              src={APP_URL}
              allow="autoplay; clipboard-write"
              loading="lazy"
            />
          </div>
        </div>
      </section>

      {/* ── Feature highlights ────────────────────────────── */}
      <section className="features">
        <h2>What makes it different</h2>
        <div className="feature-grid">
          <FeatureCard
            icon="🎙️"
            title="Autonomous, not a copilot"
            body="Actions execute themselves — bookings confirmed, WhatsApp messages sent, customer profiles updated. No approve button. Every action is logged and can be individually reverted."
          />
          <FeatureCard
            icon="⚡"
            title="Zero AI in the live call"
            body="The pipeline runs entirely post-call. The operator's screen updates in the background while they're still saying goodbye. Postgres latency, not model latency."
          />
          <FeatureCard
            icon="🧠"
            title="Caller memory"
            body="Every call enriches a Vector Store. At the next ring, prior history is pre-fetched via RAG so the operator greets the caller already knowing their preferences and last visit."
          />
          <FeatureCard
            icon="🏗️"
            title="Any vertical in minutes"
            body="A 4-step wizard turns a plain-language description into a typed extraction schema with fields, actions, and PII rules — no code required."
          />
        </div>
      </section>

      {/* ── Built on (partner strip) ──────────────────────── */}
      <section id="built-on" className="built-on">
        <h2>Built on</h2>
        <div className="partner-grid">
          <PartnerCard
            name="Vultr"
            pills={['Managed Postgres', 'Vector Store', 'Cloud Compute', 'IAM']}
            description="System of record for calls, actions, customer profiles, and audit log. Vector Store powers the RAG memory loop in production."
          />
          <PartnerCard
            name="Google Gemini + ADK"
            pills={['Gemini 3.1 Flash', 'Structured output', 'ADK agentic loop']}
            description="A single Gemini structured-output call extracts every field, classifies intent, and plans actions. Google ADK drives the autonomous action planner."
          />
          <PartnerCard
            name="Speechmatics"
            pills={['Batch STT', 'Diarization', 'Language detect', 'TTS']}
            description="Transcribes every recording with speaker labels and automatic language detection. The demo audio files were generated with Speechmatics TTS preview voices."
          />
        </div>
      </section>

      <footer>
        <p>
          MIT licensed. Built for the AI Hackathon by lablab.ai (Milano AI Week 2026).
        </p>
      </footer>
    </div>
  );
}

function Step({ n, title, body }: { n: number; title: string; body: string }) {
  return (
    <li className="step">
      <span className="step-n">{n}</span>
      <div>
        <h3>{title}</h3>
        <p>{body}</p>
      </div>
    </li>
  );
}

function FeatureCard({ icon, title, body }: { icon: string; title: string; body: string }) {
  return (
    <div className="feature-card">
      <span className="feature-icon">{icon}</span>
      <h3>{title}</h3>
      <p>{body}</p>
    </div>
  );
}

function PartnerCard({
  name,
  pills,
  description,
}: {
  name: string;
  pills: string[];
  description: string;
}) {
  return (
    <div className="partner-card">
      <h3 className="partner-name">{name}</h3>
      <div className="partner-pills">
        {pills.map((p) => (
          <span key={p} className="pill">{p}</span>
        ))}
      </div>
      <p className="partner-desc">{description}</p>
    </div>
  );
}
