// Static require() map for the three demo audios. Metro only bundles literal
// require() calls — a dynamic require(`./..${name}.mp3`) would silently break
// the static web export.

import { Asset } from 'expo-asset';

// Bundled demo recordings, one per business domain.
export const audioByDomain = {
  restaurant: require('../assets/audio/restaurant.mp3'),
  dentist: require('../assets/audio/dentist.mp3'),
  bodyshop: require('../assets/audio/bodyshop.mp3'),
} as const;

// Synthetic Bell-style ringer: 1300/1700 Hz warble alternated at 20 Hz,
// 2s on / 4s off (6s loop). Sounds like a classic electromechanical phone
// ring on the *called* side — not a ringback tone.
export const ringtoneAsset = require('../assets/audio/ringtone.mp3');

export type AudioDomain = keyof typeof audioByDomain;

async function resolveAssetUri(mod: number): Promise<string> {
  const asset = Asset.fromModule(mod);
  await asset.downloadAsync();
  return asset.localUri ?? asset.uri;
}

export async function resolveAudioUri(domain: AudioDomain): Promise<string> {
  return resolveAssetUri(audioByDomain[domain]);
}

export async function resolveRingtoneUri(): Promise<string> {
  return resolveAssetUri(ringtoneAsset);
}

export async function resolveAudioBlob(domain: AudioDomain): Promise<Blob> {
  const uri = await resolveAudioUri(domain);
  const res = await fetch(uri);
  return await res.blob();
}
