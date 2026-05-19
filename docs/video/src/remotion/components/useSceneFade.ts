import { useCurrentFrame, interpolate, Easing } from 'remotion';

/**
 * Restituisce l'opacità della scena con fade-in e fade-out automatici.
 * @param durationInFrames durata totale della scena (da SCENES.xxx.duration)
 * @param fadeInFrames     frame del fade-in iniziale (default 20)
 * @param fadeOutFrames    frame del fade-out finale (default 30)
 */
export function useSceneFade(
  durationInFrames: number,
  fadeInFrames = 20,
  fadeOutFrames = 30,
): number {
  const frame = useCurrentFrame();

  const fadeIn = interpolate(frame, [0, fadeInFrames], [0, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.4, 0, 0.2, 1),
  });

  const fadeOut = fadeOutFrames > 0
    ? interpolate(
        frame,
        [durationInFrames - fadeOutFrames, durationInFrames],
        [1, 0],
        {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
          easing: Easing.bezier(0.4, 0, 0.2, 1),
        },
      )
    : 1;

  return Math.min(fadeIn, fadeOut);
}
