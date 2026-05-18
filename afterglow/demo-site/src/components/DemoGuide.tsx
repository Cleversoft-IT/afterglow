// "How to get the most out of this demo" modal.
//
// Six-step playthrough wrapped in a Radix Dialog, launched from the
// CTA inside DemoSection. Each step explains a concrete user action
// inside the live iframe + a collapsible "Under the hood" block that
// names the hackathon partners and stack pieces involved (round-10
// architecture: single run_call_agent Gemini/ADK multi-turn).
//
// Implementation plan: `.claude/plans/wise-bubbling-brooks.md`.
// IMPORTANT: do NOT modify phone-frame CSS rules to evolve this
// component — see `.claude/memory/feedback_demo_over_gif.md`.

import { Dialog } from 'radix-ui';
import { X, ExternalLink, Sparkles } from 'lucide-react';

type DemoGuideProps = {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  appUrl: string;
};

type Step = {
  title: string;
  action: React.ReactNode;
  underHood: React.ReactNode;
};

const STEPS: Step[] = [
  {
    title: 'Activate a preset',
    action: (
      <>
        Open the <strong>Templates</strong> drawer item (the welcome dialog also
        appears on first load). Pick one of the three presets —{' '}
        <code>Restaurant</code>, <code>Dentist</code>, <code>Body shop</code> —
        and tap <code>Activate</code>.
      </>
    ),
    underHood: (
      <>
        Each preset ships a Pydantic <code>fields_schema</code> for the post-call
        extractor, an action catalog (book, send confirmation, flag follow-up),
        and a pair of Speechmatics-TTS MP3s (
        <code>&lt;domain&gt;_existing.mp3</code> +{' '}
        <code>&lt;domain&gt;_new.mp3</code>) wired into the simulator. Seed lives
        in <code>backend/app/db/seed.py</code>. Templates built later via the
        wizard ship WAVs instead — see step 5.
      </>
    ),
  },
  {
    title: 'Explore the calls feed',
    action: (
      <>
        On Home, switch between <code>All</code> / <code>Missed</code> /{' '}
        <code>Bookings</code> / <code>Clients</code> / <code>Saved</code> /{' '}
        <code>Unsaved</code> filter chips. Open any call for{' '}
        <em>extracted fields, intent, urgency, sentiment</em>, and the{' '}
        <em>next-call briefing</em>. Tap <code>🔄 Regenerate briefing</code> to
        re-run the LLM on the same transcript. Tap a customer's name to see
        their full history.
      </>
    ),
    underHood: (
      <>
        The briefing comes from <code>briefing_regenerator</code> — a single
        Gemini structured-output call, separate from the live agent — using
        customer memory pulled from <strong>Vultr Vector Store</strong>. In demo
        mode the pipeline reads RAG context but never writes back; the
        seed-customer collection is pre-baked at boot.
      </>
    ),
  },
  {
    title: 'Simulate a call',
    action: (
      <>
        Drawer → <code>Test simulator</code>. Tap{' '}
        <code>Call from existing customer</code> to hear the AI handle a
        returning caller with memory, or <code>Call from new customer</code> for
        a cold lead. The phone drives through ringing → in-call → hang-up →
        post-call view.
      </>
    ),
    underHood: (
      <>
        A real Speechmatics-TTS WAV is streamed to the backend, then transcribed
        (<strong>Speechmatics</strong> batch STT with diarization + language
        detect). The post-call pipeline is{' '}
        <strong>a single Gemini/ADK agent</strong>: turn by turn it chooses
        whether to call <code>lookup_customer_memory</code> (Vultr Vector Store,
        on demand), <code>search_transcript</code>,{' '}
        <code>read_transcript_segment</code>, the template's action tools (which
        execute inline and return <code>{`{status, result}`}</code> so the model
        can self-correct on failures), <code>flag_for_review</code>, and finally{' '}
        <code>finalize_call</code>. Up to 12 turns. Running out of budget lands
        the call on <code>needs_review</code> — explicit failure, no silent stub.
      </>
    ),
  },
  {
    title: 'Build a template from scratch',
    action: (
      <>
        Templates → <code>Build from prompt</code>. Describe your business in
        plain English; the wizard asks 2–5 questions, proposes fields + actions,
        then tap <code>Save</code> (<code>Set as active</code> flips it on
        immediately).
      </>
    ),
    underHood: (
      <>
        The <code>wizard_chat</code> agent (Gemini structured output) fills
        slots iteratively — name, domain hint, <code>fields_schema</code>,{' '}
        <code>action_types</code> — validating each action key against the
        global action catalog. Hard 5-question ceiling keeps the UX tight.
      </>
    ),
  },
  {
    title: 'Generate the demo audio for your template',
    action: (
      <>
        On the new template, open <code>Test simulator</code>. Tap{' '}
        <code>Generate script</code> (the LLM writes the dialogue), then{' '}
        <code>Generate audio (Speechmatics TTS)</code> — 30 seconds later you
        have two WAVs and the simulator lights up like for a preset.
      </>
    ),
    underHood: (
      <>
        Custom templates produce <code>&lt;template_id&gt;_existing.wav</code> +{' '}
        <code>&lt;template_id&gt;_new.wav</code>. The script generator builds a
        coherent multi-turn dialogue using the template's{' '}
        <code>fields_schema</code>; <strong>Speechmatics TTS</strong> renders it
        multi-voice. Status (<code>pending</code> / <code>ready</code>) tracked
        in <code>template.simulation_config.scenarios.*.audio_status</code>.
      </>
    ),
  },
  {
    title: 'Inspect the pipeline via audit',
    action: (
      <>
        Drawer → <code>Audit</code>. Expand any call to walk the agent loop turn
        by turn. Tap <code>▸ Show payload</code> on any leaf for raw JSON.
      </>
    ),
    underHood: (
      <>
        The audit log is the demo's source of truth. Per call you see{' '}
        <code>agent_loop_start</code> → <code>agent_turn</code> (×N, one per ADK
        iteration) → <code>agent_loop_end</code>, plus <code>action_exec</code>{' '}
        rows tagged with <code>payload.agent_turn</code> so the UI's{' '}
        <code>&lt;AgentReasoningTrail&gt;</code> groups actions under their
        source turn deterministically. Each row records input/output tokens,
        duration, status, full payload. Actions flagged{' '}
        <code>mock_external: true</code> are simulated integrations;{' '}
        <code>mutates: true</code> means the DB actually changed.
      </>
    ),
  },
];

export function DemoGuide({ open, onOpenChange, appUrl }: DemoGuideProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="demo-guide-overlay" />
        <Dialog.Content
          className="demo-guide-content"
          aria-describedby="demo-guide-description"
        >
          <div className="demo-guide-header">
            <span className="demo-guide-icon" aria-hidden="true">
              <Sparkles className="w-4 h-4" />
            </span>
            <div className="demo-guide-header-text">
              <Dialog.Title className="demo-guide-title">
                Make this demo earn its keep
              </Dialog.Title>
              <Dialog.Description
                id="demo-guide-description"
                className="demo-guide-description"
              >
                Six steps, ~5 minutes — touches every partner in the stack:
                Vultr Vector Store, Gemini multi-turn agent (ADK), Speechmatics
                STT + TTS.
              </Dialog.Description>
            </div>
            <Dialog.Close
              className="demo-guide-close"
              aria-label="Close demo guide"
            >
              <X className="w-4 h-4" />
            </Dialog.Close>
          </div>

          <ol className="demo-guide-steps">
            {STEPS.map((step, i) => (
              <li key={i} className="demo-guide-step">
                <span className="demo-guide-step-num" aria-hidden="true">
                  {i + 1}
                </span>
                <div className="demo-guide-step-body">
                  <h3>{step.title}</h3>
                  <p className="demo-guide-step-action">{step.action}</p>
                  <details className="demo-guide-underhood">
                    <summary>Under the hood</summary>
                    <p className="demo-guide-underhood-body">{step.underHood}</p>
                  </details>
                </div>
              </li>
            ))}
          </ol>

          <div className="demo-guide-footer">
            <span>
              Powered by <strong>Vultr Cloud Compute + Vector Store</strong> ·{' '}
              <strong>Gemini (ADK multi-turn agent)</strong> ·{' '}
              <strong>Speechmatics STT + TTS</strong>
            </span>
            <a
              className="demo-guide-footer-link"
              href={appUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              Open the app in a new tab
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
