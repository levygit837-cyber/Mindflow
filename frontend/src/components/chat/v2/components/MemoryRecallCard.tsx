/**
 * MemoryRecallCard Component
 *
 * Displays memory recall events with theme-dependent rendering.
 * Only renders in dark theme as per requirements.
 *
 * Requirements: 8.1, 8.2, 8.3
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Database, Search } from 'lucide-react';
import { resolveMindflowV2Tone } from '../utils';
import { useThemeController } from '../../../theme/useThemeController';
import '../styles.css';

export interface MemoryRecallCardProps {
  source: 'vector' | 'database';
  status: string;
  label?: string;
  count?: number;
  detail?: string;
  agentName?: string;
  done?: boolean;
  className?: string;
}

export const MemoryRecallCard: React.FC<MemoryRecallCardProps> = ({
  source,
  status,
  label,
  count,
  detail,
  agentName,
  done = false,
  className = '',
}) => {
  // Theme-dependent rendering: only render in dark theme
  const { theme } = useThemeController();

  // Return null for light theme (Requirement 8.3)
  if (theme !== 'dark') {
    return null;
  }

  // Determine icon based on source
  const Icon = source === 'database' ? Database : Search;

  // Determine tone based on source
  const tone = source === 'database' ? 'info' : 'accent';
  const toneClass = `mindflow-v2-tone-${tone}`;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      className={`memory-recall-card ${toneClass} ${className}`}
      data-theme={theme}
      style={{
        background: 'var(--tone-bg)',
        border: '1px solid var(--tone-color)',
        borderRadius: 'var(--radius-md)',
        padding: 'var(--spacing-3)',
      }}
    >
      {/* Header */}
      <div className="flex items-start gap-3">
        <div
          className="flex-shrink-0 p-2 rounded"
          style={{
            background: 'var(--tone-color)',
            color: 'white',
            opacity: done ? 1 : 0.7,
          }}
        >
          <Icon size={16} />
        </div>

        <div className="flex-1">
          {/* Title */}
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm">
              {label || (source === 'database' ? 'Database Recall' : 'Vector Search')}
            </span>
            {count !== undefined && count > 0 && (
              <span
                className="text-xs font-mono px-2 py-0.5 rounded"
                style={{
                  background: 'var(--tone-color)',
                  color: 'white',
                  opacity: 0.9,
                }}
              >
                {count}
              </span>
            )}
          </div>

          {/* Status */}
          <div className="text-meta text-xs mt-1">
            {status}
            {agentName && ` • ${agentName}`}
          </div>

          {/* Detail preview */}
          {detail && (
            <div className="mt-2 text-sm opacity-80">
              {detail}
            </div>
          )}
        </div>

        {/* Done indicator */}
        {done && (
          <div
            className="flex-shrink-0 w-2 h-2 rounded-full"
            style={{ background: 'var(--state-success)' }}
          />
        )}
      </div>
    </motion.div>
  );
};
