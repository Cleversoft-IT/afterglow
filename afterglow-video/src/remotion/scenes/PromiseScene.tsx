import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from 'remotion';
import { PenLine, ArrowLeftRight, AlertCircle, Sparkles } from 'lucide-react';
import { COLORS } from '../data/videoScript';
import { GlowOrb } from '../components/GlowOrb';
import { useSceneFade } from '../components/useSceneFade';

const E = Easing.bezier(0.16, 1, 0.3, 1);

function appear(frame: number, at: number, dur = 28): number {
  return interpolate(frame, [at, at + dur], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E,
  });
}
function slideUp(frame: number, at: number, dur = 28, dist = 20): number {
  return interpolate(frame, [at, at + dur], [dist, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E,
  });
}

function ProblemItem({
  icon: Icon, label, frame, showAt,
}: {
  icon: React.ElementType;
  label: string;
  frame: number;
  showAt: number;
}) {
  return (
    <div style={{
      opacity: appear(frame, showAt),
      transform: `translateY(${slideUp(frame, showAt)}px)`,
      display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16,
    }}>
      <div style={{
        width: 44, height: 44, borderRadius: 12, flexShrink: 0,
        background: COLORS.surfaceVariant,
        border: `1px solid ${COLORS.border}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <Icon size={19} strokeWidth={1.8} color={COLORS.onSurfaceVariant} />
      </div>
      <p style={{
        fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
        fontSize: 22, fontWeight: 600, color: COLORS.onSurface, letterSpacing: '-0.2px',
      }}>{label}</p>
    </div>
  );
}

export const PromiseScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const sceneOpacity = useSceneFade(durationInFrames);

  const lineW = interpolate(frame, [100, 128], [0, 260], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E,
  });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: sceneOpacity }}>
      <GlowOrb x="20%" y="30%" size={480} color="#7c3aed"        opacity={0.08} blur={140} />
      <GlowOrb x="78%" y="68%" size={520} color={COLORS.primary}  opacity={0.08} blur={150} />

      <AbsoluteFill style={{
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        padding: '0 200px',
      }}>

        {/* ── "EVERY DAY," ──────────────────────────────────── */}
        <div style={{
          opacity: appear(frame, 8),
          transform: `translateY(${slideUp(frame, 8, 26, 16)}px)`,
          marginBottom: 12, textAlign: 'center',
        }}>
          <p style={{
            fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
            fontSize: 13, fontWeight: 700, color: COLORS.primary,
            letterSpacing: '5px', textTransform: 'uppercase',
          }}>Every day,</p>
        </div>

        {/* ── Headline ──────────────────────────────────────── */}
        <div style={{
          opacity: appear(frame, 18),
          transform: `translateY(${slideUp(frame, 18, 30, 22)}px)`,
          marginBottom: 44, textAlign: 'center',
        }}>
          <h2 style={{
            fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
            fontSize: 52, fontWeight: 800, color: COLORS.onSurface,
            letterSpacing: '-2px', lineHeight: 1.08,
          }}>
            operators answer<br />
            <span style={{ color: COLORS.onSurfaceVariant, fontWeight: 500 }}>
              dozens of calls.
            </span>
          </h2>
        </div>

        {/* ── Separatore centrato ───────────────────────────── */}
        <div style={{
          width: lineW, height: 1,
          background: `linear-gradient(90deg, transparent, ${COLORS.border}, transparent)`,
          marginBottom: 36,
        }} />

        {/* ── "Each one ends the same way:" ─────────────────── */}
        <div style={{
          opacity: appear(frame, 108),
          transform: `translateY(${slideUp(frame, 108, 26, 14)}px)`,
          marginBottom: 28, textAlign: 'center',
        }}>
          <p style={{
            fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
            fontSize: 19, fontWeight: 400, color: COLORS.onSurfaceVariant,
          }}>Each one ends the same way:</p>
        </div>

        {/* ── I 3 problemi — centrati come gruppo ───────────── */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
          <ProblemItem icon={PenLine}        label="A handwritten note"           frame={frame} showAt={142} />
          <ProblemItem icon={ArrowLeftRight} label="A tab switch"                 frame={frame} showAt={172} />
          <ProblemItem icon={AlertCircle}    label="A follow-up they might forget" frame={frame} showAt={210} />
        </div>

        {/* ── Insight ───────────────────────────────────────── */}
        <div style={{
          opacity: appear(frame, 310, 35),
          transform: `translateY(${slideUp(frame, 310, 35, 14)}px)`,
          marginTop: 36,
          display: 'flex', alignItems: 'center', gap: 12,
        }}>
          <div style={{
            width: 34, height: 34, borderRadius: 9, flexShrink: 0,
            background: COLORS.primaryDim,
            border: `1px solid ${COLORS.primaryMid}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Sparkles size={16} strokeWidth={1.8} color={COLORS.primary} />
          </div>
          <p style={{
            fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
            fontSize: 17, fontWeight: 600, color: COLORS.primary, letterSpacing: '-0.2px',
          }}>AI should handle what comes after.</p>
        </div>

      </AbsoluteFill>
    </AbsoluteFill>
  );
};
