import React from 'react';
import { AgentType } from '../../lib/constants';
import { Spinner, MagnifyingGlass } from '@phosphor-icons/react';

interface ThinkingIndicatorProps {
  type: AgentType;
  customText?: string;
}

export const OrchestratorThinking: React.FC<{ text?: string }> = ({ text = 'Orchestrator is thinking...' }) => (
  <div className="flex items-center gap-3 py-2 px-3 bg-[#1a1a1a]/50 rounded-lg border border-[#2a2a2a]">
    <div className="flex items-center gap-1">
      <span className="w-1.5 h-1.5 bg-[#0D6E6E] rounded-full animate-pulse-dot" />
      <span className="w-1.5 h-1.5 bg-[#0D6E6E] rounded-full animate-pulse-dot-delay-1" />
      <span className="w-1.5 h-1.5 bg-[#0D6E6E] rounded-full animate-pulse-dot-delay-2" />
    </div>
    <span className="text-[13px] text-[#0D6E6E] font-medium">{text}</span>
  </div>
);

export const AnalystThinking: React.FC<{ text?: string }> = ({ text = 'Analyzing data...' }) => (
  <div className="flex items-center gap-3 py-2 px-3 bg-[#1a1a1a]/50 rounded-lg border border-[#2a2a2a]">
    <Spinner className="text-[#5B6ABF] text-lg animate-spin-slow" weight="bold" />
    <span className="text-[13px] text-[#5B6ABF] font-medium">{text}</span>
  </div>
);

export const CoderThinking: React.FC<{ text?: string; filename?: string }> = ({ 
  text = 'Writing code...',
  filename = 'generating_code.ts'
}) => (
  <div className="flex items-center gap-3 py-2 px-3 bg-[#1a1a1a]/50 rounded-lg border border-[#2a2a2a]">
    <span className="text-[#C75D2C] text-lg font-mono font-bold">&gt;</span>
    <span className="w-2.5 h-4 bg-[#C75D2C] animate-blink" />
    <span className="text-[13px] text-[#C75D2C] font-medium font-mono">{filename || text}</span>
  </div>
);

export const ResearcherThinking: React.FC<{ text?: string }> = ({ text = 'Researching...' }) => (
  <div className="flex items-center gap-3 py-2 px-3 bg-[#1a1a1a]/50 rounded-lg border border-[#2a2a2a]">
    <MagnifyingGlass className="text-[#2D8F5E] text-lg animate-search-bounce" weight="bold" />
    <span className="text-[13px] text-[#2D8F5E] font-medium">{text}</span>
  </div>
);

export const ThinkingIndicator: React.FC<ThinkingIndicatorProps> = ({ type, customText }) => {
  switch (type) {
    case 'orchestrator':
      return <OrchestratorThinking text={customText} />;
    case 'analyst':
      return <AnalystThinking text={customText} />;
    case 'coder':
      return <CoderThinking text={customText} />;
    case 'researcher':
      return <ResearcherThinking text={customText} />;
    default:
      return <OrchestratorThinking text={customText} />;
  }
};

export default ThinkingIndicator;
