import React from 'react';
import { AGENTS, AgentType } from '../../lib/constants';

interface AgentPillProps {
  type: AgentType;
  isSelected?: boolean;
  onClick?: () => void;
  className?: string;
}

export const AgentPill: React.FC<AgentPillProps> = ({ 
  type, 
  isSelected = false,
  onClick,
  className = ''
}) => {
  const agent = AGENTS[type];
  
  return (
    <button
      onClick={onClick}
      className={`
        inline-flex items-center gap-1.5 
        px-2 py-1 
        rounded 
        text-[11px] 
        border 
        transition-all
        ${isSelected 
          ? 'text-white' 
          : 'bg-[#1a1a1a] text-[#b0b0b0] border-[#3a3a3a] hover:text-white'
        }
        ${className}
      `}
      style={isSelected ? {
        backgroundColor: `${agent.color}15`,
        borderColor: agent.color,
        color: 'white'
      } : {}}
    >
      <span 
        className="w-1.5 h-1.5 rounded-full"
        style={{ backgroundColor: agent.color }}
      />
      {agent.name}
    </button>
  );
};

export default AgentPill;
