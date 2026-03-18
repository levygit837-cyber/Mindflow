import React, { startTransition, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowUpRight, ChevronDown, Paperclip } from 'lucide-react';
import { AgentBubble } from '../common/AgentBubble';
import { FolderPathBar } from '../common/FolderPathBar';
import { useOmniStream } from '../../hooks/useOmniStream';
import { useAppStore } from '../../stores/appStore';
import type { LlmProvider } from '../../types';
import type { AgentType } from '../../types/agentTypes';

const STREAM_URL = '/v1/agent/chat/stream';

const AGENT_DISPLAY_NAMES: Partial<Record<AgentType, string>> = {
  orchestrator: 'Orchestrator',
  coder: 'Coder',
  analyst: 'Analyst',
  researcher: 'Research',
  architect: 'Architect',
  critic: 'Critic',
  creative: 'Creative',
  security: 'Security',
  default: 'Agent',
};

type DisplayMsg =
  | { id: string; role: 'user'; content: string; timestamp: Date }
  | {
      id: string;
      role: 'agent';
      agentType: AgentType;
      agentName: string;
      content: string;
      model: string;
      timestamp: Date;
    };

function resolveAgentType(raw: string | undefined | null): AgentType {
  const map: Record<string, AgentType> = {
    orchestrator: 'orchestrator',
    coder: 'coder',
    analyst: 'analyst',
    researcher: 'researcher',
    architect: 'architect',
    critic: 'critic',
    creative: 'creative',
    security: 'security',
    security_guard: 'security',
    arch_tech: 'architect',
  };

  return map[raw?.toLowerCase() ?? ''] ?? 'default';
}

function titleCase(value: string) {
  return value
    .split(/[\s_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function formatAgentName(agentType: AgentType, rawName?: string | null) {
  const cleaned = String(rawName ?? '').trim();
  const normalized = cleaned.toLowerCase().replace(/[\s-]+/g, '_');

  if (
    cleaned &&
    !/^(agent|default)$/i.test(cleaned) &&
    normalized !== agentType &&
    normalized !== `${agentType}_agent` &&
    normalized !== 'researcher' &&
    normalized !== 'research' &&
    normalized !== 'analyst' &&
    normalized !== 'coder' &&
    normalized !== 'orchestrator' &&
    normalized !== 'architect' &&
    normalized !== 'critic' &&
    normalized !== 'creative' &&
    normalized !== 'security' &&
    normalized !== 'security_guard'
  ) {
    return titleCase(cleaned);
  }

  return AGENT_DISPLAY_NAMES[agentType] ?? 'Agent';
}

function inferHistoricAgent(content: string, model?: string) {
  const normalized = `${content} ${model ?? ''}`.toLowerCase();

  if (/(researcher|research|search|lookup)/.test(normalized)) {
    return { agentType: 'researcher' as AgentType, agentName: AGENT_DISPLAY_NAMES.researcher! };
  }
  if (/(analyst|analysis|audit|investigation)/.test(normalized)) {
    return { agentType: 'analyst' as AgentType, agentName: AGENT_DISPLAY_NAMES.analyst! };
  }
  if (/(coder|engineer|developer|implementation|build)/.test(normalized)) {
    return { agentType: 'coder' as AgentType, agentName: AGENT_DISPLAY_NAMES.coder! };
  }
  if (/(orchestrator|routing|delegate)/.test(normalized)) {
    return { agentType: 'orchestrator' as AgentType, agentName: AGENT_DISPLAY_NAMES.orchestrator! };
  }

  const specialistMatch = content.match(/^([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s_-]{2,32})(?::|-)\s/);
  if (specialistMatch) {
    return { agentType: 'default' as AgentType, agentName: titleCase(specialistMatch[1]) };
  }

  return { agentType: 'default' as AgentType, agentName: AGENT_DISPLAY_NAMES.default! };
}

function getAgentFromEvents(
  events: ReturnType<typeof useOmniStream>['events'],
): { type: AgentType; name: string } {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];
    const meta = event.meta as Record<string, unknown> | undefined;
    if (!meta) continue;

    const rawAgent = (meta.agent_type ??
      meta.agent ??
      meta.specialist_type ??
      meta.specialist) as string | undefined;

    if (!rawAgent) continue;

    const type = resolveAgentType(rawAgent);
    return {
      type,
      name: formatAgentName(
        type,
        (meta.agent_name ??
          meta.specialist_name ??
          meta.specialist ??
          meta.agent ??
          meta.agent_type) as string | undefined,
      ),
    };
  }

  return { type: 'orchestrator', name: 'Orchestrator' };
}

function getAssistantText(events: ReturnType<typeof useOmniStream>['events']) {
  return events
    .filter((event) => event.type === 'response')
    .map((event) => event.data)
    .join('');
}

function renderMessage(message: DisplayMsg): React.ReactNode {
  if (message.role === 'user') {
    return (
      <motion.section
        key={message.id}
        className="user-event"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <span
            style={{
              color: 'var(--text-meta)',
              fontFamily: 'var(--font-mono)',
              fontSize: 10,
              fontWeight: 600,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
            }}
          >
            You
          </span>
          <span
            style={{
              marginLeft: 'auto',
              color: 'var(--text-meta)',
              fontFamily: 'var(--font-mono)',
              fontSize: 10,
            }}
          >
            {message.timestamp.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
        <p className="user-event-copy">{message.content}</p>
      </motion.section>
    );
  }

  return (
    <AgentBubble
      key={message.id}
      agentType={message.agentType}
      agentName={message.agentName}
      content={message.content}
      timestamp={message.timestamp}
      model={message.model}
    />
  );
}

interface ChatInterfaceProps {
  sessionId?: string;
  selectedProvider: LlmProvider;
  selectedModel: string;
  onTitleChange?: (title: string) => void;
  onAgentCountChange?: (count: number) => void;
  onWorkflowChange?: (type: 'parallel' | 'sequential' | 'orchestrator' | 'chain') => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  sessionId: propSessionId,
  selectedProvider,
  selectedModel,
  onTitleChange,
  onAgentCountChange,
  onWorkflowChange,
}) => {
  const [inputValue, setInputValue] = useState('');
  const [folderPath, setFolderPath] = useState('');
  const [showFolderPathBar, setShowFolderPathBar] = useState(false);
  const [messages, setMessages] = useState<DisplayMsg[]>([]);
  const [sessionId] = useState(() => propSessionId ?? `sess-${Date.now()}`);
  const [isLoadingHistory, setIsLoadingHistory] = useState(Boolean(propSessionId));
  const [streamStartedAt, setStreamStartedAt] = useState<Date | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pendingSaveRef = useRef<{ userText: string; isFirst: boolean } | null>(null);

  const { events, isStreaming, error, startStream, clearEvents } = useOmniStream(STREAM_URL);
  const bumpSessionRefresh = useAppStore((state) => state.bumpSessionRefresh);

  const streamingText = useMemo(() => getAssistantText(events), [events]);
  const streamingAgent = useMemo(() => getAgentFromEvents(events), [events]);

  useEffect(() => {
    onWorkflowChange?.('orchestrator');
  }, [onWorkflowChange]);

  useEffect(() => {
    if (!propSessionId) return;

    fetch(`/v1/chat/sessions/${propSessionId}`)
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (!data) return;

        const historicMessages: DisplayMsg[] = ((data.messages ?? []) as Array<{
          id: number;
          role: string;
          content: string;
          model?: string;
          created_at: string;
        }>)
          .filter((message) => message.content)
          .map((message) => {
            if (message.role === 'user') {
              return {
                id: `hist-user-${message.id}`,
                role: 'user' as const,
                content: message.content,
                timestamp: new Date(message.created_at),
              };
            }

            const historicAgent = inferHistoricAgent(message.content, message.model);

            return {
              id: `hist-agent-${message.id}`,
              role: 'agent' as const,
              agentType: historicAgent.agentType,
              agentName: historicAgent.agentName,
              content: message.content,
              model: message.model ?? '',
              timestamp: new Date(message.created_at),
            };
          });

        if (historicMessages.length > 0) {
          setMessages(historicMessages);
        }
        if (data.title) onTitleChange?.(data.title);
      })
      .catch(() => undefined)
      .finally(() => setIsLoadingHistory(false));
  }, [propSessionId, onTitleChange]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
  }, [inputValue]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, isStreaming, streamingText.length]);

  useEffect(() => {
    if (isStreaming || error || events.length === 0) return;

    const assistantText = streamingText;
    const pending = pendingSaveRef.current;
    pendingSaveRef.current = null;

    if (assistantText) {
      const agent = getAgentFromEvents(events);

      startTransition(() => {
        setMessages((previous) => [
          ...previous,
          {
            id: `agent-${Date.now()}`,
            role: 'agent',
            agentType: agent.type,
            agentName: agent.name,
            content: assistantText,
            model: selectedModel,
            timestamp: new Date(),
          },
        ]);
      });
    }

    onAgentCountChange?.(0);
    setStreamStartedAt(null);

    if (pending && assistantText && pending.isFirst) {
      fetch(`/v1/chat/sessions/${sessionId}/generate-title`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: pending.userText }),
      })
        .then((response) => (response.ok ? response.json() : null))
        .then((data) => {
          if (data?.title) {
            onTitleChange?.(data.title);
            bumpSessionRefresh();
          }
        })
        .catch(() => undefined);
    }

    clearEvents();
  }, [
    isStreaming,
    error,
    events,
    streamingText,
    selectedModel,
    sessionId,
    onTitleChange,
    onAgentCountChange,
    bumpSessionRefresh,
    clearEvents,
  ]);

  useEffect(() => {
    if (!error) return;
    pendingSaveRef.current = null;
    setStreamStartedAt(null);
    onAgentCountChange?.(0);
    clearEvents();
  }, [error, clearEvents, onAgentCountChange]);

  const handleSend = useCallback(async () => {
    const text = inputValue.trim();
    if (!text || isStreaming) return;

    setInputValue('');
    setStreamStartedAt(new Date());

    const isFirst = messages.length === 0;
    const userMessage: DisplayMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date(),
    };

    setMessages((previous) => [...previous, userMessage]);

    if (isFirst) {
      const title = text.length > 42 ? `${text.slice(0, 42)}…` : text;
      onTitleChange?.(title);
    }

    onAgentCountChange?.(1);
    pendingSaveRef.current = { userText: text, isFirst };

    await startStream({
      message: text,
      session_id: sessionId,
      provider: selectedProvider,
      model: selectedModel,
      orchestrate: true,
      folder_path: folderPath.trim() || undefined,
    });
  }, [
    folderPath,
    inputValue,
    isStreaming,
    messages.length,
    onAgentCountChange,
    onTitleChange,
    selectedProvider,
    selectedModel,
    sessionId,
    startStream,
  ]);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  const canSend = inputValue.trim().length > 0 && !isStreaming;
  const showHistory = messages.length > 0 || isStreaming;

  return (
    <div className="diagram-canvas flex min-h-0 flex-1 flex-col">
      <div className="flex-1 overflow-y-auto" style={{ padding: '24px 32px' }}>
        <div className="chat-column mx-auto flex w-full max-w-3xl flex-col" style={{ gap: 20 }}>
          {isLoadingHistory ? (
            <div className="mx-auto w-full">
              <div className="event-node-lab">
                <span
                  style={{
                    color: 'var(--text-secondary)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 'calc(13px * var(--font-scale, 1))',
                  }}
                >
                  loading...
                </span>
              </div>
            </div>
          ) : showHistory ? (
            <>
              {messages.map((message) => renderMessage(message))}

              {isStreaming &&
                (streamingText ? (
                  <AgentBubble
                    key="streaming-agent"
                    agentType={streamingAgent.type}
                    agentName={streamingAgent.name}
                    content={streamingText}
                    timestamp={streamStartedAt ?? new Date()}
                    model={selectedModel}
                  />
                ) : (
                  <motion.div
                    key="streaming-status"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                    className="event-node-lab"
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span
                        style={{
                          width: 6,
                          height: 6,
                          borderRadius: '50%',
                          background: 'var(--text-meta)',
                          flexShrink: 0,
                        }}
                      />
                      <span
                        style={{
                          color: 'var(--text-primary)',
                          fontFamily: 'var(--font-mono)',
                          fontSize: 11,
                          fontWeight: 600,
                          letterSpacing: '0.1em',
                          textTransform: 'uppercase',
                        }}
                      >
                        {streamingAgent.name}
                      </span>
                      <span
                        style={{
                          marginLeft: 'auto',
                          color: 'var(--text-meta)',
                          fontFamily: 'var(--font-mono)',
                          fontSize: 11,
                        }}
                      >
                        respondendo...
                      </span>
                    </div>
                  </motion.div>
                ))}
            </>
          ) : (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="mx-auto w-full"
            >
              <div className="event-node-lab">
                <h2
                  style={{
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-brand)',
                    fontSize: 32,
                    fontWeight: 400,
                    letterSpacing: '-0.01em',
                    lineHeight: 1.15,
                  }}
                >
                  Descreva o trabalho.
                </h2>
                <p
                  style={{
                    marginTop: 10,
                    maxWidth: 480,
                    color: 'var(--text-meta)',
                    fontFamily: 'var(--font-sans)',
                    fontSize: 13,
                    lineHeight: 1.65,
                  }}
                >
                  O chat agora mostra apenas conversa e resposta final. O resto da trilha foi removido para a refatoração.
                </p>
              </div>
            </motion.div>
          )}

          {error && (
            <div
              className="event-expand"
              style={{
                color: 'var(--state-error)',
                fontFamily: 'var(--font-mono)',
                fontSize: 'calc(13px * var(--font-scale, 1))',
              }}
            >
              error / {error}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      <div
        style={{
          borderTop: '1px solid var(--line-primary)',
          background: 'var(--surface)',
          padding: '16px 32px',
        }}
      >
        <div className="chat-input-section mx-auto flex w-full max-w-3xl flex-col gap-2">
          <div className="chat-input-toolbar">
            <button
              type="button"
              className="chat-compose-action"
              onClick={() => setShowFolderPathBar((current) => !current)}
            >
              <Paperclip size={13} />
              <span>{folderPath ? 'folder set' : 'folder'}</span>
            </button>

            <button type="button" className="chat-compose-action">
              <span>{selectedModel}</span>
              <ChevronDown size={13} />
            </button>
          </div>

          {(showFolderPathBar || folderPath) && <FolderPathBar value={folderPath} onChange={setFolderPath} />}

          <div className="chat-compose-shell" style={{ padding: '12px 16px' }}>
            <div className="flex items-end gap-3">
              <textarea
                ref={textareaRef}
                value={inputValue}
                onChange={(event) => setInputValue(event.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
                placeholder="Pergunte ao MindFlow..."
                className="min-h-[28px] flex-1 resize-none bg-transparent outline-none"
                style={{
                  color: 'var(--text-primary)',
                  fontSize: 'calc(14px * var(--font-scale, 1))',
                  fontFamily: 'var(--font-sans)',
                  lineHeight: 1.6,
                  maxHeight: 180,
                }}
              />

              <motion.button
                type="button"
                onClick={handleSend}
                disabled={!canSend}
                className="chat-compose-send"
                style={{ opacity: canSend ? 1 : 0.38 }}
                whileHover={canSend ? { y: -1 } : {}}
                whileTap={canSend ? { y: 1 } : {}}
                transition={{ duration: 0.15 }}
              >
                <ArrowUpRight size={15} />
              </motion.button>
            </div>
          </div>

          <p className="chat-compose-hint">
            {folderPath
              ? `Folder: ${folderPath}`
              : 'MindFlow pode cometer erros. Verifique informações importantes.'}
          </p>
        </div>
      </div>
    </div>
  );
};
