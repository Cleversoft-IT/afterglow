import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from 'remotion';
import {
  COLORS, MARKET_METRICS, MARKET_NOTE, USP_ROWS, REVENUE_STRIP,
} from '../data/videoScript';
import { GlowOrb } from '../components/GlowOrb';
import { useSceneFade } from '../components/useSceneFade';
import { AnimatedText } from '../components/AnimatedText';

// Act II.G (4:00–4:30, 900f / 30s) — market sizing + USP.

export const MarketScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const sceneOpacity = useSceneFade(durationInFrames);

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: sceneOpacity }}>
      <GlowOrb x="20%" y="40%" size={500} color={COLORS.primary} opacity={0.08} blur={150} delay={0} />
      <GlowOrb x="80%" y="60%" size={500} color={COLORS.primaryDeep} opacity={0.06} blur={150} delay={60} />

      <div style={{ padding: '70px 90px' }}>
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
            business value
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
            Worldwide problem.<br />
            Italy is where we measured first.
          </div>
        </AnimatedText>

        <div
          style={{
            marginTop: 36,
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 36,
          }}
        >
          {/* LEFT — metric card */}
          <div
            style={{
              background: COLORS.surface,
              border: `1px solid ${COLORS.border}`,
              borderRadius: 18,
              padding: 32,
            }}
          >
            <div
              style={{
                display: 'inline-block',
                padding: '5px 12px',
                borderRadius: 999,
                background: COLORS.primaryDim,
                color: COLORS.primarySoft,
                fontSize: 13,
                fontWeight: 700,
                letterSpacing: '0.12em',
                textTransform: 'uppercase',
                marginBottom: 20,
              }}
            >
              Italian baseline · floor, not ceiling
            </div>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 14,
              }}
            >
              {MARKET_METRICS.map((m, i) => {
                const reveal = 50 + i * 24;
                const op = interpolate(frame, [reveal, reveal + 18], [0, 1], {
                  extrapolateLeft: 'clamp',
                  extrapolateRight: 'clamp',
                });
                const ty = interpolate(frame, [reveal, reveal + 18], [10, 0], {
                  extrapolateLeft: 'clamp',
                  extrapolateRight: 'clamp',
                  easing: Easing.bezier(0.16, 1, 0.3, 1),
                });
                return (
                  <div
                    key={m.num}
                    style={{
                      opacity: op,
                      transform: `translateY(${ty}px)`,
                      background: COLORS.primaryDim,
                      border: `1px solid ${COLORS.primary}33`,
                      borderRadius: 12,
                      padding: '18px 14px',
                      textAlign: 'center',
                    }}
                  >
                    <div
                      style={{
                        fontSize: 44,
                        fontWeight: 800,
                        letterSpacing: '-0.04em',
                        color: COLORS.primarySoft,
                        lineHeight: 1,
                      }}
                    >
                      {m.num}
                    </div>
                    <div
                      style={{
                        marginTop: 6,
                        fontSize: 13,
                        color: COLORS.onSurfaceVariant,
                        lineHeight: 1.35,
                      }}
                    >
                      {m.label}
                    </div>
                  </div>
                );
              })}
            </div>
            <div
              style={{
                marginTop: 22,
                fontSize: 15,
                color: COLORS.muted,
                lineHeight: 1.5,
              }}
            >
              {MARKET_NOTE}
            </div>
          </div>

          {/* RIGHT — USP table */}
          <div
            style={{
              background: COLORS.surface,
              border: `1px solid ${COLORS.border}`,
              borderRadius: 18,
              padding: 32,
              display: 'flex',
              flexDirection: 'column',
              gap: 14,
            }}
          >
            <div style={{ fontSize: 19, fontWeight: 700, color: COLORS.white }}>
              USP vs CallRail · Aircall · Dialpad AI
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
              <thead>
                <tr>
                  <th></th>
                  <th
                    style={{
                      textAlign: 'left',
                      fontSize: 11,
                      letterSpacing: '0.1em',
                      textTransform: 'uppercase',
                      color: COLORS.muted,
                      paddingBottom: 6,
                    }}
                  >
                    Them
                  </th>
                  <th
                    style={{
                      textAlign: 'left',
                      fontSize: 11,
                      letterSpacing: '0.1em',
                      textTransform: 'uppercase',
                      color: COLORS.muted,
                      paddingBottom: 6,
                    }}
                  >
                    Afterglow
                  </th>
                </tr>
              </thead>
              <tbody>
                {USP_ROWS.map((row, i) => {
                  const reveal = 110 + i * 18;
                  const op = interpolate(frame, [reveal, reveal + 14], [0, 1], {
                    extrapolateLeft: 'clamp',
                    extrapolateRight: 'clamp',
                  });
                  return (
                    <tr key={row.label} style={{ opacity: op }}>
                      <td
                        style={{
                          padding: '8px 0',
                          borderBottom: `1px solid ${COLORS.borderDim}`,
                          color: COLORS.muted,
                          fontSize: 13,
                        }}
                      >
                        {row.label}
                      </td>
                      <td
                        style={{
                          padding: '8px 0',
                          borderBottom: `1px solid ${COLORS.borderDim}`,
                          color: COLORS.onSurfaceVariant,
                        }}
                      >
                        {row.them}
                      </td>
                      <td
                        style={{
                          padding: '8px 0',
                          borderBottom: `1px solid ${COLORS.borderDim}`,
                          color: COLORS.primarySoft,
                          fontWeight: 700,
                        }}
                      >
                        {row.us}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <div
              style={{
                marginTop: 'auto',
                padding: '12px 16px',
                background: COLORS.primaryDim,
                borderRadius: 10,
                fontSize: 14,
                color: COLORS.onSurface,
                lineHeight: 1.4,
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: '0.12em',
                  textTransform: 'uppercase',
                  color: COLORS.primarySoft,
                  marginBottom: 4,
                }}
              >
                Revenue model
              </div>
              {REVENUE_STRIP}
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
