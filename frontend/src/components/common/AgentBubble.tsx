import React, { type CSSProperties } from 'react';
import { motion } from 'framer-motion';
import { format } from 'date-fns';
import { RichText } from './RichText';

type AgentType =
  | 'orchestrator'
  | 'coder'
  | 'analyst'
  | 'researcher'
  | 'architect'
  | 'critic'
  | 'creative'
  | 'security'
  | 'default';

interface AgentBubbleProps {
  agentType: AgentType;
  agentName: string;
  content: string;
  timestamp: Date;
  model?: string;
  className?: string;
}

const AGENT_ACCENTS: Record<string, string> = {
  orchestrator: 'var(--signal-synapse)',
  coder: '#8ac79d',
  analyst: '#d1a957',
  researcher: '#79c1d6',
  architect: 'var(--signal-synapse)',
  critic: '#c68ba6',
  creative: '#b899e4',
  security: '#93b1a4',
  default: 'var(--signal-synapse)',
};

export const AgentBubble: React.FC<AgentBubbleProps> = ({
  agentType,
  agentName,
  content,
  timestamp,
  model,
  className = '',
}) => {
  const accent = AGENT_ACCENTS[agentType] ?? AGENT_ACCENTS.default;

  return (
    <motion.section
      className={`event-shell w-full ${className}`}
      data-model={model || undefined}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24, ease: 'easeOut' }}
    >
      <div className="event-track">
        <span className="signal-dot" />
      </div>

      <div
        className="agent-thread"
        style={
          {
            '--agent-accent': accent,
          } as CSSProperties
        }
      >
        <div className="agent-thread-header">
          <span className="agent-thread-name">{agentName}</span>
          <span className="agent-thread-time">
            {format(timestamp, 'HH:mm')}
          </span>
        </div>

        <div className="agent-thread-bubble">
          <RichText content={content} className="agent-thread-copy" />
        </div>
      </div>
    </motion.section>
  );
};

export default AgentBubble;
