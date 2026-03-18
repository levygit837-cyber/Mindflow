/**
 * Shared Stream Components
 *
 * These components are used by both old and V2 chat visualization systems.
 * Most components have been moved to V2 - this file only contains shared utilities.
 */

import React from 'react';
import { motion } from 'framer-motion';
import type { MindflowV2Tone } from './mindflowV2';

export interface StreamNotifierProps {
  title: string;
  status: string;
  message?: string;
  detail?: string;
  tone?: MindflowV2Tone;
  className?: string;
}

export interface ChatDiagnosticProps {
  variant: 'scope-escape' | 'slow-run';
  elapsed?: string;
  className?: string;
}

export interface DiagnosticNotifierProps {
  message: string;
  code?: string;
  recoverable?: boolean;
  className?: string;
}

function cn(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(' ');
}

function statusToneClass(tone: MindflowV2Tone) {
  switch (tone) {
    case 'accent':
      return 'stream-notifier--accent';
    case 'info':
      return 'stream-notifier--info';
    case 'success':
      return 'stream-notifier--success';
    case 'warning':
      return 'stream-notifier--warning';
    case 'error':
      return 'stream-notifier--error';
    case 'neutral':
    default:
      return 'stream-notifier--neutral';
  }
}

export const StreamNotifier: React.FC<StreamNotifierProps> = ({
  title,
  status,
  message,
  detail,
  tone = 'neutral',
  className = '',
}) => {
  const toneClass = statusToneClass(tone);

  return (
    <motion.section
      className={cn('stream-notifier', toneClass, className)}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
    >
      <div className="stream-notifier-header">
        <span className="stream-notifier-lead" />
        <div className="stream-notifier-copy">
          <span className="stream-notifier-title">{title}</span>
          <span className="stream-notifier-sep">/</span>
          <span className="stream-notifier-status">{status}</span>
        </div>
        <span className="stream-notifier-pulse" />
      </div>

      {(message || detail) && (
        <div className="stream-notifier-detail">
          <p className="stream-notifier-detail-copy">{message ?? detail}</p>
          {message && detail && <p className="stream-notifier-detail-copy mt-2">{detail}</p>}
        </div>
      )}
    </motion.section>
  );
};

// DiagnosticNotifier - Critical error display component
export const DiagnosticNotifier: React.FC<DiagnosticNotifierProps> = ({
  message,
  code,
  recoverable = false,
  className = '',
}) => {
  return (
    <motion.div
      className={cn(className)}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      style={{
        padding: '12px',
        borderRadius: '8px',
        border: '1px solid #FCA5A5',
        background: '#FEF2F2',
        fontFamily: 'var(--font-mono, monospace)',
        fontSize: '0.875rem',
        color: 'var(--state-error, #E11D48)',
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: '4px' }}>
        {code ? `[${code}] ` : ''}Error
      </div>
      <div>{message}</div>
      {!recoverable && (
        <div style={{ marginTop: '8px', fontSize: '0.75rem', opacity: 0.75 }}>
          Este erro não é recuperável.
        </div>
      )}
    </motion.div>
  );
};

// Matches scopeEscapeNotifier / slowRunNotifier design from Pencil
export const ChatDiagnostic: React.FC<ChatDiagnosticProps> = ({ variant, elapsed, className = '' }) => {
  const isScopeEscape = variant === 'scope-escape';
  return (
    <motion.div
      className={cn(className)}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', borderRadius: 14, background: '#FDFBFF', border: '1px solid #DED6E8' }}
    >
      <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#FFFFFF', border: '1px solid #F7C873', flexShrink: 0 }} />
      <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontFamily: 'Cormorant Garamond, serif', fontSize: 18, fontWeight: 500, color: '#251D2E' }}>
          {isScopeEscape ? 'Scope' : 'Performance'}
        </span>
        <span style={{ fontFamily: 'Azeret Mono, monospace', fontSize: 11, color: '#B2A8C2' }}>/</span>
        <span style={{ fontFamily: 'Azeret Mono, monospace', fontSize: 11, fontWeight: 500, color: '#B45309' }}>
          {isScopeEscape ? 'fora do escopo' : `execução lenta${elapsed ? ` · ${elapsed}` : ''}`}
        </span>
      </span>
    </motion.div>
  );
};
