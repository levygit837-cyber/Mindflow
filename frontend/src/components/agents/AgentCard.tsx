import React from 'react';
import { AGENTS, AgentType } from '../../lib/constants';
import { cn } from '../../lib/utils';
import { Target, ChartBar, BracketsCurly, MagnifyingGlass } from '@phosphor-icons/react';

interface AgentCardProps {
  type: AgentType;
  onClick?: () => void;
  className?: string;
  isSelected?: boolean;
}

const iconMap = {
  orchestrator: Target,
  analyst: ChartBar,
  coder: BracketsCurly,
  researcher: MagnifyingGlass,
};

export const AgentCard: React.FC<AgentCardProps> = ({ type, onClick, className, isSelected }) => {
  const agent = AGENTS[type];
  const Icon = iconMap[type];

  return (
    <div
      onClick={onClick}
      className={cn(
        'rounded-r-xl p-4 border-y border-r border-[#2a2a2a]',
        'hover:bg-[#2a2a2a] transition-colors cursor-pointer group',
        isSelected ? 'bg-[#2a2a2a] ring-1 ring-[#4a4a4a]' : 'bg-[#1a1a1a]',
        className
      )}
      style={{ borderLeftWidth: '3px', borderLeftColor: agent.color }}
    >
      <div className="flex items-center gap-3 mb-2">
        <div 
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: `${agent.color}15` }}
        >
          <Icon style={{ color: agent.color }} size={20} weight="bold" />
        </div>
        <span className="text-sm font-semibold text-white">{agent.name}</span>
      </div>
      <p className="text-[11px] text-[#b0b0b0] leading-relaxed">{agent.description}</p>
    </div>
  );
};

export default AgentCard;
