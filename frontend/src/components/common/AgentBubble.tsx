import React, { type CSSProperties } from 'react';
import { motion } from 'framer-motion';
import { RichText } from './RichText';
import type { AgentType } from '../../types/agentTypes';
import { AGENT_ACCENTS, AGENT_LABELS } from '../../types/agentTypes';

interface AgentBubbleProps {
  agentType: AgentType;
  agentName: string;
  content: string;
  timestamp: Date;
  model?: string;
  className?: string;
}

export const AgentBubble: React.FC<AgentBubbleProps> = ({
  agentType,
  agentName,
  content,
  model,
  className = '',
}) => {
  const accent = AGENT_ACCENTS[agentType] ?? AGENT_ACCENTS.default;
  const label = AGENT_LABELS[agentType] ?? 'AGENT';

  return (
    <motion.section
      className={`event-shell w-full ${className}`}
      data-model={model || undefined}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
    >
      <div
        className="agent-thread"
        style={{ '--agent-accent': accent } as CSSProperties}
      >
        <div className="agent-thread-header">
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: accent,
              flexShrink: 0,
            }}
          />
          <span className="agent-thread-name">{label}</span>
          {agentName && agentName.toLowerCase() !== agentType && (
            <span
              style={{
                color: 'var(--text-meta)',
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                letterSpacing: '0.04em',
              }}
            >
              · {agentName}
            </span>
          )}
        </div>

        <div className="agent-thread-bubble">
          <RichText content={content} className="agent-thread-copy" />
        </div>
      </div>
    </motion.section>
  );
};

export default AgentBubble;
