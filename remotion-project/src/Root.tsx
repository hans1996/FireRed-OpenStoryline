import React from 'react';
import { Composition } from 'remotion';
import { NewsReport, computeTotalDuration } from './NewsReport';
import type { NewsItem, NewsReportProps } from './NewsReport';

const items: NewsItem[] = [
  {
    title: 'OpenAI Slashes Pro Price',
    subtitle:
      'OpenAI cut ChatGPT Pro to $100 a month for heavy Codex users, undercutting rival premium AI plans.',
    bgGradient: ['#081a3a', '#0d2b5f', '#153d86'],
  },
  {
    title: 'UK Stargate Project Paused',
    subtitle:
      'OpenAI halted its UK data-center plan as energy costs and regulation complicated the proposed buildout.',
    bgGradient: ['#0a2418', '#103829', '#18513b'],
  },
  {
    title: 'Anthropic Unveils Glasswing',
    subtitle:
      'Anthropic introduced Project Glasswing, a security-focused system for protecting critical software in the AI era.',
    bgGradient: ['#1d1038', '#2a1756', '#3d2380'],
  },
  {
    title: 'Google And Intel Expand AI',
    subtitle:
      'Google and Intel widened their partnership to advance AI chips and the infrastructure powering large-scale models.',
    bgGradient: ['#06272f', '#0b3c48', '#135866'],
  },
  {
    title: 'Gemini Answers Go 3D',
    subtitle:
      'Google’s Gemini can now respond with interactive 3D models and simulations for more visual explanations.',
    bgGradient: ['#301228', '#4a1b3d', '#6a2757'],
  },
  {
    title: 'Meta Locks In More Compute',
    subtitle:
      'Meta and CoreWeave expanded their AI cloud partnership with a fresh $21 billion infrastructure deal.',
    bgGradient: ['#1b2408', '#2b3810', '#41561a'],
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
