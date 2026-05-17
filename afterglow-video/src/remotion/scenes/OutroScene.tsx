import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from 'remotion';
import { COLORS } from '../data/videoScript';
import { GlowOrb } from '../components/GlowOrb';
import { useSceneFade } from '../components/useSceneFade';

export const OutroScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const sceneOpacity = useSceneFade(durationInFrames, 30, 0);

  // Wordmark
  const wordmarkOpacity = interpolate(frame, [20, 55], [0, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const wordmarkScale = interpolate(frame, [20, 55], [0.94, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  // Tagline
  const taglineOpacity = interpolate(frame, [45, 75], [0, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const taglineY = interpolate(frame, [45, 75], [20, 0], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  // CTA
  const ctaOpacity = interpolate(frame, [80, 110], [0, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const ctaY = interpolate(frame, [80, 110], [20, 0], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  // Footer line
  const footerOpacity = interpolate(frame, [120, 150], [0, 1], { extrapolateRight: 'clamp' });

  // Pulsing glow on logo
  const glowPulse = 0.12 + 0.04 * Math.sin(frame * 0.08);

  // Separator line
  const lineWidth = interpolate(frame, [60, 95], [0, 320], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: sceneOpacity }}>
      {/* Atmospheric glows */}
      <GlowOrb x="50%" y="48%" size={900} color={COLORS.primary} opacity={glowPulse} blur={200} />
      <GlowOrb x="35%" y="55%" size={500} color="#1d4ed8" opacity={0.07} blur={160} />
      <GlowOrb x="65%" y="40%" size={400} color="#7c3aed" opacity={0.05} blur={140} />

      {/* Grid dots overlay */}
      <div style={{
        position: 'absolute', inset: 0,
        backgroundImage: 'radial-gradient(circle, rgba(58,63,78,0.4) 1px, transparent 1px)',
        backgroundSize: '40px 40px',
        opacity: 0.4,
      }} />

      <AbsoluteFill style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      }}>
        {/* Wordmark */}
        <div style={{
          opacity: wordmarkOpacity,
          transform: `scale(${wordmarkScale})`,
          marginBottom: 0,
        }}>
          <span style={{
            fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
            fontSize: 108,
            fontWeight: 800,
            letterSpacing: '-3px',
            color: COLORS.onSurface,
          }}>
            after
          </span>
          <span style={{
            fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
            fontSize: 108,
            fontWeight: 800,
            letterSpacing: '-3px',
            color: COLORS.primary,
          }}>
            glow
          </span>
        </div>

        {/* Separator */}
        <div style={{
          width: lineWidth,
          height: 1,
          background: `linear-gradient(90deg, transparent, ${COLORS.primary}66, transparent)`,
          marginTop: 20,
          marginBottom: 28,
        }} />

        {/* Tagline */}
        <p style={{
          fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
          fontSize: 26,
          fontWeight: 300,
          color: COLORS.onSurfaceVariant,
          letterSpacing: '0.3px',
          opacity: taglineOpacity,
          transform: `translateY(${taglineY}px)`,
          marginBottom: 48,
        }}>
          AI for what happens after the call.
        </p>

        {/* CTA button */}
        <div style={{
          opacity: ctaOpacity,
          transform: `translateY(${ctaY}px)`,
          marginBottom: 80,
        }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 12,
            background: COLORS.primary,
            borderRadius: 100,
            padding: '16px 40px',
            boxShadow: `0 0 40px rgba(59,130,246,0.35), 0 0 80px rgba(59,130,246,0.15)`,
          }}>
            <span style={{
              fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
              fontSize: 20, fontWeight: 700, color: COLORS.white, letterSpacing: '-0.2px',
            }}>
              Try the live demo
            </span>
            <span style={{ color: COLORS.white, fontSize: 20, fontWeight: 700 }}>→</span>
          </div>
        </div>

        {/* Footer */}
        <div style={{ opacity: footerOpacity }}>
          <p style={{
            fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
            fontSize: 14, fontWeight: 400, color: COLORS.onSurfaceVariant,
            textAlign: 'center', letterSpacing: '0.2px',
          }}>
            MIT licensed · AI Hackathon by lablab.ai · Milano AI Week 2026
          </p>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
