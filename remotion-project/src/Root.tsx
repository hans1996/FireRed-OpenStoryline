import React from 'react';
import { Composition } from 'remotion';
import { NewsReport, computeTotalDuration } from './NewsReport';
import type { NewsItem, NewsReportProps } from './NewsReport';

const items: NewsItem[] = [
  {
    title: 'Anthropic Eyes Custom Chips',
    subtitle:
      'Reuters reported Anthropic is weighing its own AI chips to reduce reliance on outside accelerators as demand surges.',
    bgGradient: ['#071a33', '#0b2a4d', '#123b6b'],
  },
  {
    title: 'OpenAI Pauses UK Campus',
    subtitle:
      'OpenAI put its UK data-center project on hold while it reworks plans around regulation and rising build costs.',
    bgGradient: ['#0a2418', '#11362a', '#1a4c3a'],
  },
  {
    title: 'ChatGPT Pro Drops To $100',
    subtitle:
      'CNBC said OpenAI cut ChatGPT Pro pricing for heavy Codex users, turning up pressure on premium rival plans.',
    bgGradient: ['#22103d', '#34195d', '#4c2583'],
  },
  {
    title: 'Google And Intel Go Deeper',
    subtitle:
      'Google and Intel expanded their AI infrastructure partnership to push more chip capacity into large-scale model workloads.',
    bgGradient: ['#06252c', '#0d3942', '#15535f'],
  },
  {
    title: 'Meta Debuts Muse Spark',
    subtitle:
      'Meta launched Muse Spark, its first major AI model release under Alexandr Wang as it races to catch up in frontier AI.',
    bgGradient: ['#301228', '#4a1c3f', '#6a2a5a'],
  },
  {
    title: 'Project Glasswing Launches',
    subtitle:
      'Anthropic introduced Project Glasswing, aimed at securing critical software systems against emerging AI-era cyber risks.',
    bgGradient: ['#1a2309', '#2a3810', '#41541a'],
  },
];

const defaultProps: NewsReportProps = {
  headerTitle: '本週 AI 新聞快訊',
  items,
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="NewsReport"
        component={NewsReport}
        durationInFrames={computeTotalDuration(items.length)}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={defaultProps}
      />
    </>
  );
};
