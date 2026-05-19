import type { ThemePreference } from './themePreference';

const STORAGE_KEY = 'afterglow.theme_mode';

let memoryPref: ThemePreference | null = null;

export function readStoredThemePreference(): ThemePreference | null {
  if (memoryPref) return memoryPref;
  try {
    if (typeof localStorage === 'undefined') return null;
    const value = localStorage.getItem(STORAGE_KEY);
    if (value === 'auto' || value === 'light' || value === 'dark') return value;
  } catch {
    /* private mode / unavailable storage */
  }
  return null;
}

export function readInitialThemePreference(): ThemePreference {
  return readStoredThemePreference() ?? 'auto';
}

export function writeStoredThemePreference(pref: ThemePreference): void {
  memoryPref = pref;
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, pref);
    }
  } catch {
    /* ignore */
  }
}
