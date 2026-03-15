import React, { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Box,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  FileText,
  Folder,
  Globe,
  Loader2,
  Terminal,
  Wrench,
  XCircle,
} from 'lucide-react';

export interface ToolCallData {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result?: string;
  error?: string;
  status: 'calling' | 'success' | 'error';
  timestamp: Date;
}

interface ToolMeta {
  category: string;
  Icon: React.FC<{ size: number }>;
}

const TOOL_META: Record<string, ToolMeta> = {
  read_file: { category: 'filesystem', Icon: ({ size }) => <FileText size={size} /> },
  write_file: { category: 'filesystem', Icon: ({ size }) => <FileText size={size} /> },
  edit_file: { category: 'filesystem', Icon: ({ size }) => <FileText size={size} /> },
  grep_search: { category: 'filesystem', Icon: ({ size }) => <Folder size={size} /> },
  glob_search: { category: 'filesystem', Icon: ({ size }) => <Folder size={size} /> },
  list_directory: { category: 'filesystem', Icon: ({ size }) => <Folder size={size} /> },
  list_dir: { category: 'filesystem', Icon: ({ size }) => <Folder size={size} /> },
  shell_execute: { category: 'system', Icon: ({ size }) => <Terminal size={size} /> },
  shell_tab_open: { category: 'system', Icon: ({ size }) => <Terminal size={size} /> },
  shell_tab_list: { category: 'system', Icon: ({ size }) => <Terminal size={size} /> },
  shell_tab_status: { category: 'system', Icon: ({ size }) => <Terminal size={size} /> },
  shell_tab_exec: { category: 'system', Icon: ({ size }) => <Terminal size={size} /> },
  shell_tab_read: { category: 'system', Icon: ({ size }) => <Terminal size={size} /> },
  shell_tab_close: { category: 'system', Icon: ({ size }) => <Terminal size={size} /> },
  system_info: { category: 'system', Icon: ({ size }) => <Terminal size={size} /> },
  browser_search: { category: 'web', Icon: ({ size }) => <Globe size={size} /> },
  api_client: { category: 'web', Icon: ({ size }) => <Globe size={size} /> },
  git_manager: { category: 'integration', Icon: ({ size }) => <Box size={size} /> },
};

const DEFAULT_META: ToolMeta = {
  category: 'tool',
  Icon: ({ size }) => <Wrench size={size} />,
};

function getToolMeta(name: string): ToolMeta {
  return TOOL_META[name.toLowerCase()] ?? DEFAULT_META;
}

function formatValue(value: unknown, maxLength = 220): string {
  const raw = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  return raw.length > maxLength ? `${raw.slice(0, maxLength)}…` : raw;
}

function formatArgs(args: Record<string, unknown>): string {
  if (Object.keys(args).length === 0) return 'sem argumentos';

  return Object.entries(args)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([key, value]) => `${key}: ${formatValue(value, 140)}`)
    .join('\n');
}

function formatResult(result: string): string {
  try {
    const parsed = JSON.parse(result);
    return formatValue(parsed, 460);
  } catch {
    return formatValue(result, 460);
  }
}

function isErrorResult(result: string): boolean {
  try {
    const parsed = JSON.parse(result);
    return parsed?.success === false || typeof parsed?.error === 'string';
  } catch {
    return false;
  }
}

interface ToolCallBlockProps {
  toolCall: ToolCallData;
}

export const ToolCallBlock: React.FC<ToolCallBlockProps> = ({ toolCall }) => {
  const [expanded, setExpanded] = useState(true);
  const meta = useMemo(() => getToolMeta(toolCall.name), [toolCall.name]);
  const hasArgs = Object.keys(toolCall.args).length > 0;
  const hasOutput = Boolean(toolCall.result || toolCall.error);

  const statusIcon = (() => {
    if (toolCall.status === 'calling') {
      return (
        <motion.span
          animate={{ rotate: 360 }}
          transition={{ duration: 1.1, repeat: Infinity, ease: 'linear' }}
          style={{ display: 'flex' }}
        >
          <Loader2 size={14} />
        </motion.span>
      );
    }

    if (toolCall.status === 'success') return <CheckCircle2 size={14} />;
    return <XCircle size={14} />;
  })();

  return (
    <motion.section
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18, ease: 'easeOut' }}
      className="event-shell min-w-0 max-w-[760px] w-full"
    >
      <div className="event-track">
        <span className={toolCall.status === 'calling' ? 'signal-dot' : 'signal-dot idle'} />
      </div>

      <motion.div layout className="event-node-lab">
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          className="flex w-full items-start gap-3 text-left"
          style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}
        >
          <div className="min-w-0 flex-1">
            <div className="event-header">
              <meta.Icon size={14} />
              <span
                style={{
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 12,
                  letterSpacing: '0.04em',
                }}
              >
                {toolCall.name}
              </span>
              <span className="event-badge">{meta.category}</span>
              <span className="event-badge" style={{ marginLeft: 'auto' }}>
                {toolCall.status === 'calling' ? 'calling' : toolCall.status === 'success' ? 'ready' : 'error'}
              </span>
              <span style={{ color: 'var(--text-meta)' }}>{statusIcon}</span>
              <span className="event-toggle">
                {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </span>
            </div>

            <div
              style={{
                marginTop: 10,
                color: 'var(--text-secondary)',
                fontSize: 13,
                lineHeight: 1.6,
              }}
            >
              {hasArgs
                ? `--- ${Object.keys(toolCall.args).length} parâmetro${Object.keys(toolCall.args).length > 1 ? 's' : ''}`
                : '--- execução direta'}
            </div>
          </div>
        </button>

        <AnimatePresence initial={false}>
          {expanded && (
            <motion.div
              layout
              key="body"
              className="event-expand event-expand-block"
              initial={{ opacity: 0, height: 0, y: -6 }}
              animate={{ opacity: 1, height: 'auto', y: 0 }}
              exit={{ opacity: 0, height: 0, y: -4 }}
              transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="flex flex-col gap-4">
                {hasArgs && (
                  <div>
                    <div className="mono-label mb-2">input</div>
                    <pre
                      style={{
                        margin: 0,
                        color: 'var(--text-secondary)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: 12,
                        lineHeight: 1.7,
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      {formatArgs(toolCall.args)}
                    </pre>
                  </div>
                )}

                {toolCall.status === 'calling' && !hasOutput && (
                  <div>
                    <div className="flex items-center gap-3">
                      <span className="signal-dot" />
                      <div
                        style={{
                          color: 'var(--text-meta)',
                          fontFamily: 'var(--font-mono)',
                          fontSize: 12,
                        }}
                      >
                        aguardando retorno do notifier
                      </div>
                    </div>
                  </div>
                )}

                {hasOutput && (
                  <div>
                    <div className="mono-label mb-2">
                      {toolCall.error ? 'erro' : 'output'}
                    </div>
                    <pre
                      style={{
                        margin: 0,
                        color: toolCall.error ? 'var(--state-error)' : 'var(--text-secondary)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: 12,
                        lineHeight: 1.7,
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      {toolCall.error ? toolCall.error : formatResult(toolCall.result!)}
                    </pre>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </motion.section>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export function parseToolCallEvent(data: string, metaToolCallId?: string, timestamp?: Date): ToolCallData | null {
  try {
    const parsed = JSON.parse(data);
    const id = parsed.id ?? metaToolCallId ?? `tc-${Date.now()}`;

    return {
      id,
      name: parsed.name ?? parsed.tool ?? 'tool',
      args: parsed.args ?? {},
      status: 'calling',
      timestamp: timestamp ?? new Date(),
    };
  } catch {
    return null;
  }
}

// eslint-disable-next-line react-refresh/only-export-components
export function parseToolResultEvent(
  data: string,
  existing: ToolCallData,
  metaToolCallId?: string,
): ToolCallData {
  try {
    const parsed = JSON.parse(data);
    const resultRaw: unknown = parsed.result ?? parsed.result_preview;
    const resultStr = typeof resultRaw === 'string' ? resultRaw : JSON.stringify(resultRaw);
    const error = isErrorResult(resultStr);

    return {
      ...existing,
      id: parsed.id ?? metaToolCallId ?? existing.id,
      result: error ? undefined : resultStr,
      error: error ? resultStr : undefined,
      status: error ? 'error' : 'success',
    };
  } catch {
    return { ...existing, status: 'error', error: 'Falha ao interpretar o retorno da ferramenta.' };
  }
}

// eslint-disable-next-line react-refresh/only-export-components
export { isErrorResult };
