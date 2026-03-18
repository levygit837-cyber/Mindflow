/**
 * ToolEventCard Component
 *
 * Displays tool call events with expandable/collapsible states.
 * Supports specialized visualizations for different tool types.
 *
 * Requirements: 13.1, 13.2, 13.3, 14.1, 14.2, 14.3, 14.4
 * Performance: Memoized to prevent unnecessary re-renders
 */

import React, { useState, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, AlertCircle, Loader2, ChevronDown, ChevronRight } from 'lucide-react';
import { formatMindflowV2Value, summarizeMindflowV2Value } from '../utils';
import { useThemeController } from '../../../theme/useThemeController';
import '../styles.css';

/**
 * Props for ToolEventCard component
 */
export interface ToolEventCardProps {
  toolName: string;
  status: 'running' | 'completed' | 'error' | 'collapsed';
  args?: unknown;
  result?: unknown;
  error?: string;
  elapsed?: string;
  agentName?: string;
  className?: string;
}

const ToolEventCardComponent: React.FC<ToolEventCardProps> = ({
  toolName,
  status,
  args,
  result,
  error,
  elapsed,
  agentName,
  className = '',
}) => {
  const { theme } = useThemeController();
  const [expanded, setExpanded] = useState(status !== 'collapsed');

  const handleToggle = () => {
    setExpanded(!expanded);
  };

  const getIcon = () => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 size={16} className="text-success" />;
      case 'error':
        return <AlertCircle size={16} className="text-error" />;
      case 'running':
        return <Loader2 size={16} className="mindflow-v2-pulse text-info" />;
      default:
        return <ChevronRight size={16} className="text-meta" />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'completed':
        return 'border-success';
      case 'error':
        return 'border-error';
      case 'running':
        return 'border-info';
      default:
        return 'border-primary';
    }
  };

  const renderSpecializedVisualization = () => {
    const normalizedToolName = toolName.toLowerCase();

    // Read Tool specialized visualization
    if (normalizedToolName.includes('read') || normalizedToolName.includes('file')) {
      return (
        <div className="tool-read-visualization">
          {args && typeof args === 'object' && 'file_path' in args && (
            <div className="mb-2">
              <span className="text-meta text-xs">Path:</span>
              <code className="ml-2 text-sm font-mono">{String(args.file_path)}</code>
            </div>
          )}
          {result && (
            <div className="tool-result-structured">
              <pre className="text-xs font-mono overflow-x-auto">
                {formatMindflowV2Value(result)}
              </pre>
            </div>
          )}
        </div>
      );
    }

    // Shell Tool specialized visualization
    if (normalizedToolName.includes('shell') || normalizedToolName.includes('bash')) {
      return (
        <div className="tool-shell-visualization">
          {args && typeof args === 'object' && 'command' in args && (
            <div className="mb-2 p-2 bg-surface-elevated rounded">
              <span className="text-meta text-xs">Command:</span>
              <code className="block mt-1 text-sm font-mono">{String(args.command)}</code>
            </div>
          )}
          {result && (
            <div className="tool-result-shell">
              <pre className="text-xs font-mono overflow-x-auto p-2 bg-surface rounded">
                {formatMindflowV2Value(result)}
              </pre>
            </div>
          )}
        </div>
      );
    }

    // Grep Search Tool specialized visualization
    if (normalizedToolName.includes('grep') || normalizedToolName.includes('search')) {
      return (
        <div className="tool-grep-visualization">
          {args && typeof args === 'object' && 'pattern' in args && (
            <div className="mb-2">
              <span className="text-meta text-xs">Pattern:</span>
              <code className="ml-2 text-sm font-mono">{String(args.pattern)}</code>
            </div>
          )}
          {result && (
            <div className="tool-result-grep">
              <div className="text-xs font-mono overflow-x-auto max-h-64">
                {formatMindflowV2Value(result)}
              </div>
            </div>
          )}
        </div>
      );
    }

    // Default visualization
    return null;
  };

  const hasSpecializedVisualization =
    toolName.toLowerCase().includes('read') ||
    toolName.toLowerCase().includes('file') ||
    toolName.toLowerCase().includes('shell') ||
    toolName.toLowerCase().includes('bash') ||
    toolName.toLowerCase().includes('grep') ||
    toolName.toLowerCase().includes('search');

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      className={`mindflow-v2-card tool-event-card border-l-2 ${getStatusColor()} ${className}`}
      data-theme={theme}
      onClick={handleToggle}
      style={{ cursor: 'pointer' }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-1">
          {getIcon()}
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-semibold">{toolName}</span>
              {elapsed && (
                <span className="text-meta text-xs">({elapsed})</span>
              )}
            </div>
            {agentName && (
              <div className="text-meta text-xs mt-1">{agentName}</div>
            )}
          </div>
        </div>
        <div className="text-meta">
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </div>
      </div>

      {/* Parameters - Always visible */}
      {args && (
        <div className="mt-3 pt-3 border-t border-primary">
          <div className="text-meta text-xs mb-1">Parameters:</div>
          <div className="text-sm">
            {summarizeMindflowV2Value(args, 120)}
          </div>
        </div>
      )}

      {/* Expanded content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.18 }}
            className="overflow-hidden"
          >
            {/* Specialized visualization or default result */}
            {hasSpecializedVisualization && status === 'completed' && (
              <div className="mt-3 pt-3 border-t border-primary">
                {renderSpecializedVisualization()}
              </div>
            )}

            {/* Default result display */}
            {!hasSpecializedVisualization && result && status === 'completed' && (
              <div className="mt-3 pt-3 border-t border-primary">
                <div className="text-meta text-xs mb-1">Result:</div>
                <pre className="text-xs font-mono overflow-x-auto max-h-64 p-2 bg-surface-elevated rounded">
                  {formatMindflowV2Value(result)}
                </pre>
              </div>
            )}

            {/* Error display */}
            {error && status === 'error' && (
              <div className="mt-3 pt-3 border-t border-error">
                <div className="text-error text-xs mb-1">Error:</div>
                <div className="text-sm text-error">{error}</div>
              </div>
            )}

            {/* Running state - show partial results if available */}
            {status === 'running' && result && (
              <div className="mt-3 pt-3 border-t border-info">
                <div className="text-info text-xs mb-1">Partial Result:</div>
                <pre className="text-xs font-mono overflow-x-auto max-h-32 p-2 bg-surface-elevated rounded">
                  {summarizeMindflowV2Value(result, 300)}
                </pre>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

/**
 * ToolCallGroup Component
 *
 * Groups related tool calls together for better organization.
 * Requirement: 14.4
 */
export interface ToolCallGroupProps {
  title: string;
  tools: ToolEventCardProps[];
  className?: string;
}

export const ToolCallGroup: React.FC<ToolCallGroupProps> = ({
  title,
  tools,
  className = '',
}) => {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className={`tool-call-group ${className}`}>
      <div
        className="flex items-center gap-2 mb-2 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        <span className="text-sm font-semibold">{title}</span>
        <span className="text-meta text-xs">({tools.length} tools)</span>
      </div>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.18 }}
            className="space-y-2 pl-4"
          >
            {tools.map((tool, index) => (
              <ToolEventCard key={index} {...tool} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// Memoize component to prevent unnecessary re-renders
export const ToolEventCard = memo(ToolEventCardComponent);
ToolEventCard.displayName = 'ToolEventCard';
