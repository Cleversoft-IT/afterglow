import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import {
  getColors,
  getShadows,
  type ColorPalette,
  type ShadowPalette,
  type ThemeMode,
} from './theme';
import { readInitialThemeMode, writeStoredThemeMode } from './themeStorage';

type ThemeContextValue = {
  mode: ThemeMode;
  colors: ColorPalette;
  shadows: ShadowPalette;
  setMode: (mode: ThemeMode) => void;
  isDark: boolean;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(readInitialThemeMode);

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next);
    writeStoredThemeMode(next);
  }, []);

  const colors = useMemo(() => getColors(mode), [mode]);
  const shadows = useMemo(() => getShadows(mode), [mode]);

  const value = useMemo(
    () => ({
      mode,
      colors,
      shadows,
      setMode,
      isDark: mode === 'dark',
    }),
    [mode, colors, shadows, setMode],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return ctx;
}
