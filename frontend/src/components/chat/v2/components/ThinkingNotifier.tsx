/**
 * Chat Visualization V2 - ThinkingNotifier Component
 *
 * Displays a compact pill indicator showing which agent is active or waiting.
 * Features pulse animation for active agents and accent colors based on agent type.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { getMindflowV2AgentTheme, type MindflowV2AgentType } from '../index';
import { useThemeController } from '../../../theme/useThemeController';

export interface ThinkingNotifierProps {
  agentType: MindflowV2AgentType;
  active?: boolean;
  status?: string;
  className?: string;
}

/**
 * Format status text for display
 * Maps common status values to Portuguese labels
 */
function formatStatus(status: string | undefined, active: boolean): string {
  if (!status) {
    return active ? 'pensando' : 'aguardando';
  }

  const normalized = status.toLowerCase().trim();

  if (normalized === 'thinking' || normalized === 'processing') {
    return 'pensando';
  }

  if (normalized === 'waiting' || normalized === 'queued') {
    return 'aguardando';
  }

  if (normalized === 'active' || normalized === 'running') {
    return 'ativo';
  }

  if (normalized === 'done' || normalized === 'completed') {
    return 'concluído';
  }

  return status;
}

export const ThinkingNotifier: React.FC<ThinkingNotifierProps> = ({
  agentType,
  active = false,
  status,
  className = '',
}) => {
  const agentTheme = getMindflowV2AgentTheme(agentType);
  const { theme } = useThemeController();
  const formattedStatus = formatStatus(status, active);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.18 }}
      className={`mindflow-v2-thinking-notifier ${className}`}
      data-agent-type={agentType}
      data-active={active}
      data-theme={theme}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '4px 10px',
        borderRadius: '999px',
        fontSize: '0.75rem',
        fontFamily: 'var(--font-meta)',
        fontWeight: 500,
        backgroundColor: active ? `${agentTheme.accent}15` : 'var(--surface-glass)',
        border: `1px solid ${active ? agentTheme.accent : 'var(--line-primary)'}`,
        color: active ? agentTheme.accent : 'var(--text-meta)',
        opacity: active ? 1 : 0.6,
        transition: 'all 0.2s ease',
      }}
    >
      {/* Pulse dot for active state */}
      <span
        className={active ? 'mindflow-v2-pulse' : ''}
        style={{
          display: 'inline-block',
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          backgroundColor: active ? agentTheme.accent : 'var(--text-meta)',
        }}
      />

      {/* Agent label */}
      <span style={{ whiteSpace: 'nowrap' }}>
        {agentTheme.shortLabel}
      </span>

      {/* Status text */}
      <span
        style={{
          fontSize: '0.7rem',
          opacity: 0.8,
          whiteSpace: 'nowrap',
        }}
      >
        {formattedStatus}
      </span>
    </motion.div>
  );
};

ThinkingNotifier.displayName = 'ThinkingNotifier';
