---
name: feedback-mock-avatars-hardcoded
description: Mock phonebook avatars must be hard-coded URLs from a deterministic source (today: `randomuser.me/api/portraits/{women,men}/N.jpg`). Generative styles (DiceBear avataaars/personas) seed-RNG can land on masculine eyebrows for "Amelia" — gender ambiguity makes the demo look careless.
metadata:
  type: feedback
---

**Why:** during the round-3 audit a user spotted that Amelia Brooks
rendered as a bearded man with `dicebear/avataaars`, despite a `top=`
filter constrained to long-hair options and `facialHairProbability=0`.
The seed-RNG controls eyebrows/clothing/mouth independently and the
result for some seeds reads masculine regardless of the hair. The user
asked to skip the gender randomization entirely and pick photos by
hand. The fix:

```ts
// app/lib/mockContacts.ts
const W = (n: number) => `https://randomuser.me/api/portraits/women/${n}.jpg`;
const M = (n: number) => `https://randomuser.me/api/portraits/men/${n}.jpg`;
// then per contact:
{ id: 'pc_001', display_name: 'Amelia Brooks', ..., avatar_url: W(12) },
{ id: 'pc_004', display_name: 'Daniel Edwards', ..., avatar_url: M(32) },
```

`randomuser.me` serves a fixed pool of real-photo portraits with
explicit `/women/` and `/men/` paths — the gender is in the URL, no
ambiguity possible.

**How to apply:**
- When adding a mock contact, pick a `W(n)` or `M(n)` URL by hand to
  match the name. Roughly half the contacts keep no `avatar_url` so the
  colored-initials fallback stays visible in the demo.
- `ContactAvatar` already has `onError → fallback to initials` for the
  case where the network is blocked (CSP / offline), so the URL choice
  doesn't have to be bulletproof — but it does have to be gendered
  correctly.
- **Do not** reintroduce DiceBear / Boring Avatars / any other
  generative service unless you can constrain the output enough to
  guarantee the gender. Hard-coded URLs are the simpler answer for a
  demo asset set this small.
