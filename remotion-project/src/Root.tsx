import React from 'react';
import { Composition } from 'remotion';
import { NewsReport, computeTotalDuration } from './NewsReport';
import type { NewsItem, NewsReportProps } from './NewsReport';

const items: NewsItem[] = [
  {
    title: 'Anthropic 推出 Mythos AI 模型',
    subtitle: '新一代 AI 模型專注網路安全，首發預覽版展示威脅偵測能力',
    bgGradient: ['#0a193c', '#142850', '#1a3a6e'],
  },
  {
    title: 'Broadcom 擴大 AI 晶片合作',
    subtitle: 'Broadcom 與 Google 和 Anthropic 簽署擴展晶片協議，滿足飆升算力需求',
    bgGradient: ['#0a3328', '#145040', '#1a6e50'],
  },
  {
    title: 'Salesforce 推出 Slackbot AI 代理',
    subtitle: '全新 Slack AI 代理加入職場戰場，與微軟和 Google 正面競爭',
    bgGradient: ['#28144a', '#3a1a60', '#502080'],
  },
  {
    title: '量子電腦破解加密大幅提前',
    subtitle: 'Google 將量子破解時間表提前至 2029 年，遠早於先前預測',
    bgGradient: ['#3c0a28', '#50143a', '#6e1a50'],
  },
  {
    title: 'Uber 採用 Amazon AI 晶片',
    subtitle: '亞馬遜自研 AI 晶片持續擴張，Uber 成為最新加入科技巨頭',
    bgGradient: ['#1a2a0a', '#2a4014', '#3a5a1e'],
  },
  {
    title: 'Intel 加入 Musk Terafab 計畫',
    subtitle: 'Intel 正式簽署 Elon Musk 的超級晶片廠 Terafab 合作計畫',
    bgGradient: ['#0a2a3c', '#144050', '#1e5a6e'],
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
