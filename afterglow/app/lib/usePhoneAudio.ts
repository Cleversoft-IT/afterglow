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
import { resolveAudioUri, resolveRingtoneUri, type AudioDomain } from './audio';

const isWeb = Platform.OS === 'web';

export type PhoneAudio = {
  prefetch: (domain: AudioDomain) => Promise<void>;
  playRingtone: () => void;
  stopRinging: () => void;
  playCallAudio: (domain: AudioDomain, onEnded: () => void, onError: (err: Error) => void) => void;
  getCallBlob: () => Blob | null;
  stopAll: () => void;
};

export function usePhoneAudio(): PhoneAudio {
  const ringtoneRef = useRef<HTMLAudioElement | null>(null);
  const callRef = useRef<HTMLAudioElement | null>(null);
  const callBlobRef = useRef<Blob | null>(null);
  const ringtoneUriRef = useRef<string | null>(null);
  const callUriByDomainRef = useRef<Partial<Record<AudioDomain, string>>>({});

  const prefetch = useCallback(async (domain: AudioDomain) => {
    if (!isWeb) return;
    if (!ringtoneUriRef.current) {
      ringtoneUriRef.current = await resolveRingtoneUri();
    }
    if (!callUriByDomainRef.current[domain]) {
      const uri = await resolveAudioUri(domain);
      callUriByDomainRef.current[domain] = uri;
      // Warm the blob cache too, so the post-call upload doesn't pay a second
      // network roundtrip after the recording finishes playing.
      try {
        const res = await fetch(uri);
        callBlobRef.current = await res.blob();
      } catch {
        // Non-fatal: upload path will retry the fetch.
      }
    }
  }, []);

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
    (domain: AudioDomain, onEnded: () => void, onError: (err: Error) => void) => {
      if (!isWeb) {
        onEnded();
        return;
      }
      const uri = callUriByDomainRef.current[domain];
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
      el.play().catch((err) => onError(err instanceof Error ? err : new Error(String(err))));
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

  useEffect(() => () => stopAll(), [stopAll]);

  // Memoize the returned object so consumers can list it as an effect dep
  // without retriggering on every render. All members are stable useCallback
  // refs anyway.
  return useMemo(
    () => ({ prefetch, playRingtone, stopRinging, playCallAudio, getCallBlob, stopAll }),
    [prefetch, playRingtone, stopRinging, playCallAudio, getCallBlob, stopAll],
  );
}
