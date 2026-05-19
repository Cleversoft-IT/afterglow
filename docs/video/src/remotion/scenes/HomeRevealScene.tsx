import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from 'remotion';
import { COLORS } from '../data/videoScript';
import { GlowOrb } from '../components/GlowOrb';
import { AnimatedText } from '../components/AnimatedText';
import { ScreenshotInPhone } from '../components/ScreenshotInPhone';
import { useSceneFade } from '../components/useSceneFade';

export const HomeRevealScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const sceneOpacity = useSceneFade(durationInFrames);

  // Secondo telefono (ghost, leggermente indietro)
  const phone2Opacity = interpolate(frame, [45, 75], [0, 0.28], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: sceneOpacity }}>
      <GlowOrb x="68%" y="50%" size={800} color={COLORS.primary} opacity={0.11} blur={180} />
      <GlowOrb x="25%" y="40%" size={500} color="#7c3aed" opacity={0.07} blur={160} />

      <AbsoluteFill style={{
        display: 'flex', flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
        gap: 80, padding: '0 80px',
      }}>
        {/* Sinistra: copy */}
        <div style={{ flex: 1, maxWidth: 460, minWidth: 0 }}>
          <AnimatedText delay={5} style={{ marginBottom: 16 }}>
            <p style={{
              fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
              fontSize: 12, fontWeight: 700, color: COLORS.primary,
              letterSpacing: '4px', textTransform: 'uppercase',
            }}>The app</p>
          </AnimatedText>

          <AnimatedText delay={15} style={{ marginBottom: 24 }}>
            <h2 style={{
              fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
              fontSize: 48, fontWeight: 800, color: COLORS.onSurface,
              letterSpacing: '-1.5px', lineHeight: 1.06,
              wordBreak: 'break-word',
            }}>
              All your calls.
              <br />
              <span style={{ color: COLORS.primary }}>Finally structured.</span>
            </h2>
          </AnimatedText>

          <AnimatedText delay={30} style={{ marginBottom: 44 }}>
            <p style={{
              fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
              fontSize: 18, fontWeight: 400, color: COLORS.onSurfaceVariant,
              lineHeight: 1.6, maxWidth: 420,
            }}>
              Afterglow replaces the phone app. Every call gets a structured record, extracted fields, and autonomous follow-ups — automatically.
            </p>
          </AnimatedText>

          {/* Feature tags */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {['Real-time status', 'Smart search', 'Booking filter', 'Missed call alerts'].map((tag, i) => {
              const tagDelay = 55 + i * 12;
              const tagF = Math.max(0, frame - tagDelay);
              const tagOpacity = interpolate(tagF, [0, 20], [0, 1], { extrapolateRight: 'clamp' });
              const tagScale = interpolate(tagF, [0, 20], [0.85, 1], {
                extrapolateRight: 'clamp',
                easing: Easing.bezier(0.34, 1.56, 0.64, 1),
              });
              return (
                <span key={tag} style={{
                  fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
                  fontSize: 13, fontWeight: 600, color: COLORS.onSurfaceVariant,
                  background: COLORS.surface, border: `1px solid ${COLORS.border}`,
                  borderRadius: 100, padding: '8px 18px',
                  opacity: tagOpacity, transform: `scale(${tagScale})`, display: 'inline-block',
                }}>{tag}</span>
              );
            })}
          </div>
        </div>

        {/* Destra: telefono reale */}
        <div style={{ position: 'relative', flexShrink: 0 }}>
          {/* Ghost phone dietro */}
          <div style={{
            position: 'absolute', right: -60, top: 24,
            opacity: phone2Opacity, filter: 'blur(3px)',
            transform: 'scale(0.96)',
          }}>
            <ScreenshotInPhone
              src="screenshots/home-dark.png"
              screenWidth={280}
              delay={0}
              slideFrom="none"
            />
          </div>

          {/* Foreground phone */}
          <ScreenshotInPhone
            src="screenshots/home-dark.png"
            screenWidth={310}
            delay={10}
            slideFrom="right"
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
