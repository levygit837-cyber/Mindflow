import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Paperclip, Send, Cpu, ChevronUp } from 'lucide-react';
import { AgentBubble } from '../common/AgentBubble';
import { ThinkingNotifier } from '../common/ThinkingNotifier';
import { useOmniStream } from '../../hooks/useOmniStream';

const STREAM_URL = '/v1/agent/chat/stream';

type AgentType = 'orchestrator' | 'coder' | 'analyst' | 'researcher' | 'default';

type DisplayMsg =
  | { id: string; role: 'user'; content: string; timestamp: Date }
  | { id: string; role: 'agent'; agentType: AgentType; agentName: string; content: string; model: string; timestamp: Date };

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
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
}) => {
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<DisplayMsg[]>([]);
  const [_modelPickerOpen, setModelPickerOpen] = useState(false);
  const [sessionId] = useState(() => propSessionId ?? `sess-${Date.now()}`);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const { events, isStreaming, error, startStream, clearEvents } = useOmniStream(STREAM_URL);

  // ── Auto-resize textarea ───────────────────────────
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  }, [inputValue]);

  // ── Scroll to bottom ───────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, isStreaming, events.length]);

  // ── Finalise streamed events → messages ───────────
  useEffect(() => {
    if (isStreaming) return;
    if (events.length === 0) return;

    // Build agent messages from response events, grouped by agent
    const finalMsgs: DisplayMsg[] = [];
    let cur: { agentType: AgentType; agentName: string; content: string } | null = null;

    for (const ev of events) {
      if (ev.type === 'response') {
        const at = resolveAgentType((ev.meta as any)?.agent);
        const an = capitalize(at);
        if (!cur || cur.agentType !== at) {
          if (cur && cur.content.trim()) finalMsgs.push({
            id: `agent-${Date.now()}-${Math.random()}`,
            role: 'agent',
            agentType: cur.agentType,
            agentName: cur.agentName,
            content: cur.content.trim(),
            model: selectedModel,
            timestamp: new Date(),
          });
          cur = { agentType: at, agentName: an, content: ev.data };
        } else {
          cur.content += ev.data;
        }
      }
    }
    if (cur && cur.content.trim()) {
      finalMsgs.push({
        id: `agent-${Date.now()}-${Math.random()}`,
        role: 'agent',
        agentType: cur.agentType,
        agentName: cur.agentName,
        content: cur.content.trim(),
        model: selectedModel,
        timestamp: new Date(),
      });
    }

    if (finalMsgs.length > 0) {
      setMessages((prev) => [...prev, ...finalMsgs]);
      onAgentCountChange?.(0);
    }
    clearEvents();
  }, [isStreaming]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Live streaming content ─────────────────────────
  const streamingContent = React.useMemo(() => {
    if (!isStreaming) return '';
    return events
      .filter((e) => e.type === 'response')
      .map((e) => e.data)
      .join('');
  }, [events, isStreaming]);

  // Active thinking agent (most recent agent_step or orchestrator)
  const thinkingAgent = React.useMemo((): { type: AgentType; name: string } => {
    for (let i = events.length - 1; i >= 0; i--) {
      const e = events[i];
      if (e.meta && (e.meta as any).agent) {
        const at = resolveAgentType((e.meta as any).agent);
        return { type: at, name: capitalize(at) };
      }
    }
    return { type: 'orchestrator', name: 'Orchestrator' };
  }, [events]);

  // ── Send message ───────────────────────────────────
  const handleSend = useCallback(async () => {
    const text = inputValue.trim();
    if (!text || isStreaming) return;

    setInputValue('');

    const userMsg: DisplayMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);

    // Set title from first message
    if (messages.length === 0) {
      const title = text.length > 40 ? text.slice(0, 40) + '…' : text;
      onTitleChange?.(title);
    }

    onAgentCountChange?.(1);

    await startStream({
      message: text,
      session_id: sessionId,
      model: selectedModel,
      orchestrate: true,
    });
  }, [inputValue, isStreaming, messages.length, sessionId, selectedModel, startStream, onTitleChange, onAgentCountChange]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canSend = inputValue.trim().length > 0 && !isStreaming;

  return (
    <div
      className="flex flex-col flex-1 min-h-0"
      style={{ backgroundColor: '#080614' }}
    >
      {/* ── Messages area ─────────────────────────────── */}
      <div
        className="flex-1 overflow-y-auto"
        style={{ padding: '32px 40px', display: 'flex', flexDirection: 'column', gap: 20 }}
      >
        {messages.length === 0 && !isStreaming ? (
          <motion.div
            className="flex-1 flex items-center justify-center"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <div className="text-center">
              <div
                className="flex items-center justify-center mx-auto"
                style={{
                  width: 48,
                  height: 48,
                  borderRadius: 12,
                  background: 'linear-gradient(135deg, #7C3AFF 0%, #22D3EE 100%)',
                  marginBottom: 16,
                }}
              >
                <Send size={20} color="#fff" />
              </div>
              <h3
                style={{
                  color: '#EDE9FF',
                  fontFamily: 'Space Grotesk, sans-serif',
                  fontSize: 17,
                  fontWeight: 600,
                  marginBottom: 8,
                }}
              >
                Pergunte ao MindFlow
              </h3>
              <p style={{ color: '#4D4575', fontFamily: 'Inter, sans-serif', fontSize: 14 }}>
                O Orquestrador delegará para os agentes especialistas conforme necessário.
              </p>
            </div>
          </motion.div>
        ) : (
          <AnimatePresence initial={false}>
            {messages.map((msg) =>
              msg.role === 'user' ? (
                <motion.div
                  key={msg.id}
                  className="flex justify-end"
                  initial={{ opacity: 0, y: 14 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25 }}
                >
                  <div
                    style={{
                      maxWidth: 520,
                      background: 'linear-gradient(160deg, #4C1D95 0%, #1D4ED8 100%)',
                      borderRadius: '14px 4px 14px 14px',
                      padding: '14px 18px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 8,
                    }}
                  >
                    <p
                      style={{
                        color: '#EDE9FF',
                        fontFamily: 'Inter, sans-serif',
                        fontSize: 14,
                        lineHeight: 1.65,
                        margin: 0,
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {msg.content}
                    </p>
                    <span
                      style={{
                        color: '#A78BFA',
                        fontFamily: 'Inter, sans-serif',
                        fontSize: 11,
                        textAlign: 'right',
                      }}
                    >
                      Você · {msg.timestamp.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </motion.div>
              ) : (
                <AgentBubble
                  key={msg.id}
                  agentType={msg.agentType}
                  agentName={msg.agentName}
                  content={msg.content}
                  timestamp={msg.timestamp}
                  model={msg.model}
                />
              )
            )}

            {/* Live streaming agent bubble */}
            {isStreaming && streamingContent && (
              <motion.div
                key="streaming-agent"
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
              >
                <AgentBubble
                  agentType={thinkingAgent.type}
                  agentName={thinkingAgent.name}
                  content={streamingContent}
                  timestamp={new Date()}
                  model={selectedModel}
                />
              </motion.div>
            )}

            {/* Thinking notifier (while no text yet) */}
            {isStreaming && !streamingContent && (
              <motion.div
                key="thinking"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.22 }}
              >
                <ThinkingNotifier
                  agentType={thinkingAgent.type}
                  agentName={thinkingAgent.name}
                />
              </motion.div>
            )}
          </AnimatePresence>
        )}

        {/* Error banner */}
        {error && (
          <div
            style={{
              padding: '10px 16px',
              borderRadius: 8,
              backgroundColor: '#2A0A0A',
              border: '1px solid #7F1D1D',
              color: '#FCA5A5',
              fontFamily: 'Inter, sans-serif',
              fontSize: 13,
            }}
          >
            Erro: {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ── Input section ──────────────────────────────── */}
      <div style={{ padding: '0 24px 20px' }}>

        {/* Model picker row */}
        <div className="flex items-center" style={{ gap: 8, marginBottom: 10 }}>
          {/* Attach button */}
          <button
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 5,
              backgroundColor: '#130F28',
              border: '1px solid #231E4A',
              borderRadius: 7,
              padding: '7px 10px',
              cursor: 'pointer',
              color: '#4D4575',
            }}
          >
            <Paperclip size={13} color="#4D4575" />
            <span
              style={{
                fontFamily: 'Space Grotesk, sans-serif',
                fontSize: 12,
                fontWeight: 500,
                color: '#4D4575',
              }}
            >
              Anexar
            </span>
          </button>

          {/* Model picker button */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setModelPickerOpen((o) => !o)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                backgroundColor: '#130F28',
                border: '1px solid #2A1F50',
                borderRadius: 7,
                padding: '7px 12px',
                cursor: 'pointer',
              }}
            >
              <Cpu size={13} color="#A78BFA" />
              <span
                style={{
                  fontFamily: 'Space Grotesk, sans-serif',
                  fontSize: 12,
                  fontWeight: 500,
                  color: '#A78BFA',
                  maxWidth: 180,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {selectedModel}
              </span>
              <ChevronUp size={12} color="#4D4575" />
            </button>
          </div>
        </div>

        {/* Input wrapper */}
        <div
          className="flex items-end"
          style={{
            backgroundColor: '#130F28',
            border: '1px solid #2A1F50',
            borderRadius: 12,
            padding: '14px 16px',
            gap: 12,
          }}
        >
          <textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Pergunte ao MindFlow..."
            rows={1}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              resize: 'none',
              fontFamily: 'Inter, sans-serif',
              fontSize: 14,
              color: inputValue ? '#EDE9FF' : '#4D4575',
              lineHeight: 1.5,
              maxHeight: 160,
              caretColor: '#7C3AFF',
            }}
          />

          {/* Send button */}
          <motion.button
            onClick={handleSend}
            disabled={!canSend}
            className="flex items-center justify-center flex-shrink-0"
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: canSend
                ? 'linear-gradient(135deg, #7C3AFF 0%, #5B21B6 100%)'
                : '#1A1545',
              border: 'none',
              cursor: canSend ? 'pointer' : 'not-allowed',
              transition: 'background 0.2s ease',
            }}
            whileHover={canSend ? { scale: 1.08 } : {}}
            whileTap={canSend ? { scale: 0.92 } : {}}
            transition={{ type: 'spring', stiffness: 400, damping: 17 }}
          >
            <Send size={15} color="#fff" />
          </motion.button>
        </div>

        {/* Hint */}
        <p
          style={{
            marginTop: 8,
            textAlign: 'center',
            color: '#4D4575',
            fontFamily: 'Inter, sans-serif',
            fontSize: 11,
          }}
        >
          MindFlow pode cometer erros. Verifique informações importantes.
        </p>
      </div>
    </div>
  );
};
