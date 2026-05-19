import React from 'react';
import { AbsoluteFill, Sequence, Audio, staticFile } from 'remotion';
import { SCENES, TOTAL_FRAMES, COLORS } from './remotion/data/videoScript';
import { IntroScene } from './remotion/scenes/IntroScene';
import { PromiseScene } from './remotion/scenes/PromiseScene';
import { HomeRevealScene } from './remotion/scenes/HomeRevealScene';
import { IncomingCallScene } from './remotion/scenes/IncomingCallScene';
import { CallAnalysisScene } from './remotion/scenes/CallAnalysisScene';
import { ActionsScene } from './remotion/scenes/ActionsScene';
import { MemoryScene } from './remotion/scenes/MemoryScene';
import { TechScene } from './remotion/scenes/TechScene';
import { OutroScene } from './remotion/scenes/OutroScene';

// ─── Voiceover segments ─────────────────────────────────────────────────────
// startFrame calibrato su: scene_start + 0.7s lead-in (@30fps)
// Scene timing aggiornato per adattarsi alle durate audio reali (no sovrapposizioni).
const VOICEOVER = [
  { file: 'audio/seg_00_intro-tagline.mp3', startFrame: 21   },  // intro    0.7s
  { file: 'audio/seg_01_promise.mp3',       startFrame: 171  },  // promise  5.7s
  { file: 'audio/seg_02_home.mp3',          startFrame: 546  },  // home    18.2s
  { file: 'audio/seg_03_incoming-call.mp3', startFrame: 951  },  // incoming 31.7s
  { file: 'audio/seg_04_call-analysis.mp3', startFrame: 1971 },  // analysis 65.7s
  { file: 'audio/seg_05_actions.mp3',       startFrame: 2436 },  // actions  81.2s
  { file: 'audio/seg_06_memory.mp3',        startFrame: 2946 },  // memory   98.2s
  { file: 'audio/seg_07_tech.mp3',          startFrame: 3351 },  // tech    111.7s
  { file: 'audio/seg_08_outro.mp3',         startFrame: 3741 },  // outro   124.7s
] as const;

export const MyComposition: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: COLORS.bg, fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif' }}>

      {/* ── Audio layer ─────────────────────────────────────────────────── */}

      {/* Musica di sottofondo — loop automatico, fade in/out ai bordi */}
      <Audio
        src={staticFile('audio/bg-music.mp3')}
        loop
        volume={(f) => {
          const fadeIn  = Math.min(1, f / 60);
          const fadeOut = Math.min(1, (TOTAL_FRAMES - f) / 90);
          return Math.min(fadeIn, fadeOut) * 0.16;
        }}
      />

      {/* Voiceover — segmenti sincronizzati scena per scena */}
      {VOICEOVER.map(({ file, startFrame }) => (
        <Sequence key={file} from={startFrame}>
          <Audio src={staticFile(file)} volume={1} />
        </Sequence>
      ))}

      {/* ── Visual layer ────────────────────────────────────────────────── */}

      {/* Scena 1 — Intro */}
      <Sequence from={SCENES.intro.start} durationInFrames={SCENES.intro.duration}>
        <IntroScene durationInFrames={SCENES.intro.duration} />
      </Sequence>

      {/* Scena 2 — Problem & Insight */}
      <Sequence from={SCENES.promise.start} durationInFrames={SCENES.promise.duration}>
        <PromiseScene durationInFrames={SCENES.promise.duration} />
      </Sequence>

      {/* Scena 3 — Home reveal */}
      <Sequence from={SCENES.pipeline.start} durationInFrames={SCENES.pipeline.duration}>
        <HomeRevealScene durationInFrames={SCENES.pipeline.duration} />
      </Sequence>

      {/* Scena 4 — Incoming call */}
      <Sequence from={SCENES.incomingCall.start} durationInFrames={SCENES.incomingCall.duration}>
        <IncomingCallScene durationInFrames={SCENES.incomingCall.duration} />
      </Sequence>

      {/* Scena 5 — Call analysis */}
      <Sequence from={SCENES.callAnalysis.start} durationInFrames={SCENES.callAnalysis.duration}>
        <CallAnalysisScene durationInFrames={SCENES.callAnalysis.duration} />
      </Sequence>

      {/* Scena 6 — Autonomous actions */}
      <Sequence from={SCENES.actions.start} durationInFrames={SCENES.actions.duration}>
        <ActionsScene durationInFrames={SCENES.actions.duration} />
      </Sequence>

      {/* Scena 7 — Caller memory */}
      <Sequence from={SCENES.memory.start} durationInFrames={SCENES.memory.duration}>
        <MemoryScene durationInFrames={SCENES.memory.duration} />
      </Sequence>

      {/* Scena 8 — Tech stack */}
      <Sequence from={SCENES.techStack.start} durationInFrames={SCENES.techStack.duration}>
        <TechScene durationInFrames={SCENES.techStack.duration} />
      </Sequence>

      {/* Scena 9 — Outro */}
      <Sequence from={SCENES.outro.start} durationInFrames={SCENES.outro.duration}>
        <OutroScene durationInFrames={SCENES.outro.duration} />
      </Sequence>
    </AbsoluteFill>
  );
};

export { TOTAL_FRAMES };
