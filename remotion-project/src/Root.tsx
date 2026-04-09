import React from 'react';
import { Composition } from 'remotion';
import { NewsReport, computeTotalDuration } from './NewsReport';
import type { NewsItem, NewsReportProps } from './NewsReport';

const items: NewsItem[] = [
  {
    title: 'OpenAI Eyes Cyber Product',
    subtitle:
      'Axios reported OpenAI is preparing a new cybersecurity-focused product aimed at enterprise and government use cases.',
    bgGradient: ['#081a3a', '#0d2b5f', '#153d86'],
  },
  {
    title: 'Stargate UK Put On Hold',
    subtitle:
      'OpenAI paused its UK Stargate data-center project amid regulatory concerns and high energy prices.',
    bgGradient: ['#0a2418', '#103829', '#18513b'],
  },
  {
    title: 'Anthropic Launches Glasswing',
    subtitle:
      'Anthropic unveiled Project Glasswing to help defend critical software systems against AI-era cyber threats.',
    bgGradient: ['#1d1038', '#2a1756', '#3d2380'],
  },
  {
    title: 'Google-Intel AI Chip Pact',
    subtitle:
      'Google expanded its partnership with Intel to push forward AI chips and cloud infrastructure capacity.',
    bgGradient: ['#06272f', '#0b3c48', '#135866'],
  },
  {
    title: 'Shorts Adds AI Avatars',
    subtitle:
      'Google is bringing AI-generated avatars to YouTube Shorts as it broadens creator-facing generative tools.',
    bgGradient: ['#301228', '#4a1b3d', '#6a2757'],
  },
  {
    title: 'Meta Doubles Down on Compute',
    subtitle:
      'Meta deepened its AI cloud partnership with CoreWeave through a fresh $21 billion infrastructure deal.',
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
