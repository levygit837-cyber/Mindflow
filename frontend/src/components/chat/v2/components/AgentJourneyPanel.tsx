/**
 * AgentJourneyPanel Component
 *
 * Fixed side panel that displays detailed agent journey with timeline.
 * Features:
 * - Slide-from-right animation (380px width)
 * - Backdrop overlay
 * - "Delegation Received" as first step
 * - Integrated JourneyTimeline component
 * - Scrollable area with vertical scroll
 * - Close button
 * - Supports multiple panels side by side
 *
 * Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6
 */

import React, { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { DelegationCardProps } from './DelegationCard';
import { JourneyTimeline, JourneyStep } from './JourneyTimeline';
import { getMindflowV2AgentTheme } from '../utils';
import { useThemeController } from '../../../theme/useThemeController';

export interface AgentJourneyPanelProps {
  delegation: DelegationCardProps;
  steps: JourneyStep[];
  isStreaming?: boolean;
  onClose: () => void;
  className?: string;
}

/**
 * AgentJourneyPanel - Side panel with agent journey visualization
 */
export const AgentJourneyPanel: React.FC<AgentJourneyPanelProps> = ({
  delegation,
  steps,
  isStreaming = false,
  onClose,
  className = '',
}) => {
  const { theme } = useThemeController();
  // Add "Delegation Received" as first step if not already present
  const enrichedSteps = useMemo(() => {
    const hasInitialStep = steps.some(
      (s) => s.title.toLowerCase().includes('delegation') || s.title.toLowerCase().includes('received')
    );

    if (hasInitialStep) {
      return steps;
    }

    // Get agent type from delegation
    const firstAgent = delegation.agents[0];
    const agentType = firstAgent?.agentType;

    const initialStep: JourneyStep = {
      id: 'delegation-received',
      title: 'Delegation Received',
      detail: `Task delegated to ${firstAgent?.name || 'agent'} for execution`,
      status: 'done',
      agentType,
      meta: delegation.subtitle || delegation.title,
    };

    return [initialStep, ...steps];
  }, [steps, delegation]);

  // Get primary accent color from delegation
  const primaryAgent = delegation.agents[0];
  const agentTheme = primaryAgent?.agentType
    ? getMindflowV2AgentTheme(primaryAgent.agentType)
    : null;
  const accentColor = delegation.accent || agentTheme?.accent || '#0D6E6E';

  return (
    <AnimatePresence>
      <div className={`agent-journey-panel-container ${className}`}>
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={onClose}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.3)',
            zIndex: 1000,
          }}
        />

        {/* Side Panel */}
        <motion.div
          initial={{ x: 380, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 380, opacity: 0 }}
          transition={{ duration: 0.22, ease: 'easeOut' }}
          className="agent-journey-panel"
          data-theme={theme}
          style={{
            position: 'fixed',
            top: 0,
            right: 0,
            width: '380px',
            height: '100vh',
            background: 'var(--surface)',
            borderLeft: '1px solid var(--line-primary)',
            boxShadow: '-4px 0 12px rgba(0, 0, 0, 0.1)',
            zIndex: 1001,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: 'var(--spacing-4)',
              borderBottom: '1px solid var(--line-primary)',
              background: 'var(--surface-elevated)',
              flexShrink: 0,
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                marginBottom: 'var(--spacing-2)',
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <h2
                  style={{
                    fontSize: '16px',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    margin: 0,
                    marginBottom: '4px',
                  }}
                >
                  {delegation.title || 'Agent Journey'}
                </h2>
                {delegation.subtitle && (
                  <p
                    style={{
                      fontSize: '13px',
                      color: 'var(--text-secondary)',
                      margin: 0,
                    }}
                  >
                    {delegation.subtitle}
                  </p>
                )}
              </div>

              {/* Close button */}
              <button
                onClick={onClose}
                aria-label="Close journey panel"
                style={{
                  width: '32px',
                  height: '32px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'transparent',
                  border: '1px solid var(--line-primary)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-meta)',
                  cursor: 'pointer',
                  flexShrink: 0,
                  transition: 'all 0.15s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'var(--surface)';
                  e.currentTarget.style.borderColor = accentColor;
                  e.currentTarget.style.color = accentColor;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.borderColor = 'var(--line-primary)';
                  e.currentTarget.style.color = 'var(--text-meta)';
                }}
              >
                <X size={16} />
              </button>
            </div>

            {/* Agent list */}
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 'var(--spacing-2)',
                marginTop: 'var(--spacing-3)',
              }}
            >
              {delegation.agents.map((agent, index) => {
                const agentTheme = agent.agentType
                  ? getMindflowV2AgentTheme(agent.agentType)
                  : null;
                const agentAccent = agent.accent || agentTheme?.accent || accentColor;

                return (
                  <div
                    key={index}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '4px 10px',
                      background: `${agentAccent}15`,
                      border: `1px solid ${agentAccent}30`,
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '12px',
                    }}
                  >
                    <div
                      style={{
                        width: '6px',
                        height: '6px',
                        borderRadius: '50%',
                        background: agentAccent,
                      }}
                    />
                    <span style={{ color: agentAccent, fontWeight: 500 }}>
                      {agent.name}
                    </span>
                    <span style={{ color: 'var(--text-meta)', fontSize: '11px' }}>
                      {agent.status}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Scrollable content area */}
          <div
            className="agent-journey-content"
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: 'var(--spacing-4)',
            }}
          >
            {/* Journey Timeline */}
            <JourneyTimeline
              steps={enrichedSteps}
              summary={delegation.summary}
              liveLabel={isStreaming ? 'ao vivo' : undefined}
            />
          </div>

          {/* CSS for scrollbar */}
          <style>{`
            .agent-journey-content::-webkit-scrollbar {
              width: 6px;
            }

            .agent-journey-content::-webkit-scrollbar-track {
              background: transparent;
            }

            .agent-journey-content::-webkit-scrollbar-thumb {
              background: var(--line-primary);
              border-radius: 3px;
            }

            .agent-journey-content::-webkit-scrollbar-thumb:hover {
              background: var(--text-meta);
            }
          `}</style>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
