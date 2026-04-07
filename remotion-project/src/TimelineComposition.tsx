/**
 * TimelineComposition — renders an OpenStoryline timeline as animated video.
 * Media files should be in remotion-project/public/ (Relative path like assets/x.png).
 */
import React, { useMemo } from 'react';
import {
  AbsoluteFill,
  Sequence,
  Img,
  OffthreadVideo,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  spring,
} from 'remotion';
import {
  TimelineData,
  timelineToRemotionProps,
} from './timeline_schema';

// ============================================================================
// MediaClip — renders image or video with transitions
// ============================================================================

const MediaClip: React.FC<{
  item: {
    media_type: string;
    path: string;
    durationFrames: number;
    transitionFrames: number;
    transition: string;
    caption: string;
  };
}> = ({ item }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const cf = Math.floor(frame);
  const tf = Math.max(1, item.transitionFrames);
  const dur = item.durationFrames;
  const t = item.transition || 'fade';

  const style = useMemo(() => {
    let opacity = 1, scale = 1, translateX = 0, translateY = 0;
    const isEntering = cf < tf;
    const isLeaving = cf > dur - tf;

    if (isEntering && t !== 'none') {
      const p = Math.min(cf / tf, 1);
      const e = spring({ frame: Math.min(Math.max(cf, 0), tf), fps, durationInFrames: tf });
      if (t === 'fade') opacity = e;
      else if (t === 'slide-left') translateX = interpolate(p, [0, 1], [-width*0.4, 0]);
      else if (t === 'slide-right') translateX = interpolate(p, [0, 1], [width*0.4, 0]);
      else if (t === 'slide-up') translateY = interpolate(p, [0, 1], [-height*0.4, 0]);
      else if (t === 'slide-down') translateY = interpolate(p, [0, 1], [height*0.4, 0]);
      else if (t === 'zoom-in') scale = interpolate(e, [0, 1], [0.5, 1]);
      else if (t === 'zoom-out') scale = interpolate(e, [0, 1], [1.5, 1]);
    } else if (isLeaving && t !== 'none') {
      const d = dur - cf;
      const p = Math.max(0, (tf - d) / tf);
      const e = spring({ frame: Math.min(Math.max(Math.floor(d), 0), tf), fps, durationInFrames: tf, reverse: true });
      if (t === 'fade') opacity = e;
      else if (t === 'slide-left') translateX = interpolate(p, [0, 1], [0, width*0.4]);
      else if (t === 'slide-right') translateX = interpolate(p, [0, 1], [0, -width*0.4]);
      else if (t === 'slide-up') translateY = interpolate(p, [0, 1], [0, height*0.4]);
      else if (t === 'slide-down') translateY = interpolate(p, [0, 1], [0, -height*0.4]);
      else if (t === 'zoom-in') scale = interpolate(e, [0, 1], [1, 1.5]);
      else if (t === 'zoom-out') scale = interpolate(e, [0, 1], [1, 0.5]);
    }
    return {
      opacity,
      transform: `translate(${translateX}px, ${translateY}px) scale(${scale})`,
    } as React.CSSProperties;
  }, [frame, item, fps, width, height]);

  if (item.media_type === 'image') {
    return (
      <AbsoluteFill style={style}>
        <Img src={item.path} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
      </AbsoluteFill>
    );
  }
  if (item.media_type === 'video') {
    return (
      <AbsoluteFill style={style}>
        <OffthreadVideo src={item.path} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
      </AbsoluteFill>
    );
  }
  return null;
};

// ============================================================================
// SubtitleText
// ============================================================================

const SubtitleText: React.FC<{
  text: string; startFrame: number; endFrame: number;
  fontSize?: number; fontColor?: number[];
}> = ({ text, startFrame, endFrame, fontSize = 40, fontColor = [255,255,255] }) => {
  const cf = Math.floor(useCurrentFrame());
  if (cf < startFrame || cf > endFrame) return null;

  const fi = 5, fo = 5;
  let opacity = 1;
  if (cf < startFrame + fi) opacity = spring({ frame: Math.max(0, cf - startFrame), fps: 25, durationInFrames: fi });
  else if (cf > endFrame - fo) opacity = spring({ frame: Math.max(0, endFrame - cf), fps: 25, durationInFrames: fo, reverse: true });

  return (
    <div style={{
      position: 'absolute', bottom: 60, left: '50%', transform: 'translateX(-50%)',
      fontSize: `${fontSize}px`, color: `rgb(${fontColor.join(',')})`,
      fontWeight: 'bold', textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
      opacity, textAlign: 'center', maxWidth: '90%', lineHeight: 1.5,
      padding: '10px 24px', backgroundColor: 'rgba(0,0,0,0.45)', borderRadius: '8px',
    }}>
      {text}
    </div>
  );
};

// ============================================================================
// Main Composition
// ============================================================================

export const TimelineComposition: React.FC<{ timelineData: TimelineData | null }> = ({ timelineData }) => {
  if (!timelineData) {
    return (
      <AbsoluteFill style={{ backgroundColor: '#000', justifyContent: 'center', alignItems: 'center' }}>
        <div style={{ color: '#fff', fontSize: 48 }}>No timeline data provided</div>
      </AbsoluteFill>
    );
  }

  const props = timelineToRemotionProps(timelineData);
  const bgColor = `rgb(${props.style.bg_color.join(',')})`;

  return (
    <AbsoluteFill style={{ backgroundColor: bgColor }}>
      {/* Header */}
      <div style={{
        position: 'absolute', top: 20, left: 0, right: 0, textAlign: 'center',
        fontSize: 26, fontWeight: 'bold', color: '#fff',
        textShadow: '0 0 10px rgba(0,0,0,0.5)',
        letterSpacing: 2, padding: '12px 40px',
        backgroundColor: 'rgba(0,0,0,0.35)', borderRadius: '0 0 14px 14px',
        display: 'block', zIndex: 10,
      }}>
        本週 AI 新聞快訊
      </div>

      {props.sequences.map((item, idx) => {
        // Title overlay per slide
        return (
          <Sequence
            key={item.media_id + '-' + idx}
            from={item.fromFrame}
            durationInFrames={item.durationFrames}
            name={`clip-${item.media_id}`}
          >
            <MediaClip item={item} />
            {/* Slide number & title badge */}
            <div style={{
              position: 'absolute', top: 80, left: 40,
              fontSize: 22, fontWeight: 'bold', color: '#fff',
              textShadow: '1px 1px 3px rgba(0,0,0,0.6)',
              display: 'block', width: '80%',
            }}>
              【{idx + 1}】{item.caption || ''}
            </div>
          </Sequence>
        );
      })}

      {props.subtitles.map(sub => (
        <SubtitleText
          key={sub.unit_id}
          text={sub.text}
          startFrame={sub.startFrame}
          endFrame={sub.endFrame}
          fontSize={props.style.font_size}
          fontColor={props.style.font_color}
        />
      ))}
    </AbsoluteFill>
  );
};
