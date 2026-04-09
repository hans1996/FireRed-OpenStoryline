import React from 'react';
import { Composition } from 'remotion';
import { NewsReport, computeTotalDuration } from './NewsReport';
import type { NewsItem, NewsReportProps } from './NewsReport';

const items: NewsItem[] = [
  {
    title: 'Meta Unveils New AI Model',
    subtitle:
      'Meta introduced a fresh flagship model from its superintelligence lab as it tries to close the gap with Google and OpenAI.',
    bgGradient: ['#071a3d', '#0b2757', '#123b7a'],
  },
  {
    title: 'OpenAI Opens IPO to Retail',
    subtitle:
      'OpenAI said retail investors will receive part of its IPO share allocation, widening access beyond institutions.',
    bgGradient: ['#0b2c1f', '#11402d', '#1a5b40'],
  },
  {
    title: 'Anthropic Holds Back Mythos',
    subtitle:
      'Anthropic is limiting public release of Claude Mythos after concluding the model could be too dangerous to deploy broadly.',
    bgGradient: ['#1e103f', '#2a1760', '#3d2290'],
  },
  {
    title: 'Google Launches Offline Dictation',
    subtitle:
      'Google quietly released an AI dictation app that works without an internet connection, expanding on-device productivity tools.',
    bgGradient: ['#062b30', '#0b3d44', '#14606b'],
  },
  {
    title: 'AI Giants Unite on Model Theft',
    subtitle:
      'OpenAI, Anthropic, and Google are reportedly coordinating defenses against Chinese AI distillation and model-theft threats.',
    bgGradient: ['#311125', '#4b1937', '#702454'],
  },
  {
    title: 'Broadcom Lands Google Chip Deal',
    subtitle:
      'Broadcom shares surged after securing a Google AI chip supply agreement, highlighting relentless demand for AI infrastructure.',
    bgGradient: ['#1d2508', '#2b3810', '#43581b'],
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
