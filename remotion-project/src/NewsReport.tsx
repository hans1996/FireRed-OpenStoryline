/**
 * Main NewsReport composition.
 * Uses Series for sequential slides with @remotion/transitions.
 */
import React from 'react';
import {
  AbsoluteFill,
  Sequence,
  Series,
  useVideoConfig,
  spring,
  interpolate,
  useCurrentFrame,
} from 'remotion';
import { TransitionSeries, linearTiming } from '@remotion/transitions';
import { slide } from '@remotion/transitions/slide';
import { wipe } from '@remotion/transitions/wipe';
import { AnimatedHeader } from './components/AnimatedHeader';
import { NewsSlide } from './components/NewsSlide';

// Timing (30 fps)
const FPS = 30;
const HEADER_SECS = 2.0;
const SLIDE_SECS = 3.5;
const TRANSITION_SECS = 0.5;
const OUTRO_SECS = 1.5;

const headerFrames = Math.ceil(HEADER_SECS * FPS); // 60
const slideFrames = Math.ceil(SLIDE_SECS * FPS); // 105
const transitionFrames = Math.ceil(TRANSITION_SECS * FPS); // 15
const outroFrames = Math.ceil(OUTRO_SECS * FPS); // 45

export function computeTotalDuration(itemsLen: number): number {
  return headerFrames + itemsLen * slideFrames + (itemsLen > 0 ? (itemsLen - 1) * transitionFrames : 0) + outroFrames;
}

// Outro
const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, durationInFrames: 20, config: { damping: 200 } });
  const o = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: 'clamp' });
  return (
    <AbsoluteFill style={{ background: 'linear-gradient(135deg, #0a0f1e, #162032)', justifyContent: 'center', alignItems: 'center' }}>
      <div style={{ opacity: s * o, textAlign: 'center' }}>
        <div style={{ fontSize: 20, color: '#60a5fa', letterSpacing: 4, marginBottom: 8 }}>THANKS FOR WATCHING</div>
        <div style={{ fontSize: 14, color: '#64748b' }}>Powered by FireRed OpenStoryline</div>
      </div>
    </AbsoluteFill>
  );
};

// Props type — matches Root.tsx props
export type NewsItem = { title: string; subtitle: string; bgGradient: [string, string, string] };
export type NewsReportProps = { headerTitle: string; items: NewsItem[] };

export const NewsReport: React.FC<NewsReportProps> = ({ headerTitle, items }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>
      {/* Header */}
      <Sequence durationInFrames={headerFrames}>
        <AnimatedHeader title={headerTitle} />
      </Sequence>

      {/* Slides with transitions */}
      <TransitionSeries style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 }}>
        {items.map((item, i) => {
          const slideStart = headerFrames + i * (slideFrames + transitionFrames);
          const isLast = i === items.length - 1;
          const trans = i % 3 === 0 ? undefined : isLast ? undefined : slide({ direction: 'from-left' });
          return (
            <React.Fragment key={i}>
              <TransitionSeries.Sequence durationInFrames={slideFrames + (isLast ? 0 : transitionFrames)}>
                <NewsSlide item={{ index: i + 1, total: items.length, ...item }} />
              </TransitionSeries.Sequence>
              {!isLast && (
                <TransitionSeries.Transition
                  presentation={i % 2 === 0 ? slide({ direction: 'from-left' }) : wipe({ direction: 'from-left' })}
                  timing={linearTiming({ durationInFrames: transitionFrames })}
                />
              )}
            </React.Fragment>
          );
        })}
      </TransitionSeries>

      {/* Outro */}
      <Sequence
        from={headerFrames + items.length * slideFrames + (items.length > 0 ? (items.length - 1) * transitionFrames : 0)}
        durationInFrames={outroFrames}
      >
        <OutroScene />
      </Sequence>
    </AbsoluteFill>
  );
};
