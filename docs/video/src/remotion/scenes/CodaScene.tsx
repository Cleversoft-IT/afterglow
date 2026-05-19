import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from 'remotion';
import { COLORS, STACK, URLS, CLAIM } from '../data/videoScript';
import { GlowOrb } from '../components/GlowOrb';
import { useSceneFade } from '../components/useSceneFade';
import { AnimatedText } from '../components/AnimatedText';

// Coda (4:30–5:00, 900f / 30s) — partners, stack, claim, URLs.

export const CodaScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const sceneOpacity = useSceneFade(durationInFrames, 30, 60);

  const claimOpacity = interpolate(frame, [180, 240], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return (
    <AbsoluteFill style={{ background: '#000', opacity: sceneOpacity }}>
      <GlowOrb x="50%" y="35%" size={900} color={COLORS.primary} opacity={0.15} blur={200} delay={20} />
      <GlowOrb x="50%" y="75%" size={500} color={COLORS.primaryDeep} opacity={0.08} blur={160} delay={80} />

      <AbsoluteFill
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 32,
          padding: '0 120px',
        }}
      >
        {/* Wordmark — split-color, mirrors the demo-site home logo */}
        <AnimatedText delay={10} duration={30} direction="up" distance={20}>
          <div
            style={{
              fontSize: 132,
              fontWeight: 800,
              letterSpacing: '-0.055em',
              lineHeight: 1,
            }}
          >
            <span style={{ color: COLORS.white }}>{CLAIM.wordmark.after}</span>
            <span style={{ color: COLORS.primary }}>{CLAIM.wordmark.glow}</span>
          </div>
        </AnimatedText>

        {/* Stack line — fades in, then out before claim */}
        <div
          style={{
            opacity: interpolate(frame, [50, 90, 170, 210], [0, 1, 1, 0], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }),
            textAlign: 'center',
            color: COLORS.muted,
            fontSize: 17,
            lineHeight: 1.7,
            maxWidth: 1100,
          }}
        >
          <div>{STACK.vultr}</div>
          <div>{STACK.google}</div>
          <div>{STACK.speechmatics}</div>
          <div style={{ marginTop: 4 }}>{STACK.deploy}</div>
        </div>

        {/* Claim — replaces stack */}
        <div
          style={{
            position: 'absolute',
            opacity: claimOpacity,
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
            marginTop: 220,
          }}
        >
          <div style={{ fontSize: 72, fontWeight: 800, color: COLORS.white, letterSpacing: '-0.04em' }}>
            {CLAIM.line1}
          </div>
          <div style={{ fontSize: 72, fontWeight: 800, color: COLORS.primarySoft, letterSpacing: '-0.04em' }}>
            {CLAIM.line2}
          </div>
        </div>

        {/* URLs at the bottom */}
        <div
          style={{
            position: 'absolute',
            bottom: 80,
            opacity: interpolate(frame, [300, 360], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }),
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 6,
            fontFamily: '"JetBrains Mono", ui-monospace, Menlo, monospace',
          }}
        >
          <div style={{ fontSize: 22, color: '#BFDBFE' }}>{URLS.demo}</div>
          <div style={{ fontSize: 16, color: '#64748B' }}>
            {URLS.repo} · MIT
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
