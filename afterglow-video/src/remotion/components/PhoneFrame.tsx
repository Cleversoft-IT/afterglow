import React from 'react';
import { interpolate, useCurrentFrame, Easing } from 'remotion';
import { COLORS } from '../data/videoScript';

interface PhoneFrameProps {
  children: React.ReactNode;
  delay?: number;
  scale?: number;
  style?: React.CSSProperties;
}

export const PhoneFrame: React.FC<PhoneFrameProps> = ({
  children,
  delay = 0,
  scale = 1,
  style,
}) => {
  const frame = useCurrentFrame();
  const f = Math.max(0, frame - delay);

  const progress = interpolate(f, [0, 40], [0, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const opacity = progress;
  const translateY = interpolate(progress, [0, 1], [32, 0]);
  const frameScale = interpolate(progress, [0, 1], [0.94, 1]);

  const W = 390 * scale;
  const H = 844 * scale;
  const BORDER = 12 * scale;
  const RADIUS = 52 * scale;
  const NOTCH_W = 120 * scale;
  const NOTCH_H = 34 * scale;

  return (
    <div
      style={{
        opacity,
        transform: `translateY(${translateY}px) scale(${frameScale})`,
        position: 'relative',
        width: W + BORDER * 2,
        height: H + BORDER * 2,
        ...style,
      }}
    >
      {/* Outer shell */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: RADIUS + BORDER,
          background: `linear-gradient(160deg, #2A2F3E 0%, #1A1F2B 50%, #0F1118 100%)`,
          boxShadow: `
            0 0 0 1px ${COLORS.border},
            0 40px 80px rgba(0,0,0,0.6),
            0 20px 40px rgba(0,0,0,0.4),
            inset 0 1px 0 rgba(255,255,255,0.07)
          `,
        }}
      />
      {/* Side button */}
      <div
        style={{
          position: 'absolute',
          right: -BORDER - 3 * scale,
          top: 100 * scale,
          width: 4 * scale,
          height: 64 * scale,
          borderRadius: 4 * scale,
          background: '#2A2F3E',
        }}
      />
      {/* Volume buttons */}
      {[60, 110, 150].map((top, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: -BORDER - 3 * scale,
            top: top * scale,
            width: 4 * scale,
            height: i === 0 ? 40 * scale : 56 * scale,
            borderRadius: 4 * scale,
            background: '#2A2F3E',
          }}
        />
      ))}
      {/* Screen area */}
      <div
        style={{
          position: 'absolute',
          inset: BORDER,
          borderRadius: RADIUS,
          overflow: 'hidden',
          background: COLORS.bg,
        }}
      >
        {/* Dynamic island / notch */}
        <div
          style={{
            position: 'absolute',
            top: 12 * scale,
            left: '50%',
            transform: 'translateX(-50%)',
            width: NOTCH_W,
            height: NOTCH_H,
            borderRadius: NOTCH_H / 2,
            background: '#000',
            zIndex: 10,
          }}
        />
        {/* Content */}
        <div style={{ position: 'absolute', inset: 0 }}>{children}</div>
      </div>
    </div>
  );
};
