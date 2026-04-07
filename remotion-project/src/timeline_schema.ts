/**
 * Zod schema for OpenStoryline timeline → Remotion data contract.
 * Python 端產生符合此 schema 的 JSON → Remotion 接收並渲染
 */
import { z } from 'zod';

const SubtitleUnitSchema = z.object({
  unit_id: z.string(),
  index_in_group: z.number(),
  text: z.string(),
  start_ms: z.number().optional().default(0),
  end_ms: z.number().optional().default(0),
});

const TimelineItemSchema = z.object({
  media_id: z.string(),
  media_type: z.enum(['image', 'video']),
  path: z.string(),
  start: z.number(),
  end: z.number(),
  duration: z.number(),
  caption: z.string().default(''),
  transition: z.enum(['fade','slide-left','slide-right','slide-up','slide-down','zoom-in','zoom-out','none']).default('fade'),
  transition_duration: z.number().default(500),
}).passthrough();

const BgmItemSchema = z.object({
  media_id: z.string(),
  path: z.string(),
  volume: z.number().default(0.25),
});

export const TimelineSchema = z.object({
  fps: z.number().default(25),
  width: z.number().default(1920),
  height: z.number().default(1080),
  total_duration: z.number(),
  tracks: z.object({
    video: z.array(TimelineItemSchema).default([]),
    bgm: z.array(BgmItemSchema).default([]),
    voiceover: z.array(z.object({
      media_id: z.string(),
      path: z.string(),
    })).default([]),
  }).default({ video: [], bgm: [], voiceover: [] }),
  subtitles: z.array(SubtitleUnitSchema).default([]),
  style: z.object({
    bg_color: z.array(z.number()).length(3).default([0, 0, 0]),
    font_color: z.array(z.number()).length(3).default([255, 255, 255]),
    font_size: z.number().default(40),
    transition_duration: z.number().default(500),
    layout_mode: z.enum(['fill', 'fit', 'crop']).default('fit'),
  }).default({}),
}).passthrough();

export type TimelineData = z.infer<typeof TimelineSchema>;

/**
 * Convert timeline to Remotion props.
 * Sequences handle absolute offsets; items inside are relative to sequence start.
 */
export function timelineToRemotionProps(timeline: TimelineData) {
  const fps = timeline.fps;
  const ms = (v: number) => Math.max(1, Math.round((v / 1000) * fps));

  return {
    fps,
    width: timeline.width,
    height: timeline.height,
    totalFrames: ms(timeline.total_duration),
    sequences: timeline.tracks.video.map(item => ({
      ...item,
      fromFrame: ms(item.start),
      durationFrames: ms(item.duration),
      transitionFrames: ms(item.transition_duration),
    })),
    bgm: timeline.tracks.bgm,
    voiceover: timeline.tracks.voiceover,
    subtitles: timeline.subtitles.map(s => ({
      ...s,
      startFrame: ms(s.start_ms ?? 0),
      endFrame: ms(s.end_ms ?? 0),
    })),
    style: timeline.style,
  };
}
