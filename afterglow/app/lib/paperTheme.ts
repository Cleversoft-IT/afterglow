import {
  argbFromHex,
  hexFromArgb,
  themeFromSourceColor,
  type Scheme,
} from '@material/material-color-utilities';
import { MD3LightTheme, MD3DarkTheme, type MD3Theme } from 'react-native-paper';

const BRAND_SEED = '#3b82f6';

// Phone-app semantic colors — survive any brand-color change.
export const callGreen = '#26B31E';
export const callRed = '#B3261E';

// Semantic success palette — separate from MD3 secondary/tertiary which the
// `themeFromSourceColor` generator pushes toward muted blue / pink. Audit log
// "success" rows, "completed" call status and similar states need green.
const successLight = {
  success: '#1F7A3D',
  onSuccess: '#FFFFFF',
  successContainer: '#B7E7C5',
  onSuccessContainer: '#0A3D1C',
};
const successDark = {
  success: '#86D8A2',
  onSuccess: '#063820',
  successContainer: '#1F5230',
  onSuccessContainer: '#B7E7C5',
};

// Pixel-like neutral backgrounds. We override the MD3-generated background and
// surface so the light theme reads as a clean off-white (no pinkish tint) and
// the dark theme reads as a true near-black, matching the Google Phone app.
const surfacesLight = {
  background: '#F7F8FA',
  onBackground: '#1A1C1F',
  surface: '#FFFFFF',
  onSurface: '#1A1C1F',
  surfaceVariant: '#EEF0F4',
  onSurfaceVariant: '#5A5D63',
  outline: '#C7C9CF',
  outlineVariant: '#E5E7EC',
};
const surfacesDark = {
  background: '#0B0D12',
  onBackground: '#ECEEF2',
  surface: '#161922',
  onSurface: '#ECEEF2',
  surfaceVariant: '#1F2330',
  onSurfaceVariant: '#A5A9B3',
  outline: '#3A3F4E',
  outlineVariant: '#262B3A',
};

function buildSchemeColors(
  scheme: Scheme,
  base: MD3Theme['colors'],
  surfaces: typeof surfacesLight,
): MD3Theme['colors'] {
  return {
    ...base,
    primary: hexFromArgb(scheme.primary),
    onPrimary: hexFromArgb(scheme.onPrimary),
    primaryContainer: hexFromArgb(scheme.primaryContainer),
    onPrimaryContainer: hexFromArgb(scheme.onPrimaryContainer),
    secondary: hexFromArgb(scheme.secondary),
    onSecondary: hexFromArgb(scheme.onSecondary),
    secondaryContainer: hexFromArgb(scheme.secondaryContainer),
    onSecondaryContainer: hexFromArgb(scheme.onSecondaryContainer),
    tertiary: hexFromArgb(scheme.tertiary),
    onTertiary: hexFromArgb(scheme.onTertiary),
    tertiaryContainer: hexFromArgb(scheme.tertiaryContainer),
    onTertiaryContainer: hexFromArgb(scheme.onTertiaryContainer),
    error: '#B3261E',
    onError: '#FFFFFF',
    errorContainer: hexFromArgb(scheme.errorContainer),
    onErrorContainer: hexFromArgb(scheme.onErrorContainer),
    inverseSurface: hexFromArgb(scheme.inverseSurface),
    inverseOnSurface: hexFromArgb(scheme.inverseOnSurface),
    inversePrimary: hexFromArgb(scheme.inversePrimary),
    ...surfaces,
  };
}

const matTheme = themeFromSourceColor(argbFromHex(BRAND_SEED));

// Extend MD3 colors with a semantic success palette. We keep the standard
// MD3Theme type via cast so consumers can `useTheme<AppTheme>()` to read it.
type AppColors = MD3Theme['colors'] & {
  success: string;
  onSuccess: string;
  successContainer: string;
  onSuccessContainer: string;
};

export type AppTheme = Omit<MD3Theme, 'colors'> & { colors: AppColors };

export const paperLightTheme: AppTheme = {
  ...MD3LightTheme,
  colors: {
    ...buildSchemeColors(matTheme.schemes.light, MD3LightTheme.colors, surfacesLight),
    ...successLight,
  },
};

export const paperDarkTheme: AppTheme = {
  ...MD3DarkTheme,
  colors: {
    ...buildSchemeColors(matTheme.schemes.dark, MD3DarkTheme.colors, surfacesDark),
    ...successDark,
  },
};
