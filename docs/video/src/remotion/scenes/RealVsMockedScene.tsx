import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from 'remotion';
import {
  COLORS, REAL_PROOFS, REAL_AND_MORE,
  MOCKED_TAGS, MOCK_SUMMARY, MOCK_SWAP_NOTE,
} from '../data/videoScript';
import { GlowOrb } from '../components/GlowOrb';
import { useSceneFade } from '../components/useSceneFade';
import { AnimatedText } from '../components/AnimatedText';

// Act II.F (3:30–4:00, 900f / 30s) — the honest table.

export const RealVsMockedScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const sceneOpacity = useSceneFade(durationInFrames);

  const realCardOpacity = interpolate(frame, [10, 60], [0, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const mockCardOpacity = interpolate(frame, [50, 110], [0, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: sceneOpacity }}>
      <GlowOrb x="25%" y="50%" size={500} color={COLORS.successDeep} opacity={0.06} blur={150} delay={0} />
      <GlowOrb x="75%" y="50%" size={500} color={COLORS.amberDeep} opacity={0.06} blur={150} delay={60} />

      <div style={{ padding: '70px 90px', height: '100%' }}>
        <AnimatedText delay={0} duration={20} direction="up">
          <div
            style={{
              fontSize: 16,
              fontWeight: 600,
              letterSpacing: '0.18em',
              textTransform: 'uppercase',
              color: COLORS.primarySoft,
            }}
          >
            the honest table
          </div>
        </AnimatedText>

        <AnimatedText delay={10} duration={30} direction="up">
          <div
            style={{
              marginTop: 12,
              fontSize: 52,
              fontWeight: 800,
              letterSpacing: '-0.03em',
              lineHeight: 1.05,
              color: COLORS.white,
            }}
          >
            Real where it matters.
          </div>
        </AnimatedText>

        <div
          style={{
            marginTop: 40,
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 36,
          }}
        >
          {/* REAL card */}
          <div
            style={{
              opacity: realCardOpacity,
              background: COLORS.surface,
              border: `1px solid ${COLORS.border}`,
              borderTop: `4px solid ${COLORS.successSolid}`,
              borderRadius: 18,
              padding: 32,
              display: 'flex',
              flexDirection: 'column',
              gap: 18,
            }}
          >
            <div
              style={{
                fontSize: 22,
                fontWeight: 700,
                color: COLORS.white,
                display: 'flex',
                alignItems: 'center',
                gap: 10,
              }}
            >
              <span
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  background: COLORS.successSolid,
                  display: 'inline-block',
                }}
              />
              REAL · billed, not stubbed
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {REAL_PROOFS.map((p, i) => {
                const reveal = 70 + i * 24;
                const op = interpolate(frame, [reveal, reveal + 18], [0, 1], {
                  extrapolateLeft: 'clamp',
                  extrapolateRight: 'clamp',
                });
                const ty = interpolate(frame, [reveal, reveal + 18], [8, 0], {
                  extrapolateLeft: 'clamp',
                  extrapolateRight: 'clamp',
                  easing: Easing.bezier(0.16, 1, 0.3, 1),
                });
                return (
                  <div
                    key={p.n}
                    style={{
                      opacity: op,
                      transform: `translateY(${ty}px)`,
                      display: 'grid',
                      gridTemplateColumns: '36px 1fr',
                      gap: 14,
                      alignItems: 'start',
                    }}
                  >
                    <div
                      style={{
                        width: 30,
                        height: 30,
                        borderRadius: '50%',
                        background: COLORS.successSolid,
                        color: COLORS.white,
                        fontSize: 14,
                        fontWeight: 700,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      {p.n}
                    </div>
                    <div>
                      <div
                        style={{
                          fontSize: 20,
                          fontWeight: 700,
                          color: COLORS.onSurface,
                        }}
                      >
                        {p.head}
                      </div>
                      <div
                        style={{
                          marginTop: 2,
                          fontSize: 16,
                          color: COLORS.onSurfaceVariant,
                          lineHeight: 1.45,
                        }}
                      >
                        {p.body}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            <div
              style={{
                marginTop: 'auto',
                paddingTop: 14,
                borderTop: `1px dashed ${COLORS.border}`,
                fontSize: 15,
                color: COLORS.muted,
              }}
            >
              {REAL_AND_MORE}
            </div>
          </div>

          {/* MOCK card */}
          <div
            style={{
              opacity: mockCardOpacity,
              background: COLORS.surface,
              border: `1px solid ${COLORS.border}`,
              borderTop: `4px solid ${COLORS.amber}`,
              borderRadius: 18,
              padding: 32,
              display: 'flex',
              flexDirection: 'column',
              gap: 18,
            }}
          >
            <div
              style={{
                fontSize: 22,
                fontWeight: 700,
                color: COLORS.white,
                display: 'flex',
                alignItems: 'center',
                gap: 10,
              }}
            >
              <span
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  background: COLORS.amber,
                  display: 'inline-block',
                }}
              />
              MOCKED · by design
            </div>
            <div
              style={{
                fontSize: 19,
                color: COLORS.onSurfaceVariant,
                lineHeight: 1.5,
              }}
            >
              {MOCK_SUMMARY}
            </div>
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 8,
              }}
            >
              {MOCKED_TAGS.map((tag, i) => {
                const reveal = 130 + i * 12;
                const op = interpolate(frame, [reveal, reveal + 14], [0, 1], {
                  extrapolateLeft: 'clamp',
                  extrapolateRight: 'clamp',
                });
                return (
                  <span
                    key={tag}
                    style={{
                      opacity: op,
                      fontSize: 14,
                      padding: '5px 10px',
                      borderRadius: 7,
                      background: COLORS.amberDim,
                      color: COLORS.amber,
                      border: `1px solid rgba(251,191,36,0.3)`,
                      fontFamily: tag.includes('*') || tag.includes('.')
                        ? '"JetBrains Mono", ui-monospace, Menlo, monospace'
                        : undefined,
                    }}
                  >
                    {tag}
                  </span>
                );
              })}
            </div>
            <div
              style={{
                marginTop: 'auto',
                paddingTop: 14,
                borderTop: `1px dashed ${COLORS.border}`,
                fontSize: 14,
                color: COLORS.muted,
                lineHeight: 1.5,
              }}
            >
              {MOCK_SWAP_NOTE}
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
