import React from 'react';
import { motion } from 'framer-motion';

type AgentType = 'orchestrator' | 'coder' | 'analyst' | 'researcher' | 'default';

interface ThinkingNotifierProps {
  agentType?: AgentType;
  agentName?: string;
  status?: 'thinking' | 'processing' | 'analyzing' | 'waiting';
  lastThought?: string;
  className?: string;
}

const STATUS_LABELS: Record<NonNullable<ThinkingNotifierProps['status']>, string> = {
  thinking: 'thinking',
  processing: 'processing',
  analyzing: 'analyzing',
  waiting: 'waiting',
};

export const ThinkingNotifier: React.FC<ThinkingNotifierProps> = ({
  agentType = 'orchestrator',
  agentName,
  status = 'thinking',
  lastThought,
  className = '',
}) => {
  const displayName = agentName ?? 'Orchestrator';

  return (
    <motion.section
      className={`event-shell w-full ${className}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
    >
      <div className="event-track">
        <motion.span
          className="signal-dot"
          animate={{ opacity: [0.9, 0.4, 0.9] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
        />
      </div>

      <div className="thought-stack">
        <div className="thought-pill">
          <span className={`thought-synapse thought-synapse--${agentType}`}>
            <span className="thought-synapse-link thought-synapse-link-a" />
            <span className="thought-synapse-link thought-synapse-link-b" />
            <span className="thought-synapse-node thought-synapse-node-a" />
            <span className="thought-synapse-node thought-synapse-node-b" />
            <span className="thought-synapse-node thought-synapse-node-c" />
          </span>

          <span className="thought-name">{displayName}</span>
          <span className="thought-sep">/</span>
          <span className="thought-status">{STATUS_LABELS[status]}</span>

          <motion.span
            className="thought-pulse"
            animate={{ opacity: [0.32, 1, 0.32] }}
            transition={{ duration: 1.1, repeat: Infinity, ease: 'easeInOut' }}
          />
        </div>

        {lastThought ? (
          <div className="thought-body">
            <p className="thought-note">{lastThought}</p>
          </div>
        ) : null}
      </div>
    </motion.section>
  );
};

export default ThinkingNotifier;
