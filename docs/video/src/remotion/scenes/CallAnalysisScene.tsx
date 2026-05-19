import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { COLORS, DEMO_CALL } from '../data/videoScript';
import { GlowOrb } from '../components/GlowOrb';
import { AnimatedText } from '../components/AnimatedText';
import { ScreenshotInPhone } from '../components/ScreenshotInPhone';
import { useSceneFade } from '../components/useSceneFade';

export const CallAnalysisScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const sceneOpacity = useSceneFade(durationInFrames);

  const geminiBadgeOpacity = interpolate(frame, [80, 105], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: sceneOpacity }}>
      <GlowOrb x="25%" y="50%" size={700} color={COLORS.primary} opacity={0.12} blur={160} />
      <GlowOrb x="70%" y="40%" size={500} color="#8b5cf6" opacity={0.07} blur={140} />

      <AbsoluteFill style={{
        display: 'flex', flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
        gap: 80, padding: '0 80px',
      }}>
        {/* Sinistra: telefono reale */}
        <div style={{ flexShrink: 0 }}>
          <ScreenshotInPhone
            src="screenshots/call-detail-fields.png"
            screenWidth={310}
            delay={10}
            slideFrom="left"
          />
        </div>

        {/* Destra: copy */}
        <div style={{ flex: 1, maxWidth: 480, minWidth: 0 }}>
          <AnimatedText delay={5} style={{ marginBottom: 16 }}>
            <p style={{
              fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
              fontSize: 12, fontWeight: 700, color: COLORS.primary,
              letterSpacing: '4px', textTransform: 'uppercase',
            }}>03 — Extract</p>
          </AnimatedText>

          <AnimatedText delay={15} style={{ marginBottom: 24 }}>
            <h2 style={{
              fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
              fontSize: 48, fontWeight: 800, color: COLORS.onSurface,
              letterSpacing: '-1.5px', lineHeight: 1.06, wordBreak: 'break-word',
            }}>
              Every word,
              <br />
              <span style={{ color: COLORS.primary }}>structured.</span>
            </h2>
          </AnimatedText>

          <AnimatedText delay={30} style={{ marginBottom: 32 }}>
            <p style={{
              fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
              fontSize: 18, fontWeight: 400, color: COLORS.onSurfaceVariant,
              lineHeight: 1.6, maxWidth: 420,
            }}>
              Gemini 2.0 Flash reads the transcript and extracts every field in a single structured pass — with evidence citations.
            </p>
          </AnimatedText>

          {/* Transcript excerpt */}
          <AnimatedText delay={55} style={{ marginBottom: 24 }}>
            <div style={{
              background: COLORS.surface, border: `1px solid ${COLORS.border}`,
              borderRadius: 16, padding: 20,
            }}>
              <p style={{
                fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
                fontSize: 11, fontWeight: 700, color: COLORS.onSurfaceVariant,
                letterSpacing: '1px', textTransform: 'uppercase', marginBottom: 14,
              }}>Transcript excerpt</p>
              {DEMO_CALL.transcript.slice(0, 2).map((turn, i) => (
                <div key={i} style={{ marginBottom: i === 0 ? 10 : 0 }}>
                  <span style={{
                    fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
                    fontSize: 12, fontWeight: 700,
                    color: turn.speaker === 'Caller' ? COLORS.success : COLORS.primary,
                    marginRight: 8,
                  }}>{turn.speaker}:</span>
                  <span style={{
                    fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
                    fontSize: 13, fontWeight: 400, color: COLORS.onSurface, lineHeight: 1.5,
                  }}>{turn.text}</span>
                </div>
              ))}
            </div>
          </AnimatedText>

          {/* Gemini badge */}
          <div style={{ opacity: geminiBadgeOpacity }}>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 10,
              background: COLORS.primaryDim, border: `1px solid ${COLORS.primaryMid}`,
              borderRadius: 100, padding: '8px 18px',
            }}>
              <span style={{ fontSize: 18 }}>✦</span>
              <p style={{
                fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
                fontSize: 14, fontWeight: 600, color: COLORS.primary,
              }}>Gemini 2.0 Flash — single structured pass</p>
            </div>
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
