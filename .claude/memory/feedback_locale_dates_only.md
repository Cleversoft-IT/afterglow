---
name: feedback-locale-dates-only
description: The Settings → Format toggle (IT/EN) is for date/time formats ONLY — not for UI string i18n. UI strings stay English per feedback-code-language. Only `app/lib/dateFormat.ts` consumers (date sections, relative times, call detail header, booking badge slot) react to the locale.
metadata:
  type: feedback
---

**Why:** the hackathon demo is single-tenant Italian-market positioning,
but the codebase is required to be English-first (see
[[feedback-code-language]]). Mixing a locale toggle for strings would
violate the "English code/seed/UI" invariant and the demo MP3s ship in
English regardless. The pragmatic split is: dates and times localize
(operators care about `DD/MM/YYYY HH:mm` vs `MM/DD/YYYY h:mm a`),
strings stay English.

**How to apply:**
- When you add a new screen that shows a date or time, route it through
  `app/lib/dateFormat.ts` (`formatDate`, `formatDateTime`,
  `formatDayMonth`, `formatTime`, `formatRelativeTime`, `relativeDay`)
  and read the locale via `useLocale()` from `app/lib/LocaleContext.tsx`.
  Never call `new Date(...).toLocaleString()` directly: it does not
  honor the user's chosen locale (it follows the browser).
- When you add a new UI string, leave it in English. Do **not** add an
  `it` translation behind the same flag — that would be feature creep
  and conflicts with the seed-data-English rule.
- `Intl.DateTimeFormat` is the underlying API. Don't pull a dates
  library (date-fns, dayjs); `dateFormat.ts` caches one
  `Intl.DateTimeFormat` per `(locale, options)` pair to avoid the
  per-render allocation cost.
