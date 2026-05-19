import React from 'react';
import { AbsoluteFill, Img, staticFile, useCurrentFrame, interpolate, Easing } from 'remotion';
import { COLORS, CLAIM } from '../data/videoScript';
import { GlowOrb } from '../components/GlowOrb';
import { useSceneFade } from '../components/useSceneFade';
import { AnimatedText } from '../components/AnimatedText';

// Act II.A (0:30–0:55, 750f) — product in one sentence.
// Visual: Home screen of the operator app inside a Pixel-style phone
// frame on the right, claim copy on the left. The Home screenshot
// already exists at public/screenshots/home-dark.png.

export const ProductIntroScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const sceneOpacity = useSceneFade(durationInFrames);

  // Phone slide-in from right
  const phoneOpacity = interpolate(frame, [10, 50], [0, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const phoneX = interpolate(frame, [10, 60], [80, 0], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: sceneOpacity }}>
      <GlowOrb x="20%" y="50%" size={700} color={COLORS.primary} opacity={0.10} blur={160} delay={0} />
      <GlowOrb x="80%" y="30%" size={400} color={COLORS.primaryDeep} opacity={0.06} blur={120} delay={20} />

      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'grid',
          gridTemplateColumns: '1.1fr 0.9fr',
          alignItems: 'center',
          padding: '0 80px',
          gap: 60,
        }}
      >
        {/* LEFT — copy */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
          <AnimatedText delay={15} duration={30} direction="up">
            <div
              style={{
                fontSize: 16,
                fontWeight: 600,
                letterSpacing: '0.18em',
                textTransform: 'uppercase',
                color: COLORS.primarySoft,
              }}
            >
              the product
            </div>
          </AnimatedText>

          <AnimatedText delay={35} duration={40} direction="up">
            <div
              style={{
                fontSize: 88,
                fontWeight: 800,
                letterSpacing: '-0.04em',
                lineHeight: 1.05,
                color: COLORS.white,
              }}
            >
              A phone app.
            </div>
          </AnimatedText>

          <AnimatedText delay={75} duration={40} direction="up">
            <div
              style={{
                fontSize: 36,
                fontWeight: 500,
                lineHeight: 1.4,
                color: COLORS.onSurfaceVariant,
                letterSpacing: '-0.015em',
              }}
            >
              The operator picks up — like always. The moment they hang up, the&nbsp;
              <span style={{ color: COLORS.primary, fontWeight: 700 }}>after</span>&nbsp;
              begins.
            </div>
          </AnimatedText>

          <AnimatedText delay={180} duration={30} direction="up">
            <div
              style={{
                marginTop: 24,
                fontSize: 22,
                fontWeight: 600,
                color: COLORS.muted,
                letterSpacing: '0.02em',
              }}
            >
              {CLAIM.line1} {CLAIM.line2}
            </div>
          </AnimatedText>
        </div>

        {/* RIGHT — phone frame with Home screenshot */}
        <div
          style={{
            opacity: phoneOpacity,
            transform: `translateX(${phoneX}px)`,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
          }}
        >
          {/*
             Frame derived from capture-screenshots.mjs viewport (430×932 @2x).
             Inner screen aspect 932/430 = 2.167; wrapper width 510 + 10 border
             + 8 padding on each side → inner 474, inner height 474×2.167 = 1027.
           */}
          <div
            style={{
              width: 510,
              height: 1063,
              borderRadius: 64,
              border: `10px solid ${COLORS.border}`,
              background: '#000',
              padding: 8,
              boxShadow: '0 30px 80px rgba(0,0,0,0.6)',
              overflow: 'hidden',
            }}
          >
            <Img
              src={staticFile('screenshots/home.png')}
              alt="Home"
              style={{
                width: '100%',
                height: '100%',
                borderRadius: 54,
                objectFit: 'contain',
                objectPosition: 'center',
                display: 'block',
              }}
            />
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
