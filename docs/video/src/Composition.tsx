import React from 'react';
import { AbsoluteFill, Sequence, Audio, staticFile } from 'remotion';
import { SCENES, TOTAL_FRAMES, COLORS } from './remotion/data/videoScript';

// Act I (typographic spot) was deliberately dropped — the video opens
// straight on the product.

// Act II — live product demo.
import { ProductIntroScene } from './remotion/scenes/ProductIntroScene';     // II.A
import { EndToEndRunScene } from './remotion/scenes/EndToEndRunScene';       // II.B
import { SelfCorrectionScene } from './remotion/scenes/SelfCorrectionScene'; // II.C
import { MemoryScene } from './remotion/scenes/MemoryScene';                 // II.D (reused)
import { WizardScene } from './remotion/scenes/WizardScene';                 // II.E
import { RealVsMockedScene } from './remotion/scenes/RealVsMockedScene';     // II.F
import { MarketScene } from './remotion/scenes/MarketScene';                 // II.G

// Coda
import { CodaScene } from './remotion/scenes/CodaScene';

// ─── Voiceover segments ────────────────────────────────────────────────
// One MP3 per Act II scene + Coda. Lead-in: each VO starts ~0.4s (12f)
// after its scene begins, leaving room for the scene to fade in cleanly.
//
// Generate / regenerate via:
//   python -X utf8 docs/video/scripts/generate-voiceover.py

const LEAD_IN = 12;

const VOICEOVER = [
  { file: 'audio/seg_iiA_intro.mp3',        startFrame: SCENES.iiA.start + LEAD_IN },
  { file: 'audio/seg_iiB_endrun.mp3',       startFrame: SCENES.iiB.start + LEAD_IN },
  { file: 'audio/seg_iiC_selfcorrect.mp3',  startFrame: SCENES.iiC.start + LEAD_IN },
  { file: 'audio/seg_iiD_memory.mp3',       startFrame: SCENES.iiD.start + LEAD_IN },
  { file: 'audio/seg_iiE_wizard.mp3',       startFrame: SCENES.iiE.start + LEAD_IN },
  { file: 'audio/seg_iiF_honest.mp3',       startFrame: SCENES.iiF.start + LEAD_IN },
  { file: 'audio/seg_iiG_market.mp3',       startFrame: SCENES.iiG.start + LEAD_IN },
  { file: 'audio/seg_coda_close.mp3',       startFrame: SCENES.coda.start + LEAD_IN },
] as const;

export const MyComposition: React.FC = () => {
  return (
    <AbsoluteFill
      style={{
        background: COLORS.bg,
        fontFamily: '-apple-system, "SF Pro Display", "Inter", "Segoe UI", Roboto, sans-serif',
      }}
    >
      {/* ── Audio layer ───────────────────────────────────────────────── */}

      {/* Background pad — low duck under VO throughout, gentle in/out. */}
      <Audio
        src={staticFile('audio/bg-music.mp3')}
        loop
        volume={(f) => {
          const fadeIn  = Math.max(0, Math.min(1, f / 30));                  // 0–1s
          const fadeOut = Math.max(0, Math.min(1, (TOTAL_FRAMES - f) / 90)); // last 3s
          return Math.min(fadeIn, fadeOut) * 0.12;
        }}
      />

      {/* Voiceover — one MP3 per scene, no overlap with sibling sequences. */}
      {VOICEOVER.map(({ file, startFrame }) => (
        <Sequence key={file} from={startFrame}>
          <Audio src={staticFile(file)} volume={1} />
        </Sequence>
      ))}

      {/* ── Visual layer — Act II ─────────────────────────────────────── */}

      <Sequence from={SCENES.iiA.start} durationInFrames={SCENES.iiA.duration}>
        <ProductIntroScene durationInFrames={SCENES.iiA.duration} />
      </Sequence>

      <Sequence from={SCENES.iiB.start} durationInFrames={SCENES.iiB.duration}>
        <EndToEndRunScene durationInFrames={SCENES.iiB.duration} />
      </Sequence>

      <Sequence from={SCENES.iiC.start} durationInFrames={SCENES.iiC.duration}>
        <SelfCorrectionScene durationInFrames={SCENES.iiC.duration} />
      </Sequence>

      <Sequence from={SCENES.iiD.start} durationInFrames={SCENES.iiD.duration}>
        <MemoryScene durationInFrames={SCENES.iiD.duration} />
      </Sequence>

      <Sequence from={SCENES.iiE.start} durationInFrames={SCENES.iiE.duration}>
        <WizardScene durationInFrames={SCENES.iiE.duration} />
      </Sequence>

      <Sequence from={SCENES.iiF.start} durationInFrames={SCENES.iiF.duration}>
        <RealVsMockedScene durationInFrames={SCENES.iiF.duration} />
      </Sequence>

      <Sequence from={SCENES.iiG.start} durationInFrames={SCENES.iiG.duration}>
        <MarketScene durationInFrames={SCENES.iiG.duration} />
      </Sequence>

      {/* ── Visual layer — Coda ───────────────────────────────────────── */}

      <Sequence from={SCENES.coda.start} durationInFrames={SCENES.coda.duration}>
        <CodaScene durationInFrames={SCENES.coda.duration} />
      </Sequence>
    </AbsoluteFill>
  );
};

export { TOTAL_FRAMES };
