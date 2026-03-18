import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ChevronRight, Plus, Settings } from 'lucide-react';
import { useAppStore } from '../../stores/appStore';

interface Session {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  message_count?: number | null;
}

const BASE_URL = '/v1';
const GENERIC_SESSION_TITLES = new Set([
  'new chat',
  'new session',
  'nova conversa',
  'untitled',
  'sem título',
]);

function timeAgo(dateStr: string): string {
  const ms = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(ms / 60000);
  const hours = Math.floor(ms / 3600000);
  const days = Math.floor(ms / 86400000);

  if (mins < 60) return `${mins}m`;
  if (hours < 24) return `${hours}h`;
  if (days < 7) return `${days}d`;
  return 'older';
}

function hasRealHistory(session: Session): boolean {
  if ((session.message_count ?? 0) > 0) return true;

  const normalizedTitle = String(session.title ?? '')
    .trim()
    .toLowerCase();

  if (!GENERIC_SESSION_TITLES.has(normalizedTitle)) return true;

  const createdAt = new Date(session.created_at).getTime();
  const updatedAt = new Date(session.updated_at).getTime();

  if (Number.isNaN(createdAt) || Number.isNaN(updatedAt)) return false;

  return updatedAt - createdAt > 5000;
}

export const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const { sessionId: activeSessionId } = useParams();
  const [sessions, setSessions] = useState<Session[]>([]);
  const sessionRefreshTick = useAppStore((state) => state.sessionRefreshTick);

  const fetchSessions = useCallback(async () => {
    try {
      const response = await fetch(`${BASE_URL}/chat/sessions`);
      if (!response.ok) return;
      const data = await response.json();
      setSessions(Array.isArray(data) ? data.filter(hasRealHistory) : []);
    } catch {
      setSessions([]);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchSessions();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [fetchSessions, activeSessionId, sessionRefreshTick]);

  const handleNewChat = async () => {
    try {
      const response = await fetch(`${BASE_URL}/chat/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New session' }),
      });

      if (!response.ok) {
        navigate('/chat');
        return;
      }

      const session: Session = await response.json();
      await fetchSessions();
      navigate(`/chat/${session.id}`);
    } catch {
      navigate('/chat');
    }
  };

  return (
    <aside
      className="sidebar-shell flex h-full flex-col border-r px-3 py-4 md:px-4 md:py-5"
      style={{
        width: 'clamp(232px, 22vw, 304px)',
        borderColor: 'var(--line-primary)',
      }}
    >
      <div className="sidebar-section flex flex-col gap-4 px-1 pb-2 md:px-2">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div
              className="flex items-center gap-3"
              style={{ minHeight: 28 }}
            >
              <span className="signal-dot" />
              <div className="min-w-0">
                <div
                  style={{
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-brand)',
                    fontSize: 28,
                    fontWeight: 600,
                    letterSpacing: '-0.03em',
                    lineHeight: 0.94,
                  }}
                >
                  Inicio
                </div>
              </div>
            </div>
          </div>

          <button
            className="subtle-button hidden md:inline-flex"
            type="button"
            onClick={() => navigate('/settings')}
            style={{ minHeight: 34, paddingInline: 12 }}
          >
            <Settings size={14} />
          </button>
        </div>

        <button
          className="subtle-button w-full justify-between"
          type="button"
          onClick={handleNewChat}
        >
          <span className="flex items-center gap-3">
            <Plus size={14} />
            <span className="hidden md:inline">New session</span>
          </span>
          <span className="mono-label hidden md:inline" style={{ letterSpacing: '0.08em' }}>
            start
          </span>
        </button>
      </div>

      <div className="sidebar-section flex min-h-0 flex-1 flex-col px-1 md:px-2">
        <div className="flex items-center gap-3">
          <span className="mono-label">Sessions</span>
          <div style={{ flex: 1, height: 1, background: 'var(--line-soft)' }} />
        </div>

        <div className="mt-3 flex-1 overflow-y-auto pr-1">
          <div className="flex flex-col gap-2">
            {sessions.length === 0 ? (
              <div
                className="px-1 py-4"
                style={{
                  color: 'var(--text-meta)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 'calc(13px * var(--font-scale, 1))',
                }}
              >
                no sessions yet
              </div>
            ) : (
              sessions.map((session, index) => {
                const isActive = session.id === activeSessionId;
                const updatedAt = session.updated_at || session.created_at;

                return (
                  <motion.button
                    key={session.id}
                    type="button"
                    onClick={() => navigate(`/chat/${session.id}`)}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.2, delay: index * 0.03 }}
                    className={`sidebar-session relative flex items-start gap-3 overflow-hidden text-left ${isActive ? 'active' : ''}`}
                  >
                    <div className="flex flex-col items-center self-stretch pt-1">
                      <span className={`signal-dot ${isActive ? '' : 'idle'}`} />
                      <span className="trace-rail mt-2 flex-1" />
                    </div>

                    <div className="min-w-0 flex-1">
                      <div
                        style={{
                          color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                          fontSize: 'calc(14px * var(--font-scale, 1))',
                          fontWeight: 500,
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                          overflow: 'hidden',
                          lineHeight: 1.45,
                        }}
                      >
                        {session.title || 'untitled'}
                      </div>
                      <div
                        className="mt-1 flex items-center gap-2"
                        style={{
                          color: 'var(--text-meta)',
                          fontFamily: 'var(--font-mono)',
                          fontSize: 'calc(12px * var(--font-scale, 1))',
                        }}
                      >
                        <span>{timeAgo(updatedAt)}</span>
                      </div>
                    </div>

                    <ChevronRight
                      size={14}
                      style={{ color: isActive ? 'var(--text-primary)' : 'var(--text-ghost)' }}
                    />
                  </motion.button>
                );
              })
            )}
          </div>
        </div>
      </div>

      <div className="sidebar-footer mt-4 px-1 py-3 md:px-2">
        <div className="flex items-center gap-3">
          <span className="signal-dot idle" />
          <div className="min-w-0 flex-1">
            <div
              className="truncate"
              style={{ color: 'var(--text-primary)', fontSize: 'calc(14px * var(--font-scale, 1))', fontWeight: 500 }}
            >
              Levy Bonito
            </div>
            <div
              className="truncate"
              style={{
                color: 'var(--text-meta)',
                fontFamily: 'var(--font-mono)',
                fontSize: 'calc(12px * var(--font-scale, 1))',
              }}
            >
              admin / pencil
            </div>
          </div>

          <button
            className="subtle-button md:hidden"
            type="button"
            onClick={() => navigate('/settings')}
            style={{ minHeight: 34, paddingInline: 12 }}
          >
            <Settings size={14} />
          </button>
        </div>
      </div>
    </aside>
  );
};
