import type { ThemeMode } from './theme';

const STORAGE_KEY = 'afterglow.theme_mode';

let memoryMode: ThemeMode | null = null;

export function readStoredThemeMode(): ThemeMode | null {
  if (memoryMode) return memoryMode;
  try {
    if (typeof localStorage === 'undefined') return null;
    const value = localStorage.getItem(STORAGE_KEY);
    if (value === 'light' || value === 'dark') return value;
  } catch {
    /* private mode / unavailable storage */
  }
  return null;
}

export function readInitialThemeMode(): ThemeMode {
  return readStoredThemeMode() ?? 'dark';
}

export function writeStoredThemeMode(mode: ThemeMode): void {
  memoryMode = mode;
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, mode);
    }
  } catch {
    /* ignore */
  }
}
