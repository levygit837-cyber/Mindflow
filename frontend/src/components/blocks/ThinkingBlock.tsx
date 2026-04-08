import React, { useState } from 'react';
import { AGENTS, AgentType } from '../../lib/constants';
import { AgentBadge } from '../agents/AgentBadge';
import { CaretDown, CaretUp } from '@phosphor-icons/react';

interface ThinkingBlockProps {
  agentType: AgentType;
  reasoning: string;
  isExpanded?: boolean;
  className?: string;
  onToggle?: (isExpanded: boolean) => void;
}

export const ThinkingBlock: React.FC<ThinkingBlockProps> = ({
  agentType,
  reasoning,
  isExpanded: controlledExpanded,
  className = '',
  onToggle,
}) => {
  const [internalExpanded, setInternalExpanded] = useState(false);
  const isExpanded = controlledExpanded !== undefined ? controlledExpanded : internalExpanded;
  const agent = AGENTS[agentType];

  const handleToggle = () => {
    const newValue = !isExpanded;
    if (controlledExpanded === undefined) {
      setInternalExpanded(newValue);
    }
    onToggle?.(newValue);
  };
  
  return (
    <div className={`bg-[#2a2a2a] border border-[#2a2a2a] rounded-lg overflow-hidden ${className}`}>
      <button
        onClick={handleToggle}
        className="w-full flex items-center justify-between p-3 hover:bg-[#3a3a3a] transition-colors"
      >
        <div className="flex items-center gap-3">
          <AgentBadge type={agentType} size="sm" />
          <span className="text-[13px] text-[#b0b0b0]">Thinking</span>
          {!isExpanded && (
            <span className="text-[12px] text-[#707070] truncate max-w-md">
              {reasoning.substring(0, 80)}...
            </span>
          )}
        </div>
        {isExpanded ? (
          <CaretUp className="text-[#707070]" size={16} weight="bold" />
        ) : (
          <CaretDown className="text-[#707070]" size={16} weight="bold" />
        )}
      </button>
      
      {isExpanded && (
        <div 
          className="p-4 border-t border-[#2a2a2a]"
          style={{ borderLeftWidth: '3px', borderLeftColor: agent.color }}
        >
          <p className="text-[13px] text-[#b0b0b0] leading-relaxed whitespace-pre-wrap">
            {reasoning}
          </p>
        </div>
      )}
    </div>
  );
};

export default ThinkingBlock;
