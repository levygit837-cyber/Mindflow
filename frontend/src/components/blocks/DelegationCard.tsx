import React from 'react';
import { AGENTS, AgentType } from '../../lib/constants';
import { Target } from '@phosphor-icons/react';

interface DelegationCardProps {
  fromAgent: AgentType;
  toAgent: AgentType;
  strategy: 'parallel' | 'sequential' | 'single';
  tools: string[];
  context: string;
  className?: string;
}

export const DelegationCard: React.FC<DelegationCardProps> = ({
  fromAgent,
  toAgent,
  strategy,
  tools,
  context,
  className = ''
}) => {
  const toAgentConfig = AGENTS[toAgent];
  const fromAgentConfig = AGENTS[fromAgent];
  
  return (
    <div className={`bg-[#2a2a2a] border border-[#2a2a2a] rounded-lg overflow-hidden ${className}`}>
      <div className="p-3 border-b border-[#2a2a2a] bg-[#1a1a1a]/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div 
              className="w-7 h-7 rounded flex items-center justify-center"
              style={{ backgroundColor: `${fromAgentConfig.color}15` }}
            >
              <Target style={{ color: fromAgentConfig.color }} size={16} />
            </div>
            <span className="text-sm font-medium text-white">
              Delegating to {toAgentConfig.name}
            </span>
          </div>
          <span className="px-2 py-0.5 bg-[#0a0a0a] border border-[#3a3a3a] rounded text-[10px] text-[#707070] uppercase tracking-wider font-semibold">
            {strategy}
          </span>
        </div>
      </div>
      
      <div className="p-3">
        <p className="text-[12px] text-[#b0b0b0] mb-2">{context}</p>
        <div className="flex flex-wrap gap-1.5">
          {tools.map((tool, index) => (
            <span
              key={index}
              className="px-1.5 py-0.5 rounded text-[10px] border"
              style={{ 
                backgroundColor: `${toAgentConfig.color}10`,
                borderColor: `${toAgentConfig.color}20`,
                color: toAgentConfig.color 
              }}
            >
              {tool}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};

export default DelegationCard;
