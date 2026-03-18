import React from 'react';
import { motion } from 'framer-motion';

export type StreamNotifierTone = 'accent' | 'info' | 'success' | 'warning' | 'error' | 'neutral';

interface StreamNotifierProps {
  title: string;
  status: string;
  detail?: string;
  tone?: StreamNotifierTone;
  active?: boolean;
  className?: string;
}

export const StreamNotifier: React.FC<StreamNotifierProps> = ({
  title,
  status,
  detail,
  tone = 'neutral',
  active = false,
  className = '',
}) => {
  return (
    <motion.section
      className={`event-shell w-full ${className}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
    >
      <div className="event-track">
        <span className={active ? 'signal-dot' : 'signal-dot idle'} />
      </div>

      <div className={`stream-notifier stream-notifier--${tone} ${active ? 'is-active' : ''}`}>
        <div className="stream-notifier-header">
          <span className="stream-notifier-lead" />

          <div className="stream-notifier-copy">
            <span className="stream-notifier-title">{title}</span>
            <span className="stream-notifier-sep">/</span>
            <span className="stream-notifier-status">{status}</span>
          </div>

          {active ? (
            <motion.span
              className="stream-notifier-pulse"
              animate={{ opacity: [0.32, 1, 0.32] }}
              transition={{ duration: 1.1, repeat: Infinity, ease: 'easeInOut' }}
            />
          ) : null}
        </div>

        {detail ? (
          <div className="stream-notifier-detail">
            <p className="stream-notifier-detail-copy">{detail}</p>
          </div>
        ) : null}
      </div>
    </motion.section>
  );
};

export default StreamNotifier;
