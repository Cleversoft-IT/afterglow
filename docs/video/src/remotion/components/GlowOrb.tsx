import React from 'react';
import { interpolate, useCurrentFrame, Easing } from 'remotion';

interface GlowOrbProps {
  x?: string;
  y?: string;
  size?: number;
  color?: string;
  opacity?: number;
  blur?: number;
  delay?: number;
}

export const GlowOrb: React.FC<GlowOrbProps> = ({
  x = '50%',
  y = '50%',
  size = 600,
  color = '#3b82f6',
  opacity = 0.18,
  blur = 120,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const f = Math.max(0, frame - delay);

  const currentOpacity = interpolate(f, [0, 40], [0, opacity], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.4, 0, 0.2, 1),
  });

  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        transform: 'translate(-50%, -50%)',
        width: size,
        height: size,
        borderRadius: '50%',
        background: color,
        opacity: currentOpacity,
        filter: `blur(${blur}px)`,
        pointerEvents: 'none',
      }}
    />
  );
};
