import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp } from 'lucide-react';

type AgentType = 'orchestrator' | 'coder' | 'analyst' | 'researcher' | 'default';

interface ThoughtBubbleProps {
  agentType?: AgentType;
  agentName?: string;
  content: string;
  isStreaming?: boolean;
  className?: string;
}

export const ThoughtBubble: React.FC<ThoughtBubbleProps> = ({
  agentType,
  agentName,
  content,
  isStreaming = false,
  className = '',
}) => {
  const [collapsed, setCollapsed] = useState(false);
  const displayName = agentName ?? 'Orchestrator';

  useEffect(() => {
    if (!isStreaming && content) {
      const timer = setTimeout(() => setCollapsed(true), 900);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [content, isStreaming]);

  return (
    <motion.section
      layout
      className={`event-shell w-full ${className}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
    >
      <div className="event-track">
        <span className="signal-dot" />
      </div>

      <motion.div layout className="thought-stack">
        <button
          type="button"
          onClick={() => setCollapsed((value) => !value)}
          className="thought-pill thought-pill-button"
        >
          <span className={`thought-synapse thought-synapse--${agentType ?? 'orchestrator'}`}>
            <span className="thought-synapse-link thought-synapse-link-a" />
            <span className="thought-synapse-link thought-synapse-link-b" />
            <span className="thought-synapse-node thought-synapse-node-a" />
            <span className="thought-synapse-node thought-synapse-node-b" />
            <span className="thought-synapse-node thought-synapse-node-c" />
          </span>

          <span className="thought-name">{displayName}</span>
          <span className="thought-sep">/</span>
          <span className="thought-status">thinking</span>

          <span className="thought-toggle-copy">{collapsed ? 'open' : 'close'}</span>
          {collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
        </button>

        <AnimatePresence initial={false}>
          {!collapsed && (
            <motion.div
              layout
              key="content"
              className="thought-body thought-body-expanded"
              initial={{ opacity: 0, height: 0, y: -6 }}
              animate={{ opacity: 1, height: 'auto', y: 0 }}
              exit={{ opacity: 0, height: 0, y: -4 }}
              transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
            >
              <pre className="thought-note thought-note-pre">{content}</pre>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </motion.section>
  );
};

export default ThoughtBubble;
