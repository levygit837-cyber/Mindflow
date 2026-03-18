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

type AgentType = 'orchestrator' | 'coder' | 'analyst' | 'researcher' | 'default';

export interface ToolCallData {
  id: string;
  name: string;
  args: Record<string, unknown>;
  toolMeta?: Record<string, unknown>;
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
  gitnexus_status: { category: 'gitnexus', Icon: ({ size }) => <Box size={size} /> },
  gitnexus_query: { category: 'gitnexus', Icon: ({ size }) => <Box size={size} /> },
  gitnexus_context: { category: 'gitnexus', Icon: ({ size }) => <Box size={size} /> },
  gitnexus_impact: { category: 'gitnexus', Icon: ({ size }) => <Box size={size} /> },
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

const TOOL_TONE: Record<ToolCallData['status'], 'warning' | 'success' | 'error'> = {
  calling: 'warning',
  success: 'success',
  error: 'error',
};

const TOOL_STATUS_LABELS: Record<ToolCallData['status'], string> = {
  calling: 'executando ferramenta',
  success: 'resultado recebido',
  error: 'falha de execução',
};

function getToolMeta(name: string, explicitMeta?: Record<string, unknown>): ToolMeta {
  const normalized = name.toLowerCase();
  const explicitCategory = typeof explicitMeta?.category === 'string'
    ? explicitMeta.category
    : typeof explicitMeta?.family === 'string'
      ? explicitMeta.family
      : undefined;

  if ((typeof explicitMeta?.family === 'string' && explicitMeta.family === 'gitnexus') || normalized.startsWith('gitnexus_')) {
    return {
      ...(TOOL_META[normalized] ?? { category: 'gitnexus', Icon: ({ size }) => <Box size={size} /> }),
      category: explicitCategory ?? 'gitnexus',
    };
  }

  const base = TOOL_META[normalized] ?? DEFAULT_META;
  if (!explicitCategory) return base;

  return {
    ...base,
    category: explicitCategory,
  };
}

function formatValue(value: unknown, maxLength = 220): string {
  const raw = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  return raw.length > maxLength ? `${raw.slice(0, maxLength)}…` : raw;
}

function formatArgs(args: Record<string, unknown>): string {
  if (Object.keys(args).length === 0) return 'no params';

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

function humanizeToolName(name: string) {
  return name.replaceAll('_', ' ');
}

function formatAgentBadge(agentType?: AgentType, agentName?: string) {
  if (!agentName) return null;
  return agentType === 'default' ? agentName : `${agentName} · agent`;
}

const detailSurfaceStyle: React.CSSProperties = {
  margin: 0,
  padding: '14px 16px',
  borderRadius: 18,
  border: '1px solid var(--line-soft)',
  background: 'color-mix(in srgb, var(--surface-glass) 62%, var(--surface) 38%)',
  color: 'var(--text-secondary)',
  fontFamily: 'var(--font-mono)',
  fontSize: 'calc(13px * var(--font-scale, 1))',
  lineHeight: 1.7,
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
};

interface ToolCallBlockProps {
  toolCall: ToolCallData;
  agentType?: AgentType;
  agentName?: string;
}

export const ToolCallBlock: React.FC<ToolCallBlockProps> = ({
  toolCall,
  agentType,
  agentName,
}) => {
  const [expanded, setExpanded] = useState(true);
  const meta = useMemo(
    () => getToolMeta(toolCall.name, toolCall.toolMeta),
    [toolCall.name, toolCall.toolMeta],
  );
  const tone = TOOL_TONE[toolCall.status];
  const agentBadge = formatAgentBadge(agentType, agentName);
  const argCount = Object.values(toolCall.args).filter(
    (value) => value !== undefined && value !== null && value !== '',
  ).length;
  const hasArgs = argCount > 0;
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
      className="event-shell min-w-0 w-full"
    >
      <div className="event-track">
        <span className={toolCall.status === 'calling' ? 'signal-dot' : 'signal-dot idle'} />
      </div>

      <motion.div layout className="event-node-lab">
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          className={`tool-event-card tool-event-card--${tone}`}
          style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}
        >
          <div className="tool-event-card-header">
            <div className="tool-event-topline">
              <span className="tool-event-lead" />

              <div className="tool-event-topline-copy">
                <span className="tool-event-title">Tool</span>
                <span className="tool-event-sep">/</span>
                <span className="tool-event-status">{TOOL_STATUS_LABELS[toolCall.status]}</span>
              </div>

              {toolCall.status === 'calling' ? (
                <span className="tool-event-live">
                  <span />
                  <span />
                  <span />
                </span>
              ) : (
                <span className="tool-event-icon">{statusIcon}</span>
              )}
            </div>

            <div className="tool-event-meta">
              <div className="tool-event-name-row">
                <meta.Icon size={14} />
                <span className="tool-event-name">{toolCall.name}</span>
              </div>

              <div className="tool-event-badges">
                <span className="event-badge">{meta.category}</span>
                <span className="event-badge">{humanizeToolName(toolCall.name)}</span>
                {agentBadge ? <span className="event-badge">{agentBadge}</span> : null}
                <span className="event-badge">
                  {toolCall.status === 'calling' ? 'running' : toolCall.status === 'success' ? 'ready' : 'error'}
                </span>
              </div>
            </div>

            <div className="tool-event-summary">
              {hasArgs ? `${argCount} ${argCount === 1 ? 'param' : 'params'}` : 'direct execution'}
            </div>

            <span className="event-toggle">
              <span className="tool-event-icon">
                {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </span>
            </span>
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
                    <pre style={detailSurfaceStyle}>{formatArgs(toolCall.args)}</pre>
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
                          fontSize: 'calc(13px * var(--font-scale, 1))',
                        }}
                      >
                        waiting for tool response
                      </div>
                    </div>
                  </div>
                )}

                {hasOutput && (
                  <div>
                    <div className="mono-label mb-2">
                      {toolCall.error ? 'error' : 'result'}
                    </div>
                    <pre
                      style={{
                        ...detailSurfaceStyle,
                        color: toolCall.error ? 'var(--state-error)' : 'var(--text-secondary)',
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
      toolMeta: parsed.tool_meta ?? undefined,
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
      toolMeta: parsed.tool_meta ?? existing.toolMeta,
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
