import React from 'react';
import { interpolate, useCurrentFrame, Easing } from 'remotion';

interface AnimatedTextProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  style?: React.CSSProperties;
  direction?: 'up' | 'down' | 'none';
  distance?: number;
}

export const AnimatedText: React.FC<AnimatedTextProps> = ({
  children,
  delay = 0,
  duration = 30,
  style,
  direction = 'up',
  distance = 28,
}) => {
  const frame = useCurrentFrame();
  const f = Math.max(0, frame - delay);

  const progress = interpolate(f, [0, duration], [0, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const opacity = progress;
  const translateY =
    direction === 'up'
      ? distance * (1 - progress)
      : direction === 'down'
      ? -distance * (1 - progress)
      : 0;

  return (
    <div
      style={{
        opacity,
        transform: `translateY(${translateY}px)`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};
