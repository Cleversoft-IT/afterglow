import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from 'remotion';
import {
  COLORS,
  MARKET_HEADLINE,
  MARKET_BIG_NUMBER,
  USP_CARDS,
  USP_EYEBROW,
} from '../data/videoScript';
import { GlowOrb } from '../components/GlowOrb';
import { useSceneFade } from '../components/useSceneFade';
import { AnimatedText } from '../components/AnimatedText';

// Act II.G — Market & USP (two-beat layout, 750f / 25s @ 30fps).
//
// Beat 1 (frame 0 – ~360, ~12s): one giant number (€110M) with counter-up.
// Beat 2 (frame ~360 – 720, ~12s): three USP cards horizontal.
// 30f cross-fade between beats. No comparison table — that lives in the deck.

const BEAT_1_END = 360;
const BEAT_2_START = 360;
const CROSSFADE = 30;

export const MarketScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const sceneOpacity = useSceneFade(durationInFrames);

  // Counter-up: 0 → 110 between frame 90 and 200.
  const counterValue = Math.round(
    interpolate(frame, [90, 200], [0, MARKET_BIG_NUMBER.value], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    }),
  );

  const beat1Opacity = interpolate(
    frame,
    [BEAT_1_END - CROSSFADE, BEAT_1_END],
    [1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );

  const beat2Opacity = interpolate(
    frame,
    [BEAT_2_START, BEAT_2_START + CROSSFADE],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: sceneOpacity }}>
      <GlowOrb x="20%" y="40%" size={500} color={COLORS.primary} opacity={0.10} blur={150} delay={0} />
      <GlowOrb x="80%" y="60%" size={500} color={COLORS.primaryDeep} opacity={0.07} blur={150} delay={60} />

      {/* Beat 1 — giant €110M */}
      <AbsoluteFill
        style={{
          opacity: beat1Opacity,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '0 120px',
          textAlign: 'center',
        }}
      >
        <AnimatedText delay={0} duration={20} direction="up">
          <div
            style={{
              fontSize: 18,
              fontWeight: 700,
              letterSpacing: '0.2em',
              textTransform: 'uppercase',
              color: COLORS.primarySoft,
            }}
          >
            {MARKET_HEADLINE.eyebrow}
          </div>
        </AnimatedText>

        <AnimatedText delay={10} duration={30} direction="up">
          <div
            style={{
              marginTop: 18,
              fontSize: 56,
              fontWeight: 800,
              letterSpacing: '-0.03em',
              lineHeight: 1.05,
              color: COLORS.white,
            }}
          >
            {MARKET_HEADLINE.line1}
            <br />
            {MARKET_HEADLINE.line2}
          </div>
        </AnimatedText>

        {/* Giant counter-up number */}
        <div
          style={{
            marginTop: 56,
            fontSize: 240,
            fontWeight: 800,
            letterSpacing: '-0.05em',
            lineHeight: 1,
            color: COLORS.primarySoft,
            fontVariantNumeric: 'tabular-nums',
            opacity: interpolate(frame, [60, 100], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }),
          }}
        >
          {MARKET_BIG_NUMBER.prefix}{counterValue}{MARKET_BIG_NUMBER.suffix}
        </div>

        <div
          style={{
            marginTop: 22,
            fontSize: 22,
            fontWeight: 600,
            color: COLORS.onSurfaceVariant,
            letterSpacing: '0.01em',
            opacity: interpolate(frame, [180, 220], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }),
          }}
        >
          {MARKET_BIG_NUMBER.caption}
        </div>

        <div
          style={{
            marginTop: 18,
            fontSize: 14,
            color: COLORS.muted,
            letterSpacing: '0.05em',
            opacity: interpolate(frame, [240, 280], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }),
          }}
        >
          sources · {MARKET_BIG_NUMBER.sources}
        </div>
      </AbsoluteFill>

      {/* Beat 2 — 3 USP cards horizontal */}
      <AbsoluteFill
        style={{
          opacity: beat2Opacity,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '0 90px',
        }}
      >
        <div
          style={{
            fontSize: 18,
            fontWeight: 700,
            letterSpacing: '0.2em',
            textTransform: 'uppercase',
            color: COLORS.primarySoft,
            opacity: interpolate(
              frame,
              [BEAT_2_START + 10, BEAT_2_START + 40],
              [0, 1],
              { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
            ),
          }}
        >
          {USP_EYEBROW}
        </div>

        <div
          style={{
            marginTop: 18,
            fontSize: 52,
            fontWeight: 800,
            letterSpacing: '-0.03em',
            lineHeight: 1.05,
            color: COLORS.white,
            textAlign: 'center',
            opacity: interpolate(
              frame,
              [BEAT_2_START + 20, BEAT_2_START + 60],
              [0, 1],
              { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
            ),
          }}
        >
          One word of difference.{' '}
          <span style={{ color: COLORS.primary }}>After.</span>
        </div>

        <div
          style={{
            marginTop: 64,
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 32,
            width: '100%',
            maxWidth: 1620,
          }}
        >
          {USP_CARDS.map((card, i) => {
            const reveal = BEAT_2_START + 60 + i * 25;
            const op = interpolate(frame, [reveal, reveal + 24], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            });
            const ty = interpolate(frame, [reveal, reveal + 24], [20, 0], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            });
            return (
              <div
                key={card.head}
                style={{
                  opacity: op,
                  transform: `translateY(${ty}px)`,
                  background: COLORS.surface,
                  border: `1px solid ${COLORS.border}`,
                  borderRadius: 18,
                  padding: '32px 28px',
                  minHeight: 240,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 14,
                }}
              >
                <div
                  style={{
                    fontSize: 30,
                    fontWeight: 800,
                    letterSpacing: '-0.02em',
                    color: COLORS.primarySoft,
                    lineHeight: 1.1,
                  }}
                >
                  {card.head}
                </div>
                <div
                  style={{
                    fontSize: 19,
                    lineHeight: 1.5,
                    color: COLORS.onSurfaceVariant,
                    fontWeight: 500,
                  }}
                >
                  {card.body}
                </div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
