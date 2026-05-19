import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { useColorScheme } from 'react-native';
import type { ThemeMode, ThemePreference } from './themePreference';
import { readInitialThemePreference, writeStoredThemePreference } from './themeStorage';

type ThemeContextValue = {
  mode: ThemePreference;          // user-facing preference (auto/light/dark)
  resolvedMode: ThemeMode;        // concrete mode actually rendered (light/dark)
  setMode: (mode: ThemePreference) => void;
  isDark: boolean;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemePreference>(readInitialThemePreference);
  const systemScheme = useColorScheme(); // 'light' | 'dark' | null

  const resolvedMode: ThemeMode = mode === 'auto'
    ? (systemScheme === 'dark' ? 'dark' : 'light')
    : mode;

  const setMode = useCallback((next: ThemePreference) => {
    setModeState(next);
    writeStoredThemePreference(next);
  }, []);

  const value = useMemo(
    () => ({
      mode,
      resolvedMode,
      setMode,
      isDark: resolvedMode === 'dark',
    }),
    [mode, resolvedMode, setMode],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useThemePreference(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useThemePreference must be used within ThemeProvider');
  }
  return ctx;
}
