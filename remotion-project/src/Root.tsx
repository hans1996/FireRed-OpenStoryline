import React from 'react';
import { Composition } from 'remotion';
import { NewsReport, computeTotalDuration } from './NewsReport';
import type { NewsItem, NewsReportProps } from './NewsReport';

const items: NewsItem[] = [
  {
    title: 'Anthropic Unveils Glasswing',
    subtitle:
      'Anthropic launched Project Glasswing, a new effort focused on securing critical software systems for the AI era.',
    bgGradient: ['#071a33', '#0b2a4d', '#123b6b'],
  },
  {
    title: 'Anthropic Eyes Its Own Chips',
    subtitle:
      'Reuters reported Anthropic is weighing custom AI chips to reduce dependence on outside accelerator suppliers.',
    bgGradient: ['#0b2014', '#113525', '#1b4f38'],
  },
  {
    title: 'Google And Intel Deepen AI Pact',
    subtitle:
      'Reuters said Google and Intel expanded their partnership to push harder on AI CPUs and data-center infrastructure.',
    bgGradient: ['#1a1038', '#2a1a56', '#3f2a7d'],
  },
  {
    title: 'OpenAI Pauses UK Data Center',
    subtitle:
      'OpenAI put its UK data-center project on hold as it reassesses rising costs and regulatory pressure, according to Reuters.',
    bgGradient: ['#06262c', '#0d3c45', '#155762'],
  },
  {
    title: 'ChatGPT Pro Drops To $100',
    subtitle:
      'OpenAI introduced a $100 ChatGPT Pro tier with much higher Codex usage limits, sharpening pressure on rivals.',
    bgGradient: ['#2a1029', '#431842', '#61255f'],
  },
  {
    title: 'Meta Reassigns AI Talent',
    subtitle:
      'Reuters reported Meta moved top engineers into a new AI tooling team as competition in frontier model development intensifies.',
    bgGradient: ['#1d220c', '#2f3814', '#48561f'],
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
