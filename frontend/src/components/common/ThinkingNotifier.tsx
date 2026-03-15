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

const STATUS_LABELS: Record<AgentType, string> = {
  orchestrator: 'routing',
  analyst: 'analyzing',
  coder: 'building',
  researcher: 'searching',
  default: 'processing',
};

export const ThinkingNotifier: React.FC<ThinkingNotifierProps> = ({
  agentType = 'orchestrator',
  agentName,
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

      <div className="event-node-lab">
        <div className="event-header">
          <span className="mono-label">--- Thinking</span>

          <span className="event-title">
            {displayName}
          </span>

          <span className="event-badge">
            {STATUS_LABELS[agentType] ?? STATUS_LABELS.default}
          </span>

          <div className="ml-auto flex items-center gap-2">
            {[0, 1, 2].map((index) => (
              <motion.span
                key={index}
                style={{
                  width: index === 2 ? 18 : 8,
                  height: 1,
                  background: index === 2
                    ? 'linear-gradient(90deg, rgba(255,255,255,0.88) 0%, rgba(139,92,246,0.8) 100%)'
                    : 'rgba(255,255,255,0.36)',
                  borderRadius: 999,
                }}
                animate={{ opacity: [0.35, 1, 0.35] }}
                transition={{ duration: 1.2, repeat: Infinity, delay: index * 0.16 }}
              />
            ))}
          </div>
        </div>

        {lastThought && (
          <div className="event-expand">
            <p
              style={{
                margin: 0,
                color: 'var(--text-meta)',
                fontFamily: 'var(--font-mono)',
                fontSize: 12,
                lineHeight: 1.72,
                whiteSpace: 'pre-wrap',
              }}
            >
              {lastThought}
            </p>
          </div>
        )}
      </div>
    </motion.section>
  );
};

export default ThinkingNotifier;
