import React from 'react';
import { AbsoluteFill, Img, staticFile, useCurrentFrame, interpolate, Easing } from 'remotion';
import { COLORS, AGENT_TURNS, DEMO_CALL } from '../data/videoScript';
import { GlowOrb } from '../components/GlowOrb';
import { useSceneFade } from '../components/useSceneFade';
import { AgentReasoningTrail } from '../components/AgentReasoningTrail';

// Act II.B (0:43–1:29, 1380f / 46s) — the end-to-end Mark Ross run.
// Layout: phone (left) with incoming-call → call-detail screenshot
// cross-fade; AgentReasoningTrail panel (right) revealing 5 turns ~4.5s apart.
//
// Frame budget (within scene, 0…1380):
//   0–120    incoming-call screen
//   120–200  cross-fade to call-detail-fields
//   60–1260  trail (firstTurnAt=60, cadence=240 → turns at 60,300,540,780,1020; done ~1040)
//   1040–1380 hold + final "completed" chip pulse

export const EndToEndRunScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const sceneOpacity = useSceneFade(durationInFrames, 30, 30);

  // Phone screenshot cross-fade
  const incomingOpacity = interpolate(frame, [0, 30, 160, 200], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    easing: Easing.bezier(0.4, 0, 0.2, 1),
  });
  const detailOpacity = interpolate(frame, [140, 200], [0, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.4, 0, 0.2, 1),
  });

  // Status chip animation (transcribing → analyzing → completed)
  const status =
    frame < 200 ? { label: 'transcribing', color: COLORS.primary, dim: COLORS.primaryDim } :
    frame < 1180 ? { label: 'analyzing', color: COLORS.amber, dim: COLORS.amberDim } :
    { label: 'completed', color: COLORS.successSolid, dim: COLORS.successDim };

  const completedPulse = frame >= 1180
    ? 0.7 + 0.3 * Math.abs(Math.sin((frame - 1180) / 20))
    : 1;

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: sceneOpacity }}>
      <GlowOrb x="15%" y="50%" size={500} color={COLORS.primary} opacity={0.08} blur={150} delay={0} />
      <GlowOrb x="85%" y="50%" size={500} color={COLORS.successDeep} opacity={0.05} blur={150} delay={120} />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'grid',
          gridTemplateColumns: '480px 1fr',
          alignItems: 'center',
          padding: '40px 60px',
          gap: 60,
        }}
      >
        {/* LEFT — phone */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24, alignItems: 'center' }}>
          {/*
             Inner screen aspect 932/430 = 2.167; wrapper 480 + 10 border + 8
             padding on each side → inner 444, inner height 444×2.167 = 962
             → wrapper height 962 + 18×2 = 998.
           */}
          <div
            style={{
              position: 'relative',
              width: 480,
              height: 998,
              borderRadius: 64,
              border: `10px solid ${COLORS.border}`,
              background: '#000',
              padding: 8,
              boxShadow: '0 30px 80px rgba(0,0,0,0.6)',
              overflow: 'hidden',
            }}
          >
            <Img
              src={staticFile('screenshots/incoming-call.png')}
              alt="Incoming call"
              style={{
                position: 'absolute',
                inset: 8,
                width: 'calc(100% - 16px)',
                height: 'calc(100% - 16px)',
                borderRadius: 54,
                objectFit: 'contain',
                objectPosition: 'center',
                opacity: incomingOpacity,
              }}
            />
            <Img
              src={staticFile('screenshots/call-detail-fields.png')}
              alt="Call detail"
              style={{
                position: 'absolute',
                inset: 8,
                width: 'calc(100% - 16px)',
                height: 'calc(100% - 16px)',
                borderRadius: 54,
                objectFit: 'contain',
                objectPosition: 'center',
                opacity: detailOpacity,
              }}
            />
          </div>

          {/* Status chip under the phone */}
          <div
            style={{
              padding: '10px 20px',
              borderRadius: 999,
              background: status.dim,
              color: status.color,
              fontSize: 18,
              fontWeight: 700,
              fontFamily: '"JetBrains Mono", ui-monospace, Menlo, monospace',
              letterSpacing: '0.04em',
              opacity: completedPulse,
            }}
          >
            {status.label}
          </div>

          {/* Caller meta */}
          <div style={{ textAlign: 'center', color: COLORS.onSurfaceVariant }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: COLORS.onSurface }}>
              {DEMO_CALL.caller}
            </div>
            <div style={{ fontSize: 15, marginTop: 2 }}>
              {DEMO_CALL.phone} · {DEMO_CALL.duration}
            </div>
          </div>
        </div>

        {/* RIGHT — Agent Reasoning Trail */}
        <div
          style={{
            alignSelf: 'stretch',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <div style={{ width: '100%' }}>
            <AgentReasoningTrail
              turns={AGENT_TURNS}
              firstTurnAt={60}
              cadence={240}
              highlightLast
            />

            {/* Footer summary line */}
            <div
              style={{
                marginTop: 20,
                fontSize: 16,
                color: COLORS.muted,
                fontFamily: '"JetBrains Mono", ui-monospace, Menlo, monospace',
                letterSpacing: '0.02em',
                opacity: interpolate(frame, [1180, 1240], [0, 1], {
                  extrapolateLeft: 'clamp',
                  extrapolateRight: 'clamp',
                }),
              }}
            >
              5 turns · ~2,000 tokens · 6 s end to end
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
