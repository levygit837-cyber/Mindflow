/**
 * ThoughtBlock Component
 *
 * Displays agent reasoning with expandable state and token-by-token animation.
 * Features:
 * - Synapse visual (3 nodes + 2 links) with agent accent color
 * - Reasoning Depth Bar (3 segments based on content size)
 * - Header with agent name, status, and chevron
 * - Preview collapsed (first 60 chars)
 * - Body expanded with RichText formatting
 * - Token-by-token animation with framer-motion
 * - Click to expand/collapse
 *
 * Performance: Memoized to prevent unnecessary re-renders during streaming
 */

import React, { useState, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { RichText } from '../../../common/RichText';
import { MindflowV2AgentType } from '../types';
import { getMindflowV2AgentTheme } from '../utils';
import { useThemeController } from '../../../theme/useThemeController';

/**
 * Props for ThoughtBlock component
 * @property {MindflowV2AgentType} agentType - Type of agent (orchestrator, analyst, coder, researcher)
 * @property {string} [title] - Optional title for the thought block
 * @property {string} [status] - Status text (e.g., "thinking", "decision")
 * @property {string} content - Main content of the thought (supports markdown)
 * @property {string} [summary] - Optional summary text
 * @property {boolean} [defaultExpanded] - Whether to start expanded (default: false for content > 300 chars)
 * @property {string} [className] - Additional CSS classes
 */
export interface ThoughtBlockProps {
  agentType: MindflowV2AgentType;
  title?: string;
  status?: string;
  content: string;
  summary?: string;
  defaultExpanded?: boolean;
  className?: string;
}

/**
 * Calculate reasoning depth level (1-3) based on content length
 */
function calculateReasoningDepth(content: string): number {
  const length = content.length;
  if (length < 200) return 1;
  if (length < 500) return 2;
  return 3;
}

/**
 * Determine if thought should be expanded by default
 * Expanded for: decisions or content < 300 chars
 */
function shouldDefaultExpand(content: string, status?: string): boolean {
  if (content.length < 300) return true;
  if (status?.toLowerCase().includes('decision')) return true;
  return false;
}

const ThoughtBlockComponent: React.FC<ThoughtBlockProps> = ({
  agentType,
  title,
  status = 'thinking',
  content,
  summary,
  defaultExpanded,
  className = '',
}) => {
  const agentTheme = getMindflowV2AgentTheme(agentType);
  const { theme } = useThemeController();
  const autoExpanded = defaultExpanded ?? shouldDefaultExpand(content, status);
  const [expanded, setExpanded] = useState(autoExpanded);
  const depth = calculateReasoningDepth(content);

  // Preview: first 60 characters
  const preview = content.length > 60 ? `${content.slice(0, 60)}...` : content;

  const handleToggle = () => {
    setExpanded(!expanded);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      className={`thought-block mindflow-v2-agent-${agentType} ${className}`}
      data-theme={theme}
      style={{
        background: 'var(--mindflow-v2-bg-surface)',
        border: '1px solid var(--mindflow-v2-border-primary)',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
      }}
    >
      {/* Header - clickable to expand/collapse */}
      <button
        onClick={handleToggle}
        className="thought-block-header"
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--spacing-2)',
          padding: 'var(--spacing-3)',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          textAlign: 'left',
          transition: 'background var(--transition-fast)',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'var(--mindflow-v2-bg-hover)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'transparent';
        }}
      >
        {/* Synapse Visual - 3 nodes + 2 links */}
        <div
          className="thought-synapse"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '2px',
            flexShrink: 0,
          }}
        >
          <div
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: agentTheme.accent,
            }}
          />
          <div
            style={{
              width: '8px',
              height: '1px',
              background: agentTheme.accent,
              opacity: 0.5,
            }}
          />
          <div
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: agentTheme.accent,
            }}
          />
          <div
            style={{
              width: '8px',
              height: '1px',
              background: agentTheme.accent,
              opacity: 0.5,
            }}
          />
          <div
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: agentTheme.accent,
            }}
          />
        </div>

        {/* Agent Name and Status */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: 'var(--text-xs)',
              fontFamily: 'var(--font-meta)',
              fontWeight: 600,
              color: agentTheme.accent,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            {title || agentTheme.label}
          </div>
          {status && status !== 'thinking' && (
            <div
              style={{
                fontSize: 'var(--text-xs)',
                fontFamily: 'var(--font-meta)',
                color: 'var(--text-meta)',
                marginTop: '2px',
              }}
            >
              {status}
            </div>
          )}
        </div>

        {/* Chevron Icon */}
        <div style={{ flexShrink: 0, color: 'var(--text-secondary)' }}>
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </div>
      </button>

      {/* Content Area */}
      <AnimatePresence mode="wait">
        {expanded ? (
          // Expanded Body with RichText
          <motion.div
            key="expanded"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.18 }}
            className="thought-body-expanded"
            style={{
              padding: '0 var(--spacing-3) var(--spacing-3) var(--spacing-3)',
            }}
          >
            <RichText
              content={content}
              className="thought-content"
            />
            {summary && (
              <div
                style={{
                  marginTop: 'var(--spacing-2)',
                  padding: 'var(--spacing-2)',
                  background: 'var(--mindflow-v2-bg-muted)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: 'var(--text-sm)',
                  color: 'var(--text-secondary)',
                  fontStyle: 'italic',
                }}
              >
                {summary}
              </div>
            )}
          </motion.div>
        ) : (
          // Collapsed Preview with Depth Bar
          <motion.div
            key="collapsed"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="thought-preview"
            style={{
              padding: '0 var(--spacing-3) var(--spacing-3) var(--spacing-3)',
            }}
          >
            {/* Preview Text */}
            <div
              style={{
                fontSize: 'var(--text-sm)',
                color: 'var(--text-secondary)',
                lineHeight: 1.5,
                marginBottom: 'var(--spacing-2)',
              }}
            >
              {preview}
            </div>

            {/* Reasoning Depth Bar - 3 segments */}
            <div
              className="reasoning-depth-bar"
              style={{
                display: 'flex',
                gap: '4px',
                alignItems: 'center',
              }}
            >
              <div
                style={{
                  fontSize: 'var(--text-xs)',
                  fontFamily: 'var(--font-meta)',
                  color: 'var(--text-meta)',
                  marginRight: '4px',
                }}
              >
                Depth:
              </div>
              {[1, 2, 3].map((level) => (
                <div
                  key={level}
                  style={{
                    width: '24px',
                    height: '4px',
                    borderRadius: '2px',
                    background: level <= depth ? agentTheme.accent : 'var(--mindflow-v2-border-primary)',
                    opacity: level <= depth ? 1 : 0.3,
                    transition: 'all var(--transition-fast)',
                  }}
                />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// Memoize component to prevent unnecessary re-renders during streaming
export const ThoughtBlock = memo(ThoughtBlockComponent);
ThoughtBlock.displayName = 'ThoughtBlock';

export default ThoughtBlock;
