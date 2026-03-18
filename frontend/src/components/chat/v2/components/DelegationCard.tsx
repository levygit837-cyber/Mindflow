/**
 * DelegationCard Component
 *
 * Displays delegation information with two variants:
 * - Simple: Compact version for todo-list (origin → target with status badge)
 * - Rich: Full version with header, agent list, summary, and journey button
 *
 * Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
 * Performance: Memoized to prevent unnecessary re-renders
 */

import React, { memo } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, ExternalLink } from 'lucide-react';
import { MindflowV2AgentType, getMindflowV2AgentTheme } from '../index';
import { useThemeController } from '../../../theme/useThemeController';
import '../styles.css';

/**
 * Agent row in delegation card
 */
export interface DelegationAgentRow {
  name: string;
  role: string;
  status: string;
  accent?: string;
  agentType?: MindflowV2AgentType;
}

/**
 * Props for DelegationCard component
 */
export interface DelegationCardProps {
  title?: string;
  subtitle?: string;
  status?: string;
  pipeline?: string;
  summary?: string;
  agents: DelegationAgentRow[];
  variant?: 'simple' | 'rich';
  accent?: string;
  onOpenJourney?: () => void;
  className?: string;
}

const DelegationCardComponent: React.FC<DelegationCardProps> = ({
  title,
  subtitle,
  status,
  pipeline,
  summary,
  agents,
  variant = 'rich',
  accent,
  onOpenJourney,
  className = '',
}) => {
  const { theme } = useThemeController();

  if (agents.length === 0) {
    return null;
  }

  // Simple variant: compact for todo-list
  if (variant === 'simple') {
    const firstAgent = agents[0];
    const agentTheme = firstAgent.agentType
      ? getMindflowV2AgentTheme(firstAgent.agentType)
      : null;
    const agentAccent = firstAgent.accent || agentTheme?.accent || accent || '#0D6E6E';

    return (
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.15 }}
        className={`simple-delegation-card ${className}`}
        data-theme={theme}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--spacing-2)',
          padding: 'var(--spacing-2) var(--spacing-3)',
          background: 'var(--surface-elevated)',
          border: '1px solid var(--line-primary)',
          borderRadius: 'var(--radius-md)',
          fontSize: '13px',
        }}
      >
        {/* Origin role */}
        <span style={{ color: 'var(--text-meta)', fontSize: '12px' }}>
          {firstAgent.role}
        </span>

        {/* Arrow */}
        <ArrowRight size={14} style={{ color: 'var(--text-meta)', opacity: 0.5 }} />

        {/* Target agent */}
        <span style={{ color: agentAccent, fontWeight: 500 }}>
          {firstAgent.name}
        </span>

        {/* Status badge */}
        <span
          style={{
            marginLeft: 'auto',
            padding: '2px 8px',
            background: `${agentAccent}15`,
            color: agentAccent,
            borderRadius: 'var(--radius-sm)',
            fontSize: '11px',
            fontWeight: 500,
          }}
        >
          {firstAgent.status}
        </span>
      </motion.div>
    );
  }

  // Rich variant: full version
  const primaryAccent = accent || agents[0]?.accent || '#0D6E6E';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`delegation-card ${className}`}
      data-theme={theme}
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--line-primary)',
        borderRadius: 'var(--radius-lg)',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      {(title || subtitle || status) && (
        <div
          style={{
            padding: 'var(--spacing-3) var(--spacing-4)',
            borderBottom: '1px solid var(--line-primary)',
            background: 'var(--surface-elevated)',
          }}
        >
          {title && (
            <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>
              {title}
            </div>
          )}
          {subtitle && (
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              {subtitle}
            </div>
          )}
          {status && (
            <div
              style={{
                marginTop: '8px',
                fontSize: '12px',
                color: 'var(--text-meta)',
              }}
            >
              {status}
            </div>
          )}
        </div>
      )}

      {/* Agent list */}
      <div style={{ padding: 'var(--spacing-3) var(--spacing-4)' }}>
        {agents.map((agent, index) => {
          const agentTheme = agent.agentType
            ? getMindflowV2AgentTheme(agent.agentType)
            : null;
          const agentAccent = agent.accent || agentTheme?.accent || primaryAccent;

          return (
            <div
              key={index}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--spacing-3)',
                padding: 'var(--spacing-2) 0',
                borderBottom:
                  index < agents.length - 1 ? '1px solid var(--line-primary)' : 'none',
              }}
            >
              {/* Agent indicator */}
              <div
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: agentAccent,
                  flexShrink: 0,
                }}
              />

              {/* Agent info */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 500, fontSize: '13px', color: agentAccent }}>
                  {agent.name}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-meta)' }}>
                  {agent.role}
                </div>
              </div>

              {/* Status */}
              <div
                style={{
                  padding: '2px 8px',
                  background: `${agentAccent}15`,
                  color: agentAccent,
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '11px',
                  fontWeight: 500,
                  flexShrink: 0,
                }}
              >
                {agent.status}
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary bar */}
      {summary && (
        <div
          style={{
            padding: 'var(--spacing-3) var(--spacing-4)',
            background: 'var(--surface-elevated)',
            borderTop: '1px solid var(--line-primary)',
            fontSize: '12px',
            color: 'var(--text-secondary)',
          }}
        >
          {summary}
        </div>
      )}

      {/* Journey button */}
      {onOpenJourney && (
        <div
          style={{
            padding: 'var(--spacing-3) var(--spacing-4)',
            borderTop: '1px solid var(--line-primary)',
          }}
        >
          <button
            onClick={onOpenJourney}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--spacing-2)',
              padding: 'var(--spacing-2) var(--spacing-3)',
              background: 'transparent',
              border: '1px solid var(--line-primary)',
              borderRadius: 'var(--radius-md)',
              color: primaryAccent,
              fontSize: '12px',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = `${primaryAccent}10`;
              e.currentTarget.style.borderColor = primaryAccent;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.borderColor = 'var(--line-primary)';
            }}
          >
            percurso
            <ExternalLink size={12} />
          </button>
        </div>
      )}
    </motion.div>
  );
};

// Memoize component to prevent unnecessary re-renders
export const DelegationCard = memo(DelegationCardComponent);
DelegationCard.displayName = 'DelegationCard';
