import React from 'react';
import { Composition } from 'remotion';
import { NewsReport, computeTotalDuration } from './NewsReport';
import type { NewsItem, NewsReportProps } from './NewsReport';

const items: NewsItem[] = [
  {
    title: 'OpenAI Slows New Model Launch',
    subtitle:
      'Axios reported OpenAI is staggering release of a new model after identifying cybersecurity risks that require tighter controls.',
    bgGradient: ['#081a3a', '#0d2b5f', '#153d86'],
  },
  {
    title: 'Meta Debuts Muse Spark',
    subtitle:
      'Meta unveiled its new Muse Spark AI model as it pushes to regain ground on Google, OpenAI, and Anthropic.',
    bgGradient: ['#0a2418', '#103829', '#18513b'],
  },
  {
    title: 'Anthropic Holds Back Top Model',
    subtitle:
      'Anthropic said its newest model is too powerful to release broadly, underscoring growing safety tension at the frontier.',
    bgGradient: ['#1d1038', '#2a1756', '#3d2380'],
  },
  {
    title: 'Google Ships Offline Speech AI',
    subtitle:
      'Google introduced a speech-to-text app that works even without internet access, expanding practical on-device AI.',
    bgGradient: ['#06272f', '#0b3c48', '#135866'],
  },
  {
    title: 'Microsoft Pushes New Speech Models',
    subtitle:
      'Microsoft rolled out fresh speech models as part of a broader move toward a more self-reliant first-party AI stack.',
    bgGradient: ['#301228', '#4a1b3d', '#6a2757'],
  },
  {
    title: 'AI Labs Unite on Distillation Threat',
    subtitle:
      'OpenAI, Google, and Anthropic are reportedly coordinating to counter Chinese AI model distillation and theft risks.',
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
