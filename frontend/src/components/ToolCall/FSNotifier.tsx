import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  FilePlus,
  FileSearch,
  FileText,
  Folder,
  FolderPlus,
  Loader2,
  Pencil,
  Trash2,
  XCircle,
} from 'lucide-react';
import type { ToolCallData } from './ToolCallBlock';

export const FS_TOOL_NAMES = new Set([
  'read_file',
  'write_file',
  'edit_file',
  'list_dir',
  'list_directory',
  'grep_search',
  'glob_search',
  'file_finder',
  'delete_file',
  'mkdir',
]);

// eslint-disable-next-line react-refresh/only-export-components
export function isFSTool(name: string): boolean {
  return FS_TOOL_NAMES.has(name.toLowerCase());
}

function shortPath(path: string): string {
  if (!path) return '(sem caminho)';
  const parts = path.replace(/\\/g, '/').split('/').filter(Boolean);
  if (parts.length <= 3) return path;
  return `…/${parts.slice(-2).join('/')}`;
}

function truncate(value: string, max = 220): string {
  return value.length > max ? `${value.slice(0, max)}…` : value;
}

function parseResult(raw: string | undefined): Record<string, unknown> | null {
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const inner = parsed.result;
    if (inner && typeof inner === 'object' && !Array.isArray(inner)) {
      return inner as Record<string, unknown>;
    }
    return parsed;
  } catch {
    return null;
  }
}

interface FSConfig {
  Icon: React.FC<{ size: number }>;
  label: (args: Record<string, unknown>) => string;
  subtitle: (args: Record<string, unknown>, result: Record<string, unknown> | null) => string;
  body: (args: Record<string, unknown>, result: Record<string, unknown> | null) => React.ReactNode;
}

const FS_CONFIG: Record<string, FSConfig> = {
  read_file: {
    Icon: ({ size }) => <FileText size={size} />,
    label: (args) => shortPath(String(args.file_path ?? '')),
    subtitle: (_, result) => result?.line_count ? `${result.line_count} linhas` : 'leitura',
    body: (_, result) => result?.content ? (
      <pre style={preStyle}>{truncate(String(result.content), 420)}</pre>
    ) : null,
  },
  write_file: {
    Icon: ({ size }) => <FilePlus size={size} />,
    label: (args) => shortPath(String(args.file_path ?? '')),
    subtitle: () => 'escrita',
    body: (args) => args.content ? <pre style={preStyle}>{truncate(String(args.content), 420)}</pre> : null,
  },
  edit_file: {
    Icon: ({ size }) => <Pencil size={size} />,
    label: (args) => shortPath(String(args.file_path ?? '')),
    subtitle: (_, result) => result?.replacements != null ? `${result.replacements} troca(s)` : 'edição',
    body: (args) => (
      <pre style={preStyle}>
        {`old: ${truncate(String(args.old_string ?? ''), 160)}\nnew: ${truncate(String(args.new_string ?? ''), 160)}`}
      </pre>
    ),
  },
  list_dir: {
    Icon: ({ size }) => <Folder size={size} />,
    label: (args) => shortPath(String(args.path ?? args.directory_path ?? '')),
    subtitle: (_, result) => `${((result?.entries as unknown[])?.length ?? 0)} item(ns)`,
    body: (_, result) => (
      <pre style={preStyle}>
        {Array.isArray(result?.entries) && result.entries.length > 0
          ? result.entries.slice(0, 18).join('\n')
          : 'diretório vazio'}
      </pre>
    ),
  },
  list_directory: {
    Icon: ({ size }) => <Folder size={size} />,
    label: (args) => shortPath(String(args.directory_path ?? args.path ?? '')),
    subtitle: (_, result) => {
      const files = Array.isArray(result?.files) ? result.files.length : 0;
      const dirs = Array.isArray(result?.directories) ? result.directories.length : 0;
      return `${files + dirs} item(ns)`;
    },
    body: (_, result) => (
      <pre style={preStyle}>
        {[
          ...(Array.isArray(result?.directories) ? result.directories.map((item) => `[dir] ${(item as { name?: string }).name ?? ''}`) : []),
          ...(Array.isArray(result?.files) ? result.files.map((item) => `[file] ${(item as { name?: string }).name ?? ''}`) : []),
        ].slice(0, 18).join('\n') || 'diretório vazio'}
      </pre>
    ),
  },
  grep_search: {
    Icon: ({ size }) => <FileSearch size={size} />,
    label: (args) => `"${truncate(String(args.pattern ?? ''), 32)}"`,
    subtitle: (_, result) => `${result?.total_matches ?? 0} match(es)`,
    body: (_, result) => (
      <pre style={preStyle}>
        {Array.isArray(result?.matches)
          ? result.matches
              .slice(0, 10)
              .map((match) => {
                const typedMatch = match as { file?: string; line_number?: number; line?: string };
                return `${shortPath(String(typedMatch.file ?? ''))}:${typedMatch.line_number ?? '?'} ${typedMatch.line ?? ''}`;
              })
              .join('\n')
          : 'sem resultados'}
      </pre>
    ),
  },
  glob_search: {
    Icon: ({ size }) => <FileSearch size={size} />,
    label: (args) => String(args.pattern ?? '*'),
    subtitle: (_, result) => `${result?.total_count ?? 0} arquivo(s)`,
    body: (_, result) => (
      <pre style={preStyle}>
        {Array.isArray(result?.files) ? result.files.slice(0, 18).join('\n') : 'sem resultados'}
      </pre>
    ),
  },
  file_finder: {
    Icon: ({ size }) => <FileSearch size={size} />,
    label: (args) => String(args.pattern ?? '*'),
    subtitle: (_, result) => `${result?.total_count ?? 0} encontrado(s)`,
    body: (_, result) => (
      <pre style={preStyle}>
        {Array.isArray(result?.files)
          ? result.files
              .slice(0, 18)
              .map((file) => shortPath(String((file as { path?: string }).path ?? '')))
              .join('\n')
          : 'sem resultados'}
      </pre>
    ),
  },
  delete_file: {
    Icon: ({ size }) => <Trash2 size={size} />,
    label: (args) => shortPath(String(args.file_path ?? args.path ?? '')),
    subtitle: () => 'remoção',
    body: () => null,
  },
  mkdir: {
    Icon: ({ size }) => <FolderPlus size={size} />,
    label: (args) => shortPath(String(args.path ?? '')),
    subtitle: () => 'nova pasta',
    body: () => null,
  },
};

const preStyle: React.CSSProperties = {
  margin: 0,
  color: 'var(--text-secondary)',
  fontFamily: 'var(--font-mono)',
  fontSize: 12,
  lineHeight: 1.7,
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
};

interface FSNotifierProps {
  toolCall: ToolCallData;
}

export const FSNotifier: React.FC<FSNotifierProps> = ({ toolCall }) => {
  const [expanded, setExpanded] = useState(true);
  const config = FS_CONFIG[toolCall.name.toLowerCase()];

  if (!config) return null;

  const result = parseResult(toolCall.result);
  const body = config.body(toolCall.args, result);
  const hasBody = Boolean(body);

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
          onClick={() => hasBody && setExpanded((value) => !value)}
          className="flex w-full items-start gap-3 text-left"
          style={{ background: 'transparent', border: 'none', cursor: hasBody ? 'pointer' : 'default' }}
        >
          <div className="min-w-0 flex-1">
            <div className="event-header">
              <config.Icon size={14} />
              <span
                style={{
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 12,
                  letterSpacing: '0.04em',
                }}
              >
                {config.label(toolCall.args)}
              </span>
              <span className="event-badge">filesystem</span>
              <span className="event-badge" style={{ marginLeft: 'auto' }}>
                {config.subtitle(toolCall.args, result)}
              </span>
              <span style={{ color: 'var(--text-meta)' }}>{statusIcon}</span>
              {hasBody && (
                <span className="event-toggle">
                  {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </span>
              )}
            </div>

            <div
              style={{
                marginTop: 10,
                color: 'var(--text-secondary)',
                fontSize: 13,
                lineHeight: 1.6,
              }}
            >
              --- {toolCall.name}
            </div>
          </div>
        </button>

        <AnimatePresence initial={false}>
          {hasBody && expanded && (
            <motion.div
              layout
              key="body"
              className="event-expand event-expand-block"
              initial={{ opacity: 0, height: 0, y: -6 }}
              animate={{ opacity: 1, height: 'auto', y: 0 }}
              exit={{ opacity: 0, height: 0, y: -4 }}
              transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
            >
              <div>
                {toolCall.status === 'error' ? (
                  <pre style={{ ...preStyle, color: 'var(--state-error)' }}>
                    {toolCall.error}
                  </pre>
                ) : toolCall.status === 'calling' && !result ? (
                  <div className="flex items-center gap-3">
                    <span className="signal-dot" />
                    <span style={{ color: 'var(--text-meta)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                      aguardando leitura do notifier
                    </span>
                  </div>
                ) : (
                  body
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </motion.section>
  );
};

export default FSNotifier;
