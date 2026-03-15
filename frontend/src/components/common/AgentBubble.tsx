import React from 'react';
import { motion } from 'framer-motion';
import { format } from 'date-fns';

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

const ROLE_LABELS: Record<string, string> = {
  orchestrator: 'root',
  coder: 'build',
  analyst: 'trace',
  researcher: 'lookup',
  architect: 'frame',
  critic: 'audit',
  creative: 'draft',
  security: 'guard',
  default: 'agent',
};

export const AgentBubble: React.FC<AgentBubbleProps> = ({
  agentType,
  agentName,
  content,
  timestamp,
  model,
  className = '',
}) => {
  return (
    <motion.section
      className={`event-shell w-full ${className}`}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24, ease: 'easeOut' }}
    >
      <div className="event-track">
        <span className="signal-dot" />
      </div>

      <div className="event-node-lab">
        <div className="event-header">
          <span className="mono-label">{ROLE_LABELS[agentType] ?? ROLE_LABELS.default}</span>
          <span className="event-title">
            {agentName}
          </span>

          {model && (
            <span className="event-badge">
              <span style={{ color: 'var(--text-meta)' }}>model</span>
              {model}
            </span>
          )}

          <span
            style={{
              color: 'var(--text-meta)',
              fontFamily: 'var(--font-mono)',
              fontSize: 11,
              marginLeft: 'auto',
            }}
          >
            {format(timestamp, 'HH:mm')}
          </span>
        </div>

        <div className="event-expand">
          <div
            style={{
              color: 'var(--text-secondary)',
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
            }}
          >
            --- {agentName}
          </div>

          <div className="event-inline-copy">{content}</div>
        </div>
      </div>
    </motion.section>
  );
};

export default AgentBubble;
