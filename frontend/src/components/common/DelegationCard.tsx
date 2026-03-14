import React from 'react';
import { motion } from 'framer-motion';
import { GitBranch, Clock } from 'lucide-react';

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

// Per-agent design tokens for delegation card
const AGENT_DOT_COLORS: Record<string, string> = {
  orchestrator: '#8B5CF6',
  analyst: '#F59E0B',
  coder: '#4ADE80',
  researcher: '#22D3EE',
};

const AGENT_STATUS_CONFIGS: Record<AgentStatus, {
  label: string;
  dotColor: string;
  bgColor: string;
  textColor: string;
}> = {
  active: { label: 'Active', dotColor: '#22D3EE', bgColor: '#031118', textColor: '#22D3EE' },
  pending: { label: 'Pending', dotColor: '#4D4575', bgColor: '#0D0D1A', textColor: '#4D4575' },
  done: { label: 'Done', dotColor: '#10B981', bgColor: '#041208', textColor: '#10B981' },
  waiting: { label: 'Waiting', dotColor: '#F59E0B', bgColor: '#150D04', textColor: '#F59E0B' },
};

export const DelegationCard: React.FC<DelegationCardProps> = ({
  title = 'Task Delegation',
  subtitle = 'Routing to specialized agents',
  agents,
  pipelineLabel = 'Pipeline',
  className = '',
}) => {
  return (
    <motion.div
      className={`rounded-xl overflow-hidden ${className}`}
      style={{ backgroundColor: '#0E0820' }}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
    >
      {/* Header — matches delHeader #160D36 */}
      <div
        className="flex items-center justify-between px-4 py-3"
        style={{ backgroundColor: '#160D36' }}
      >
        <div className="flex items-center gap-2.5">
          <GitBranch className="w-4 h-4" style={{ color: '#8B5CF6' }} />
          <div>
            <div
              className="text-[13px] font-semibold leading-tight"
              style={{ color: '#EDE9FF', fontFamily: 'var(--font-brand)' }}
            >
              {title}
            </div>
            <div
              className="text-[11px]"
              style={{ color: '#8B81C0', fontFamily: 'var(--font-meta)' }}
            >
              {subtitle}
            </div>
          </div>
        </div>

        {/* Processing badge */}
        <div
          className="flex items-center gap-1.5 px-2 py-1 rounded-full"
          style={{ backgroundColor: '#1D1840' }}
        >
          <motion.span
            className="w-1.5 h-1.5 rounded-full"
            style={{ backgroundColor: '#8B5CF6' }}
            animate={{ opacity: [1, 0.4, 1] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
          />
          <span
            className="text-[11px] font-medium"
            style={{ color: '#8B5CF6', fontFamily: 'var(--font-brand)' }}
          >
            Processing
          </span>
        </div>
      </div>

      {/* Body — agent rows */}
      <div className="px-4 py-3 space-y-2.5">
        {agents.map((agent, i) => {
          const dotColor = AGENT_DOT_COLORS[agent.agentType] ?? '#4D4575';
          const statusConfig = AGENT_STATUS_CONFIGS[agent.status];

          return (
            <motion.div
              key={agent.agentName}
              className="flex items-center gap-2"
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.22, delay: i * 0.07 }}
            >
              {/* Agent dot */}
              <span
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: dotColor }}
              />

              {/* Agent name */}
              <span
                className="text-[13px] font-medium flex-1"
                style={{
                  color: agent.status === 'pending' ? '#8B81C0' : '#EDE9FF',
                  fontFamily: 'var(--font-brand)',
                }}
              >
                {agent.agentName}
              </span>

              {/* Status badge */}
              <div
                className="flex items-center gap-1 px-1.5 py-0.5 rounded"
                style={{ backgroundColor: statusConfig.bgColor }}
              >
                <span
                  className="w-1.5 h-1.5 rounded-full"
                  style={{ backgroundColor: statusConfig.dotColor }}
                />
                <span
                  className="text-[11px] font-medium"
                  style={{ color: statusConfig.textColor, fontFamily: 'var(--font-brand)' }}
                >
                  {statusConfig.label}
                </span>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Divider */}
      <div className="mx-4" style={{ height: 1, backgroundColor: '#1A1545' }} />

      {/* Footer */}
      <div
        className="flex items-center gap-2 px-4 py-2.5"
      >
        <Clock className="w-3.5 h-3.5 flex-shrink-0" style={{ color: '#4D4575' }} />
        <span
          className="text-[11px] flex-1"
          style={{ color: '#4D4575', fontFamily: 'var(--font-meta)' }}
        >
          Orchestrated task execution
        </span>
        <div
          className="px-2 py-0.5 rounded"
          style={{ backgroundColor: '#160D36' }}
        >
          <span
            className="text-[11px] font-medium"
            style={{ color: '#8B5CF6', fontFamily: 'var(--font-brand)' }}
          >
            {pipelineLabel}
          </span>
        </div>
      </div>
    </motion.div>
  );
};

export default DelegationCard;
