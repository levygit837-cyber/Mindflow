/**
 * Chat Visualization V2 - ThinkingNotifierRow Component
 *
 * Renders a row of ThinkingNotifier pills showing all active and waiting agents.
 * Uses flexible layout with wrap for responsive display.
 */

import React from 'react';
import { ThinkingNotifier } from './ThinkingNotifier';
import { MINDFLOW_V2_AGENT_ORDER, type MindflowV2AgentType } from '../index';

export interface ThinkingNotifierRowProps {
  activeAgents: MindflowV2AgentType[];
  statuses?: Partial<Record<MindflowV2AgentType, string>>;
  className?: string;
}

export const ThinkingNotifierRow: React.FC<ThinkingNotifierRowProps> = ({
  activeAgents,
  statuses = {},
  className = '',
}) => {
  // Show all agent types in order, marking which are active
  const agentsToShow = MINDFLOW_V2_AGENT_ORDER;

  return (
    <div
      className={`mindflow-v2-thinking-notifier-row ${className}`}
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '8px',
        alignItems: 'center',
      }}
    >
      {agentsToShow.map((agentType) => {
        const isActive = activeAgents.includes(agentType);
        const status = statuses[agentType];

        return (
          <ThinkingNotifier
            key={agentType}
            agentType={agentType}
            active={isActive}
            status={status}
          />
        );
      })}
    </div>
  );
};

ThinkingNotifierRow.displayName = 'ThinkingNotifierRow';
