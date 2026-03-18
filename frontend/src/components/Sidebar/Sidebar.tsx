import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Database, FolderOpen, Plus, Settings, X } from 'lucide-react';
import { useAppStore } from '../../stores/appStore';

interface Session {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  message_count?: number | null;
  folder_path?: string | null;
}

interface DirectoryGroup {
  path: string | null;   // null = ungrouped / global
  label: string;
  sessions: Session[];
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
  if (mins < 1) return 'now';
  if (mins < 60) return `${mins}m`;
  if (hours < 24) return `${hours}h`;
  if (days < 7) return `${days}d`;
  return 'older';
}

function shortPath(fullPath: string): string {
  const parts = fullPath.replace(/\\/g, '/').split('/').filter(Boolean);
  if (parts.length === 0) return fullPath;
  if (parts.length === 1) return parts[0];
  return `…/${parts.at(-1) ?? ''}`;
}

function hasRealHistory(session: Session): boolean {
  if ((session.message_count ?? 0) > 0) return true;
  const normalizedTitle = String(session.title ?? '').trim().toLowerCase();
  if (!GENERIC_SESSION_TITLES.has(normalizedTitle)) return true;
  const createdAt = new Date(session.created_at).getTime();
  const updatedAt = new Date(session.updated_at).getTime();
  if (Number.isNaN(createdAt) || Number.isNaN(updatedAt)) return false;
  return updatedAt - createdAt > 5000;
}

function groupByDirectory(sessions: Session[]): DirectoryGroup[] {
  const map = new Map<string, Session[]>();

  for (const session of sessions) {
    const key = session.folder_path?.trim() || '';
    const existing = map.get(key) ?? [];
    existing.push(session);
    map.set(key, existing);
  }

  const groups: DirectoryGroup[] = [];

  // Non-directory sessions first (general)
  const global = map.get('');
  if (global?.length) {
    groups.push({ path: null, label: 'General', sessions: global });
  }

  // Directory groups sorted alphabetically
  const dirs = [...map.entries()]
    .filter(([key]) => key !== '')
    .sort(([a], [b]) => a.localeCompare(b));

  for (const [path, sessions] of dirs) {
    groups.push({ path, label: shortPath(path), sessions });
  }

  return groups;
}

// ─── Workspace Indexer ───────────────────────────────────────────────────────

interface WorkspaceIndexerProps {
  onClose: () => void;
}

const WorkspaceIndexer: React.FC<WorkspaceIndexerProps> = ({ onClose }) => {
  const [path, setPath] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleBrowse = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;
    // Extract directory from first file's webkitRelativePath
    const firstPath = (files[0] as File & { webkitRelativePath?: string }).webkitRelativePath ?? '';
    const dirName = firstPath.split('/')[0];
    setPath(dirName || files[0].name);
  };

  const handleIndex = async () => {
    const trimmed = path.trim();
    if (!trimmed) return;
    setStatus('loading');
    setErrorMsg('');

    try {
      const response = await fetch(`${BASE_URL}/workspace/index`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: trimmed }),
      });

      if (response.ok) {
        setStatus('done');
        setTimeout(onClose, 1400);
      } else {
        const data = await response.json().catch(() => ({}));
        setErrorMsg((data as { detail?: string }).detail ?? `error ${response.status}`);
        setStatus('error');
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'network error');
      setStatus('error');
    }
  };

  return (
    <div
      style={{
        margin: '0 8px 8px',
        padding: '10px 12px',
        border: '1px solid var(--line-primary)',
        borderRadius: 8,
        background: 'var(--surface)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            color: '#0D6E6E',
          }}
        >
          Index Workspace
        </span>
        <button
          type="button"
          onClick={onClose}
          style={{ background: 'none', border: 'none', color: 'var(--text-meta)', cursor: 'pointer', display: 'flex', padding: 2 }}
        >
          <X size={12} />
        </button>
      </div>

      <div style={{ display: 'flex', gap: 6 }}>
        <input
          type="text"
          value={path}
          onChange={(e) => setPath(e.target.value)}
          placeholder="/path/to/workspace"
          onKeyDown={(e) => e.key === 'Enter' && handleIndex()}
          style={{
            flex: 1,
            height: 30,
            padding: '0 10px',
            border: '1px solid var(--line-primary)',
            borderRadius: 6,
            background: 'var(--surface-elevated)',
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-mono)',
            fontSize: 12,
            outline: 'none',
          }}
        />
        <button
          type="button"
          onClick={handleBrowse}
          title="Browse folder"
          style={{
            width: 30,
            height: 30,
            border: '1px solid var(--line-primary)',
            borderRadius: 6,
            background: 'var(--surface-elevated)',
            color: 'var(--text-meta)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <FolderOpen size={13} />
        </button>
      </div>

      {/* Hidden folder picker */}
      <input
        ref={fileInputRef}
        type="file"
        // @ts-expect-error — webkitdirectory is not in TS types
        webkitdirectory=""
        multiple
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />

      <button
        type="button"
        onClick={handleIndex}
        disabled={!path.trim() || status === 'loading'}
        style={{
          marginTop: 8,
          width: '100%',
          height: 28,
          border: 'none',
          borderRadius: 6,
          background: status === 'done' ? '#0D2E2E' : '#0D6E6E',
          color: '#fff',
          fontFamily: 'var(--font-mono)',
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          cursor: path.trim() && status !== 'loading' ? 'pointer' : 'not-allowed',
          opacity: !path.trim() ? 0.5 : 1,
          transition: 'background 200ms',
        }}
      >
        {status === 'loading' ? 'Indexing…' : status === 'done' ? '✓ Indexed' : 'Index'}
      </button>

      {status === 'error' && (
        <p
          style={{
            marginTop: 6,
            color: 'var(--state-error)',
            fontFamily: 'var(--font-mono)',
            fontSize: 10,
            lineHeight: 1.4,
          }}
        >
          {errorMsg}
        </p>
      )}
    </div>
  );
};

// ─── Session Item ─────────────────────────────────────────────────────────────

interface SessionItemProps {
  session: Session;
  isActive: boolean;
  showDir: boolean;
  onClick: () => void;
}

const SessionItem: React.FC<SessionItemProps> = ({ session, isActive, showDir, onClick }) => {
  const updatedAt = session.updated_at || session.created_at;

  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        padding: '10px 16px 10px 14px',
        border: 'none',
        borderLeft: isActive ? '2px solid #0D6E6E' : '2px solid transparent',
        borderRadius: 0,
        background: isActive ? 'var(--mindflow-bg-active-session)' : 'transparent',
        textAlign: 'left',
        cursor: 'pointer',
        transition: 'background 150ms, border-color 150ms',
      }}
      onMouseEnter={(e) => {
        if (!isActive) (e.currentTarget as HTMLElement).style.background = 'var(--mindflow-bg-active-session)';
      }}
      onMouseLeave={(e) => {
        if (!isActive) (e.currentTarget as HTMLElement).style.background = 'transparent';
      }}
    >
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 8, minWidth: 0 }}>
        <span
          style={{
            flex: 1,
            color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
            fontFamily: 'var(--font-sans)',
            fontSize: 13,
            fontWeight: isActive ? 500 : 400,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            lineHeight: 1.35,
          }}
        >
          {session.title || 'untitled'}
        </span>
        <span
          style={{
            color: 'var(--text-meta)',
            fontFamily: 'var(--font-mono)',
            fontSize: 9,
            flexShrink: 0,
            letterSpacing: '0.04em',
          }}
        >
          {timeAgo(updatedAt)}
        </span>
      </div>

      {showDir && session.folder_path && (
        <span
          style={{
            marginTop: 2,
            color: 'var(--text-meta)',
            fontFamily: 'var(--font-mono)',
            fontSize: 9,
            letterSpacing: '0.02em',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {shortPath(session.folder_path)}
        </span>
      )}
    </button>
  );
};

// ─── Main Sidebar ─────────────────────────────────────────────────────────────

export const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const { sessionId: activeSessionId } = useParams();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [showIndexer, setShowIndexer] = useState(false);
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
    const timer = window.setTimeout(() => void fetchSessions(), 0);
    return () => window.clearTimeout(timer);
  }, [fetchSessions, activeSessionId, sessionRefreshTick]);

  const handleNewChat = async () => {
    try {
      const response = await fetch(`${BASE_URL}/chat/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New session' }),
      });
      if (!response.ok) { navigate('/chat'); return; }
      const session: Session = await response.json();
      await fetchSessions();
      navigate(`/chat/${session.id}`);
    } catch {
      navigate('/chat');
    }
  };

  const groups = groupByDirectory(sessions);
  // sessions with NO directory are the "global" ones — also collect all dirs
  const hasDirectories = groups.some((g) => g.path !== null);

  return (
    <aside
      style={{
        width: 240,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: 'var(--mindflow-bg-sidebar)',
        borderRight: '1px solid var(--line-primary)',
      }}
    >
      {/* ── Logo ── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '20px 20px 16px',
          borderBottom: '1px solid var(--line-primary)',
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: '#0D6E6E',
            flexShrink: 0,
          }}
        />
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 13,
            fontWeight: 600,
            color: 'var(--text-primary)',
            letterSpacing: '0.02em',
            flex: 1,
          }}
        >
          MindFlow
        </span>
        <button
          type="button"
          onClick={() => navigate('/settings')}
          style={{
            background: 'none',
            border: 'none',
            padding: 4,
            color: 'var(--text-meta)',
            cursor: 'pointer',
            display: 'flex',
            borderRadius: 4,
          }}
        >
          <Settings size={13} />
        </button>
      </div>

      {/* ── Actions ── */}
      <div style={{ padding: '10px 8px 6px' }}>
        {/* New Chat */}
        <button
          type="button"
          onClick={handleNewChat}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
            width: '100%',
            height: 34,
            border: 'none',
            borderRadius: 6,
            background: 'var(--mindflow-bg-new-chat)',
            color: '#0D6E6E',
            fontFamily: 'var(--font-mono)',
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            cursor: 'pointer',
            marginBottom: 6,
          }}
        >
          <Plus size={12} />
          New Chat
        </button>

        {/* Index Workspace */}
        {!showIndexer && (
          <button
            type="button"
            onClick={() => setShowIndexer(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              width: '100%',
              height: 30,
              border: '1px solid var(--line-primary)',
              borderRadius: 6,
              background: 'transparent',
              color: 'var(--text-meta)',
              fontFamily: 'var(--font-mono)',
              fontSize: 10,
              fontWeight: 500,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              cursor: 'pointer',
              paddingInline: 10,
            }}
          >
            <Database size={11} />
            Index Workspace
          </button>
        )}
      </div>

      {/* ── Indexer panel ── */}
      {showIndexer && (
        <WorkspaceIndexer onClose={() => setShowIndexer(false)} />
      )}

      {/* ── Sessions ── */}
      {/* Sessions section header */}
      <div
        style={{
          padding: '0 20px 4px',
          fontFamily: 'var(--font-mono)',
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: 2,
          textTransform: 'uppercase',
          color: 'var(--text-meta)',
        }}
      >
        Recent
      </div>

      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
        {sessions.length === 0 ? (
          <div
            style={{
              padding: '12px 16px',
              color: 'var(--text-meta)',
              fontFamily: 'var(--font-mono)',
              fontSize: 11,
            }}
          >
            no sessions yet
          </div>
        ) : hasDirectories ? (
          // Directory-grouped view
          groups.map((group) => (
            <div key={group.path ?? '__global__'}>
              {/* Group header */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '10px 16px 4px',
                }}
              >
                {group.path && <FolderOpen size={10} style={{ color: 'var(--text-meta)', flexShrink: 0 }} />}
                <span
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 9,
                    fontWeight: 600,
                    letterSpacing: '0.1em',
                    textTransform: 'uppercase',
                    color: 'var(--text-meta)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                  title={group.path ?? undefined}
                >
                  {group.label}
                </span>
                <span
                  style={{
                    marginLeft: 'auto',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 9,
                    color: 'var(--text-ghost)',
                  }}
                >
                  {group.sessions.length}
                </span>
              </div>

              {/* Sessions in this group */}
              {group.sessions.map((session) => (
                <SessionItem
                  key={session.id}
                  session={session}
                  isActive={session.id === activeSessionId}
                  showDir={false}
                  onClick={() => navigate(`/chat/${session.id}`)}
                />
              ))}
            </div>
          ))
        ) : (
          // Flat list (no directories yet)
          sessions.map((session) => (
            <SessionItem
              key={session.id}
              session={session}
              isActive={session.id === activeSessionId}
              showDir={false}
              onClick={() => navigate(`/chat/${session.id}`)}
            />
          ))
        )}
      </div>

      {/* ── User area ── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '12px 14px',
          borderTop: '1px solid var(--line-primary)',
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            background: '#0D6E6E',
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: 'var(--font-mono)',
            fontSize: 11,
            fontWeight: 600,
            flexShrink: 0,
          }}
        >
          L
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div
            style={{
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-sans)',
              fontSize: 13,
              fontWeight: 500,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              lineHeight: 1.3,
            }}
          >
            Levy Bonito
          </div>
          <div
            style={{
              color: 'var(--text-meta)',
              fontFamily: 'var(--font-mono)',
              fontSize: 10,
              letterSpacing: '0.04em',
              lineHeight: 1.3,
            }}
          >
            admin
          </div>
        </div>
      </div>
    </aside>
  );
};
