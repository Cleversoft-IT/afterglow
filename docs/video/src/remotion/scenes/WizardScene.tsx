import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from 'remotion';
import { COLORS, WIZARD_CHAT, WIZARD_OUTPUT_FIELDS } from '../data/videoScript';
import { GlowOrb } from '../components/GlowOrb';
import { useSceneFade } from '../components/useSceneFade';
import { AnimatedText } from '../components/AnimatedText';

// Act II.E (2:06–2:29, 690f / 23s) — the wizard. A chat panel on the
// left stacks 4 messages (user / wizard / user / wizard); on the right a
// "generated template" card lists 6 fields and a 2-MP3 badge.

const MESSAGE_INTERVAL = 120; // ~4s per message reveal

export const WizardScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const sceneOpacity = useSceneFade(durationInFrames);

  // Output card appears after the last message
  const outputStart = MESSAGE_INTERVAL * WIZARD_CHAT.length;
  const outputOpacity = interpolate(frame, [outputStart, outputStart + 30], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: sceneOpacity }}>
      <GlowOrb x="50%" y="20%" size={700} color={COLORS.primary} opacity={0.08} blur={160} delay={0} />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 60,
          padding: '90px 100px',
        }}
      >
        {/* LEFT — chat panel */}
        <div>
          <AnimatedText delay={0} duration={20} direction="up">
            <div
              style={{
                fontSize: 16,
                fontWeight: 600,
                letterSpacing: '0.18em',
                textTransform: 'uppercase',
                color: COLORS.primarySoft,
                marginBottom: 12,
              }}
            >
              templates · wizard
            </div>
          </AnimatedText>

          <AnimatedText delay={10} duration={30} direction="up">
            <div
              style={{
                fontSize: 52,
                fontWeight: 800,
                letterSpacing: '-0.03em',
                color: COLORS.white,
                marginBottom: 32,
                lineHeight: 1.05,
              }}
            >
              Any vertical.<br />Two to five questions.
            </div>
          </AnimatedText>

          <div
            style={{
              background: COLORS.surface,
              border: `1px solid ${COLORS.border}`,
              borderRadius: 16,
              padding: '24px 24px',
              display: 'flex',
              flexDirection: 'column',
              gap: 14,
              minHeight: 460,
            }}
          >
            {WIZARD_CHAT.map((msg, i) => {
              const reveal = MESSAGE_INTERVAL * i + 30;
              const op = interpolate(frame, [reveal, reveal + 18], [0, 1], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
                easing: Easing.bezier(0.16, 1, 0.3, 1),
              });
              const ty = interpolate(frame, [reveal, reveal + 18], [10, 0], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
                easing: Easing.bezier(0.16, 1, 0.3, 1),
              });
              const isUser = msg.from === 'user';
              return (
                <div
                  key={i}
                  style={{
                    opacity: op,
                    transform: `translateY(${ty}px)`,
                    alignSelf: isUser ? 'flex-end' : 'flex-start',
                    maxWidth: '85%',
                    background: isUser ? COLORS.primaryDim : COLORS.surfaceVariant,
                    color: COLORS.onSurface,
                    border: `1px solid ${isUser ? COLORS.primary : COLORS.border}`,
                    borderRadius: 14,
                    padding: '12px 16px',
                    fontSize: 19,
                    lineHeight: 1.4,
                  }}
                >
                  {msg.text}
                </div>
              );
            })}
          </div>
        </div>

        {/* RIGHT — generated template card */}
        <div
          style={{
            opacity: outputOpacity,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
          }}
        >
          <div
            style={{
              background: COLORS.surface,
              border: `2px solid ${COLORS.primary}`,
              borderRadius: 22,
              padding: 36,
              boxShadow: '0 20px 60px rgba(59,130,246,0.18)',
            }}
          >
            <div
              style={{
                fontSize: 14,
                fontWeight: 700,
                letterSpacing: '0.14em',
                textTransform: 'uppercase',
                color: COLORS.successSolid,
                marginBottom: 10,
              }}
            >
              ✓ generated · dog grooming
            </div>
            <div
              style={{
                fontSize: 30,
                fontWeight: 700,
                letterSpacing: '-0.02em',
                color: COLORS.white,
                marginBottom: 22,
              }}
            >
              Template · 6 fields · 4 action tools
            </div>

            {/* Fields list */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: 8,
                marginBottom: 22,
              }}
            >
              {WIZARD_OUTPUT_FIELDS.map((f) => (
                <div
                  key={f}
                  style={{
                    padding: '8px 12px',
                    background: COLORS.surfaceElevated,
                    border: `1px solid ${COLORS.borderDim}`,
                    borderRadius: 8,
                    fontFamily: '"JetBrains Mono", ui-monospace, Menlo, monospace',
                    fontSize: 16,
                    color: COLORS.onSurfaceVariant,
                  }}
                >
                  {f}
                </div>
              ))}
            </div>

            <div
              style={{
                paddingTop: 18,
                borderTop: `1px dashed ${COLORS.border}`,
                fontSize: 16,
                color: COLORS.onSurfaceVariant,
              }}
            >
              + 2 fresh demo MP3s rendered via <strong style={{ color: COLORS.amber }}>Speechmatics TTS</strong> (existing-caller + new-caller).
            </div>
          </div>

          <div
            style={{
              marginTop: 24,
              fontSize: 18,
              color: COLORS.muted,
              textAlign: 'center',
            }}
          >
            Same loop. Same audit trail. New domain.
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
