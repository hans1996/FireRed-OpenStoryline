import React from 'react';
import { Composition } from 'remotion';
import { NewsReport, computeTotalDuration } from './NewsReport';
import type { NewsItem, NewsReportProps } from './NewsReport';

const items: NewsItem[] = [
  {
    title: 'OpenAI GPT-4.1 強化長上下文能力',
    subtitle: 'OpenAI 發布 GPT-4.1 系列模型，支援百萬 token 窗口與更精細的工具使用能力',
    bgGradient: ['#0a193c', '#142850', '#1a3a6e'],
  },
  {
    title: 'Google DeepMind 推出 Gemini 2.5',
    subtitle: '多模態能力全面升級，影像、文字、程式碼推理能力顯著提升',
    bgGradient: ['#0a3328', '#145040', '#1a6e50'],
  },
  {
    title: 'Anthropic 考慮 10 月 IPO',
    subtitle: 'Claude 開發商 Anthropic 考慮最快 10 月上市，估值可能超過 1000 億美元',
    bgGradient: ['#3c0a28', '#50143a', '#6e1a50'],
  },
  {
    title: 'Claude Cowork 整合 Google 生態系',
    subtitle: '連接 Google Drive、Gmail、DocuSign，企業 AI 工作流全面升級',
    bgGradient: ['#28144a', '#3a1a60', '#502080'],
  },
  {
    title: 'AI 邏輯模型省能百倍突破',
    subtitle: '邏輯驅動模型能耗降低 100 倍且在準確度領先',
    bgGradient: ['#0a3328', '#14503a', '#1a6e4a'],
  },
  {
    title: 'AI Coding Agent 市場爆發',
    subtitle: 'Claude Code 與 Cursor 用戶數翻倍，開發工具新時代來臨',
    bgGradient: ['#3c0a19', '#501428', '#6e1a3c'],
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
