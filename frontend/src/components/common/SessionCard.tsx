import React from 'react';
import { motion } from 'framer-motion';
import { formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';

interface SessionCardProps {
  name: string;
  type: 'orchestrator' | 'chain' | 'parallel' | 'sequential';
  agentCount: number;
  lastActivity: Date;
  isActive?: boolean;
  onClick?: () => void;
  className?: string;
}

export const SessionCard: React.FC<SessionCardProps> = ({
  name,
  type,
  agentCount,
  lastActivity,
  isActive = false,
  onClick,
  className = ''
}) => {
  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'orchestrator':
        return 'Orchestrator';
      case 'chain':
        return 'Chain';
      case 'parallel':
        return 'Parallel workflow';
      case 'sequential':
        return 'Sequential';
      default:
        return 'Unknown';
    }
  };

  const getTimeAgo = (date: Date) => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) {
      return `${diffMins}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else if (diffDays < 7) {
      return `${diffDays}d ago`;
    } else {
      return formatDistanceToNow(date, { 
        addSuffix: true, 
        locale: ptBR 
      });
    }
  };

  const typeLabel = getTypeLabel(type);
  const timeAgo = getTimeAgo(lastActivity);

  return (
    <motion.div
      className={`
        w-full rounded-lg transition-all duration-200 cursor-pointer
        ${isActive 
          ? 'bg-[var(--mindflow-bg-active-session)] border-l-2 border-[var(--agent-orchestrator)]' 
          : 'hover:bg-[var(--mindflow-bg-card)]'
        }
        ${className}
      `}
      onClick={onClick}
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2 }}
    >
      <div className="p-3 space-y-1">
        {/* Session Name */}
        <div className={`
          text-sm font-medium truncate
          ${isActive ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'}
        `}>
          {name}
        </div>
        
        {/* Meta Information */}
        <div className={`
          text-xs font-normal
          ${isActive ? 'text-[var(--text-meta)]' : 'text-[var(--text-disabled)]'}
        `}>
          {typeLabel} · {agentCount} {agentCount === 1 ? 'agent' : 'agents'} · {timeAgo}
        </div>
      </div>
    </motion.div>
  );
};

export default SessionCard;
