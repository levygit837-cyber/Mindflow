import React, { useCallback } from 'react';
import { useChatStore } from '../../stores/chatStore';
import { ThinkingBlock } from '../blocks/ThinkingBlock';
import { DelegationCard } from '../blocks/DelegationCard';
import { ToolCallCard } from './ToolCallCard';
import { ThinkingIndicator } from '../indicators/ThinkingIndicator';
import { StreamingIndicator } from './StreamingIndicator';
import { AgentType } from '../../types/backend';

interface EventRailProps {
  className?: string;
}

export const EventRail: React.FC<EventRailProps> = ({ className = '' }) => {
  const { thinkingEvents, toolCallEvents, delegationEvents, activeStreamings, isStreaming, thinkingStreamings } =
    useChatStore();

  // Convert maps to arrays and sort by timestamp
  const sortedThinkingEvents = Array.from(thinkingEvents.values()).sort(
    (a, b) => a.timestamp.getTime() - b.timestamp.getTime()
  );

  const sortedToolCallEvents = Array.from(toolCallEvents.values()).sort(
    (a, b) => a.timestamp.getTime() - b.timestamp.getTime()
  );

  const sortedDelegationEvents = Array.from(delegationEvents.values()).sort(
    (a, b) => a.timestamp.getTime() - b.timestamp.getTime()
  );

  // Combine all events for display
  const allEvents = [
    ...sortedThinkingEvents.map((e) => ({ type: 'thinking' as const, data: e, time: e.timestamp })),
    ...sortedToolCallEvents.map((e) => ({ type: 'tool_call' as const, data: e, time: e.timestamp })),
    ...sortedDelegationEvents.map((e) => ({ type: 'delegation' as const, data: e, time: e.timestamp })),
  ].sort((a, b) => a.time.getTime() - b.time.getTime());

  // Get active thinking indicators (agents currently thinking but no block yet)
  const activeAgents = new Set<AgentType>();
  sortedThinkingEvents.forEach((event) => {
    if (event.status === 'start' || event.status === 'update') {
      activeAgents.add(event.agentType);
    }
  });

  // Get currently streaming agents
  const streamingAgents = Array.from(activeStreamings.entries()).map(([agentType, data]) => ({
    agentType,
    ...data,
  }));

  const handleToggleThinking = useCallback((id: string, expanded: boolean) => {
    useChatStore.getState().updateThinkingEvent(id, { isExpanded: expanded });
  }, []);

  if (allEvents.length === 0 && !isStreaming) {
    return null;
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Active Thinking Indicators - shown when agents are transitioning/thinking */}
      {isStreaming && activeAgents.size > 0 && (
        <div className="flex flex-wrap gap-2">
          {Array.from(activeAgents).map((agentType) => (
            <ThinkingIndicator
              key={`thinking-${agentType}`}
              type={agentType}
              customText={getThinkingText(agentType)}
            />
          ))}
        </div>
      )}

      {/* Streaming Indicators - shown when agents are writing/coding */}
      {streamingAgents.map(({ agentType, text, progress }) => (
        <StreamingIndicator
          key={`streaming-${agentType}`}
          agentType={agentType}
          variant={progress !== undefined ? 'bar' : 'dots'}
          progress={progress}
          text={text}
        />
      ))}

      {/* Event Blocks - all events in chronological order */}
      {allEvents.map((event, index) => {
        switch (event.type) {
          case 'thinking':
            return (
              <ThinkingBlock
                key={`thinking-block-${event.data.id}-${index}`}
                agentType={event.data.agentType}
                reasoning={event.data.reasoning}
                isExpanded={event.data.isExpanded}
                isStreaming={thinkingStreamings.has(event.data.agentType)}
                onToggle={(expanded) => handleToggleThinking(event.data.id, expanded)}
              />
            );

          case 'tool_call':
            return (
              <ToolCallCard
                key={`tool-call-${event.data.id}-${index}`}
                agentType={event.data.agentType}
                toolName={event.data.toolName}
                status={event.data.status}
                input={event.data.input}
                output={event.data.output}
                error={event.data.error}
              />
            );

          case 'delegation':
            return (
              <DelegationCard
                key={`delegation-${event.data.id}-${index}`}
                fromAgent={event.data.fromAgent}
                toAgent={event.data.toAgent}
                strategy={event.data.strategy}
                tools={event.data.tools}
                context={event.data.context}
              />
            );

          default:
            return null;
        }
      })}
    </div>
  );
};

function getThinkingText(agentType: AgentType): string {
  switch (agentType) {
    case 'orchestrator':
      return 'Orchestrator is planning...';
    case 'analyst':
      return 'Analyzing data...';
    case 'coder':
      return 'Preparing code...';
    case 'researcher':
      return 'Researching...';
    default:
      return 'Thinking...';
  }
}

export default EventRail;
