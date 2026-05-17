---
name: feedback-web-first-paint
description: Theme flash on Expo web cold load can only be minimized from JS (module-level effect), not eliminated. Don't promise "pre-paint" in commit messages or comments — that requires a custom Expo HTML template (`app.json` `web.template` or `web/index.html`), currently out of scope.
metadata:
  type: feedback
---

**Why:** the `_layout.tsx` module-level block that reads
`readStoredThemePreference()` + `prefers-color-scheme` and stamps
`document.documentElement.style.colorScheme` runs at bundle parse — after
the HTML is already painted with the browser default white background.
It minimizes the runtime flash on theme flip but cannot remove the cold-
load flash.

**How to apply:**
- The honest framing is "earliest possible from JS" / "minimizes the
  flash". Never claim "pre-paint" without also shipping a custom
  `web/index.html` that inlines the color-scheme detection inside a
  `<script>` in `<head>`.
- If a future bug report demands true pre-paint, scope it as: customize
  Expo's HTML template (`app.json` `web.output` / `expo.web.template`)
  and inline the localStorage read + matchMedia + style assignment in
  `<head>`. That's a separate piece of work — don't tack it onto a
  theme cleanup commit.
- The `useColorScheme()` hook can return `null` (the React Native docs
  warn about this when `Appearance` is unavailable). `ThemeContext`
  handles it by falling back to `light` when `mode === 'auto'`. Don't
  assume it's always `'light' | 'dark'`.
