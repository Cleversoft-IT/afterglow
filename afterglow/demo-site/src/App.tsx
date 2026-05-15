const APP_URL =
  import.meta.env.VITE_APP_URL ?? 'https://app.95-179-245-107.sslip.io';

export default function App() {
  return (
    <div className="page">
      <header className="hero">
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
          <a className="primary" href="#demo">Try the live demo</a>
          <a className="secondary" href="#how">How it works</a>
        </div>
      </header>

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
            body="In production every call enriches a Vultr Vector Store collection. The next ring pre-fetches the caller's history via /v1/chat/completions/RAG so the operator opens the call already briefed. The public sandbox below isolates each visitor (audit log marks Vector Store as skipped on purpose), so try a private deployment to see the full memory loop."
          />
        </ol>
      </section>

      <section id="demo" className="demo">
        <h2>Live demo</h2>
        <p className="demo-help">
          The phone below is the real Afterglow app, running against the production backend on
          Vultr. Activate a template, tap the blue button, and inspect the call.
        </p>
        <div className="phone">
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
