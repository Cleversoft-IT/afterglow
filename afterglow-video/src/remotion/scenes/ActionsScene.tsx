import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from 'remotion';
import { COLORS, DEMO_CALL } from '../data/videoScript';
import { GlowOrb } from '../components/GlowOrb';
import { AnimatedText } from '../components/AnimatedText';
import { ScreenshotInPhone } from '../components/ScreenshotInPhone';
import { useSceneFade } from '../components/useSceneFade';

const ACTION_ICONS: Record<string, string> = {
  'booking.create': '📅',
  'whatsapp.send_confirmation': '💬',
  'customer.update_profile': '👤',
};

export const ActionsScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const sceneOpacity = useSceneFade(durationInFrames);

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: sceneOpacity }}>
      <GlowOrb x="70%" y="50%" size={700} color={COLORS.primary} opacity={0.1} blur={160} />
      <GlowOrb x="20%" y="45%" size={500} color="#10b981" opacity={0.08} blur={140} />

      <AbsoluteFill style={{
        display: 'flex', flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
        gap: 80, padding: '0 80px',
      }}>
        {/* Sinistra: copy */}
        <div style={{ flex: 1, maxWidth: 480, minWidth: 0 }}>
          <AnimatedText delay={5} style={{ marginBottom: 16 }}>
            <p style={{
              fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
              fontSize: 12, fontWeight: 700, color: COLORS.primary,
              letterSpacing: '4px', textTransform: 'uppercase',
            }}>04 — Act</p>
          </AnimatedText>

          <AnimatedText delay={15} style={{ marginBottom: 24 }}>
            <h2 style={{
              fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
              fontSize: 48, fontWeight: 800, color: COLORS.onSurface,
              letterSpacing: '-1.5px', lineHeight: 1.06, wordBreak: 'break-word',
            }}>
              Autonomous.
              <br />
              <span style={{ color: COLORS.success }}>Not a copilot.</span>
            </h2>
          </AnimatedText>

          <AnimatedText delay={30} style={{ marginBottom: 36 }}>
            <p style={{
              fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
              fontSize: 18, fontWeight: 400, color: COLORS.onSurfaceVariant,
              lineHeight: 1.6, maxWidth: 420,
            }}>
              Bookings confirmed. WhatsApp sent. Profile updated. No clicks required — every action is audited and individually reversible.
            </p>
          </AnimatedText>

          {/* Action cards */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {DEMO_CALL.actions.map((action, i) => {
              const d = 50 + i * 18;
              const af = Math.max(0, frame - d);
              return (
                <div key={action.type} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  background: COLORS.surface, border: `1px solid ${COLORS.border}`,
                  borderRadius: 14, padding: '13px 18px',
                  opacity: interpolate(af, [0, 22], [0, 1], { extrapolateRight: 'clamp' }),
                  transform: `translateX(${interpolate(af, [0, 22], [-18, 0], { extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1) })}px)`,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{
                      width: 38, height: 38, borderRadius: 9,
                      background: COLORS.successDim,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 17, flexShrink: 0,
                    }}>
                      {ACTION_ICONS[action.type] ?? '⚡'}
                    </div>
                    <div>
                      <p style={{
                        fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
                        fontSize: 14, fontWeight: 600, color: COLORS.onSurface,
                      }}>{action.label}</p>
                      <p style={{
                        fontFamily: 'monospace',
                        fontSize: 11, fontWeight: 400, color: COLORS.onSurfaceVariant,
                      }}>{action.type}</p>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, flexShrink: 0 }}>
                    {action.mock && (
                      <span style={{
                        fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
                        fontSize: 10, fontWeight: 600, color: COLORS.onSurfaceVariant,
                        background: COLORS.surfaceVariant, borderRadius: 6, padding: '2px 8px',
                      }}>Simulated</span>
                    )}
                    <span style={{
                      fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
                      fontSize: 12, fontWeight: 700, color: COLORS.success,
                      background: COLORS.successDim, borderRadius: 8, padding: '4px 12px',
                    }}>Done</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Destra: screenshot reale azioni */}
        <div style={{ flexShrink: 0 }}>
          <ScreenshotInPhone
            src="screenshots/call-detail-actions.png"
            screenWidth={310}
            delay={10}
            slideFrom="right"
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
