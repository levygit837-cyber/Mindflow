import React, { startTransition, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowUpRight, Paperclip } from 'lucide-react';
import { AgentBubble } from '../common/AgentBubble';
import { ThinkingNotifier } from '../common/ThinkingNotifier';
import { ThoughtBubble } from '../common/ThoughtBubble';
import { DelegationCard } from '../common/DelegationCard';
import { FolderPathBar } from '../common/FolderPathBar';
import { ToolCallBlock, parseToolCallEvent, parseToolResultEvent } from '../ToolCall/ToolCallBlock';
import { FSNotifier, isFSTool } from '../ToolCall/FSNotifier';
import { ShellTabsPanel } from './ShellTabsPanel';
import type { ToolCallData } from '../ToolCall/ToolCallBlock';
import { useOmniStream } from '../../hooks/useOmniStream';
import { useAppStore } from '../../stores/appStore';

const STREAM_URL = '/v1/agent/chat/stream';

type AgentType = 'orchestrator' | 'coder' | 'analyst' | 'researcher' | 'default';

type DisplayMsg =
  | { id: string; role: 'user'; content: string; timestamp: Date }
  | { id: string; role: 'agent'; agentType: AgentType; agentName: string; content: string; model: string; timestamp: Date }
  | { id: string; role: 'tool_call'; toolCall: ToolCallData }
  | { id: string; role: 'thought'; agentType: AgentType; agentName: string; content: string }
  | {
      id: string;
      role: 'delegation';
      title: string;
      subtitle: string;
      agents: Array<{
        agentType: 'orchestrator' | 'analyst' | 'coder' | 'researcher';
        agentName: string;
        status: 'active' | 'pending' | 'done' | 'waiting';
      }>;
      pipelineLabel: string;
    };

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function resolveAgentType(raw: string | undefined | null): AgentType {
  const map: Record<string, AgentType> = {
    orchestrator: 'orchestrator',
    coder: 'coder',
    analyst: 'analyst',
    researcher: 'researcher',
  };

  return map[raw?.toLowerCase() ?? ''] ?? 'default';
}

function eventKey(prefix: string, primary: number | string, secondary?: number | string) {
  return secondary == null ? `${prefix}-${primary}` : `${prefix}-${primary}-${secondary}`;
}

function parseDelegationEvent(eventData: string): {
  type: AgentType;
  name: string;
  task: string;
} | null {
  try {
    const data = JSON.parse(eventData) as Record<string, string>;
    const raw = (data.agent_type ?? '').toLowerCase();
    const type = resolveAgentType(raw);
    return {
      type,
      name: capitalize(raw || 'agent'),
      task: data.task ?? '',
    };
  } catch {
    return null;
  }
}

function buildDisplayMessagesFromEvents(
  events: ReturnType<typeof useOmniStream>['events'],
  selectedModel: string,
): DisplayMsg[] {
  const displayMessages: DisplayMsg[] = [];
  const toolMessageIndex = new Map<string, number>();

  events.forEach((event, index) => {
    const seq = event.seq ?? index;
    const agentType = resolveAgentType((event.meta as Record<string, unknown> | undefined)?.agent as string | undefined);
    const agentName = capitalize(agentType);

    if (event.type === 'thought') {
      displayMessages.push({
        id: eventKey('thought', seq, index),
        role: 'thought',
        agentType,
        agentName,
        content: event.data,
      });
      return;
    }

    if (event.type === 'agent_delegation_start') {
      const delegation = parseDelegationEvent(event.data);
      if (!delegation) return;

      displayMessages.push({
        id: eventKey('delegation', seq, index),
        role: 'delegation',
        title: 'Orchestrator',
        subtitle: delegation.task || 'Delegou tarefa para especialista.',
        agents: [
          { agentType: 'orchestrator', agentName: 'Orchestrator', status: 'done' },
          {
            agentType: delegation.type === 'default' ? 'analyst' : delegation.type,
            agentName: delegation.name,
            status: 'active',
          },
        ],
        pipelineLabel: 'delegation',
      });
      return;
    }

    if (event.type === 'tool_call') {
      const metaId = (event.meta as Record<string, unknown> | undefined)?.toolCallId as string | undefined;
      const toolCall = parseToolCallEvent(event.data, metaId);
      if (!toolCall) return;

      toolMessageIndex.set(toolCall.id, displayMessages.length);
      displayMessages.push({
        id: eventKey('tool', toolCall.id, index),
        role: 'tool_call',
        toolCall,
      });
      return;
    }

    if (event.type === 'tool_result') {
      const metaId = (event.meta as Record<string, unknown> | undefined)?.toolCallId as string | undefined;
      let toolId: string | undefined;

      try {
        const data = JSON.parse(event.data) as Record<string, unknown>;
        toolId = (data.id as string | undefined) ?? metaId;
      } catch {
        toolId = metaId;
      }

      if (!toolId) return;

      const displayIndex = toolMessageIndex.get(toolId);
      if (displayIndex == null) return;

      const existingMessage = displayMessages[displayIndex];
      if (existingMessage?.role !== 'tool_call') return;

      displayMessages[displayIndex] = {
        ...existingMessage,
        toolCall: parseToolResultEvent(event.data, existingMessage.toolCall, metaId),
      };
      return;
    }

    if (event.type === 'response') {
      const lastMessage = displayMessages[displayMessages.length - 1];
      if (
        lastMessage?.role === 'agent' &&
        lastMessage.agentType === agentType
      ) {
        lastMessage.content += event.data;
        return;
      }

      displayMessages.push({
        id: eventKey('agent', seq, index),
        role: 'agent',
        agentType,
        agentName,
        content: event.data,
        model: selectedModel,
        timestamp: new Date(),
      });
    }
  });

  return displayMessages;
}

interface ChatInterfaceProps {
  sessionId?: string;
  selectedModel: string;
  onTitleChange?: (title: string) => void;
  onAgentCountChange?: (count: number) => void;
  onWorkflowChange?: (type: 'parallel' | 'sequential' | 'orchestrator' | 'chain') => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  sessionId: propSessionId,
  selectedModel,
  onTitleChange,
  onAgentCountChange,
  onWorkflowChange,
}) => {
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<DisplayMsg[]>([]);
  const [sessionId] = useState(() => propSessionId ?? `sess-${Date.now()}`);
  const [folderPath, setFolderPath] = useState('');
  const [isLoadingHistory, setIsLoadingHistory] = useState(Boolean(propSessionId));
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pendingSaveRef = useRef<{ userText: string; isFirst: boolean } | null>(null);

  const { events, isStreaming, error, startStream, clearEvents } = useOmniStream(STREAM_URL);
  const bumpSessionRefresh = useAppStore((state) => state.bumpSessionRefresh);

  useEffect(() => {
    onWorkflowChange?.('orchestrator');
  }, [onWorkflowChange]);

  useEffect(() => {
    if (!propSessionId) return;

    fetch(`/v1/chat/sessions/${propSessionId}`)
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (!data?.messages?.length) return;

        const historicMessages: DisplayMsg[] = (data.messages as Array<{
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

            return {
              id: `hist-agent-${message.id}`,
              role: 'agent' as const,
              agentType: 'default' as AgentType,
              agentName: 'Agent',
              content: message.content,
              model: message.model ?? '',
              timestamp: new Date(message.created_at),
            };
          });

        setMessages(historicMessages);
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
  }, [messages.length, isStreaming, events.length]);

  useEffect(() => {
    if (isStreaming || events.length === 0) return;

    const finalMessages = buildDisplayMessagesFromEvents(events, selectedModel);

    if (finalMessages.length > 0) {
      startTransition(() => {
        setMessages((previous) => [...previous, ...finalMessages]);
      });
      onAgentCountChange?.(0);
    }

    const pending = pendingSaveRef.current;
    pendingSaveRef.current = null;

    const assistantText = events
      .filter((event) => event.type === 'response')
      .map((event) => event.data)
      .join('');

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
    events,
    selectedModel,
    sessionId,
    onTitleChange,
    onAgentCountChange,
    bumpSessionRefresh,
    clearEvents,
  ]);

  const streamingMessages = useMemo(
    () => buildDisplayMessagesFromEvents(events, selectedModel),
    [events, selectedModel],
  );

  const thinkingAgent = useMemo((): { type: AgentType; name: string } => {
    for (let index = events.length - 1; index >= 0; index -= 1) {
      const event = events[index];
      if (event.meta && (event.meta as Record<string, unknown>).agent) {
        const type = resolveAgentType((event.meta as Record<string, unknown>).agent as string);
        return { type, name: capitalize(type) };
      }
    }
    return { type: 'orchestrator', name: 'Orchestrator' };
  }, [events]);

  const lastThought = useMemo(() => {
    for (let index = events.length - 1; index >= 0; index -= 1) {
      const event = events[index];
      if (event.type === 'thought') return event.data;
      if (event.type === 'agent_step') {
        try {
          const data = JSON.parse(event.data) as Record<string, string>;
          const text = data.detail ?? data.stepName ?? '';
          if (text) return text;
        } catch {
          return '';
        }
      }
    }
    return '';
  }, [events]);

  const handleSend = useCallback(async () => {
    const text = inputValue.trim();
    if (!text || isStreaming) return;

    setInputValue('');
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
      model: selectedModel,
      orchestrate: true,
      ...(folderPath.trim() ? { folder_path: folderPath.trim() } : {}),
    });
  }, [
    folderPath,
    inputValue,
    isStreaming,
    messages.length,
    onAgentCountChange,
    onTitleChange,
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

  return (
    <div className="diagram-canvas flex min-h-0 flex-1 flex-col" style={{ backgroundColor: 'var(--background)' }}>
      <div className="flex-1 overflow-y-auto px-4 py-5 md:px-8 md:py-7">
        <div className="chat-column mx-auto flex w-full max-w-[980px] flex-col gap-7">
          {isLoadingHistory ? (
            <div className="event-shell w-full">
              <div className="event-track">
                <span className="signal-dot idle" />
              </div>
              <div className="event-node-lab">
                <span className="mono-label">carregando histórico</span>
              </div>
            </div>
          ) : messages.length === 0 && !isStreaming ? (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="event-shell w-full"
            >
              <div className="event-track">
                <span className="signal-dot idle" />
              </div>

              <div className="event-node-lab">
                <div className="mono-label mb-3">chat / minimal trace</div>
                <h2
                  style={{
                    color: 'var(--text-primary)',
                    fontSize: 24,
                    fontWeight: 600,
                    letterSpacing: '-0.04em',
                  }}
                >
                  Descreva a tarefa.
                </h2>
                <p style={{ marginTop: 14, maxWidth: 620, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                  O orchestrator aparece como linha principal. Delegações, tool calls e retornos passam a ser mostrados como trilhos finos, setas e pontos de ação.
                </p>
                <div className="mt-5 flex flex-wrap gap-2">
                  <span className="event-badge">--- thinking &gt; expandir</span>
                  <span className="event-badge">orchestrator ── delega</span>
                  <span className="event-badge">tool call ● sinapse roxa</span>
                </div>
              </div>
            </motion.div>
          ) : (
            <AnimatePresence initial={false}>
              {messages.map((message) => {
                if (message.role === 'user') {
                  return (
                    <motion.section
                      key={message.id}
                      className="user-event"
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <div className="event-header justify-end">
                        <span
                          style={{
                            color: 'var(--text-meta)',
                            fontFamily: 'var(--font-mono)',
                            fontSize: 11,
                          }}
                        >
                          {message.timestamp.toLocaleTimeString('pt-BR', {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                        <span className="mono-label">you</span>
                        <span className="mono-label">-&gt; task</span>
                      </div>

                      <p className="user-event-copy">{message.content}</p>
                    </motion.section>
                  );
                }

                if (message.role === 'tool_call') {
                  return isFSTool(message.toolCall.name)
                    ? <FSNotifier key={message.id} toolCall={message.toolCall} />
                    : <ToolCallBlock key={message.id} toolCall={message.toolCall} />;
                }

                if (message.role === 'thought') {
                  return (
                    <ThoughtBubble
                      key={message.id}
                      agentType={message.agentType}
                      agentName={message.agentName}
                      content={message.content}
                      isStreaming={false}
                    />
                  );
                }

                if (message.role === 'delegation') {
                  return (
                    <DelegationCard
                      key={message.id}
                      title={message.title}
                      subtitle={message.subtitle}
                      agents={message.agents}
                      pipelineLabel={message.pipelineLabel}
                    />
                  );
                }

                if (message.role === 'agent') {
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

                return null;
              })}

              {isStreaming && streamingMessages.map((message) => {
                if (message.role === 'tool_call') {
                  return isFSTool(message.toolCall.name)
                    ? <FSNotifier key={message.id} toolCall={message.toolCall} />
                    : <ToolCallBlock key={message.id} toolCall={message.toolCall} />;
                }

                if (message.role === 'thought') {
                  return (
                    <ThoughtBubble
                      key={message.id}
                      agentType={message.agentType}
                      agentName={message.agentName}
                      content={message.content}
                      isStreaming
                    />
                  );
                }

                if (message.role === 'delegation') {
                  return (
                    <DelegationCard
                      key={message.id}
                      title={message.title}
                      subtitle={message.subtitle}
                      agents={message.agents}
                      pipelineLabel={message.pipelineLabel}
                    />
                  );
                }

                if (message.role === 'agent') {
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

                return null;
              })}

              {isStreaming && streamingMessages.length === 0 && (
                <ThinkingNotifier
                  key="thinking"
                  agentType={thinkingAgent.type}
                  agentName={thinkingAgent.name}
                  lastThought={lastThought || undefined}
                />
              )}
            </AnimatePresence>
          )}

          {error && (
            <div
              className="event-expand"
              style={{
                color: 'var(--state-error)',
                fontFamily: 'var(--font-mono)',
                fontSize: 12,
              }}
            >
              erro / {error}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      <div
        className="border-t px-4 py-4 md:px-6 md:py-5"
        style={{
          borderColor: 'var(--line-primary)',
          background: 'linear-gradient(180deg, rgba(8, 9, 11, 0.72) 0%, rgba(7, 8, 10, 0.9) 100%)',
        }}
      >
        <div className="mx-auto flex w-full max-w-[980px] flex-col gap-3">
          <FolderPathBar value={folderPath} onChange={setFolderPath} />
          <ShellTabsPanel sessionId={sessionId} isStreaming={isStreaming} />

          <div className="flex flex-wrap items-center gap-2">
            <button type="button" className="subtle-button">
              <Paperclip size={14} />
              <span className="mono-label" style={{ letterSpacing: '0.08em' }}>
                anexar
              </span>
            </button>

            <span className="mono-chip">
              <span className="signal-dot idle" />
              {selectedModel}
            </span>

            <span className="mono-chip hidden md:inline-flex">
              orchestrator / live
            </span>
          </div>

          <div className="chat-compose-shell px-4 py-4 md:px-5 md:py-5" style={{ paddingLeft: 30 }}>
            <div className="flex items-end gap-3">
              <textarea
                ref={textareaRef}
                value={inputValue}
                onChange={(event) => setInputValue(event.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
                placeholder="descreva a tarefa, a estética ou a próxima decisão"
                className="min-h-[28px] flex-1 resize-none bg-transparent outline-none"
                style={{
                  color: inputValue ? 'var(--text-primary)' : 'var(--text-meta)',
                  fontSize: 15,
                  lineHeight: 1.7,
                  maxHeight: 180,
                }}
              />

              <motion.button
                type="button"
                onClick={handleSend}
                disabled={!canSend}
                className="subtle-button justify-center"
                style={{
                  minHeight: 42,
                  minWidth: 42,
                  paddingInline: 12,
                  opacity: canSend ? 1 : 0.45,
                  background: canSend ? 'var(--gradient-button)' : 'rgba(255,255,255,0.02)',
                }}
                whileHover={canSend ? { y: -1 } : {}}
                whileTap={canSend ? { y: 1 } : {}}
                transition={{ duration: 0.15 }}
              >
                <ArrowUpRight size={16} />
              </motion.button>
            </div>
          </div>

          <p
            style={{
              color: 'var(--text-meta)',
              fontFamily: 'var(--font-mono)',
              fontSize: 11,
              letterSpacing: '0.04em',
            }}
          >
            verifique resultados críticos antes de executar algo sensível.
          </p>
        </div>
      </div>
    </div>
  );
};
