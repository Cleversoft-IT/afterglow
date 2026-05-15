// Static require() map for the three demo audios. Metro only bundles literal
// require() calls — a dynamic require(`./..${name}.mp3`) would silently break
// the static web export.

import { Asset } from 'expo-asset';

// Placeholder bundled assets. Replace these .mp3 files with the real demo
// recordings without touching the rest of the codebase.
export const audioByDomain = {
  restaurant: require('../assets/audio/restaurant.mp3'),
  dentist: require('../assets/audio/dentist.mp3'),
  bodyshop: require('../assets/audio/bodyshop.mp3'),
} as const;

export type AudioDomain = keyof typeof audioByDomain;

export async function resolveAudioBlob(domain: AudioDomain): Promise<Blob> {
  const asset = Asset.fromModule(audioByDomain[domain]);
  await asset.downloadAsync();
  const uri = asset.localUri ?? asset.uri;
  const res = await fetch(uri);
  return await res.blob();
}
