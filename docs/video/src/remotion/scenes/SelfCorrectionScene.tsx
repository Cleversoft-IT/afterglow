import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { COLORS, SELF_CORRECTION_TURNS } from '../data/videoScript';
import { GlowOrb } from '../components/GlowOrb';
import { useSceneFade } from '../components/useSceneFade';
import { AgentReasoningTrail } from '../components/AgentReasoningTrail';
import { AnimatedText } from '../components/AnimatedText';

// Act II.C (1:55–2:25, 900f / 30s) — the agentic claim, self-correction.
// Layout: caption left, trail-only panel on the right, showing the
// `validation_failed → re-read → executed` arc.

export const SelfCorrectionScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const sceneOpacity = useSceneFade(durationInFrames);

  const captionOpacity = interpolate(frame, [10, 50], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: sceneOpacity }}>
      <GlowOrb x="20%" y="50%" size={500} color={COLORS.error} opacity={0.07} blur={150} delay={0} />
      <GlowOrb x="80%" y="50%" size={500} color={COLORS.successDeep} opacity={0.05} blur={150} delay={120} />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'grid',
          gridTemplateColumns: '480px 1fr',
          alignItems: 'center',
          padding: '60px 100px',
          gap: 80,
        }}
      >
        {/* LEFT — caption */}
        <div
          style={{
            opacity: captionOpacity,
            display: 'flex',
            flexDirection: 'column',
            gap: 24,
          }}
        >
          <div
            style={{
              fontSize: 16,
              fontWeight: 600,
              letterSpacing: '0.18em',
              textTransform: 'uppercase',
              color: COLORS.primarySoft,
            }}
          >
            why it's agentic
          </div>

          <AnimatedText delay={20} duration={30} direction="up">
            <div
              style={{
                fontSize: 64,
                fontWeight: 800,
                letterSpacing: '-0.035em',
                lineHeight: 1.05,
                color: COLORS.white,
              }}
            >
              A loop,<br />not a script.
            </div>
          </AnimatedText>

          <AnimatedText delay={60} duration={30} direction="up">
            <div
              style={{
                fontSize: 24,
                fontWeight: 500,
                lineHeight: 1.45,
                color: COLORS.onSurfaceVariant,
              }}
            >
              The validator rejects. The agent re-reads the transcript
              and re-emits with the corrected payload. Hard cap: 2 attempts
              per action. Mutations that already succeeded cannot be
              replayed.
            </div>
          </AnimatedText>
        </div>

        {/* RIGHT — trail */}
        <div>
          <AgentReasoningTrail
            turns={SELF_CORRECTION_TURNS}
            firstTurnAt={120}
            cadence={210}
            highlightLast
          />
        </div>
      </div>
    </AbsoluteFill>
  );
};
