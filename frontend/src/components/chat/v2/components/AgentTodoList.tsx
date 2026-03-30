/**
 * AgentTodoList Component
 *
 * Displays the orchestrator's task list during execution.
 * Theme-dependent: only renders in dark theme.
 * Conditional: only renders when isStreaming && delegations.length > 0.
 *
 * Requirements: 9.1, 9.2, 9.3, 9.4
 */

import React from 'react';
import { motion } from 'framer-motion';
import { DelegationCard } from './DelegationCard';
import type { DelegationCardProps } from './DelegationCard';
import { useThemeController } from '../../../theme/useThemeController';
import '../styles.css';

export interface AgentTodoListProps {
  delegations: DelegationCardProps[];
  isStreaming?: boolean;
  className?: string;
}

export const AgentTodoList: React.FC<AgentTodoListProps> = ({
  delegations,
  isStreaming = false,
  className = '',
}) => {
  // Theme-dependent rendering: only render in dark theme (Requirement 9.3)
  const { theme } = useThemeController();

  // Return null for light theme
  if (theme !== 'dark') {
    return null;
  }

  // Conditional rendering: only when isStreaming && delegations.length > 0 (Requirement 9.4)
  if (!isStreaming || delegations.length === 0) {
    return null;
  }

  // Count unique agents
  const agentCount = delegations.reduce((count, delegation) => {
    return count + delegation.agents.length;
  }, 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`agent-todo-list ${className}`}
      data-theme={theme}
      style={{
        background: 'var(--surface-elevated)',
        border: '1px solid var(--line-primary)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--spacing-4)',
        marginBottom: 'var(--spacing-4)',
      }}
    >
      {/* Header with badge */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--spacing-3)',
          marginBottom: 'var(--spacing-3)',
        }}
      >
        <h3
          style={{
            fontSize: '14px',
            fontWeight: 600,
            color: 'var(--text-primary)',
            margin: 0,
          }}
        >
          Tarefas do Orquestrador
        </h3>

        {/* Agent count badge */}
        <span
          style={{
            padding: '2px 8px',
            background: 'var(--agent-orchestrator-color)',
            color: 'white',
            borderRadius: 'var(--radius-sm)',
            fontSize: '11px',
            fontWeight: 500,
          }}
        >
          {agentCount} {agentCount === 1 ? 'agente' : 'agentes'}
        </span>

        {/* Live status badge */}
        <span
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            padding: '2px 8px',
            background: 'var(--state-success)',
            color: 'white',
            borderRadius: 'var(--radius-sm)',
            fontSize: '11px',
            fontWeight: 500,
          }}
        >
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: 'white',
              animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            }}
          />
          ao vivo
        </span>
      </div>

      {/* Delegation cards in flexible layout */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 'var(--spacing-2)',
        }}
      >
        {delegations.map((delegation, index) => (
          <div
            key={index}
            style={{
              flex: '1 1 200px',
              minWidth: '200px',
            }}
          >
            <DelegationCard
              {...delegation}
              variant="simple"
            />
          </div>
        ))}
      </div>
    </motion.div>
  );
};
