import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from 'remotion';
import { COLORS } from '../data/videoScript';
import { GlowOrb } from '../components/GlowOrb';
import { AnimatedText } from '../components/AnimatedText';
import { useSceneFade } from '../components/useSceneFade';

interface Partner {
  name: string;
  color: string;
  pills: string[];
  description: string;
  icon: string;
}

const PARTNERS: Partner[] = [
  {
    name: 'Speechmatics',
    color: '#f59e0b',
    icon: '🎙️',
    pills: ['Batch STT', 'Speaker diarization', 'Language detect', 'TTS preview'],
    description: 'Transcribes every recording with speaker labels. Demo audio generated with Speechmatics TTS voices.',
  },
  {
    name: 'Google Gemini + ADK',
    color: '#3b82f6',
    icon: '✦',
    pills: ['Gemini 2.0 Flash', 'Structured output', 'ADK agentic loop'],
    description: 'Single structured-output call extracts fields, classifies intent, plans actions. ADK drives the autonomous planner.',
  },
  {
    name: 'Vultr',
    color: '#10b981',
    icon: '🗄️',
    pills: ['Managed Postgres', 'Vector Store', 'Cloud Compute', 'IAM'],
    description: 'System of record for calls, actions, profiles and audit. Vector Store powers the RAG memory loop in production.',
  },
];

export const TechScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const sceneOpacity = useSceneFade(durationInFrames);

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: sceneOpacity }}>
      <GlowOrb x="50%" y="50%" size={900} color={COLORS.primary} opacity={0.07} blur={180} />
      <GlowOrb x="15%" y="60%" size={400} color="#f59e0b" opacity={0.06} blur={140} />
      <GlowOrb x="85%" y="35%" size={400} color="#10b981" opacity={0.06} blur={140} />

      <AbsoluteFill style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        padding: '0 80px', overflow: 'hidden',
      }}>
        <AnimatedText delay={5} style={{ marginBottom: 16 }}>
          <p style={{
            fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
            fontSize: 12, fontWeight: 700, color: COLORS.primary,
            letterSpacing: '4px', textTransform: 'uppercase',
          }}>
            04 — The stack
          </p>
        </AnimatedText>

        <AnimatedText delay={15} style={{ marginBottom: 56 }}>
          <h2 style={{
            fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
            fontSize: 56, fontWeight: 800, color: COLORS.onSurface,
            letterSpacing: '-1.5px', textAlign: 'center',
          }}>
            Built on the best.
          </h2>
        </AnimatedText>

        {/* Partner cards */}
        <div style={{ display: 'flex', gap: 20, width: '100%', maxWidth: 1060, overflow: 'hidden' }}>
          {PARTNERS.map((partner, i) => {
            const cardDelay = 35 + i * 25;
            const cardF = Math.max(0, frame - cardDelay);
            const cardOpacity = interpolate(cardF, [0, 30], [0, 1], {
              extrapolateRight: 'clamp',
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            });
            const cardY = interpolate(cardF, [0, 30], [32, 0], {
              extrapolateRight: 'clamp',
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            });

            return (
              <div key={partner.name} style={{
                flex: 1, minWidth: 0,
                opacity: cardOpacity, transform: `translateY(${cardY}px)`,
                background: COLORS.surface,
                border: `1px solid ${COLORS.border}`,
                borderRadius: 20, padding: 28,
                position: 'relative', overflow: 'hidden',
              }}>
                {/* Top accent */}
                <div style={{
                  position: 'absolute', top: 0, left: 0, right: 0, height: 3,
                  background: partner.color,
                  borderRadius: '20px 20px 0 0',
                }} />

                {/* Glow corner */}
                <div style={{
                  position: 'absolute', top: -40, right: -40, width: 160, height: 160,
                  borderRadius: '50%',
                  background: `${partner.color}12`,
                  filter: 'blur(40px)',
                }} />

                {/* Icon */}
                <div style={{
                  fontSize: 32, marginBottom: 16, lineHeight: 1,
                }}>
                  {partner.icon}
                </div>

                {/* Name */}
                <h3 style={{
                  fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
                  fontSize: 16, fontWeight: 700, color: COLORS.onSurface, marginBottom: 12,
                  wordBreak: 'break-word',
                }}>
                  {partner.name}
                </h3>

                {/* Pills */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 18 }}>
                  {partner.pills.map((pill) => (
                    <span key={pill} style={{
                      fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
                      fontSize: 11, fontWeight: 600,
                      color: partner.color,
                      background: `${partner.color}18`,
                      border: `1px solid ${partner.color}40`,
                      borderRadius: 8,
                      padding: '3px 10px',
                    }}>
                      {pill}
                    </span>
                  ))}
                </div>

                {/* Description */}
                <p style={{
                  fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
                  fontSize: 13, fontWeight: 400, color: COLORS.onSurfaceVariant, lineHeight: 1.6,
                }}>
                  {partner.description}
                </p>
              </div>
            );
          })}
        </div>

        {/* Tech tagline */}
        <AnimatedText delay={120} style={{ marginTop: 36 }}>
          <p style={{
            fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
            fontSize: 15, fontWeight: 400, color: COLORS.onSurfaceVariant, textAlign: 'center',
          }}>
            MIT licensed · AI Hackathon by lablab.ai · Milano AI Week 2026
          </p>
        </AnimatedText>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
