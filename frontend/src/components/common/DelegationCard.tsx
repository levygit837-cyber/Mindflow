import React, { type CSSProperties } from 'react';
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

const STATUS_TITLES: Record<AgentStatus, string> = {
  active: 'em execução',
  pending: 'pendente',
  done: 'pronto',
  waiting: 'aguardando',
};

const AGENT_ACCENTS: Record<DelegatedAgent['agentType'], string> = {
  orchestrator: 'var(--signal-synapse)',
  analyst: '#F59E0B',
  coder: '#4ADE80',
  researcher: '#22D3EE',
};

export const DelegationCard: React.FC<DelegationCardProps> = ({
  title = 'Delegação',
  subtitle = 'Orchestrator delegou a próxima etapa',
  agents,
  pipelineLabel = 'Pipeline',
  className = '',
}) => {
  const activeAgents = agents.filter((agent) => agent.status === 'active').length;
  const footerLabel = `${agents.length} ${agents.length === 1 ? 'agente' : 'agentes'}${
    activeAgents > 0 ? ` · ${activeAgents} ativo${activeAgents > 1 ? 's' : ''}` : ''
  }`;

  return (
    <motion.section
      className={`event-shell w-full ${className}`}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24, ease: 'easeOut' }}
    >
      <div className="event-track">
        <span className={activeAgents > 0 ? 'signal-dot' : 'signal-dot idle'} />
      </div>

      <div className="delegation-card">
        <div className="delegation-card-header">
          <div className="delegation-card-copy">
            <span className="mono-label">delegation</span>
            <span className="delegation-card-title">{title}</span>
            <p className="delegation-card-subtitle">{subtitle}</p>
          </div>

          <span className="delegation-card-pipeline">{pipelineLabel}</span>
        </div>

        <div className="delegation-card-body">
          {agents.map((agent, index) => (
            <motion.div
              key={`${agent.agentName}-${index}`}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.18, delay: index * 0.05 }}
              className="delegation-agent-row"
              style={
                {
                  '--delegation-row-accent': AGENT_ACCENTS[agent.agentType],
                } as CSSProperties
              }
            >
              <div className="delegation-agent-line">
                <span className={`signal-dot ${agent.status === 'active' ? '' : 'idle'}`} />
                <span className="delegation-agent-branch">
                  {index === agents.length - 1 ? '└─' : '├─'}
                </span>
                <span className="delegation-agent-name">{agent.agentName}</span>
              </div>

              <div className="delegation-agent-meta">
                <span className="delegation-agent-role">{agent.agentType}</span>
                <span className="delegation-agent-status">{STATUS_TITLES[agent.status]}</span>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="delegation-card-divider" />

        <div className="delegation-card-footer">
          <span className="delegation-card-footer-copy">{footerLabel}</span>
          <span className="delegation-card-footer-tag">{STATUS_LABELS[agents.at(-1)?.status ?? 'waiting']}</span>
        </div>
      </div>
    </motion.section>
  );
};

export default DelegationCard;
