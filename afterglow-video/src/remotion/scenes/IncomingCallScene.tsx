import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from 'remotion';
import { VolumeX, Brain, Zap } from 'lucide-react';
import { COLORS } from '../data/videoScript';
import { GlowOrb } from '../components/GlowOrb';
import { AnimatedText } from '../components/AnimatedText';
import { ScreenshotInPhone } from '../components/ScreenshotInPhone';
import { useSceneFade } from '../components/useSceneFade';

const BULLETS = [
  { Icon: VolumeX,  text: 'Zero AI during the live call' },
  { Icon: Brain,    text: 'AI briefing shown before you say hello' },
  { Icon: Zap,      text: 'Pipeline runs in the background' },
];

export const IncomingCallScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const sceneOpacity = useSceneFade(durationInFrames);

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: sceneOpacity }}>
      <GlowOrb x="30%" y="50%" size={700} color={COLORS.primary} opacity={0.10} blur={160} />
      <GlowOrb x="72%" y="45%" size={600} color={COLORS.primary} opacity={0.14} blur={160} />

      <AbsoluteFill style={{
        display: 'flex', flexDirection: 'row', alignItems: 'center',
        justifyContent: 'center', gap: 80, padding: '0 80px',
      }}>
        {/* ── Colonna sinistra: copy ─────────────────────────────── */}
        <div style={{ flex: 1, maxWidth: 460, minWidth: 0 }}>
          <AnimatedText delay={5} style={{ marginBottom: 16 }}>
            <p style={{
              fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
              fontSize: 12, fontWeight: 700, color: COLORS.primary,
              letterSpacing: '4px', textTransform: 'uppercase',
            }}>02 — Answer</p>
          </AnimatedText>

          <AnimatedText delay={15} style={{ marginBottom: 24 }}>
            <h2 style={{
              fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
              fontSize: 52, fontWeight: 800, color: COLORS.onSurface,
              letterSpacing: '-1.5px', lineHeight: 1.05, wordBreak: 'break-word',
            }}>Answer normally.</h2>
          </AnimatedText>

          <AnimatedText delay={30} style={{ marginBottom: 44 }}>
            <p style={{
              fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
              fontSize: 18, fontWeight: 400, color: COLORS.onSurfaceVariant,
              lineHeight: 1.65, maxWidth: 420,
            }}>
              One tap on the blue AI button starts post-call analysis.
              The operator stays in full control.
            </p>
          </AnimatedText>

          {/* Bullet list con icone Lucide */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            {BULLETS.map(({ Icon, text }, i) => {
              const d = 52 + i * 16;
              const bf = Math.max(0, frame - d);
              const bOpacity = interpolate(bf, [0, 22], [0, 1], { extrapolateRight: 'clamp' });
              const bX = interpolate(bf, [0, 22], [-18, 0], {
                extrapolateRight: 'clamp',
                easing: Easing.bezier(0.16, 1, 0.3, 1),
              });
              return (
                <div key={text} style={{
                  display: 'flex', alignItems: 'center', gap: 14,
                  opacity: bOpacity, transform: `translateX(${bX}px)`,
                }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: 10, flexShrink: 0,
                    background: COLORS.primaryDim,
                    border: `1px solid ${COLORS.primaryMid}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <Icon size={18} color={COLORS.primary} strokeWidth={2} />
                  </div>
                  <p style={{
                    fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
                    fontSize: 16, fontWeight: 500, color: COLORS.onSurface,
                  }}>{text}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Colonna destra: screenshot reale ──────────────────── */}
        <ScreenshotInPhone
          src="screenshots/incoming-call.png"
          screenWidth={310}
          delay={10}
          slideFrom="right"
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
