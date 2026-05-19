import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

export type ThemeMode = 'auto' | 'light' | 'dark';
export type ResolvedMode = 'light' | 'dark';

const STORAGE_KEY = 'afterglow.demo.theme_mode';
const VALID_MODES: ThemeMode[] = ['auto', 'light', 'dark'];

function readStoredMode(): ThemeMode {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw && (VALID_MODES as string[]).includes(raw)) return raw as ThemeMode;
  } catch {
    /* localStorage unavailable */
  }
  return 'auto';
}

function getSystemMode(): ResolvedMode {
  if (typeof window === 'undefined' || !window.matchMedia) return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function resolve(mode: ThemeMode, system: ResolvedMode): ResolvedMode {
  return mode === 'auto' ? system : mode;
}

function applyClass(resolved: ResolvedMode) {
  const root = document.documentElement;
  root.classList.toggle('dark', resolved === 'dark');
  root.style.colorScheme = resolved;
  // Chrome bug workaround: color-mix(in oklab, var(--X) ...) does not always
  // re-evaluate when --X changes via a class toggle. Force a synchronous reflow
  // by briefly hiding the body so paint re-resolves the var inside color-mix.
  // Without this, opacity-modified utilities like `bg-card/80` keep showing
  // the previous theme's color until the next layout-triggering interaction.
  if (typeof document !== 'undefined' && document.body) {
    const prev = document.body.style.display;
    document.body.style.display = 'none';
    void document.body.offsetHeight;
    document.body.style.display = prev;
  }
}

type ThemeContextValue = {
  mode: ThemeMode;
  resolvedMode: ResolvedMode;
  setMode: (next: ThemeMode) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(() => readStoredMode());
  const [systemMode, setSystemMode] = useState<ResolvedMode>(() => getSystemMode());

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e: MediaQueryListEvent) => setSystemMode(e.matches ? 'dark' : 'light');
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  const resolvedMode = resolve(mode, systemMode);

  useEffect(() => {
    applyClass(resolvedMode);
  }, [resolvedMode]);

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* localStorage unavailable */
    }
  }, []);

  const value = useMemo<ThemeContextValue>(
    () => ({ mode, resolvedMode, setMode }),
    [mode, resolvedMode, setMode],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used inside <ThemeProvider>');
  return ctx;
}
