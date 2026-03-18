import React, { startTransition, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowUpRight, ChevronDown, Paperclip } from 'lucide-react';
import { AgentBubble } from '../common/AgentBubble';
import { ThinkingNotifier } from '../common/ThinkingNotifier';
import { ThoughtBubble } from '../common/ThoughtBubble';
import { DelegationCard } from '../common/DelegationCard';
import { FolderPathBar } from '../common/FolderPathBar';
import { SimpleDelegation } from '../common/SimpleDelegation';
import { StreamNotifier, type StreamNotifierTone } from '../common/StreamNotifier';
import { ToolCallBlock, parseToolCallEvent, parseToolResultEvent } from '../ToolCall/ToolCallBlock';
import { FSNotifier, isFSTool } from '../ToolCall/FSNotifier';
import type { ToolCallData } from '../ToolCall/ToolCallBlock';
import { useOmniStream } from '../../hooks/useOmniStream';
import { useAppStore, useSettings } from '../../stores/appStore';
import type { LlmProvider } from '../../types';
import { shouldDisplayNotifierEvent, type StreamDisplayOptions } from './displayPolicy';
import { mapNotifierPayload } from './notifierMapping';

const STREAM_URL = '/v1/agent/chat/stream';

type AgentType = 'orchestrator' | 'coder' | 'analyst' | 'researcher' | 'default';

type DisplayMsg =
  | { id: string; role: 'user'; content: string; timestamp: Date }
  | { id: string; role: 'agent'; agentType: AgentType; agentName: string; content: string; model: string; timestamp: Date }
  | { id: string; role: 'tool_call'; toolCall: ToolCallData; agentType?: AgentType; agentName?: string }
  | { id: string; role: 'thought'; agentType: AgentType; agentName: string; content: string }
  | {
      id: string;
      role: 'stream_notifier';
      title: string;
      status: string;
      detail?: string;
      tone: StreamNotifierTone;
      active?: boolean;
      agentType?: AgentType;
      agentName?: string;
    }
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
    }
  | {
      id: string;
      role: 'simple_delegation';
      agentType: AgentType;
      agentName: string;
      task: string;
    };

const AGENT_DISPLAY_NAMES: Record<AgentType, string> = {
  orchestrator: 'Orchestrator',
  coder: 'Coder',
  analyst: 'Analyst',
  researcher: 'Research',
  default: 'Specialist',
};

function resolveAgentType(raw: string | undefined | null): AgentType {
  const map: Record<string, AgentType> = {
    orchestrator: 'orchestrator',
    coder: 'coder',
    analyst: 'analyst',
    researcher: 'researcher',
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
    normalized !== 'orchestrator'
  ) {
    return titleCase(cleaned);
  }

  return AGENT_DISPLAY_NAMES[agentType];
}

function inferHistoricAgent(content: string, model?: string) {
  const normalized = `${content} ${model ?? ''}`.toLowerCase();

  if (/(researcher|research|search|lookup)/.test(normalized)) {
    return {
      agentType: 'researcher' as AgentType,
      agentName: AGENT_DISPLAY_NAMES.researcher,
    };
  }

  if (/(analyst|analysis|audit|investigation)/.test(normalized)) {
    return {
      agentType: 'analyst' as AgentType,
      agentName: AGENT_DISPLAY_NAMES.analyst,
    };
  }

  if (/(coder|engineer|developer|implementation|build)/.test(normalized)) {
    return {
      agentType: 'coder' as AgentType,
      agentName: AGENT_DISPLAY_NAMES.coder,
    };
  }

  if (/(orchestrator|routing|delegate)/.test(normalized)) {
    return {
      agentType: 'orchestrator' as AgentType,
      agentName: AGENT_DISPLAY_NAMES.orchestrator,
    };
  }

  const specialistMatch = content.match(/^([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s_-]{2,32})(?::|-)\s/);
  if (specialistMatch) {
    return {
      agentType: 'default' as AgentType,
      agentName: titleCase(specialistMatch[1]),
    };
  }

  return {
    agentType: 'default' as AgentType,
    agentName: AGENT_DISPLAY_NAMES.default,
  };
}

function eventKey(prefix: string, primary: number | string, secondary?: number | string) {
  return secondary == null ? `${prefix}-${primary}` : `${prefix}-${primary}-${secondary}`;
}

function parseJson<T>(value: string): T | null {
  try {
    return JSON.parse(value) as T;
  } catch {
    return null;
  }
}

function parseDelegationEvent(eventData: string): {
  type: AgentType;
  name: string;
  task: string;
} | null {
  const data = parseJson<Record<string, string>>(eventData);
  if (!data) return null;

  const raw = (data.agent_type ?? '').toLowerCase();
  const type = resolveAgentType(raw);
  return {
    type,
    name: formatAgentName(
      type,
      data.agent_name ?? data.specialist_name ?? data.specialist ?? data.agent_type,
    ),
    task: data.task ?? '',
  };
}

function formatNotifierAgentLabel(raw: string | undefined | null) {
  const agentType = resolveAgentType(raw);
  return {
    agentType,
    agentName: formatAgentName(agentType, raw),
  };
}

function renderDisplayMessage(message: DisplayMsg, streaming = false) {
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
              fontSize: 'calc(12px * var(--font-scale, 1))',
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
      ? (
          <FSNotifier
            key={message.id}
            toolCall={message.toolCall}
            agentType={message.agentType}
            agentName={message.agentName}
          />
        )
      : (
          <ToolCallBlock
            key={message.id}
            toolCall={message.toolCall}
            agentType={message.agentType}
            agentName={message.agentName}
          />
        );
  }

  if (message.role === 'thought') {
    return (
      <ThoughtBubble
        key={message.id}
        agentType={message.agentType}
        agentName={message.agentName}
        content={message.content}
        isStreaming={streaming}
      />
    );
  }

  if (message.role === 'stream_notifier') {
    return (
      <StreamNotifier
        key={message.id}
        title={message.title}
        status={message.status}
        detail={message.detail}
        tone={message.tone}
        active={message.active}
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

  if (message.role === 'simple_delegation') {
    return (
      <SimpleDelegation
        key={message.id}
        agentType={message.agentType}
        agentName={message.agentName}
        task={message.task}
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
}

function buildDisplayMessagesFromEvents(
  events: ReturnType<typeof useOmniStream>['events'],
  selectedModel: string,
  displayOptions: StreamDisplayOptions,
): DisplayMsg[] {
  const displayMessages: DisplayMsg[] = [];
  const toolMessageIndex = new Map<string, number>();

  events.forEach((event, index) => {
    const seq = event.seq ?? index;
    const meta = (event.meta as Record<string, unknown> | undefined) ?? {};
    const rawAgent = (meta.agent_type ??
      meta.agent ??
      meta.specialist_type ??
      meta.specialist) as string | undefined;
    const rawAgentName = (meta.agent_name ??
      meta.specialist_name ??
      meta.specialist ??
      meta.name ??
      rawAgent) as string | undefined;
    const agentType = resolveAgentType(rawAgent);
    const agentName = formatAgentName(agentType, rawAgentName);

    if (event.type === 'thought') {
      if (!displayOptions.showReasoning) return;
      displayMessages.push({
        id: eventKey('thought', seq, index),
        role: 'thought',
        agentType,
        agentName,
        content: event.data,
      });
      return;
    }

    if (event.type === 'orchestrator_thinking_start') {
      if (!displayOptions.enableNotifications) return;
      displayMessages.push({
        id: eventKey('stream', seq, index),
        role: 'stream_notifier',
        title: 'Routing',
        status: 'analisando pedido',
        detail: 'orchestrator avaliando o melhor fluxo para esta tarefa',
        tone: 'accent',
        active: true,
        agentType: 'orchestrator',
        agentName: 'Orchestrator',
      });
      return;
    }

    if (event.type === 'orchestrator_decision') {
      const decision = parseJson<{
        agent?: string;
        task?: string;
        rationale?: string;
        execution_strategy?: string;
      }>(event.data);

      if (!decision) return;

      const { agentName } = formatNotifierAgentLabel(decision.agent);
      const isDirectResponse = decision.execution_strategy === 'direct_response';
      if (displayOptions.enableNotifications) {
        displayMessages.push({
          id: eventKey('stream', seq, index),
          role: 'stream_notifier',
          title: 'Routing',
          status: isDirectResponse ? 'resposta direta' : `${agentName.toLowerCase()} selecionado`,
          detail: decision.task || decision.rationale || undefined,
          tone: 'accent',
          active: false,
          agentType: isDirectResponse ? 'orchestrator' : resolveAgentType(decision.agent),
          agentName: isDirectResponse ? 'Orchestrator' : agentName,
        });
      }

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

    if (event.type === 'specialist_activation') {
      const activation = parseJson<{
        agent_type?: string;
        agent?: string;
        is_core?: boolean;
      }>(event.data);

      if (!activation) return;

      return;
    }

    if (event.type === 'agent_delegation_complete') {
      const completion = parseJson<{
        agent_type?: string;
        agent?: string;
        success?: boolean;
        error_message?: string;
      }>(event.data);

      const completionType = resolveAgentType(completion?.agent_type ?? completion?.agent);
      const completionName = formatAgentName(
        completionType,
        completion?.agent_type ?? completion?.agent,
      );
      const isSuccessful = completion?.success !== false;

      if (displayOptions.enableNotifications && !isSuccessful) {
        displayMessages.push({
          id: eventKey('stream', seq, index),
          role: 'stream_notifier',
          title: completionName,
          status: 'falha de execução',
          detail: completion?.error_message || `${completionName} encerrou com erro.`,
          tone: 'error',
          active: false,
          agentType: completionType,
          agentName: completionName,
        });
      }
      return;
    }

    if (event.type === 'notifier') {
      if (!shouldDisplayNotifierEvent(event.data, displayOptions)) return;
      const notifierMessage = mapNotifierPayload(event.data);
      if (!notifierMessage) return;

      displayMessages.push({
        id: eventKey('stream', seq, index),
        role: 'stream_notifier',
        ...notifierMessage,
        agentType,
        agentName,
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
        agentType,
        agentName,
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

    if (event.type === 'error') {
      displayMessages.push({
        id: eventKey('stream', seq, index),
        role: 'stream_notifier',
        title: 'Run',
        status: 'falha de execução',
        detail: event.data || 'erro inesperado durante o stream',
        tone: 'error',
        active: false,
      });
      return;
    }

    if (event.type === 'response') {
      const lastMessage = displayMessages[displayMessages.length - 1];
      if (
        lastMessage?.role === 'agent' &&
        lastMessage.agentType === agentType &&
        lastMessage.agentName === agentName
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
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pendingSaveRef = useRef<{ userText: string; isFirst: boolean } | null>(null);

  const { events, isStreaming, error, startStream, clearEvents } = useOmniStream(STREAM_URL);
  const bumpSessionRefresh = useAppStore((state) => state.bumpSessionRefresh);
  const settings = useSettings();

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

    const finalMessages = buildDisplayMessagesFromEvents(events, selectedModel, settings);

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
    settings,
    sessionId,
    onTitleChange,
    onAgentCountChange,
    bumpSessionRefresh,
    clearEvents,
  ]);

  const streamingMessages = useMemo(
    () => buildDisplayMessagesFromEvents(events, selectedModel, settings),
    [events, selectedModel, settings],
  );

  const thinkingAgent = useMemo((): { type: AgentType; name: string } => {
    for (let index = events.length - 1; index >= 0; index -= 1) {
      const event = events[index];
      if (event.meta) {
        const meta = event.meta as Record<string, unknown>;
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

  return (
    <div className="diagram-canvas flex min-h-0 flex-1 flex-col">
      <div className="flex-1 overflow-y-auto px-4 py-5 md:px-8 md:py-7">
        <div className="chat-column flex w-full flex-col gap-7">
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
                  loading history
                </span>
              </div>
            </div>
          ) : messages.length === 0 && !isStreaming ? (
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
                    fontSize: 40,
                    fontWeight: 500,
                    letterSpacing: '-0.04em',
                  }}
                >
                  Descreva o trabalho.
                </h2>
                <p
                  style={{
                    marginTop: 14,
                    maxWidth: 620,
                    color: 'var(--text-secondary)',
                    fontFamily: 'var(--font-sans)',
                    lineHeight: 1.8,
                  }}
                >
                  O chat principal foi reduzido para a mesma estrutura do Pencil: conversa, input e contexto mínimo.
                </p>
              </div>
            </motion.div>
          ) : (
            <AnimatePresence initial={false}>
              {messages.map((message) => renderDisplayMessage(message))}

              {isStreaming && streamingMessages.map((message) => renderDisplayMessage(message, true))}

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
        className="border-t px-4 py-3 md:px-6 md:py-4"
        style={{
          borderColor: 'var(--line-primary)',
          background: 'color-mix(in srgb, var(--surface) 92%, transparent)',
        }}
      >
        <div className="chat-input-section flex w-full flex-col gap-3">
          <div className="chat-input-toolbar">
            <button
              type="button"
              className="chat-compose-action"
              onClick={() => setShowFolderPathBar((current) => !current)}
            >
              <Paperclip size={14} />
              <span>{folderPath ? 'folder path set' : 'folder path'}</span>
            </button>

            <button type="button" className="chat-compose-action">
              <span>{selectedModel}</span>
              <ChevronDown size={14} />
            </button>
          </div>

          {(showFolderPathBar || folderPath) && (
            <FolderPathBar value={folderPath} onChange={setFolderPath} />
          )}

          <div className="chat-compose-shell px-4 py-3 md:px-5 md:py-4">
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
                  color: inputValue ? 'var(--text-primary)' : 'var(--text-meta)',
                  fontSize: 'calc(16px * var(--font-scale, 1))',
                  fontFamily: 'var(--font-sans)',
                  lineHeight: 1.7,
                  maxHeight: 180,
                }}
              />

              <motion.button
                type="button"
                onClick={handleSend}
                disabled={!canSend}
                className="chat-compose-send"
                style={{ opacity: canSend ? 1 : 0.45 }}
                whileHover={canSend ? { y: -1 } : {}}
                whileTap={canSend ? { y: 1 } : {}}
                transition={{ duration: 0.15 }}
              >
                <ArrowUpRight size={16} />
              </motion.button>
            </div>
          </div>

          <p className="chat-compose-hint">
            {folderPath
              ? `Folder path ativo: ${folderPath}. O Orchestrator pode delegar a exploração dessa pasta para o Analyst.`
              : 'MindFlow pode cometer erros. Verifique informações importantes.'}
          </p>
        </div>
      </div>
    </div>
  );
};
