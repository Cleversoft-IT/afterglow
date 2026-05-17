// HTML5 Audio wrapper for the incoming-call simulation. Web only — the app
// runs in a browser iframe inside demo-site, so we don't pull in expo-av for
// native targets. On iOS/Android the hook degrades to no-ops.
//
// Browsers require a fresh user activation for each Audio.play(). Any `await`
// between the click event and play() can drop that activation, leaving the
// audio silently paused. To avoid this we prefetch asset URIs ahead of time
// (during the ringing phase) and keep playRingtone / playCallAudio fully
// synchronous on the gesture path.

import { useCallback, useEffect, useMemo, useRef } from 'react';
import { Platform } from 'react-native';
import {
  bundledAudioKey,
  resolveAudioUri,
  resolveRingtoneUri,
  type AudioDomain,
  type CallerMode,
} from './audio';

const isWeb = Platform.OS === 'web';

// Cache keys are flat strings so `playCallAudio` / `prefetchBlob` can stay
// single-arg. For bundled audio the caller composes `${domain}_${mode}` via
// `bundledAudioKey`; for custom templates it composes `${template.id}_${mode}`.
type AudioSourceKey = string;

export type PhoneAudio = {
  prefetch: (domain: AudioDomain, mode: CallerMode) => Promise<void>;
  prefetchBlob: (key: AudioSourceKey, blob: Blob) => void;
  playRingtone: () => void;
  stopRinging: () => void;
  playCallAudio: (key: AudioSourceKey, onEnded: () => void, onError: (err: Error) => void) => void;
  getCallBlob: () => Blob | null;
  stopAll: () => void;
};

export function usePhoneAudio(): PhoneAudio {
  const ringtoneRef = useRef<HTMLAudioElement | null>(null);
  const callRef = useRef<HTMLAudioElement | null>(null);
  const callBlobRef = useRef<Blob | null>(null);
  const ringtoneUriRef = useRef<string | null>(null);
  const callUriByKeyRef = useRef<Record<AudioSourceKey, string>>({});
  // Object URLs we created so we can revoke them on unmount and avoid the
  // browser holding the underlying blob in memory forever.
  const ownedObjectUrlsRef = useRef<string[]>([]);

  const ensureRingtone = useCallback(async () => {
    if (!isWeb) return;
    if (!ringtoneUriRef.current) {
      ringtoneUriRef.current = await resolveRingtoneUri();
    }
  }, []);

  const prefetch = useCallback(async (domain: AudioDomain, mode: CallerMode) => {
    if (!isWeb) return;
    await ensureRingtone();
    const key = bundledAudioKey(domain, mode);
    if (!callUriByKeyRef.current[key]) {
      const uri = await resolveAudioUri(domain, mode);
      callUriByKeyRef.current[key] = uri;
      // Warm the blob cache too, so the post-call upload doesn't pay a second
      // network roundtrip after the recording finishes playing.
      try {
        const res = await fetch(uri);
        callBlobRef.current = await res.blob();
      } catch {
        // Non-fatal: upload path will retry the fetch.
      }
    }
  }, [ensureRingtone]);

  const prefetchBlob = useCallback((key: AudioSourceKey, blob: Blob) => {
    if (!isWeb) return;
    // Ringtone is bundled, so this is a sync call — no await needed.
    void ensureRingtone();
    // Object URL bypasses the no-custom-headers limitation of <audio src=…>:
    // session-scoped backend endpoints (X-Demo-Session) cannot be hit
    // directly by HTMLAudioElement, so the caller fetches the blob through
    // the session-aware client and hands it to us.
    const objectUrl = URL.createObjectURL(blob);
    const previous = callUriByKeyRef.current[key];
    if (previous && previous.startsWith('blob:')) {
      URL.revokeObjectURL(previous);
      const idx = ownedObjectUrlsRef.current.indexOf(previous);
      if (idx >= 0) ownedObjectUrlsRef.current.splice(idx, 1);
    }
    callUriByKeyRef.current[key] = objectUrl;
    ownedObjectUrlsRef.current.push(objectUrl);
    callBlobRef.current = blob;
  }, [ensureRingtone]);

  const stopRinging = useCallback(() => {
    const el = ringtoneRef.current;
    if (!el) return;
    el.pause();
    el.currentTime = 0;
    ringtoneRef.current = null;
  }, []);

  const playRingtone = useCallback(() => {
    if (!isWeb) return;
    stopRinging();
    const uri = ringtoneUriRef.current;
    if (!uri) return;
    const el = new Audio(uri);
    el.loop = true;
    el.volume = 0.6;
    ringtoneRef.current = el;
    el.play().catch(() => {
      // Autoplay can be blocked if no user gesture preceded us. Ringing then
      // remains visual-only — not great, but the call still works.
    });
  }, [stopRinging]);

  const playCallAudio = useCallback(
    (key: AudioSourceKey, onEnded: () => void, onError: (err: Error) => void) => {
      if (!isWeb) {
        onEnded();
        return;
      }
      const uri = callUriByKeyRef.current[key];
      if (!uri) {
        onError(new Error('Call audio not prefetched'));
        return;
      }
      const el = new Audio(uri);
      el.volume = 1;
      callRef.current = el;
      el.addEventListener('ended', onEnded, { once: true });
      el.addEventListener(
        'error',
        () => onError(new Error('Failed to play call audio')),
        { once: true },
      );
      el.play().catch((err) => {
        // Hangup mid-playback rejects play() with AbortError "interrupted by
        // a call to pause()". Treat it as a graceful stop, not an error.
        const message = err?.message ?? '';
        if (err?.name === 'AbortError' || /interrupted by a call to pause/i.test(message)) {
          return;
        }
        onError(err instanceof Error ? err : new Error(String(err)));
      });
    },
    [],
  );

  const getCallBlob = useCallback(() => callBlobRef.current, []);

  const stopAll = useCallback(() => {
    stopRinging();
    const c = callRef.current;
    if (c) {
      c.pause();
      c.currentTime = 0;
      callRef.current = null;
    }
  }, [stopRinging]);

  useEffect(
    () => () => {
      stopAll();
      for (const url of ownedObjectUrlsRef.current) {
        URL.revokeObjectURL(url);
      }
      ownedObjectUrlsRef.current = [];
      callUriByKeyRef.current = {};
    },
    [stopAll],
  );

  // Memoize the returned object so consumers can list it as an effect dep
  // without retriggering on every render. All members are stable useCallback
  // refs anyway.
  return useMemo(
    () => ({ prefetch, prefetchBlob, playRingtone, stopRinging, playCallAudio, getCallBlob, stopAll }),
    [prefetch, prefetchBlob, playRingtone, stopRinging, playCallAudio, getCallBlob, stopAll],
  );
}
