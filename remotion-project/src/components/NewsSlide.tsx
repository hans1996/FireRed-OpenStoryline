/**
 * NewsSlide — renders a single news item card with animations.
 * Uses spring() and interpolate() from remotion (no CSS transitions).
 */
import React from 'react';
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig, interpolate } from 'remotion';

export type NewsItem = {
  title: string;
  subtitle: string;
  bgGradient: [string, string, string];
  index: number;
  total: number;
};

export const NewsSlide: React.FC<{ item: NewsItem }> = ({ item }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOpacity = spring({ frame, fps, durationInFrames: 20, config: { damping: 200 } });
  const titleY = interpolate(frame, [0, 20], [30, 0], { extrapolateRight: 'clamp' });

  const charsPerFrame = 0.8;
  const titleReveal = Math.min(frame * charsPerFrame, item.title.length);
  const displayTitle = item.title.slice(0, Math.floor(titleReveal));

  const subtitleDelay = 12;
  const subtitleOpacity = spring({
    frame: frame - subtitleDelay,
    fps,
    durationInFrames: 15,
    config: { damping: 200 },
  });

  const bar1 = spring({ frame: frame - 18, fps, durationInFrames: 15, config: { damping: 200 } });
  const bar2 = spring({ frame: frame - 26, fps, durationInFrames: 15, config: { damping: 200 } });
  const bar3 = spring({ frame: frame - 34, fps, durationInFrames: 15, config: { damping: 200 } });

  const lineDelay = 25;
  const lineWidth = interpolate(frame, [lineDelay, lineDelay + 15], [0, 80], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Use rgba for alpha (JSX doesn't support CSS #hex88 in string templates with esbuild)
  const accentOpacity = ' rgba(96, 165, 250, 0.53)';

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, ${item.bgGradient[0]}, ${item.bgGradient[1]} 50%, ${item.bgGradient[2]})`,
        overflow: 'hidden',
      }}
    >
      <AbsoluteFill style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, rgba(255,255,255,0.025) 1px, transparent 0)', backgroundSize: '40px 40px', pointerEvents: 'none' }} />

      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 4, background: `linear-gradient(90deg, ${item.bgGradient[0]}, #60a5fa, ${item.bgGradient[2]})` }} />

      <div style={{ position: 'absolute', top: 32, left: 48, fontSize: 14, color: '#94a3b8', letterSpacing: 3, fontFamily: 'monospace' }}>
        {String(item.index).padStart(2, '0')} / {String(item.total).padStart(2, '0')}
      </div>

      <div style={{ position: 'absolute', top: '50%', left: '8%', transform: 'translateY(-50%)', maxWidth: '52%' }}>
        <h1 style={{ fontSize: 40, fontWeight: 800, color: '#fff', lineHeight: 1.25, margin: 0, marginBottom: 16, textShadow: '0 2px 20px rgba(0,0,0,0.3)', opacity: titleOpacity, transform: `translateY(${titleY}px)` }}>
          {displayTitle}
          {Math.floor(titleReveal) < item.title.length && <span style={{ opacity: 0.5 }}>|</span>}
        </h1>
        <div style={{ fontSize: 20, color: '#cbd5e1', lineHeight: 1.5, opacity: subtitleOpacity }}>
          {item.subtitle}
        </div>
        <div style={{ marginTop: 16, width: `${lineWidth}%`, maxWidth: 80, height: 2, background: 'linear-gradient(90deg, #60a5fa, transparent)' }} />
      </div>

      <div style={{ position: 'absolute', right: '10%', top: '28%', bottom: '28%', width: 240, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 14 }}>
        <div style={{ height: `${bar1 * 36 + 6}px`, background: `linear-gradient(90deg, ${item.bgGradient[0]}aa, ${item.bgGradient[1]}66, transparent)`, borderRadius: 4 }} />
        <div style={{ height: `${bar2 * 28 + 6}px`, background: `linear-gradient(90deg, ${item.bgGradient[1]}88, ${item.bgGradient[2]}55, transparent)`, borderRadius: 4 }} />
        <div style={{ height: `${bar3 * 20 + 6}px`, background: `linear-gradient(90deg, ${item.bgGradient[2]}77, transparent, transparent)`, borderRadius: 4 }} />
        <div style={{ height: 3, width: 100, background: 'linear-gradient(90deg, #60a5fa, transparent)', marginTop: 8, borderRadius: 2 }} />
      </div>
    </AbsoluteFill>
  );
};
