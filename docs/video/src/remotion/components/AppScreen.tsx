// Faithful UI mockups of key Afterglow screens, using the app's exact design tokens.
import React from 'react';
import { useCurrentFrame, interpolate, Easing } from 'remotion';
import { COLORS, DEMO_CALL } from '../data/videoScript';

const S = 0.9; // uniform scale factor for phone content

const txt = (size: number, weight: number | string, color: string, extra?: React.CSSProperties): React.CSSProperties => ({
  fontSize: size * S,
  fontWeight: weight,
  color,
  fontFamily: '-apple-system, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
  lineHeight: 1.4,
  ...extra,
});

// ─────────────────────────────────────────────────────────
// HomeScreen — calls list
// ─────────────────────────────────────────────────────────
export const HomeScreen: React.FC = () => {
  const frame = useCurrentFrame();
  const calls = [
    { name: 'Sarah Mitchell', time: '2 min ago', status: 'completed', tag: 'Booking' },
    { name: 'James Holloway', time: '18 min ago', status: 'completed', tag: null },
    { name: '+44 7911 123456', time: '1 hr ago', status: 'missed', tag: null },
    { name: 'Emma Thompson', time: 'Yesterday', status: 'completed', tag: 'Inquiry' },
    { name: 'David Park', time: 'Yesterday', status: 'completed', tag: 'Booking' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: COLORS.bg }}>
      {/* Status bar */}
      <div style={{ height: 50 * S, display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', paddingLeft: 24 * S, paddingRight: 20 * S, paddingBottom: 6 * S }}>
        <span style={txt(14, 600, COLORS.onSurface)}>9:41</span>
        <div style={{ display: 'flex', gap: 6 * S, alignItems: 'center' }}>
          <span style={txt(12, 400, COLORS.onSurface)}>●●●</span>
          <span style={txt(12, 400, COLORS.onSurface)}>WiFi</span>
          <span style={txt(12, 400, COLORS.onSurface)}>100%</span>
        </div>
      </div>

      {/* Header */}
      <div style={{ paddingLeft: 20 * S, paddingRight: 20 * S, paddingTop: 8 * S, paddingBottom: 16 * S }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 * S }}>
          <div>
            <span style={txt(28, 800, COLORS.onSurface, { letterSpacing: '-0.5px' })}>
              after<span style={{ color: COLORS.primary }}>glow</span>
            </span>
          </div>
          <div style={{ width: 36 * S, height: 36 * S, borderRadius: '50%', background: COLORS.primaryDim, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={txt(16, 700, COLORS.primary)}>+</span>
          </div>
        </div>

        {/* Search bar */}
        <div style={{ background: COLORS.surfaceVariant, borderRadius: 12 * S, padding: `10px ${14 * S}px`, display: 'flex', alignItems: 'center', gap: 8 * S }}>
          <span style={txt(14, 400, COLORS.onSurfaceVariant)}>🔍</span>
          <span style={txt(14, 400, COLORS.onSurfaceVariant)}>Search calls…</span>
        </div>
      </div>

      {/* Filter chips */}
      <div style={{ paddingLeft: 20 * S, paddingRight: 20 * S, display: 'flex', gap: 8 * S, marginBottom: 8 * S, overflowX: 'hidden' }}>
        {['All', 'Bookings', 'Missed', 'Clients'].map((label, i) => (
          <div key={label} style={{
            paddingLeft: 14 * S, paddingRight: 14 * S, paddingTop: 7 * S, paddingBottom: 7 * S,
            borderRadius: 20 * S,
            background: i === 0 ? COLORS.primary : COLORS.surfaceVariant,
            flexShrink: 0,
          }}>
            <span style={txt(13, i === 0 ? 700 : 500, i === 0 ? COLORS.white : COLORS.onSurfaceVariant)}>{label}</span>
          </div>
        ))}
      </div>

      {/* Today label */}
      <div style={{ paddingLeft: 20 * S, paddingRight: 20 * S, paddingTop: 12 * S, paddingBottom: 6 * S }}>
        <span style={txt(12, 700, COLORS.onSurfaceVariant, { letterSpacing: '0.5px', textTransform: 'uppercase' })}>Today</span>
      </div>

      {/* Call list */}
      <div style={{ flex: 1, overflowY: 'hidden' }}>
        {calls.map((call, i) => {
          const itemDelay = i * 8;
          const itemF = Math.max(0, frame - itemDelay);
          const itemOpacity = interpolate(itemF, [0, 20], [0, 1], { extrapolateRight: 'clamp' });
          const itemY = interpolate(itemF, [0, 20], [12, 0], { extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1) });

          return (
            <div key={call.name} style={{
              display: 'flex', alignItems: 'center', gap: 14 * S,
              paddingLeft: 20 * S, paddingRight: 20 * S,
              paddingTop: 12 * S, paddingBottom: 12 * S,
              borderBottom: `1px solid ${COLORS.borderDim}`,
              opacity: itemOpacity,
              transform: `translateY(${itemY}px)`,
            }}>
              {/* Avatar */}
              <div style={{
                width: 44 * S, height: 44 * S, borderRadius: '50%',
                background: call.status === 'missed' ? COLORS.errorDim : COLORS.primaryDim,
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                <span style={txt(16, 700, call.status === 'missed' ? COLORS.error : COLORS.primary)}>
                  {call.name[0]}
                </span>
              </div>

              {/* Info */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 * S, marginBottom: 3 * S }}>
                  <span style={txt(15, 600, COLORS.onSurface, { whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' })}>{call.name}</span>
                  {call.tag && (
                    <span style={{
                      paddingLeft: 7 * S, paddingRight: 7 * S, paddingTop: 2 * S, paddingBottom: 2 * S,
                      borderRadius: 6 * S, background: COLORS.primaryDim,
                      ...txt(10, 600, COLORS.primary, { flexShrink: 0 }),
                    }}>{call.tag}</span>
                  )}
                </div>
                <span style={txt(12, 400, COLORS.onSurfaceVariant)}>{call.time}</span>
              </div>

              {/* Status icon */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 * S, flexShrink: 0 }}>
                <div style={{
                  width: 8 * S, height: 8 * S, borderRadius: '50%',
                  background: call.status === 'missed' ? COLORS.error : COLORS.successSolid,
                }} />
                <span style={txt(12, 400, COLORS.onSurfaceVariant)}>{'›'}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom navigation */}
      <div style={{
        background: COLORS.surface, borderTop: `1px solid ${COLORS.border}`,
        display: 'flex', justifyContent: 'space-around', alignItems: 'center',
        paddingTop: 12 * S, paddingBottom: 28 * S,
      }}>
        {[{ icon: '☎', label: 'Calls', active: true }, { icon: '⌨', label: 'Keypad', active: false }].map((tab) => (
          <div key={tab.label} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 * S }}>
            <span style={txt(22, 400, tab.active ? COLORS.primary : COLORS.onSurfaceVariant)}>{tab.icon}</span>
            <span style={txt(11, tab.active ? 700 : 500, tab.active ? COLORS.primary : COLORS.onSurfaceVariant)}>{tab.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────
// IncomingCallScreen
// ─────────────────────────────────────────────────────────
export const IncomingCallScreen: React.FC<{ showAiButton?: boolean }> = ({ showAiButton = false }) => {
  const frame = useCurrentFrame();

  const pulseScale = 1 + 0.08 * Math.sin(frame * 0.12);
  const pulseOpacity = 0.25 + 0.15 * Math.sin(frame * 0.12);

  const aiBtnScale = showAiButton
    ? interpolate(Math.max(0, frame - 20), [0, 25], [0, 1], {
        extrapolateRight: 'clamp',
        easing: Easing.bezier(0.34, 1.56, 0.64, 1),
      })
    : 0;

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'space-between',
      height: '100%', background: 'linear-gradient(180deg, #0B0D12 0%, #0F1420 60%, #0B0D12 100%)',
      paddingTop: 80 * S, paddingBottom: 48 * S,
    }}>
      {/* Status bar */}
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 50 * S, display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', paddingLeft: 24 * S, paddingRight: 20 * S, paddingBottom: 6 * S }}>
        <span style={txt(14, 600, COLORS.onSurface)}>9:41</span>
        <div style={{ display: 'flex', gap: 6 * S }}>
          <span style={txt(12, 400, COLORS.onSurface)}>●●●</span>
          <span style={txt(12, 400, COLORS.onSurface)}>100%</span>
        </div>
      </div>

      {/* Caller info */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 * S, marginTop: 20 * S }}>
        {/* Avatar with pulse rings */}
        <div style={{ position: 'relative', width: 120 * S, height: 120 * S }}>
          {[1.5, 1.25, 1].map((r, i) => (
            <div key={i} style={{
              position: 'absolute', borderRadius: '50%',
              width: 120 * S * r, height: 120 * S * r,
              top: '50%', left: '50%',
              transform: `translate(-50%, -50%) scale(${i < 2 ? pulseScale : 1})`,
              background: `rgba(59,130,246,${i === 0 ? pulseOpacity * 0.3 : i === 1 ? pulseOpacity * 0.5 : 1})`,
              border: i < 2 ? `1px solid rgba(59,130,246,${pulseOpacity})` : 'none',
            }}>
              {i === 2 && (
                <div style={{ width: '100%', height: '100%', borderRadius: '50%', background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <span style={txt(42, 700, COLORS.white)}>S</span>
                </div>
              )}
            </div>
          ))}
        </div>

        <div style={{ textAlign: 'center' }}>
          <p style={txt(12, 600, COLORS.onSurfaceVariant, { letterSpacing: '2px', textTransform: 'uppercase', marginBottom: 8 * S })}>Incoming call</p>
          <p style={txt(30, 700, COLORS.onSurface, { letterSpacing: '-0.5px', marginBottom: 4 * S })}>Sarah Mitchell</p>
          <p style={txt(15, 400, COLORS.onSurfaceVariant)}>{DEMO_CALL.phone}</p>
        </div>
      </div>

      {/* Call controls */}
      <div style={{ display: 'flex', gap: 48 * S, alignItems: 'center', position: 'relative' }}>
        {/* Reject */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 * S }}>
          <div style={{
            width: 68 * S, height: 68 * S, borderRadius: '50%',
            background: '#B3261E',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 20px rgba(179,38,30,0.4)',
          }}>
            <span style={txt(28, 400, COLORS.white)}>✕</span>
          </div>
          <span style={txt(12, 500, COLORS.onSurfaceVariant)}>Decline</span>
        </div>

        {/* AI button */}
        {showAiButton && (
          <div style={{
            transform: `scale(${aiBtnScale})`,
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 * S,
          }}>
            <div style={{
              width: 80 * S, height: 80 * S, borderRadius: '50%',
              background: `linear-gradient(135deg, ${COLORS.primary}, #1d4ed8)`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: `0 4px 32px rgba(59,130,246,0.5), 0 0 0 4px rgba(59,130,246,0.15)`,
            }}>
              <span style={txt(24, 700, COLORS.white)}>AI</span>
            </div>
            <span style={txt(12, 700, COLORS.primary)}>Enable AI</span>
          </div>
        )}

        {/* Answer */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 * S }}>
          <div style={{
            width: 68 * S, height: 68 * S, borderRadius: '50%',
            background: COLORS.successSolid,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 20px rgba(38,179,30,0.4)',
          }}>
            <span style={txt(28, 400, COLORS.white)}>✆</span>
          </div>
          <span style={txt(12, 500, COLORS.onSurfaceVariant)}>Accept</span>
        </div>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────
// CallDetailScreen — extracted fields + actions
// ─────────────────────────────────────────────────────────
export const CallDetailScreen: React.FC<{ showActions?: boolean; highlightField?: string }> = ({
  showActions = false,
  highlightField,
}) => {
  const frame = useCurrentFrame();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: COLORS.bg }}>
      {/* Header */}
      <div style={{ paddingTop: 60 * S, paddingLeft: 20 * S, paddingRight: 20 * S, paddingBottom: 16 * S, borderBottom: `1px solid ${COLORS.borderDim}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 * S, marginBottom: 4 * S }}>
          <span style={txt(15, 400, COLORS.onSurfaceVariant)}>‹</span>
          <span style={txt(17, 600, COLORS.onSurface)}>Sarah Mitchell</span>
        </div>
        <div style={{ display: 'flex', gap: 8 * S, marginLeft: 24 * S }}>
          <span style={{ ...txt(11, 600, COLORS.success), paddingLeft: 8 * S, paddingRight: 8 * S, paddingTop: 3 * S, paddingBottom: 3 * S, background: COLORS.successDim, borderRadius: 6 * S }}>Completed</span>
          <span style={{ ...txt(11, 400, COLORS.onSurfaceVariant) }}>3m 42s · Just now</span>
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'hidden', paddingLeft: 20 * S, paddingRight: 20 * S }}>
        {/* Extracted fields */}
        <p style={txt(13, 700, COLORS.onSurfaceVariant, { marginTop: 20 * S, marginBottom: 12 * S, letterSpacing: '0.5px', textTransform: 'uppercase' })}>
          Extracted fields
        </p>

        {DEMO_CALL.fields.map((field, i) => {
          const fieldDelay = i * 6;
          const fieldF = Math.max(0, frame - fieldDelay);
          const fieldOpacity = interpolate(fieldF, [0, 20], [0, 1], { extrapolateRight: 'clamp' });
          const fieldX = interpolate(fieldF, [0, 20], [-12, 0], { extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1) });
          const isHighlighted = highlightField === field.key;

          return (
            <div key={field.key} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              paddingTop: 10 * S, paddingBottom: 10 * S,
              borderBottom: `1px solid ${COLORS.borderDim}`,
              opacity: fieldOpacity,
              transform: `translateX(${fieldX}px)`,
              background: isHighlighted ? COLORS.primaryDim : 'transparent',
              borderRadius: isHighlighted ? 8 * S : 0,
              paddingLeft: isHighlighted ? 8 * S : 0,
              paddingRight: isHighlighted ? 8 * S : 0,
              transition: 'background 0.3s',
            }}>
              <div>
                <p style={txt(11, 600, COLORS.onSurfaceVariant, { marginBottom: 2 * S, textTransform: 'uppercase', letterSpacing: '0.3px' })}>{field.label}</p>
                <p style={txt(15, 600, COLORS.onSurface)}>{field.value}</p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 * S }}>
                <div style={{
                  paddingLeft: 8 * S, paddingRight: 8 * S, paddingTop: 3 * S, paddingBottom: 3 * S,
                  borderRadius: 6 * S, background: COLORS.primaryDim,
                }}>
                  <span style={txt(11, 700, COLORS.primary)}>{field.confidence}%</span>
                </div>
                <span style={txt(16, 400, COLORS.success)}>✓</span>
              </div>
            </div>
          );
        })}

        {/* Actions */}
        {showActions && (
          <>
            <p style={txt(13, 700, COLORS.onSurfaceVariant, { marginTop: 20 * S, marginBottom: 12 * S, letterSpacing: '0.5px', textTransform: 'uppercase' })}>
              Autonomous actions
            </p>
            {DEMO_CALL.actions.map((action, i) => {
              const actionDelay = i * 8 + 10;
              const actionF = Math.max(0, frame - actionDelay);
              const actionOpacity = interpolate(actionF, [0, 20], [0, 1], { extrapolateRight: 'clamp' });
              const actionScale = interpolate(actionF, [0, 20], [0.95, 1], { extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1) });

              return (
                <div key={action.type} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  paddingTop: 10 * S, paddingBottom: 10 * S,
                  borderBottom: `1px solid ${COLORS.borderDim}`,
                  opacity: actionOpacity,
                  transform: `scale(${actionScale})`,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 * S }}>
                    <span style={txt(15, 400, COLORS.success)}>✓</span>
                    <div>
                      <p style={txt(14, 600, COLORS.onSurface)}>{action.label}</p>
                      <p style={txt(11, 400, COLORS.onSurfaceVariant, { fontFamily: 'monospace' })}>{action.type}</p>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 6 * S, alignItems: 'center' }}>
                    {action.mock && (
                      <span style={{ ...txt(10, 600, COLORS.onSurfaceVariant), paddingLeft: 6 * S, paddingRight: 6 * S, paddingTop: 2 * S, paddingBottom: 2 * S, background: COLORS.surfaceVariant, borderRadius: 4 * S }}>Simulated</span>
                    )}
                    <span style={{ ...txt(11, 600, COLORS.success), paddingLeft: 8 * S, paddingRight: 8 * S, paddingTop: 3 * S, paddingBottom: 3 * S, background: COLORS.successDim, borderRadius: 6 * S }}>Done</span>
                  </div>
                </div>
              );
            })}
          </>
        )}
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────
// MemoryScreen — next call briefing
// ─────────────────────────────────────────────────────────
export const MemoryScreen: React.FC = () => {
  const frame = useCurrentFrame();

  const calls = [
    { date: '23 May 2026', summary: 'Booked 4 covers for dinner, gluten allergy noted. WhatsApp confirmation sent.' },
    { date: '10 Apr 2026', summary: 'Table for 2 on anniversary. Requested quiet corner table.' },
    { date: '12 Feb 2026', summary: 'First booking — 3 covers, general inquiry about menu.' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: COLORS.bg }}>
      {/* Header */}
      <div style={{ paddingTop: 60 * S, paddingLeft: 20 * S, paddingRight: 20 * S, paddingBottom: 16 * S, borderBottom: `1px solid ${COLORS.borderDim}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 * S, marginBottom: 12 * S }}>
          <span style={txt(15, 400, COLORS.onSurfaceVariant)}>‹</span>
          <span style={txt(17, 600, COLORS.onSurface)}>Sarah Mitchell</span>
        </div>
        <div style={{ background: COLORS.surfaceVariant, borderRadius: 16 * S, padding: 16 * S }}>
          <p style={txt(11, 700, COLORS.primary, { letterSpacing: '1px', textTransform: 'uppercase', marginBottom: 8 * S })}>AI Briefing</p>
          <p style={txt(14, 400, COLORS.onSurface, { lineHeight: 1.5 })}>{DEMO_CALL.briefing}</p>
        </div>
      </div>

      {/* Call history */}
      <div style={{ flex: 1, paddingLeft: 20 * S, paddingRight: 20 * S, overflowY: 'hidden' }}>
        <p style={txt(13, 700, COLORS.onSurfaceVariant, { marginTop: 20 * S, marginBottom: 12 * S, letterSpacing: '0.5px', textTransform: 'uppercase' })}>
          Call history
        </p>
        {calls.map((call, i) => {
          const callDelay = i * 8;
          const callF = Math.max(0, frame - callDelay);
          const callOpacity = interpolate(callF, [0, 20], [0, 1], { extrapolateRight: 'clamp' });

          return (
            <div key={i} style={{
              display: 'flex', gap: 12 * S, paddingTop: 12 * S, paddingBottom: 12 * S,
              borderBottom: `1px solid ${COLORS.borderDim}`,
              opacity: callOpacity,
            }}>
              <div style={{ width: 2, background: COLORS.primary, borderRadius: 2, flexShrink: 0, alignSelf: 'stretch' }} />
              <div>
                <p style={txt(12, 600, COLORS.onSurfaceVariant, { marginBottom: 4 * S })}>{call.date}</p>
                <p style={txt(13, 400, COLORS.onSurface)}>{call.summary}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
