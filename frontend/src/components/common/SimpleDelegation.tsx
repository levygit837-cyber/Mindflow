import React, { type CSSProperties } from 'react';
import { motion } from 'framer-motion';
import { ChevronRight, Network } from 'lucide-react';

type AgentType = 'orchestrator' | 'analyst' | 'coder' | 'researcher' | 'default';

interface SimpleDelegationProps {
  /** Target agent receiving the task */
  agentType: AgentType;
  agentName?: string;
  /** Short task description */
  task: string;
  className?: string;
}

const AGENT_DELEGATION_COLORS: Record<
  string,
  {
    accent: string;
    badgeBg: string;
    badgeBorder: string;
  }
> = {
  researcher: {
    accent: '#22D3EE',
    badgeBg: '#031118',
    badgeBorder: '#22D3EE',
  },
  analyst: {
    accent: '#F59E0B',
    badgeBg: '#150D04',
    badgeBorder: '#F59E0B',
  },
  coder: {
    accent: '#4ADE80',
    badgeBg: '#041208',
    badgeBorder: '#4ADE80',
  },
  orchestrator: {
    accent: '#8B5CF6',
    badgeBg: '#110A2E',
    badgeBorder: '#8B5CF6',
  },
  default: {
    accent: 'var(--signal-synapse)',
    badgeBg: '#1D1840',
    badgeBorder: 'var(--signal-synapse)',
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
  const colors = AGENT_DELEGATION_COLORS[agentType] ?? AGENT_DELEGATION_COLORS.default;
  const displayName = agentName ?? AGENT_LABEL_MAP[agentType] ?? agentType;

  return (
    <motion.section
      className={`event-shell w-full ${className}`}
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
    >
      <div className="event-track">
        <span className="signal-dot idle" />
      </div>

      <div
        className="simple-delegation-card"
        style={
          {
            '--delegation-accent': colors.accent,
            '--delegation-badge-bg': colors.badgeBg,
            '--delegation-badge-border': colors.badgeBorder,
          } as CSSProperties
        }
      >
        <div className="simple-delegation-header">
          <div className="simple-delegation-route">
            <div className="simple-delegation-route-core">
              <Network size={13} />
              <span className="simple-delegation-origin">Orchestrator</span>
            </div>

            <ChevronRight size={13} className="simple-delegation-arrow" />

            <div className="simple-delegation-target">
              <span className="simple-delegation-dot" />
              <span className="simple-delegation-name">{displayName}</span>
            </div>
          </div>

          <span className="simple-delegation-badge">{displayName}</span>
        </div>

        <p className="simple-delegation-task">{task}</p>
      </div>
    </motion.section>
  );
};

export default SimpleDelegation;
