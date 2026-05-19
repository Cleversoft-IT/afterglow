import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from 'remotion';
import { COLORS } from '../data/videoScript';
import { GlowOrb } from '../components/GlowOrb';
import { useSceneFade } from '../components/useSceneFade';

export const IntroScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const sceneOpacity = useSceneFade(durationInFrames);

  // Wordmark reveal — staggered: "after" then "glow"
  const afterOpacity = interpolate(frame, [15, 40], [0, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const afterY = interpolate(frame, [15, 40], [24, 0], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const glowOpacity = interpolate(frame, [30, 55], [0, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const glowY = interpolate(frame, [30, 55], [24, 0], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  // Tagline appears after wordmark
  const taglineOpacity = interpolate(frame, [60, 90], [0, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const taglineY = interpolate(frame, [60, 90], [20, 0], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  // Line separator scale
  const lineScale = interpolate(frame, [55, 80], [0, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });


  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: sceneOpacity }}>
      {/* Ambient glows */}
      <GlowOrb x="50%" y="48%" size={800} color={COLORS.primary} opacity={0.12} blur={160} delay={20} />
      <GlowOrb x="30%" y="60%" size={400} color="#1d4ed8" opacity={0.08} blur={120} delay={40} />
      <GlowOrb x="70%" y="35%" size={350} color="#7c3aed" opacity={0.05} blur={120} delay={50} />

      {/* Centered content */}
      <AbsoluteFill style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        {/* Wordmark */}
        <div style={{ overflow: 'hidden', marginBottom: 0 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'baseline',
              gap: 0,
              fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
              fontSize: 112,
              fontWeight: 800,
              letterSpacing: '-3px',
            }}
          >
            <span
              style={{
                color: COLORS.onSurface,
                opacity: afterOpacity,
                transform: `translateY(${afterY}px)`,
                display: 'inline-block',
              }}
            >
              after
            </span>
            <span
              style={{
                color: COLORS.primary,
                opacity: glowOpacity,
                transform: `translateY(${glowY}px)`,
                display: 'inline-block',
              }}
            >
              glow
            </span>
          </div>
        </div>

        {/* Separator */}
        <div
          style={{
            width: 320 * lineScale,
            height: 1,
            background: `linear-gradient(90deg, transparent, ${COLORS.primary}66, transparent)`,
            marginTop: 24,
            marginBottom: 32,
          }}
        />

        {/* Tagline */}
        <p
          style={{
            fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
            fontSize: 22,
            fontWeight: 400,
            color: COLORS.onSurfaceVariant,
            letterSpacing: '0.3px',
            opacity: taglineOpacity,
            transform: `translateY(${taglineY}px)`,
          }}
        >
          AI for what happens after the call.
        </p>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
