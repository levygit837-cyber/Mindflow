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
    <motion.div
      className={`flex w-full gap-4 ${className}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
    >
      <div className="flex w-4 flex-col items-center shrink-0">
        <motion.span
          className="signal-dot"
          animate={{ opacity: [0.9, 0.4, 0.9] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
        />
        <span className="trace-rail mt-2 flex-1" />
      </div>

      <div className="rail-panel min-w-0 flex-1 px-5 py-4 md:px-6" style={{ paddingLeft: 36 }}>
        <div className="flex flex-wrap items-center gap-2">
          <span
            style={{
              color: 'var(--text-secondary)',
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
            }}
          >
            --- Thinking
          </span>

          <span
            style={{
              color: 'var(--text-primary)',
              fontSize: 14,
              fontWeight: 600,
            }}
          >
            {displayName}
          </span>

          <span className="mono-label" style={{ letterSpacing: '0.08em' }}>
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
          <p
            style={{
              marginTop: 12,
              color: 'var(--text-meta)',
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
              lineHeight: 1.7,
              whiteSpace: 'pre-wrap',
            }}
          >
            {lastThought}
          </p>
        )}
      </div>
    </motion.div>
  );
};

export default ThinkingNotifier;
