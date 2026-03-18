/**
 * JourneyTimeline Component
 *
 * Displays agent journey with dual layout:
 * - Rail: Vertical timeline with numbered dots and connecting lines
 * - Stage: Detailed visualization of selected step
 *
 * Features:
 * - Status visual indicators (live pulsing, done green, waiting muted, error red)
 * - Step selection in rail
 * - Active step details in stage
 * - Footer with "ao vivo" badge, duration, and summary
 *
 * Requirements: 12.2, 12.3, 12.5
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock, CheckCircle2, AlertCircle, Loader2, Circle } from 'lucide-react';
import { MindflowV2AgentType } from '../types';
import { getMindflowV2AgentTheme } from '../utils';
import { useThemeController } from '../../../theme/useThemeController';

export interface JourneyStep {
  id: string;
  title: string;
  detail: string;
  status: 'live' | 'done' | 'queued' | 'waiting' | 'error';
  agentType?: MindflowV2AgentType;
  meta?: string;
}

export interface JourneyTimelineProps {
  title?: string;
  subtitle?: string;
  steps: JourneyStep[];
  summary?: string;
  durationLabel?: string;
  liveLabel?: string;
  activeStepId?: string;
  className?: string;
}

/**
 * Get status color based on step status
 */
function getStatusColor(status: JourneyStep['status']): string {
  switch (status) {
    case 'live':
      return '#5B6ABF'; // Blue for active
    case 'done':
      return '#2D8F5E'; // Green for completed
    case 'error':
      return '#C75D2C'; // Orange/red for error
    case 'waiting':
    case 'queued':
      return '#6B7280'; // Muted gray for waiting
    default:
      return '#6B7280';
  }
}

/**
 * Get status icon based on step status
 */
function getStatusIcon(status: JourneyStep['status'], size: number = 16) {
  switch (status) {
    case 'live':
      return <Loader2 size={size} className="journey-step-icon-spin" />;
    case 'done':
      return <CheckCircle2 size={size} />;
    case 'error':
      return <AlertCircle size={size} />;
    case 'waiting':
    case 'queued':
      return <Circle size={size} />;
    default:
      return <Circle size={size} />;
  }
}

export const JourneyTimeline: React.FC<JourneyTimelineProps> = ({
  title,
  subtitle,
  steps,
  summary,
  durationLabel,
  liveLabel = 'ao vivo',
  activeStepId,
  className = '',
}) => {
  const { theme } = useThemeController();
  // Track selected step for stage display
  const [selectedStepId, setSelectedStepId] = useState<string | null>(
    activeStepId || (steps.length > 0 ? steps[0].id : null)
  );

  const selectedStep = steps.find((s) => s.id === selectedStepId) || steps[0];
  const hasLiveStep = steps.some((s) => s.status === 'live');

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`journey-timeline ${className}`}
      data-theme={theme}
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--line-primary)',
        borderRadius: 'var(--radius-lg)',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      {(title || subtitle) && (
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
        </div>
      )}

      {/* Dual Layout: Rail + Stage */}
      <div
        style={{
          display: 'flex',
          minHeight: '200px',
          maxHeight: '400px',
        }}
      >
        {/* Rail: Timeline list */}
        <div
          className="journey-rail"
          style={{
            width: '200px',
            borderRight: '1px solid var(--line-primary)',
            overflowY: 'auto',
            padding: 'var(--spacing-3)',
          }}
        >
          {steps.map((step, index) => {
            const isSelected = step.id === selectedStepId;
            const statusColor = getStatusColor(step.status);
            const theme = step.agentType ? getMindflowV2AgentTheme(step.agentType) : null;
            const accentColor = theme?.accent || statusColor;

            return (
              <div key={step.id} style={{ position: 'relative' }}>
                {/* Connecting line */}
                {index < steps.length - 1 && (
                  <div
                    key={`line-${step.id}`}
                    style={{
                      position: 'absolute',
                      left: '11px',
                      top: '28px',
                      width: '2px',
                      height: 'calc(100% - 8px)',
                      background: 'var(--line-primary)',
                    }}
                  />
                )}

                {/* Step card */}
                <button
                  onClick={() => setSelectedStepId(step.id)}
                  className="journey-rail-step"
                  style={{
                    position: 'relative',
                    width: '100%',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 'var(--spacing-2)',
                    padding: 'var(--spacing-2)',
                    marginBottom: 'var(--spacing-2)',
                    background: isSelected ? `${accentColor}10` : 'transparent',
                    border: isSelected ? `1px solid ${accentColor}` : '1px solid transparent',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.background = 'var(--surface-elevated)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.background = 'transparent';
                    }
                  }}
                >
                  {/* Numbered dot with status */}
                  <div
                    style={{
                      position: 'relative',
                      width: '24px',
                      height: '24px',
                      borderRadius: '50%',
                      background: statusColor,
                      color: 'white',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '11px',
                      fontWeight: 600,
                      flexShrink: 0,
                      animation: step.status === 'live' ? 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' : 'none',
                    }}
                  >
                    {index + 1}
                  </div>

                  {/* Step info */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: '12px',
                        fontWeight: 500,
                        color: isSelected ? accentColor : 'var(--text-primary)',
                        marginBottom: '2px',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {step.title}
                    </div>
                    <div
                      style={{
                        fontSize: '11px',
                        color: 'var(--text-meta)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      {getStatusIcon(step.status, 10)}
                      <span>{step.status}</span>
                    </div>
                  </div>
                </button>
              </div>
            );
          })}
        </div>

        {/* Stage: Detailed view of selected step */}
        <div
          className="journey-stage"
          style={{
            flex: 1,
            padding: 'var(--spacing-4)',
            overflowY: 'auto',
          }}
        >
          <AnimatePresence mode="wait">
            {selectedStep && (
              <motion.div
                key={selectedStep.id}
                initial={{ opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8 }}
                transition={{ duration: 0.18 }}
              >
                {/* Step header */}
                <div style={{ marginBottom: 'var(--spacing-3)' }}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 'var(--spacing-2)',
                      marginBottom: 'var(--spacing-2)',
                    }}
                  >
                    <div
                      style={{
                        color: getStatusColor(selectedStep.status),
                        display: 'flex',
                        alignItems: 'center',
                      }}
                    >
                      {getStatusIcon(selectedStep.status, 20)}
                    </div>
                    <h3
                      style={{
                        fontSize: '16px',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                        margin: 0,
                      }}
                    >
                      {selectedStep.title}
                    </h3>
                  </div>

                  {/* Agent type badge */}
                  {selectedStep.agentType && (
                    <div
                      style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        background: `${getMindflowV2AgentTheme(selectedStep.agentType).accent}15`,
                        color: getMindflowV2AgentTheme(selectedStep.agentType).accent,
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '11px',
                        fontWeight: 500,
                        marginBottom: 'var(--spacing-2)',
                      }}
                    >
                      {getMindflowV2AgentTheme(selectedStep.agentType).label}
                    </div>
                  )}
                </div>

                {/* Step detail */}
                <div
                  style={{
                    fontSize: '13px',
                    color: 'var(--text-secondary)',
                    lineHeight: 1.6,
                    marginBottom: 'var(--spacing-3)',
                  }}
                >
                  {selectedStep.detail}
                </div>

                {/* Step meta */}
                {selectedStep.meta && (
                  <div
                    style={{
                      padding: 'var(--spacing-2) var(--spacing-3)',
                      background: 'var(--surface-elevated)',
                      border: '1px solid var(--line-primary)',
                      borderRadius: 'var(--radius-md)',
                      fontSize: '12px',
                      color: 'var(--text-meta)',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    {selectedStep.meta}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          padding: 'var(--spacing-3) var(--spacing-4)',
          borderTop: '1px solid var(--line-primary)',
          background: 'var(--surface-elevated)',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--spacing-3)',
          fontSize: '12px',
        }}
      >
        {/* Live badge */}
        {hasLiveStep && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 8px',
              background: '#5B6ABF15',
              color: '#5B6ABF',
              borderRadius: 'var(--radius-sm)',
              fontWeight: 500,
            }}
          >
            <div
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: '#5B6ABF',
                animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
              }}
            />
            {liveLabel}
          </div>
        )}

        {/* Duration */}
        {durationLabel && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              color: 'var(--text-meta)',
            }}
          >
            <Clock size={12} />
            {durationLabel}
          </div>
        )}

        {/* Summary */}
        {summary && (
          <div
            style={{
              flex: 1,
              color: 'var(--text-secondary)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {summary}
          </div>
        )}
      </div>

      {/* CSS for animations */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        .journey-step-icon-spin {
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .journey-rail::-webkit-scrollbar,
        .journey-stage::-webkit-scrollbar {
          width: 6px;
        }

        .journey-rail::-webkit-scrollbar-track,
        .journey-stage::-webkit-scrollbar-track {
          background: transparent;
        }

        .journey-rail::-webkit-scrollbar-thumb,
        .journey-stage::-webkit-scrollbar-thumb {
          background: var(--line-primary);
          border-radius: 3px;
        }

        .journey-rail::-webkit-scrollbar-thumb:hover,
        .journey-stage::-webkit-scrollbar-thumb:hover {
          background: var(--text-meta);
        }
      `}</style>
    </motion.div>
  );
};
