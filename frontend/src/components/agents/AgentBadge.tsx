import React from 'react';
import { AGENTS, AgentType } from '../../lib/constants';

interface AgentBadgeProps {
  type: AgentType;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  className?: string;
}

export const AgentBadge: React.FC<AgentBadgeProps> = ({ 
  type, 
  size = 'md', 
  showIcon = false,
  className = '' 
}) => {
  const agent = AGENTS[type];
  
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[10px]',
    md: 'px-2.5 py-1 text-[11px]',
    lg: 'px-3 py-1.5 text-[12px]',
  };
  
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded font-semibold uppercase tracking-wider ${sizeClasses[size]} ${className}`}
      style={{ 
        backgroundColor: `${agent.color}15`,
        border: `1px solid ${agent.color}40`,
        color: agent.color 
      }}
    >
      {showIcon && <span>{agent.icon[0]}</span>}
      {agent.name}
    </span>
  );
};

export default AgentBadge;
