import React, { useEffect, useRef } from 'react';
import { useChatStore } from '../../stores/chatStore';
import { ThinkingBlock } from '../blocks/ThinkingBlock';
import { DelegationCard } from '../blocks/DelegationCard';
import { ToolCallCard } from '../events/ToolCallCard';
import { ThinkingIndicator } from '../indicators/ThinkingIndicator';
import { StreamingIndicator } from '../events/StreamingIndicator';
import { AgentBadge } from '../agents/AgentBadge';
import { AGENTS } from '../../lib/constants';
import { AgentType, StreamEvent } from '../../types/backend';
import { MessageContent } from '../message/MessageContent';

interface ChatViewProps {
  className?: string;
  selectedAgent?: AgentType | null;
}

export const ChatView: React.FC<ChatViewProps> = ({ className = '', selectedAgent }) => {
  const {
    messages,
    thinkingEvents,
    toolCallEvents,
    delegationEvents,
    activeStreamings,
    isStreaming,
    currentAgent,
    thinkingStreamings,
    updateThinkingEvent,
  } = useChatStore();

  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new content arrives
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  // Get events in order for a message
  const getOrderedEventsForMessage = (messageEvents: StreamEvent[]) => {
    const seenEventIds = new Set<string>();
    const seenThinkingAgents = new Set<string>(); // deduplicate per-agent thinking block
    const seenToolIds = new Set<string>();

    return messageEvents
      .filter((e) => {
        if (seenEventIds.has(e.id)) return false;
        seenEventIds.add(e.id);
        return true;
      })
      .map((e) => {
        const agentType = (e.meta?.agent || 'orchestrator') as AgentType;

        if (
          e.type === 'thought' ||
          e.type === 'orchestrator_thinking_start' ||
          e.type === 'orchestrator_thinking' ||
          e.type === 'orchestrator_thinking_end' ||
          e.type === 'specialist_thinking'
        ) {
          // All thinking for an agent is accumulated under a stable key in the store
          const thinkingKey = `thinking-${agentType}`;
          if (seenThinkingAgents.has(thinkingKey)) return null;
          seenThinkingAgents.add(thinkingKey);
          const thinking = thinkingEvents.get(thinkingKey);
          return thinking && thinking.reasoning.trim()
            ? { kind: 'thinking' as const, data: thinking }
            : null;
        }

        if (
          e.type === 'tool_call' ||
          e.type === 'tool_operation_start'
        ) {
          // Resolve the stable tool id the same way chatStore does
          let toolId = e.id;
          try {
            const parsed = JSON.parse(e.data);
            toolId = parsed.id || e.meta?.toolCallId || e.id;
          } catch { /* use e.id */ }
          if (seenToolIds.has(toolId)) return null;
          seenToolIds.add(toolId);
          const tool = toolCallEvents.get(toolId);
          return tool ? { kind: 'tool' as const, data: tool } : null;
        }

        // Skip tool_result events from rendering — they update the tool card directly
        if (e.type === 'tool_result' || e.type === 'tool_operation_complete') {
          return null;
        }

        if (e.type === 'agent_delegation_start') {
          const delegation = delegationEvents.get(e.id);
          return delegation ? { kind: 'delegation' as const, data: delegation } : null;
        }

        if (e.type === 'agent_execution_start') {
          return { kind: 'agent_start' as const, data: { agentType } };
        }

        return null;
      })
      .filter(Boolean);
  };

  if (messages.length === 0 && !isStreaming) {
    return (
      <div className={`flex flex-col items-center justify-center h-full text-center ${className}`}>
        <div className="w-16 h-16 rounded-full bg-[#1a1a1a] border border-[#2a2a2a] flex items-center justify-center mb-4">
          <span className="text-2xl font-bold text-[#707070]">M</span>
        </div>
        <h2 className="text-xl font-semibold text-white mb-2">Welcome to MindFlow</h2>
        <p className="text-[#707070] text-sm max-w-md">
          Select an agent and start a conversation. Agents will show thinking blocks, tool calls,
          and delegation events in real-time.
        </p>
      </div>
    );
  }

  return (
    <div className={`flex flex-col gap-6 ${className}`}>
      {messages.map((message) => {
        if (message.role === 'user') {
          return (
            <div key={message.id} className="flex justify-end">
              <div className="max-w-[80%]">
                <div className="bg-[#2a2a2a] border border-[#3a3a3a] rounded-2xl rounded-tr-sm px-4 py-3">
                  <p className="text-[14px] text-white whitespace-pre-wrap leading-relaxed">
                    {message.content}
                  </p>
                </div>
                <div className="mt-1 text-right">
                  <span className="text-[10px] text-[#505050]">
                    {message.timestamp.toLocaleTimeString()}
                  </span>
                </div>
              </div>
            </div>
          );
        }

        // Assistant message with inline events
        const orderedEvents = message.events ? getOrderedEventsForMessage(message.events) : [];
        const agentType = message.agentType || 'orchestrator';
        const agentConfig = AGENTS[agentType];

        return (
          <div key={message.id} className="flex flex-col gap-2">
            {/* Agent header */}
            <div className="flex items-center gap-2">
              <AgentBadge type={agentType} size="sm" />
              <span className="text-[11px] text-[#707070]">
                {agentConfig?.name || agentType}
              </span>
            </div>

            {/* Inline events (ThinkingBlocks, ToolCalls, DelegationCards) */}
            {orderedEvents.length > 0 && (
              <div className="space-y-2 ml-1 pl-3 border-l-2 border-[#2a2a2a]">
                {orderedEvents.map((event, i) => {
                  if (!event) return null;

                  if (event.kind === 'thinking') {
                    return (
                      <ThinkingBlock
                        key={`${message.id}-thinking-${i}`}
                        agentType={event.data.agentType}
                        reasoning={event.data.reasoning}
                        isExpanded={event.data.isExpanded}
                        isStreaming={thinkingStreamings.has(event.data.agentType)}
                        onToggle={(expanded) =>
                          updateThinkingEvent(event.data.id, { isExpanded: expanded })
                        }
                      />
                    );
                  }

                  if (event.kind === 'tool') {
                    return (
                      <ToolCallCard
                        key={`${message.id}-tool-${i}`}
                        agentType={event.data.agentType}
                        toolName={event.data.toolName}
                        status={event.data.status}
                        input={event.data.input}
                        output={event.data.output}
                        error={event.data.error}
                      />
                    );
                  }

                  if (event.kind === 'delegation') {
                    return (
                      <DelegationCard
                        key={`${message.id}-delegation-${i}`}
                        fromAgent={event.data.fromAgent}
                        toAgent={event.data.toAgent}
                        strategy={event.data.strategy}
                        tools={event.data.tools}
                        context={event.data.context}
                      />
                    );
                  }

                  if (event.kind === 'agent_start') {
                    return (
                      <div key={`${message.id}-agent-start-${i}`} className="flex items-center gap-2 py-1">
                        <AgentBadge type={event.data.agentType} size="sm" />
                        <span className="text-[11px] text-[#707070]">
                          {AGENTS[event.data.agentType]?.name} started
                        </span>
                      </div>
                    );
                  }

                  return null;
                })}
              </div>
            )}

            {/* Response content */}
            {message.content && (
              <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-2xl rounded-tl-sm px-4 py-3">
                <MessageContent content={message.content} agentType={agentType} />
              </div>
            )}

            {/* Show coding streaming indicator if this is the last assistant message and coder is active */}
            {isStreaming &&
              message.id === messages.filter((m) => m.role === 'assistant').slice(-1)[0]?.id && (
                <div className="space-y-2 ml-1">
                  {/* Active thinking indicator - shown as soon as streaming starts, before any event arrives */}
                  {!message.content && (
                    <ThinkingIndicator type={currentAgent || selectedAgent || 'orchestrator'} />
                  )}

                  {/* Coding streaming indicator for Coder agent */}
                  {activeStreamings.has('coder') && (
                    <StreamingIndicator agentType="coder" variant="dots" />
                  )}

                  {/* Generic streaming for other agents */}
                  {Array.from(activeStreamings.entries())
                    .filter(([at]) => at !== 'coder')
                    .map(([agentType, data]) => (
                      <StreamingIndicator
                        key={`streaming-${agentType}`}
                        agentType={agentType as AgentType}
                        variant={data.progress !== undefined ? 'bar' : 'dots'}
                        progress={data.progress}
                        text={data.text}
                      />
                    ))}
                </div>
              )}

            <div className="ml-1">
              <span className="text-[10px] text-[#505050]">
                {message.timestamp.toLocaleTimeString()}
              </span>
            </div>
          </div>
        );
      })}

      {/* Live ThinkingIndicator for when streaming but no message content yet */}
      {isStreaming && currentAgent && messages.filter((m) => m.role === 'assistant').length === 0 && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <AgentBadge type={currentAgent} size="sm" />
          </div>
          <ThinkingIndicator type={currentAgent} />
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
};

export default ChatView;
