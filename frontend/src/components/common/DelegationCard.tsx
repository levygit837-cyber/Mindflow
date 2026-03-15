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
          <span className="mono-label">--- delegation</span>
          <span className="event-title">
            {title}
          </span>
          <span className="event-badge" style={{ marginLeft: 'auto' }}>
            {pipelineLabel}
          </span>
        </div>

        <p
          style={{
            marginTop: 10,
            color: 'var(--text-secondary)',
            fontSize: 13,
            lineHeight: 1.65,
          }}
        >
          {subtitle}
        </p>

        <div className="event-expand">
          <div
            style={{
              color: 'var(--text-meta)',
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
              lineHeight: 1.85,
            }}
          >
            Orchestrator
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
      </div>
    </motion.section>
  );
};

export default DelegationCard;
