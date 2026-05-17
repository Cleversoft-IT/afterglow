import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from 'remotion';
import { COLORS } from '../data/videoScript';
import { GlowOrb } from '../components/GlowOrb';
import { AnimatedText } from '../components/AnimatedText';
import { ScreenshotInPhone } from '../components/ScreenshotInPhone';
import { useSceneFade } from '../components/useSceneFade';

export const MemoryScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const sceneOpacity = useSceneFade(durationInFrames);

  const flowItems = [
    { icon: '📞', text: 'Next call arrives', delay: 50 },
    { icon: '🔍', text: 'RAG lookup by phone number', delay: 70 },
    { icon: '🧠', text: 'Prior history pre-fetched', delay: 90 },
    { icon: '👋', text: 'Operator briefed before hello', delay: 110 },
  ];

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: sceneOpacity }}>
      <GlowOrb x="20%" y="50%" size={700} color="#8b5cf6" opacity={0.08} blur={160} />
      <GlowOrb x="70%" y="45%" size={600} color={COLORS.primary} opacity={0.1} blur={160} />

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
            }}>05 — Remember</p>
          </AnimatedText>

          <AnimatedText delay={15} style={{ marginBottom: 24 }}>
            <h2 style={{
              fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
              fontSize: 44, fontWeight: 800, color: COLORS.onSurface,
              letterSpacing: '-1.5px', lineHeight: 1.06, wordBreak: 'break-word',
            }}>
              Caller memory
              <br />
              <span style={{ color: '#8b5cf6' }}>that grows.</span>
            </h2>
          </AnimatedText>

          <AnimatedText delay={30} style={{ marginBottom: 36 }}>
            <p style={{
              fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
              fontSize: 17, fontWeight: 400, color: COLORS.onSurfaceVariant,
              lineHeight: 1.6, maxWidth: 400,
            }}>
              Every call enriches a Vultr Vector Store. At the next ring, the AI briefing arrives before the operator says hello.
            </p>
          </AnimatedText>

          {/* Flow steps */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {flowItems.map((item, i) => {
              const itemF = Math.max(0, frame - item.delay);
              const itemOpacity = interpolate(itemF, [0, 20], [0, 1], { extrapolateRight: 'clamp' });
              const itemX = interpolate(itemF, [0, 20], [-16, 0], {
                extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1),
              });
              return (
                <div key={item.text} style={{ opacity: itemOpacity, transform: `translateX(${itemX}px)` }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <div style={{
                      width: 40, height: 40, borderRadius: 11, flexShrink: 0,
                      background: COLORS.surface, border: `1px solid ${COLORS.border}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18,
                    }}>{item.icon}</div>
                    <p style={{
                      fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
                      fontSize: 15, fontWeight: 600, color: COLORS.onSurface,
                    }}>{item.text}</p>
                  </div>
                  {i < flowItems.length - 1 && (
                    <div style={{ width: 1, height: 16, background: COLORS.border, marginLeft: 20 }} />
                  )}
                </div>
              );
            })}
          </div>

          {/* Vultr badge */}
          <AnimatedText delay={135} style={{ marginTop: 24 }}>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 10,
              background: COLORS.surface, border: `1px solid ${COLORS.border}`,
              borderRadius: 100, padding: '8px 18px',
            }}>
              <span style={{ fontSize: 16 }}>🗄️</span>
              <p style={{
                fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
                fontSize: 13, fontWeight: 600, color: COLORS.onSurfaceVariant,
              }}>Vultr Vector Store — semantic recall</p>
            </div>
          </AnimatedText>
        </div>

        {/* Destra: screenshot reale customer detail */}
        <div style={{ flexShrink: 0 }}>
          <ScreenshotInPhone
            src="screenshots/customer-detail.png"
            screenWidth={310}
            delay={10}
            slideFrom="right"
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
