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
    <motion.div
      className={`flex w-full gap-4 ${className}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
    >
      <div className="flex w-4 flex-col items-center shrink-0">
        <span className="signal-dot" />
        <span className="trace-rail mt-2 flex-1" />
      </div>

      <div className="rail-panel min-w-0 flex-1 px-5 py-4 md:px-6" style={{ paddingLeft: 36 }}>
        <div className="flex flex-wrap items-center gap-2">
          <span
            style={{
              color: 'var(--text-secondary)',
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
            }}
          >
            --- Thinking
          </span>

          <span style={{ color: 'var(--text-primary)', fontSize: 14, fontWeight: 600 }}>
            {displayName}
          </span>

          <span className="mono-label" style={{ letterSpacing: '0.08em' }}>
            {collapsed ? 'expandir' : 'aberto'}
          </span>

          <button
            type="button"
            onClick={() => setCollapsed((value) => !value)}
            className="subtle-button ml-auto"
            style={{ minHeight: 30, paddingInline: 12 }}
          >
            <span className="mono-label" style={{ letterSpacing: '0.08em' }}>
              {collapsed ? '> abrir' : 'v fechar'}
            </span>
            {collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
          </button>
        </div>

        <AnimatePresence initial={false}>
          {!collapsed && (
            <motion.pre
              key="content"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2, ease: 'easeInOut' }}
              style={{
                marginTop: 14,
                overflow: 'hidden',
                whiteSpace: 'pre-wrap',
                color: 'var(--text-meta)',
                fontFamily: 'var(--font-mono)',
                fontSize: 12,
                lineHeight: 1.7,
                maxHeight: 280,
                overflowY: 'auto',
              }}
            >
              {content}
            </motion.pre>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
};

export default ThoughtBubble;
