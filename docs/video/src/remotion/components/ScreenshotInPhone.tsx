// Mostra uno screenshot reale dell'app dentro una sagoma iPhone.
// L'immagine è sempre completamente visibile (objectFit: contain) col bg dell'app.
import React from 'react';
import { Img, staticFile, interpolate, Easing, useCurrentFrame } from 'remotion';
import { COLORS } from '../data/videoScript';

// Proporzione interna schermo iPhone: altezza / larghezza
// I nostri screenshot sono catturati a viewport 430×932 → ratio 2.167
const SCREEN_RATIO = 932 / 430;

interface ScreenshotInPhoneProps {
  src: string;           // relativo a public/, es. 'screenshots/home-dark.png'
  screenWidth?: number;  // larghezza area schermo in px nel video (default 320)
  delay?: number;
  slideFrom?: 'left' | 'right' | 'bottom' | 'none';
  style?: React.CSSProperties;
}

export const ScreenshotInPhone: React.FC<ScreenshotInPhoneProps> = ({
  src,
  screenWidth = 320,
  delay = 0,
  slideFrom = 'right',
  style,
}) => {
  const frame = useCurrentFrame();
  const f = Math.max(0, frame - delay);

  // Reveal
  const progress = interpolate(f, [0, 45], [0, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const opacity = progress;
  const translateX =
    slideFrom === 'right' ? interpolate(progress, [0, 1], [60, 0]) :
    slideFrom === 'left'  ? interpolate(progress, [0, 1], [-60, 0]) :
    0;
  const translateY =
    slideFrom === 'bottom' ? interpolate(progress, [0, 1], [50, 0]) : 0;
  const scaleAnim = interpolate(progress, [0, 1], [0.95, 1]);

  // Dimensioni derivate dalle proporzioni reali degli screenshot
  const screenH = screenWidth * SCREEN_RATIO;

  // Spessore cornice telefono
  const BORDER = 14;
  const RADIUS_OUTER = 52;
  const RADIUS_INNER = 40;
  const NOTCH_W = Math.round(screenWidth * 0.28);
  const NOTCH_H = 28;

  // Dimensioni totali del frame
  const totalW = screenWidth + BORDER * 2;
  const totalH = screenH + BORDER * 2;

  return (
    <div
      style={{
        opacity,
        transform: `translateX(${translateX}px) translateY(${translateY}px) scale(${scaleAnim})`,
        flexShrink: 0,
        ...style,
      }}
    >
      {/* Corpo esterno del telefono */}
      <div style={{
        width: totalW,
        height: totalH,
        borderRadius: RADIUS_OUTER,
        background: 'linear-gradient(160deg, #2A2F3E 0%, #1A1F2B 50%, #0F1118 100%)',
        boxShadow: `
          0 0 0 1px ${COLORS.border},
          0 50px 100px rgba(0,0,0,0.65),
          0 25px 50px rgba(0,0,0,0.45),
          inset 0 1px 0 rgba(255,255,255,0.07)
        `,
        position: 'relative',
      }}>
        {/* Pulsante power */}
        <div style={{
          position: 'absolute', right: -4, top: 110,
          width: 4, height: 68, borderRadius: 4,
          background: '#2A2F3E',
        }} />
        {/* Volume buttons */}
        {[60, 110, 150].map((top, i) => (
          <div key={i} style={{
            position: 'absolute', left: -4, top,
            width: 4, height: i === 0 ? 40 : 56,
            borderRadius: 4, background: '#2A2F3E',
          }} />
        ))}

        {/* Schermo */}
        <div style={{
          position: 'absolute',
          top: BORDER, left: BORDER,
          width: screenWidth, height: screenH,
          borderRadius: RADIUS_INNER,
          overflow: 'hidden',
          background: COLORS.bg, // fallback bg = bg dell'app
        }}>
          {/* Dynamic island */}
          <div style={{
            position: 'absolute',
            top: 10, left: '50%', transform: 'translateX(-50%)',
            width: NOTCH_W, height: NOTCH_H,
            borderRadius: NOTCH_H / 2,
            background: '#000',
            zIndex: 10,
          }} />

          {/* Screenshot — interamente visibile, nessun taglio */}
          <Img
            src={staticFile(src)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'contain',
              objectPosition: 'top center',
              display: 'block',
              background: COLORS.bg,
            }}
          />
        </div>
      </div>
    </div>
  );
};
