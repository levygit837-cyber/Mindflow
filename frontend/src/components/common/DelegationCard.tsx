import React from 'react';
import { motion } from 'framer-motion';

type AgentStatus = 'active' | 'pending' | 'done' | 'waiting';

interface DelegatedAgent {
  agentType: 'orchestrator' | 'analyst' | 'coder' | 'researcher';
  agentName: string;
  status: AgentStatus;
}

interface DelegationCardProps {
  title?: string;
  subtitle?: string;
  agents: DelegatedAgent[];
  pipelineLabel?: string;
  className?: string;
}

const STATUS_LABELS: Record<AgentStatus, string> = {
  active: 'running',
  pending: 'pending',
  done: 'done',
  waiting: 'waiting',
};

export const DelegationCard: React.FC<DelegationCardProps> = ({
  title = 'Delegação',
  subtitle = 'Orchestrator delegou a próxima etapa',
  agents,
  pipelineLabel = 'Pipeline',
  className = '',
}) => {
  return (
    <motion.div
      className={`rail-panel ${className}`}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24, ease: 'easeOut' }}
      style={{ padding: '18px 20px 18px 36px' }}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="mono-label">---</span>
        <span style={{ color: 'var(--text-primary)', fontSize: 15, fontWeight: 600 }}>
          {title}
        </span>
        <span className="mono-chip" style={{ marginLeft: 'auto' }}>
          {pipelineLabel}
        </span>
      </div>

      <p
        style={{
          marginTop: 10,
          color: 'var(--text-secondary)',
          fontSize: 13,
          lineHeight: 1.6,
        }}
      >
        {subtitle}
      </p>

      <div
        className="data-surface"
        style={{
          marginTop: 16,
          padding: '14px 16px',
        }}
      >
        <div
          style={{
            color: 'var(--text-meta)',
            fontFamily: 'var(--font-mono)',
            fontSize: 12,
            lineHeight: 1.9,
            whiteSpace: 'pre-wrap',
          }}
        >
          {'Orchestrator'}
        </div>

        <div
          style={{
            marginTop: 10,
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
          }}
        >
          {agents.map((agent, index) => (
            <motion.div
              key={`${agent.agentName}-${index}`}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.18, delay: index * 0.05 }}
              className="flex items-center gap-3"
              style={{
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-mono)',
                fontSize: 12,
              }}
            >
              <span className={`signal-dot ${agent.status === 'active' ? '' : 'idle'}`} />
              <span style={{ color: 'var(--text-meta)' }}>
                {index === agents.length - 1 ? '└─' : '├─'}
              </span>
              <span style={{ minWidth: 0, flex: 1 }}>{agent.agentName}</span>
              <span style={{ color: 'var(--text-meta)' }}>
                {STATUS_LABELS[agent.status]}
              </span>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  );
};

export default DelegationCard;
