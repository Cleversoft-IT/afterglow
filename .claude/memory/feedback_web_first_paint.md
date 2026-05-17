---
name: feedback-web-first-paint
description: Afterglow's web build uses `app.json` `web.output: "single"` (SPA shell, no static prerender). Switching to `"static"` is forbidden without first auditing every first-render state — Expo's static prerender runs in Node with no browser APIs, and the SDK 54 + Paper + Drawer stack has multiple subtle divergences (theme, locale, demo session, safe-area insets) that all trip React error #418 at hydration. Keep the module-level theme sync for the cold-load flash and the in-component hydration guard as defensive scaffolding.
metadata:
  type: feedback
---

**Why:** Afterglow's frontend is a dialer SPA — SEO is irrelevant and
the bundle is large enough that a prerendered HTML stub doesn't
meaningfully speed up the first paint. We initially shipped with
`web.output: "static"` (Expo SDK 54 default) and it produced a
**persistent React error #418** ("Hydration failed because the initial
UI does not match what was rendered on the server") that no amount of
in-component guarding fully eliminated. The build runs in Node without
`localStorage`, `matchMedia`, `window`, `navigator`, or layout metrics,
so `ThemeContext`, `LocaleContext`, `SafeAreaProvider` insets, and the
`getActiveTemplate()` gate all resolved differently between the static
HTML and the client first render. Switching to `web.output: "single"`
(2026-05-17) replaced the prerender with a thin HTML shell that boots
the bundle and lets React render normally — no hydration step, no
mismatch.

Two cooperating mechanisms remain in `app/app/_layout.tsx` even after
the `"single"` switch, both defensive and cheap:

1. **Module-level theme sync** (file top, runs at bundle parse before
   React mounts): reads `readStoredThemePreference()` +
   `prefers-color-scheme` and stamps `document.documentElement.style`
   + `document.body.style`. Touches only DOM nodes React doesn't own
   (`<html>`, `<body>`). Minimizes the white-flash between the empty
   HTML shell and the first React paint.
2. **In-component hydration guard** inside `RootLayoutInner`:
   `const [hydrated, setHydrated] = useState(false)` +
   `useEffect(() => setHydrated(true), [])`. Each value that depends on
   browser APIs reads `hydrated ? realValue : buildTimeDefault`. Today
   this is a no-op (no prerender to match against), but it's the
   correct pattern if anyone ever flips `web.output` back to `"static"`,
   so we keep it documented.

**How to apply:**
- **Do not flip `web.output` to `"static"` casually.** The bundle has
  too many context providers reading browser-only state for the
  hydration to come out clean. If a future ticket truly needs SEO,
  scope it as: ship a custom `web/index.html` template that inlines a
  `<script>` populating the theme/locale **before** the bundle parses,
  audit every context for SSR-safe initial values, and only then flip
  the flag.
- Any new `useState(initialValue)` whose `initialValue` reads
  `localStorage`, `sessionStorage`, `window.*`, `navigator.*`, or
  `Date.now()` in the root layout should still be gated through
  `hydrated`. Costs nothing in `"single"` mode; saves the next person
  who experiments with static prerender.
- The honest framing of the module-level theme sync stays "earliest
  possible from JS" / "minimizes the flash". Never claim "pre-paint"
  without also shipping a custom `web/index.html` that inlines the
  color-scheme detection inside a `<script>` in `<head>`. That custom
  template is still out of scope for the hackathon.
- The `useColorScheme()` hook can return `null` (the React Native docs
  warn about this when `Appearance` is unavailable). `ThemeContext`
  handles it by falling back to `light` when `mode === 'auto'`. Don't
  assume it's always `'light' | 'dark'`.
