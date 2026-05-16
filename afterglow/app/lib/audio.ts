// Static require() map for the six demo audios (three domains × two caller
// modes). Metro only bundles literal require() calls — a dynamic
// require(`./..${name}.mp3`) would silently break the static web export.

import { Asset } from 'expo-asset';

export type CallerMode = 'existing' | 'new';

// Bundled demo recordings, one per (domain, callerMode). Existing-mode
// recordings target a seeded customer (Mark / Laura / Andrew) and skip the
// caller's self-introduction; new-mode recordings are first-time callers
// (Hannah / Sophie / Daniel) who introduce themselves from scratch.
export const audioByDomain = {
  restaurant: {
    existing: require('../assets/audio/restaurant_existing.mp3'),
    new: require('../assets/audio/restaurant_new.mp3'),
  },
  dentist: {
    existing: require('../assets/audio/dentist_existing.mp3'),
    new: require('../assets/audio/dentist_new.mp3'),
  },
  bodyshop: {
    existing: require('../assets/audio/bodyshop_existing.mp3'),
    new: require('../assets/audio/bodyshop_new.mp3'),
  },
} as const;

// Synthetic Bell-style ringer: 1300/1700 Hz warble alternated at 20 Hz,
// 2s on / 4s off (6s loop). Sounds like a classic electromechanical phone
// ring on the *called* side — not a ringback tone.
export const ringtoneAsset = require('../assets/audio/ringtone.mp3');

export type AudioDomain = keyof typeof audioByDomain;

// Flat cache key used by usePhoneAudio so its `playCallAudio` / `prefetchUrl`
// keep a single-string signature (custom templates use `${template.id}_${mode}`).
export function bundledAudioKey(domain: AudioDomain, mode: CallerMode): string {
  return `${domain}_${mode}`;
}

async function resolveAssetUri(mod: number): Promise<string> {
  const asset = Asset.fromModule(mod);
  await asset.downloadAsync();
  return asset.localUri ?? asset.uri;
}

export async function resolveAudioUri(
  domain: AudioDomain,
  mode: CallerMode,
): Promise<string> {
  return resolveAssetUri(audioByDomain[domain][mode]);
}

export async function resolveRingtoneUri(): Promise<string> {
  return resolveAssetUri(ringtoneAsset);
}

export async function resolveAudioBlob(
  domain: AudioDomain,
  mode: CallerMode,
): Promise<Blob> {
  const uri = await resolveAudioUri(domain, mode);
  const res = await fetch(uri);
  return await res.blob();
}
