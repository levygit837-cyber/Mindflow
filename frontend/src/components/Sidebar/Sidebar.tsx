import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Plus, Settings } from 'lucide-react';
import { motion } from 'framer-motion';

interface Session {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

const BASE_URL = '/v1';

function timeAgo(dateStr: string): string {
  const ms = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(ms / 60000);
  const hours = Math.floor(ms / 3600000);
  const days = Math.floor(ms / 86400000);
  if (mins < 60) return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return 'há muito tempo';
}

export const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const { sessionId: activeSessionId } = useParams();
  const [sessions, setSessions] = useState<Session[]>([]);

  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch(`${BASE_URL}/chat/sessions`);
      if (res.ok) {
        const data = await res.json();
        setSessions(Array.isArray(data) ? data : []);
      }
    } catch {
      // Backend offline — sidebar shows empty
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions, activeSessionId]);

  const handleNewChat = async () => {
    try {
      const res = await fetch(`${BASE_URL}/chat/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New Chat' }),
      });
      if (res.ok) {
        const session: Session = await res.json();
        await fetchSessions();
        navigate(`/chat/${session.id}`);
      } else {
        navigate('/chat');
      }
    } catch {
      navigate('/chat');
    }
  };

  return (
    <div
      className="flex flex-col flex-shrink-0 h-full"
      style={{
        width: 280,
        backgroundColor: '#0C0820',
        borderRight: '1px solid #1A1545',
      }}
    >
      {/* ── Top: Logo + New Chat ──────────────────────── */}
      <div style={{ padding: '24px 20px 16px' }}>
        {/* Logo row */}
        <div className="flex items-center" style={{ gap: 10, marginBottom: 20 }}>
          {/* M icon */}
          <div
            className="flex items-center justify-center flex-shrink-0"
            style={{
              width: 34,
              height: 34,
              borderRadius: 9,
              background: 'linear-gradient(135deg, #7C3AFF 0%, #22D3EE 100%)',
            }}
          >
            <span
              style={{
                color: '#fff',
                fontFamily: 'Space Grotesk, sans-serif',
                fontSize: 17,
                fontWeight: 700,
                lineHeight: 1,
              }}
            >
              M
            </span>
          </div>

          <span
            style={{
              color: '#EDE9FF',
              fontFamily: 'Space Grotesk, sans-serif',
              fontSize: 17,
              fontWeight: 700,
            }}
          >
            MindFlow
          </span>

          <div
            style={{
              backgroundColor: '#2D1F6E',
              borderRadius: 4,
              padding: '3px 7px',
            }}
          >
            <span
              style={{
                color: '#A78BFA',
                fontFamily: 'Space Grotesk, sans-serif',
                fontSize: 9,
                fontWeight: 600,
                letterSpacing: '0.05em',
              }}
            >
              BETA
            </span>
          </div>
        </div>

        {/* New Chat button */}
        <motion.button
          onClick={handleNewChat}
          className="w-full flex items-center"
          style={{
            backgroundColor: '#160D36',
            borderRadius: 8,
            padding: '10px 14px',
            gap: 8,
            border: 'none',
            cursor: 'pointer',
          }}
          whileHover={{ backgroundColor: '#1D1260' }}
          whileTap={{ scale: 0.98 }}
          transition={{ duration: 0.15 }}
        >
          <Plus size={15} color="#7C3AFF" strokeWidth={2.5} />
          <span
            style={{
              color: '#A78BFA',
              fontFamily: 'Space Grotesk, sans-serif',
              fontSize: 13,
              fontWeight: 500,
            }}
          >
            New Chat
          </span>
        </motion.button>
      </div>

      {/* ── RECENT divider ────────────────────────────── */}
      <div
        className="flex items-center"
        style={{ gap: 10, padding: '0 20px 8px' }}
      >
        <span
          style={{
            color: '#4D4575',
            fontFamily: 'Space Grotesk, sans-serif',
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: '0.08em',
            flexShrink: 0,
          }}
        >
          RECENT
        </span>
        <div style={{ flex: 1, height: 1, backgroundColor: '#1A1545' }} />
      </div>

      {/* ── Session List ──────────────────────────────── */}
      <div
        className="flex-1 overflow-y-auto"
        style={{ padding: '0 8px' }}
      >
        {sessions.length === 0 ? (
          <div
            style={{
              padding: '12px 12px',
              color: '#4D4575',
              fontFamily: 'Inter, sans-serif',
              fontSize: 12,
            }}
          >
            No sessions yet
          </div>
        ) : (
          sessions.map((session) => {
            const isActive = session.id === activeSessionId;
            return (
              <motion.button
                key={session.id}
                onClick={() => navigate(`/chat/${session.id}`)}
                className="w-full text-left"
                style={{
                  backgroundColor: isActive ? '#1D1840' : 'transparent',
                  borderRadius: 8,
                  borderLeft: isActive ? '2px solid #7C3AFF' : '2px solid transparent',
                  padding: '10px 12px',
                  marginBottom: 1,
                  cursor: 'pointer',
                  border: 'none',
                  display: 'block',
                }}
                whileHover={{ backgroundColor: isActive ? '#1D1840' : '#130F28' }}
                transition={{ duration: 0.15 }}
              >
                <div
                  style={{
                    color: isActive ? '#EDE9FF' : '#8B81C0',
                    fontFamily: 'Space Grotesk, sans-serif',
                    fontSize: 13,
                    fontWeight: 500,
                    marginBottom: 3,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {session.title || 'Untitled Chat'}
                </div>
                <div
                  style={{
                    color: '#4D4575',
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 11,
                    fontWeight: 400,
                  }}
                >
                  {timeAgo(session.updated_at || session.created_at)}
                </div>
              </motion.button>
            );
          })
        )}
      </div>

      {/* ── Bottom: User Info ─────────────────────────── */}
      <div
        className="flex items-center"
        style={{
          padding: '14px 16px',
          borderTop: '1px solid #1A1545',
          gap: 10,
        }}
      >
        {/* Avatar */}
        <div
          className="flex items-center justify-center flex-shrink-0"
          style={{
            width: 32,
            height: 32,
            borderRadius: 16,
            background: 'linear-gradient(135deg, #4C1D95 0%, #1E40AF 100%)',
          }}
        >
          <span
            style={{
              color: '#fff',
              fontFamily: 'Space Grotesk, sans-serif',
              fontSize: 14,
              fontWeight: 700,
            }}
          >
            L
          </span>
        </div>

        {/* User info */}
        <div className="flex-1 min-w-0">
          <div
            style={{
              color: '#EDE9FF',
              fontFamily: 'Space Grotesk, sans-serif',
              fontSize: 13,
              fontWeight: 500,
            }}
          >
            Levy Bonito
          </div>
          <div
            style={{
              color: '#4D4575',
              fontFamily: 'Inter, sans-serif',
              fontSize: 11,
            }}
          >
            Admin · Pro
          </div>
        </div>

        {/* Settings */}
        <button
          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}
          onClick={() => navigate('/settings')}
        >
          <Settings size={16} color="#4D4575" />
        </button>
      </div>
    </div>
  );
};
