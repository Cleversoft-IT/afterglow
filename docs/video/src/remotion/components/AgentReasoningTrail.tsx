import React from 'react';
import { useCurrentFrame, interpolate, Easing } from 'remotion';
import { COLORS } from '../data/videoScript';

// Mirror of the live app's AgentReasoningTrail panel. Each turn is one
// row; turns fade in one after another, paced by the parent scene.
//
// Expected usage: parent scene passes `turns` + `firstTurnAt` (frame
// within scene at which turn #1 lands) + `cadence` (frames between turn
// reveals). The component computes its own per-turn opacity.

export type TrailStatus = 'ok' | 'failed' | 'pending';

export interface TrailTurn {
  n: number;
  title: string;
  summary: string;
  status: TrailStatus;
  badge?: string | null;
}

interface Props {
  turns: readonly TrailTurn[];
  firstTurnAt?: number;
  cadence?: number;
  highlightLast?: boolean;
}

const STATUS_DOT: Record<TrailStatus, string> = {
  ok: COLORS.successSolid,
  failed: COLORS.error,
  pending: COLORS.muted,
};

const BADGE_STYLE: Record<string, React.CSSProperties> = {
  validation_failed: {
    background: COLORS.errorDim,
    color: COLORS.error,
  },
  executed: {
    background: COLORS.successDim,
    color: COLORS.successDeep,
  },
};

export const AgentReasoningTrail: React.FC<Props> = ({
  turns,
  firstTurnAt = 30,
  cadence = 60,
  highlightLast = false,
}) => {
  const frame = useCurrentFrame();

  return (
    <div
      style={{
        background: COLORS.surface,
        border: `1px solid ${COLORS.border}`,
        borderRadius: 16,
        padding: '20px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 6,
        }}
      >
        <div
          style={{
            fontSize: 14,
            fontWeight: 700,
            letterSpacing: '0.14em',
            textTransform: 'uppercase',
            color: COLORS.primary,
          }}
        >
          Agent Reasoning Trail
        </div>
        <div style={{ fontSize: 13, color: COLORS.onSurfaceVariant }}>
          call_agent · gemini-3.1-flash-lite
        </div>
      </div>

      {turns.map((turn, i) => {
        const reveal = firstTurnAt + i * cadence;
        const opacity = interpolate(frame, [reveal, reveal + 18], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        });
        const translateY = interpolate(frame, [reveal, reveal + 18], [12, 0], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        });
        const isLast = highlightLast && i === turns.length - 1;
        return (
          <div
            key={turn.n}
            style={{
              opacity,
              transform: `translateY(${translateY}px)`,
              display: 'grid',
              gridTemplateColumns: '36px 1fr auto',
              gap: 14,
              alignItems: 'start',
              padding: '12px 14px',
              borderRadius: 10,
              background: isLast ? COLORS.primaryDim : COLORS.surfaceElevated,
              border: `1px solid ${isLast ? COLORS.primary : COLORS.borderDim}`,
            }}
          >
            <div
              style={{
                width: 30,
                height: 30,
                borderRadius: '50%',
                background: STATUS_DOT[turn.status],
                color: COLORS.white,
                fontSize: 14,
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {turn.n}
            </div>
            <div style={{ minWidth: 0 }}>
              <div
                style={{
                  fontSize: 17,
                  fontWeight: 700,
                  color: COLORS.onSurface,
                  letterSpacing: '-0.005em',
                  fontFamily:
                    turn.title.includes('.') || turn.title.includes('_')
                      ? '"JetBrains Mono", ui-monospace, Menlo, monospace'
                      : undefined,
                }}
              >
                {turn.title}
              </div>
              <div
                style={{
                  marginTop: 4,
                  fontSize: 14,
                  lineHeight: 1.5,
                  color: COLORS.onSurfaceVariant,
                  fontFamily: '"JetBrains Mono", ui-monospace, Menlo, monospace',
                }}
              >
                {turn.summary}
              </div>
            </div>
            {turn.badge ? (
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  padding: '4px 10px',
                  borderRadius: 6,
                  fontFamily: '"JetBrains Mono", ui-monospace, Menlo, monospace',
                  ...(BADGE_STYLE[turn.badge] ?? {
                    background: COLORS.surfaceVariant,
                    color: COLORS.onSurfaceVariant,
                  }),
                }}
              >
                {turn.badge}
              </div>
            ) : (
              <div />
            )}
          </div>
        );
      })}
    </div>
  );
};
