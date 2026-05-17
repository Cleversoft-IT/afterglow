---
name: feedback-drawer-window-confirm
description: Inside an expo-router Drawer entry, never use window.confirm — it races with the drawer auto-close and the button gets stuck on "in progress…". Use a Paper `<Portal><Dialog>` driven by state instead.
metadata:
  type: feedback
---

When a `DrawerItem` handler does `await ...` after a `window.confirm(...)`,
the drawer often auto-closes on the press, the modal dialog steals focus,
and the async continuation never reaches its post-await side effect (e.g.
the `window.location.reload()` after `api.resetDemo()`). Visually the
label stays on its "in progress" string forever, because `setBusy(false)`
is only called in the catch branch and the await neither resolves nor
rejects.

**Why:** observed bug in `afterglow/app/app/(drawer)/_layout.tsx` — "Reset
demo" stayed on "Resetting…" while the identical flow in
`afterglow/app/app/(drawer)/settings.tsx` (which uses a Paper Dialog)
worked. Fixed in commit `d155c52` by reusing the Settings dialog pattern.

**How to apply:** for any destructive or async action triggered from a
DrawerItem, drive the confirmation through `<Portal><Dialog ...></Portal>`
with a boolean state flag, the same pattern Settings already uses. Keep
the two paths byte-identical so the UX never diverges. This is portable
across web/native too — `window.confirm` is web-only and was already
paired with an `Alert.alert` fallback.
