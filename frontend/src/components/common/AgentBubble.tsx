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
    <motion.div
      className={`flex w-full gap-4 ${className}`}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24, ease: 'easeOut' }}
    >
      <div className="flex w-4 flex-col items-center shrink-0">
        <span className="signal-dot" />
        <span className="trace-rail mt-2 flex-1" />
      </div>

      <div className="min-w-0 flex-1">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className="mono-label">{ROLE_LABELS[agentType] ?? ROLE_LABELS.default}</span>
          <span
            style={{
              color: 'var(--text-primary)',
              fontSize: 15,
              fontWeight: 600,
              letterSpacing: '-0.02em',
            }}
          >
            {agentName}
          </span>

          {model && (
            <span className="mono-chip">
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

        <div className="rail-panel soft-glow px-5 py-4 md:px-6 md:py-5" style={{ paddingLeft: 36 }}>
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

          <p
            style={{
              marginTop: 14,
              color: 'var(--text-primary)',
              fontSize: 14,
              lineHeight: 1.78,
              whiteSpace: 'pre-wrap',
            }}
          >
            {content}
          </p>
        </div>
      </div>
    </motion.div>
  );
};

export default AgentBubble;
