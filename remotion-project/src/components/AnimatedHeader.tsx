/**
 * AnimatedHeader — intro title sequence with spring animation
 */
import React from 'react';
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig, interpolate } from 'remotion';

export const AnimatedHeader: React.FC<{ title: string }> = ({ title }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOpacity = spring({ frame, fps, durationInFrames: 15, config: { damping: 200 } });
  const titleY = interpolate(frame, [0, 15], [40, 0], { extrapolateRight: 'clamp' });

  const subtitleDelay = 10;
  const subtitleOpacity = spring({
    frame: frame - subtitleDelay,
    fps,
    durationInFrames: 15,
    config: { damping: 200 },
  });

  const lineDelay = 20;
  const lineWidth = interpolate(
    frame,
    [lineDelay, lineDelay + 20],
    [0, 300],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  return (
    <AbsoluteFill
      style={{
        background: 'linear-gradient(135deg, #0a0f1e 0%, #162032 50%, #0d1b2a 100%)',
        justifyContent: 'center',
        alignItems: 'center',
        overflow: 'hidden',
      }}
    >
      {/* Grid pattern */}
      <AbsoluteFill
        style={{
          backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.03) 1px, transparent 0)',
          backgroundSize: '36px 36px',
        }}
      />

      {/* Top accent bar */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 4,
          background: 'linear-gradient(90deg, #0a193c, #60a5fa, #0a193c)',
        }}
      />

      <div style={{ opacity: titleOpacity, transform: `translateY(${titleY}px)`, textAlign: 'center' }}>
        <div
          style={{
            fontSize: 16,
            color: '#60a5fa',
            letterSpacing: 6,
            textTransform: 'uppercase',
            marginBottom: 16,
          }}
        >
          WEEKLY ROUNDUP
        </div>
        <div
          style={{
            fontSize: 56,
            fontWeight: 800,
            color: '#ffffff',
            textShadow: '0 0 40px rgba(96, 165, 250, 0.3)',
            lineHeight: 1.2,
          }}
        >
          {title}
        </div>
        <div style={{ width: lineWidth, height: 3, background: 'linear-gradient(90deg, transparent, #60a5fa, transparent)', margin: '20px auto 0' }} />
        <div style={{ opacity: subtitleOpacity, marginTop: 16, fontSize: 16, color: '#94a3b8', letterSpacing: 2 }}>
          TOP 6 STORIES
        </div>
      </div>
    </AbsoluteFill>
  );
};
