import {
  argbFromHex,
  hexFromArgb,
  themeFromSourceColor,
  type Scheme,
} from '@material/material-color-utilities';
import { MD3LightTheme, MD3DarkTheme, type MD3Theme } from 'react-native-paper';

const BRAND_SEED = '#3b82f6';

function buildSchemeColors(scheme: Scheme, base: MD3Theme['colors']): MD3Theme['colors'] {
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
    background: hexFromArgb(scheme.background),
    onBackground: hexFromArgb(scheme.onBackground),
    surface: hexFromArgb(scheme.surface),
    onSurface: hexFromArgb(scheme.onSurface),
    surfaceVariant: hexFromArgb(scheme.surfaceVariant),
    onSurfaceVariant: hexFromArgb(scheme.onSurfaceVariant),
    outline: hexFromArgb(scheme.outline),
    outlineVariant: hexFromArgb(scheme.outlineVariant),
    inverseSurface: hexFromArgb(scheme.inverseSurface),
    inverseOnSurface: hexFromArgb(scheme.inverseOnSurface),
    inversePrimary: hexFromArgb(scheme.inversePrimary),
  };
}

const matTheme = themeFromSourceColor(argbFromHex(BRAND_SEED));

export const paperLightTheme: MD3Theme = {
  ...MD3LightTheme,
  colors: buildSchemeColors(matTheme.schemes.light, MD3LightTheme.colors),
};

export const paperDarkTheme: MD3Theme = {
  ...MD3DarkTheme,
  colors: buildSchemeColors(matTheme.schemes.dark, MD3DarkTheme.colors),
};

export const callGreen = '#26B31E';
export const callRed = '#B3261E';
