---
name: feedback-web-first-paint
description: On Expo web with `web.output: "static"`, any first-render state that depends on `localStorage` / `matchMedia` must be hydration-guarded — the static HTML is built without browser APIs, so a raw `useState(readLocalStorage())` diverges between the prerender and the client and triggers React error #418. Pair the module-level theme sync (early DOM paint) with a hydration guard inside the layout (correct React state).
metadata:
  type: feedback
---

**Why:** Expo Router's web export prerenders every route to HTML at build
time. The build runs in Node with no `localStorage`, no `matchMedia`, no
`window` — anything that reads them returns the "default" branch. At
runtime the client may resolve to a different value (dark theme stored,
demo session already minted), so React's hydration pass sees a divergent
first render and logs the minified error #418.

Two cooperating fixes both belong in `app/app/_layout.tsx`:

1. The module-level block at file top reads `readStoredThemePreference()`
   + `prefers-color-scheme` and stamps `document.documentElement.style`
   directly. That paints the browser chrome **before** React mounts.
   It only touches DOM nodes React doesn't own (`<html>`, `<body>`) —
   it cannot fix the JSX divergence on its own.
2. Inside `RootLayoutInner` a `const [hydrated, setHydrated] = useState(false)`
   + `useEffect(() => setHydrated(true), [])` guards every value that
   could diverge. The first client render uses build-time defaults
   (`isDark=false`, `gateChecked=true`); the post-mount effect flips to
   the real values. Costs one re-render frame; eliminates #418.

**How to apply:**
- Any new `useState(initialValue)` whose `initialValue` reads `localStorage`,
  `sessionStorage`, `window.*`, `navigator.*`, or `Date.now()` in the root
  layout must be gated through `hydrated`. Pattern:
  `const value = hydrated ? realValue : buildTimeDefault`.
- The honest framing of the module-level theme sync stays "earliest
  possible from JS" / "minimizes the flash". Never claim "pre-paint"
  without also shipping a custom `web/index.html` that inlines the
  color-scheme detection inside a `<script>` in `<head>`. That custom
  template is still out of scope for the hackathon.
- The `useColorScheme()` hook can return `null` (the React Native docs
  warn about this when `Appearance` is unavailable). `ThemeContext`
  handles it by falling back to `light` when `mode === 'auto'`. Don't
  assume it's always `'light' | 'dark'`.
- If you ever switch `app.json` `web.output` from `"static"` to `"single"`,
  the hydration guard becomes a no-op (no prerendered HTML to mismatch),
  but leave it in place — `"static"` is the better cold-load and we will
  probably keep it.
