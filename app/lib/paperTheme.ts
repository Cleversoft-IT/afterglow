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

// Variant of `callRed` that stays legible on a dark surface. The MD3 error
// hue (#B3261E) goes muddy against `surfacesDark.background` (#0B0D12) and
// the FAB-style red bg the Decline button uses — pick a brighter rouge for
// dark mode but keep the same hue family.
export const callRedDark = '#FF6B6B';

// `aiPrimary` is the fill of the central "AI" CTA on the incoming-call
// screen and any other "this is an AI surface" affordance. The light value
// matches `theme.colors.primary` (brand blue from the seed); the dark
// value is a saturated indigo that reads as a deliberate button on the
// near-black dark background instead of the washed-out tonal blue MD3
// auto-generates from the seed.
export const aiPrimaryLight = '#3b82f6';
export const aiPrimaryDark = '#1d4ed8';

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

// Override MD3 secondary/tertiary containers and elevation tints. The
// `themeFromSourceColor` generator produces lavender/pink-tinted surfaces
// from the #3b82f6 brand seed; we replace them with neutral cool greys so
// chips, accordions and elevated cards read consistently across the app.
const accentsLight = {
  secondaryContainer: '#E7EEFC',
  onSecondaryContainer: '#0A2A5C',
  tertiaryContainer: '#EEF0F4',
  onTertiaryContainer: '#1A1C1F',
  elevation: {
    level0: 'transparent',
    level1: '#F4F6FB',
    level2: '#EDF1F8',
    level3: '#E5EBF6',
    level4: '#DEE5F2',
    level5: '#D8E1EF',
  },
};
const accentsDark = {
  secondaryContainer: '#1B2944',
  onSecondaryContainer: '#D6E2FA',
  tertiaryContainer: '#1F2330',
  onTertiaryContainer: '#ECEEF2',
  elevation: {
    level0: 'transparent',
    level1: '#1A1F2B',
    level2: '#1F2533',
    level3: '#242B3A',
    level4: '#293042',
    level5: '#2D344A',
  },
};

function buildSchemeColors(
  scheme: Scheme,
  base: MD3Theme['colors'],
  surfaces: typeof surfacesLight,
  errorColor: string,
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
    error: errorColor,
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

// Extend MD3 colors with semantic palettes — success, AI accent, danger.
// `danger` lives alongside MD3 `error` so callers can pick the
// readability-tuned hue (FAB Decline, drawer Reset, destructive dialog
// actions) without overriding the MD3 form-validation `error` color.
type AppColors = MD3Theme['colors'] & {
  success: string;
  onSuccess: string;
  successContainer: string;
  onSuccessContainer: string;
  danger: string;
  onDanger: string;
  aiPrimary: string;
  onAiPrimary: string;
};

export type AppTheme = Omit<MD3Theme, 'colors'> & { colors: AppColors };

export const paperLightTheme: AppTheme = {
  ...MD3LightTheme,
  colors: {
    ...buildSchemeColors(matTheme.schemes.light, MD3LightTheme.colors, surfacesLight, callRed),
    ...accentsLight,
    ...successLight,
    danger: callRed,
    onDanger: '#FFFFFF',
    aiPrimary: aiPrimaryLight,
    onAiPrimary: '#FFFFFF',
  },
};

export const paperDarkTheme: AppTheme = {
  ...MD3DarkTheme,
  colors: {
    ...buildSchemeColors(matTheme.schemes.dark, MD3DarkTheme.colors, surfacesDark, callRedDark),
    ...accentsDark,
    ...successDark,
    danger: callRedDark,
    onDanger: '#1A1A1A',
    aiPrimary: aiPrimaryDark,
    onAiPrimary: '#FFFFFF',
  },
};
