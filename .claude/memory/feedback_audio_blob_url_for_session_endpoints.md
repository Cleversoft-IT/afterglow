---
name: feedback-audio-blob-url-for-session-endpoints
description: Cross-origin <audio>/<img>/<video> elements can't carry custom headers, so session-scoped backend assets must be fetched as a Blob and exposed via URL.createObjectURL().
metadata:
  type: feedback
---

When a backend endpoint requires the `X-Demo-Session` header (or any
custom auth header) and the asset is cross-origin (`app.*` →
`api.*`), **do NOT point a media element at the bare backend URL**.
HTMLAudioElement / HTMLImageElement / HTMLVideoElement cannot set
custom request headers and the cross-origin fetch they issue won't
carry any of the app's session state — the backend will treat the
caller as the production tenant and `visibility_filter_seedable` will
404 any session-owned row. The browser then surfaces the generic
"Failed to load because no supported source was found" message.

**How to apply.** Fetch the bytes through the session-aware client
(`api.ts` `request()` flow) as a `Blob`, then feed the media element
`URL.createObjectURL(blob)`. Track owned object URLs in a ref and
revoke them on unmount so the underlying blob can be GC'd. The
canonical example is `api.fetchSimulationAudio()` +
`usePhoneAudio.prefetchBlob()` (see [[project-afterglow-decisions]]).

**Why.** Discovered while fixing the wizard-built template simulator:
custom templates have `session_id = <demo session uuid>`, so the
session-less `<audio src=URL>` request couldn't see them and the
"blue (AI)" button on the incoming-call screen always errored out
with the unsupported-source message.

**Wrong workarounds to reject.** Don't strip auth from the audio
endpoint just to please the media element — that breaks the demo
session isolation. Don't shove the session uuid into a query param
either — it leaks into server logs and Referer headers.
