import React from 'react';
import { RefreshCcw, Terminal } from 'lucide-react';

import { useShellTabs } from '../../hooks/useShellTabs';

interface ShellTabsPanelProps {
  sessionId: string;
  isStreaming: boolean;
}

function truncate(value: string | null | undefined, max = 220) {
  if (!value) return '';
  return value.length > max ? `${value.slice(0, max)}…` : value;
}

function stateTone(state: string) {
  switch (state) {
    case 'running':
      return 'var(--state-info)';
    case 'completed':
      return 'var(--state-success)';
    case 'failed':
      return 'var(--state-error)';
    case 'terminated':
      return 'var(--text-meta)';
    default:
      return 'var(--text-secondary)';
  }
}

export const ShellTabsPanel: React.FC<ShellTabsPanelProps> = ({ sessionId, isStreaming }) => {
  const { tabs, isLoading, error, refresh } = useShellTabs(sessionId, isStreaming ? 1500 : 3500);

  return (
    <section className="event-shell w-full">
      <div className="event-track">
        <span className={tabs.some((tab) => tab.state === 'running') ? 'signal-dot' : 'signal-dot idle'} />
      </div>

      <div className="event-node-lab">
        <div className="event-header">
          <Terminal size={14} />
          <span className="mono-label">shell tabs / session</span>
          <span className="event-badge">{tabs.length}</span>
          <button
            type="button"
            onClick={() => void refresh()}
            className="subtle-button"
            style={{ marginLeft: 'auto', minHeight: 28, paddingInline: 10 }}
          >
            <RefreshCcw size={13} />
            <span className="mono-label">refresh</span>
          </button>
        </div>

        {tabs.length === 0 ? (
          <div
            style={{
              marginTop: 12,
              color: error ? 'var(--state-error)' : 'var(--text-meta)',
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
              lineHeight: 1.7,
            }}
          >
            {error
              ? `falha / ${error}`
              : isLoading
                ? 'carregando abas shell...'
                : 'nenhuma aba shell registrada para esta sessão'}
          </div>
        ) : (
          <div className="mt-4 flex flex-col gap-3">
            {tabs.map((tab) => (
              <article
                key={tab.tab_id}
                style={{
                  border: '1px solid var(--line-primary)',
                  borderRadius: 14,
                  padding: 14,
                  background: 'rgba(255,255,255,0.02)',
                }}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="mono-label">{tab.title || tab.tab_id}</span>
                  <span
                    className="event-badge"
                    style={{
                      color: stateTone(tab.state),
                      borderColor: stateTone(tab.state),
                    }}
                  >
                    {tab.state}
                  </span>
                  {tab.pid ? <span className="event-badge">pid {tab.pid}</span> : null}
                  {typeof tab.last_exit_code === 'number' ? (
                    <span className="event-badge">exit {tab.last_exit_code}</span>
                  ) : null}
                </div>

                <div
                  style={{
                    marginTop: 10,
                    color: 'var(--text-meta)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 11,
                    lineHeight: 1.7,
                  }}
                >
                  cwd / {tab.cwd}
                </div>

                {tab.last_command ? (
                  <div
                    style={{
                      marginTop: 10,
                      color: 'var(--text-secondary)',
                      fontFamily: 'var(--font-mono)',
                      fontSize: 12,
                      lineHeight: 1.7,
                    }}
                  >
                    cmd / {truncate(tab.last_command, 280)}
                  </div>
                ) : null}

                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div>
                    <div className="mono-label mb-2">stdout</div>
                    <pre
                      style={{
                        margin: 0,
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        color: 'var(--text-secondary)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: 11,
                        lineHeight: 1.6,
                      }}
                    >
                      {truncate(tab.stdout_buffer, 320) || 'sem saída'}
                    </pre>
                  </div>

                  <div>
                    <div className="mono-label mb-2">stderr</div>
                    <pre
                      style={{
                        margin: 0,
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        color: tab.stderr_buffer ? 'var(--state-error)' : 'var(--text-secondary)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: 11,
                        lineHeight: 1.6,
                      }}
                    >
                      {truncate(tab.stderr_buffer, 320) || 'sem erros'}
                    </pre>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
};

