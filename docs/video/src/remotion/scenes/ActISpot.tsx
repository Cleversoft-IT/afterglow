import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from 'remotion';
import { COLORS, ACT_I_BEATS, ACT_I_PROOFS, CLAIM } from '../data/videoScript';

// Act I (0:00–0:30) — typographic spot. No actors, no UI.
// Black bg, centred type, beat-driven reveals + one phone ring at 0:02
// (audio handled in Composition.tsx).

const beatOpacity = (
  frame: number,
  start: number,
  duration: number,
  fadeIn = 12,
  fadeOut = 12,
) => {
  const fIn  = interpolate(frame, [start, start + fadeIn], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    easing: Easing.bezier(0.4, 0, 0.2, 1),
  });
  const fOut = interpolate(frame, [start + duration - fadeOut, start + duration], [1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    easing: Easing.bezier(0.4, 0, 0.2, 1),
  });
  return Math.min(fIn, fOut);
};

export const ActISpot: React.FC<{ durationInFrames: number }> = () => {
  const frame = useCurrentFrame();

  // Beat 1: "A call ends."           ~4–10s   (120–300)
  const beat1 = beatOpacity(frame, ACT_I_BEATS[0].start, ACT_I_BEATS[0].duration);
  // Beat 2: "Something else begins." ~10–16s  (300–480)
  const beat2 = beatOpacity(frame, ACT_I_BEATS[1].start, ACT_I_BEATS[1].duration);

  // Beat 3: four proof points, staggered between 420–540
  const proofsStart = 420;
  const proofStagger = 14;
  const proofsAllOut = 540;

  // Beat 4: the claim, 540–660 (~18–22s)
  const claimStart = 540;
  const claimEnd = 660;
  const claimOpacity = interpolate(frame, [claimStart, claimStart + 30, claimEnd - 30, claimEnd], [0, 1, 1, 0.85], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    easing: Easing.bezier(0.4, 0, 0.2, 1),
  });

  return (
    <AbsoluteFill
      style={{
        background: '#000000',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: COLORS.white,
      }}
    >
      {/* Beat 1 + Beat 2 — stacked, single column, centred */}
      {beat1 > 0 && beat2 < 1 ? (
        <div
          style={{
            opacity: beat1,
            fontSize: 168,
            fontWeight: 800,
            letterSpacing: '-0.05em',
            lineHeight: 1.05,
            textAlign: 'center',
          }}
        >
          A call ends.
        </div>
      ) : null}

      {beat2 > 0 ? (
        <div
          style={{
            position: 'absolute',
            opacity: beat2,
            fontSize: 168,
            fontWeight: 800,
            letterSpacing: '-0.05em',
            lineHeight: 1.05,
            textAlign: 'center',
            color: '#CBD5E1',
            whiteSpace: 'pre-line',
          }}
        >
          Something else{'\n'}begins.
        </div>
      ) : null}

      {/* Beat 3 — proof points, staggered */}
      {frame >= proofsStart && frame <= proofsAllOut + 30 ? (
        <div
          style={{
            position: 'absolute',
            display: 'flex',
            flexDirection: 'column',
            gap: 18,
            alignItems: 'center',
          }}
        >
          {ACT_I_PROOFS.map((line, i) => {
            const reveal = proofsStart + i * proofStagger;
            const out = proofsAllOut;
            const op = interpolate(
              frame,
              [reveal, reveal + 18, out, out + 24],
              [0, 1, 1, 0],
              {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
                easing: Easing.bezier(0.4, 0, 0.2, 1),
              },
            );
            const ty = interpolate(frame, [reveal, reveal + 18], [10, 0], {
              extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            });
            return (
              <div
                key={line}
                style={{
                  opacity: op,
                  transform: `translateY(${ty}px)`,
                  fontSize: 64,
                  fontWeight: 500,
                  letterSpacing: '-0.02em',
                  color: '#94A3B8',
                  lineHeight: 1.2,
                }}
              >
                {line}
              </div>
            );
          })}
        </div>
      ) : null}

      {/* Beat 4 — the claim */}
      {frame >= claimStart - 12 ? (
        <div
          style={{
            position: 'absolute',
            opacity: claimOpacity,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 28,
          }}
        >
          <div
            style={{
              fontSize: 64,
              fontWeight: 700,
              letterSpacing: '-0.03em',
              color: COLORS.white,
            }}
          >
            {CLAIM.wordmark}
          </div>
          <div
            style={{
              fontSize: 96,
              fontWeight: 800,
              letterSpacing: '-0.045em',
              lineHeight: 1.05,
              textAlign: 'center',
            }}
          >
            <div style={{ color: COLORS.white }}>{CLAIM.line1}</div>
            <div style={{ color: COLORS.primarySoft, marginTop: 6 }}>{CLAIM.line2}</div>
          </div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
