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

      <motion.div layout className="event-node-lab">
        <div className="event-header">
          <span className="mono-label">--- Thinking</span>

          <span className="event-title">
            {displayName}
          </span>

          <span className="event-badge">
            {collapsed ? 'expandir' : 'aberto'}
          </span>

          <button
            type="button"
            onClick={() => setCollapsed((value) => !value)}
            className="event-toggle ml-auto"
          >
            <span className="mono-label" style={{ letterSpacing: '0.08em' }}>
              {collapsed ? '> abrir' : 'v fechar'}
            </span>
            {collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
          </button>
        </div>

        <AnimatePresence initial={false}>
          {!collapsed && (
            <motion.div
              layout
              key="content"
              className="event-expand event-expand-block"
              initial={{ opacity: 0, height: 0, y: -6 }}
              animate={{ opacity: 1, height: 'auto', y: 0 }}
              exit={{ opacity: 0, height: 0, y: -4 }}
              transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
            >
              <pre
                style={{
                  margin: 0,
                  whiteSpace: 'pre-wrap',
                  color: 'var(--text-meta)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 12,
                  lineHeight: 1.78,
                  maxHeight: 280,
                  overflowY: 'auto',
                }}
              >
                {content}
              </pre>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </motion.section>
  );
};

export default ThoughtBubble;
