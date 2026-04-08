import React from 'react';
import { AGENTS, AgentType } from '../../lib/constants';

interface StreamingIndicatorProps {
  agentType: AgentType;
  progress?: number;
  text?: string;
  variant?: 'bar' | 'dots';
}

export const StreamingIndicator: React.FC<StreamingIndicatorProps> = ({ 
  agentType, 
  progress,
  text,
  variant = 'dots'
}) => {
  const agent = AGENTS[agentType];
  const displayText = text || (agentType === 'coder' ? 'Coding' : 'Generating');
  
  if (variant === 'bar') {
    return (
      <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[12px] text-[#b0b0b0]">Processing...</span>
          <span className="text-[12px] font-medium" style={{ color: agent.color }}>
            {progress || 0}%
          </span>
        </div>
        <div className="h-1 bg-[#2a2a2a] rounded-full overflow-hidden">
          <div 
            className="h-full rounded-full transition-all duration-300"
            style={{ 
              width: `${progress || 0}%`,
              backgroundColor: agent.color 
            }}
          />
        </div>
      </div>
    );
  }
  
  return (
    <div className="flex items-center gap-3">
      <div 
        className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-full px-3 py-1.5 flex items-center gap-2"
      >
        <div className="flex gap-1">
          <span 
            className="w-1.5 h-1.5 rounded-full animate-pulse-dot"
            style={{ backgroundColor: agent.color }}
          />
          <span 
            className="w-1.5 h-1.5 rounded-full animate-pulse-dot-delay-1"
            style={{ backgroundColor: agent.color }}
          />
          <span 
            className="w-1.5 h-1.5 rounded-full animate-pulse-dot-delay-2"
            style={{ backgroundColor: agent.color }}
          />
        </div>
        <span 
          className="text-[11px] font-medium uppercase tracking-widest"
          style={{ color: agent.color }}
        >
          {displayText}
        </span>
      </div>
    </div>
  );
};

export default StreamingIndicator;
