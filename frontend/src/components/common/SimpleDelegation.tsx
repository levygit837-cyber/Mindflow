import React from 'react';
import { motion } from 'framer-motion';
import { Network, ChevronRight } from 'lucide-react';


type AgentType = 'orchestrator' | 'analyst' | 'coder' | 'researcher';

interface SimpleDelegationProps {
  /** Target agent receiving the task */
  agentType: AgentType;
  agentName?: string;
  /** Short task description */
  task: string;
  className?: string;
}

// Matches the design sdr* node color tokens
const AGENT_DELEGATION_COLORS: Record<string, {
  containerBg: string;
  dotColor: string;
  nameColor: string;
  badgeBg: string;
  badgeText: string;
  taskColor: string;
}> = {
  researcher: {
    containerBg: '#031118',
    dotColor: '#22D3EE',
    nameColor: '#22D3EE',
    badgeBg: '#031118',
    badgeText: '#22D3EE',
    taskColor: '#2A6678',
  },
  analyst: {
    containerBg: '#150D04',
    dotColor: '#F59E0B',
    nameColor: '#F59E0B',
    badgeBg: '#150D04',
    badgeText: '#F59E0B',
    taskColor: '#7A5E1A',
  },
  coder: {
    containerBg: '#041208',
    dotColor: '#4ADE80',
    nameColor: '#4ADE80',
    badgeBg: '#041208',
    badgeText: '#4ADE80',
    taskColor: '#1E5A2A',
  },
  orchestrator: {
    containerBg: '#110A2E',
    dotColor: '#8B5CF6',
    nameColor: '#8B5CF6',
    badgeBg: '#110A2E',
    badgeText: '#8B5CF6',
    taskColor: '#4A3B7A',
  },
};

const AGENT_LABEL_MAP: Record<string, string> = {
  researcher: 'Researcher',
  analyst: 'Analyst',
  coder: 'Coder',
  orchestrator: 'Orchestrator',
};

export const SimpleDelegation: React.FC<SimpleDelegationProps> = ({
  agentType,
  agentName,
  task,
  className = '',
}) => {
  const colors = AGENT_DELEGATION_COLORS[agentType] ?? AGENT_DELEGATION_COLORS.researcher;
  const displayName = agentName ?? AGENT_LABEL_MAP[agentType] ?? agentType;

  return (
    <motion.div
      className={`rounded-lg overflow-hidden ${className}`}
      style={{ backgroundColor: colors.containerBg }}
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
    >
      {/* Header row */}
      <div className="flex items-center justify-between px-3 py-2">
        <div className="flex items-center gap-1.5">
          {/* Orchestrator icon (delegating from) */}
          <Network className="w-3.5 h-3.5" style={{ color: '#8B5CF6' }} />
          <span
            className="text-[12px]"
            style={{ color: '#7C5ABF', fontFamily: 'var(--font-brand)' }}
          >
            Orchestrator
          </span>

          {/* Arrow */}
          <ChevronRight className="w-3 h-3" style={{ color: '#1E1A40' }} />

          {/* Target agent dot + name */}
          <span
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: colors.dotColor }}
          />
          <span
            className="text-[12px] font-semibold"
            style={{ color: colors.nameColor, fontFamily: 'var(--font-brand)' }}
          >
            {displayName}
          </span>
        </div>

        {/* Agent type badge */}
        <div
          className="px-2 py-0.5 rounded"
          style={{ backgroundColor: colors.badgeBg, border: `1px solid ${colors.dotColor}22` }}
        >
          <span
            className="text-[11px] font-semibold"
            style={{ color: colors.badgeText, fontFamily: 'var(--font-brand)' }}
          >
            {displayName}
          </span>
        </div>
      </div>

      {/* Task description */}
      <div className="px-3 pb-2.5">
        <p
          className="text-[12px] leading-relaxed"
          style={{ color: colors.taskColor, fontFamily: 'var(--font-sans)' }}
        >
          {task}
        </p>
      </div>
    </motion.div>
  );
};

export default SimpleDelegation;
