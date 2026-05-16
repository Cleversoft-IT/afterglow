// Design tokens — light/dark palettes share spacing, radius, and typography.

export type ThemeMode = 'light' | 'dark';

export type ColorPalette = {
  bg: string;
  surface: string;
  surfaceAlt: string;
  border: string;
  text: string;
  textMuted: string;
  textSubtle: string;
  brand: string;
  brandStrong: string;
  accentSoft: string;
  onPrimary: string;
  success: string;
  warning: string;
  danger: string;
  overlay: string;
  infoBg: string;
  infoBorder: string;
  highlightBg: string;
  highlightBorder: string;
  callAfterglow: string;
};

export type ShadowPalette = {
  card: {
    shadowColor: string;
    shadowOffset: { width: number; height: number };
    shadowOpacity: number;
    shadowRadius: number;
    elevation: number;
  };
  raised: {
    shadowColor: string;
    shadowOffset: { width: number; height: number };
    shadowOpacity: number;
    shadowRadius: number;
    elevation: number;
  };
};

export const lightColors: ColorPalette = {
  bg: '#F7F7F4',
  surface: '#FFFFFF',
  surfaceAlt: '#F1F1EE',
  border: '#E5E5DF',
  text: '#0D0D0D',
  textMuted: '#6B6B66',
  textSubtle: '#8A8A85',
  brand: '#3b82f6',
  brandStrong: '#2563eb',
  accentSoft: '#10A37F',
  onPrimary: '#FFFFFF',
  success: '#10A37F',
  warning: '#B45309',
  danger: '#C41E3A',
  overlay: 'rgba(13, 13, 13, 0.45)',
  infoBg: 'rgba(59, 130, 246, 0.08)',
  infoBorder: 'rgba(59, 130, 246, 0.2)',
  highlightBg: 'rgba(59, 130, 246, 0.1)',
  highlightBorder: 'rgba(59, 130, 246, 0.22)',
  callAfterglow: '#3b82f6',
};

export const darkColors: ColorPalette = {
  bg: '#0b0d12',
  surface: '#161922',
  surfaceAlt: '#1f2330',
  border: '#262b3a',
  text: '#f4f5f7',
  textMuted: '#9aa1b2',
  textSubtle: '#6b7280',
  brand: '#3b82f6',
  brandStrong: '#2563eb',
  accentSoft: '#34d399',
  onPrimary: '#FFFFFF',
  success: '#34d399',
  warning: '#fbbf24',
  danger: '#f87171',
  overlay: 'rgba(0, 0, 0, 0.65)',
  infoBg: 'rgba(59, 130, 246, 0.12)',
  infoBorder: 'rgba(59, 130, 246, 0.28)',
  highlightBg: 'rgba(59, 130, 246, 0.14)',
  highlightBorder: 'rgba(59, 130, 246, 0.32)',
  callAfterglow: '#3b82f6',
};

export function getColors(mode: ThemeMode): ColorPalette {
  return mode === 'dark' ? darkColors : lightColors;
}

export function getShadows(mode: ThemeMode): ShadowPalette {
  const shadowColor = mode === 'dark' ? '#000000' : '#0D0D0D';
  const cardOpacity = mode === 'dark' ? 0.2 : 0.04;
  const raisedOpacity = mode === 'dark' ? 0.35 : 0.06;
  return {
    card: {
      shadowColor,
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: cardOpacity,
      shadowRadius: 4,
      elevation: mode === 'dark' ? 2 : 1,
    },
    raised: {
      shadowColor,
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: raisedOpacity,
      shadowRadius: 10,
      elevation: mode === 'dark' ? 4 : 2,
    },
  };
}

/** @deprecated Use `useTheme().colors` — kept for type re-exports during migration */
export const colors = lightColors;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
  xxxl: 48,
} as const;

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  pill: 999,
} as const;

export const typography = {
  title: { fontSize: 20, fontWeight: '600' as const, letterSpacing: -0.3 },
  heading: { fontSize: 16, fontWeight: '600' as const, letterSpacing: -0.2 },
  body: { fontSize: 15, fontWeight: '400' as const, lineHeight: 22 },
  bodySmall: { fontSize: 14, fontWeight: '400' as const, lineHeight: 20 },
  caption: { fontSize: 13, fontWeight: '400' as const, lineHeight: 18 },
  label: { fontSize: 13, fontWeight: '500' as const },
  micro: { fontSize: 12, fontWeight: '400' as const, lineHeight: 16 },
} as const;

export const shadows = getShadows('light');
