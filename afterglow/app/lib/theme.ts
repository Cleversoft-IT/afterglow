// Color tokens used across the app. Keep this small: a couple of greys plus
// the brand blue used by the "tasto blu" simulator.

export const colors = {
  bg: '#0b0d12',
  surface: '#161922',
  surfaceAlt: '#1f2330',
  border: '#262b3a',
  text: '#f4f5f7',
  textMuted: '#9aa1b2',
  textSubtle: '#6b7280',
  brand: '#3b82f6',
  brandStrong: '#2563eb',
  success: '#34d399',
  warning: '#fbbf24',
  danger: '#f87171',
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const radius = {
  sm: 6,
  md: 10,
  lg: 16,
  pill: 999,
} as const;
