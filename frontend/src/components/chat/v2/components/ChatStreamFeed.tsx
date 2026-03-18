/**
 * Chat Visualization V2 - ChatStreamFeed Container
 *
 * Main integration component that brings all V2 components together.
 * Transforms stream events into presentation structures and renders
 * the appropriate components based on the current state.
 *
 * Performance optimizations:
 * - Memoized buildStreamPresentation to avoid recalculation on every render
 * - Memoized expensive calculations (liveLabel, isSlowRun)
 * - Lazy loaded AgentJourneyPanel and JourneyTimeline
 * - Memoized callback functions
 */

import React, { useEffect, useState, useMemo, useCallback, lazy, Suspense } from 'react';
import { buildStreamPresentation, getMindflowV2ElapsedLabel } from '../../streamPresentation';
import type { StreamPresentation } from '../../streamPresentation';
import { ThinkingNotifierRow } from './ThinkingNotifierRow';
import { ThoughtBlock } from './ThoughtBlock';
import { DelegationCard } from './DelegationCard';
import { ToolEventCard } from './ToolEventCard';
import { MemoryRecallCard } from './MemoryRecallCard';
import { AgentTodoList } from './AgentTodoList';
import {
  StreamNotifier,
  ChatDiagnostic,
  DiagnosticNotifier,
} from '../../../chat/streamComponents';

// Lazy load heavy components
const AgentJourneyPanel = lazy(() => import('./AgentJourneyPanel').then(m => ({ default: m.AgentJourneyPanel })));
const JourneyTimeline = lazy(() => import('./JourneyTimeline').then(m => ({ default: m.JourneyTimeline })));

export interface ChatStreamFeedProps {
  events: Array<{
    id?: string;
    type: string;
    data: string;
    meta?: Record<string, unknown> | null;
  }>;
  isStreaming: boolean;
  startedAt?: Date | null;
  hasHistory?: boolean;
  className?: string;
}

/**
 * ChatStreamFeed - Main container for V2 chat visualization
 *
 * Responsibilities:
 * - Transform events using buildStreamPresentation
 * - Manage liveTick timer for elapsed time updates
 * - Manage openDelegationId state for journey panel
 * - Render all V2 components conditionally
 */
export const ChatStreamFeed: React.FC<ChatStreamFeedProps> = ({
  events,
  isStreaming,
  startedAt,
  hasHistory = false,
  className = '',
}) => {
  // State management
  const [liveTick, setLiveTick] = useState(0);
  const [openDelegationId, setOpenDelegationId] = useState<string | null>(null);

  // Transform events into presentation structure (memoized for performance)
  const presentation: StreamPresentation = useMemo(
    () => buildStreamPresentation(events, isStreaming),
    [events, isStreaming]
  );

  // Calculate elapsed label (updates with liveTick)
  const liveLabel = getMindflowV2ElapsedLabel(startedAt);

  // Calculate elapsed milliseconds
  const elapsedMs = startedAt ? Date.now() - startedAt.getTime() : 0;

  // Check if run is slow (memoized based on elapsed time)
  const isSlowRun = useMemo(
    () => isStreaming && elapsedMs > 30_000,
    [isStreaming, elapsedMs]
  );

  // LiveTick timer - updates every 1s when streaming
  useEffect(() => {
    if (!isStreaming) return;

    const interval = setInterval(() => {
      setLiveTick((tick) => tick + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [isStreaming]);

  // Interaction callbacks (memoized to prevent unnecessary re-renders)
  const handleOpenJourney = useCallback((delegationId: string) => {
    setOpenDelegationId(delegationId);
  }, []);

  const handleCloseJourney = useCallback(() => {
    setOpenDelegationId(null);
  }, []);

  // Find delegation for journey panel (memoized)
  const openDelegation = useMemo(
    () => openDelegationId
      ? presentation.delegations.find((d) => d.id === openDelegationId)
      : null,
    [openDelegationId, presentation.delegations]
  );

  // Filter journey steps for open delegation (memoized)
  const journeySteps = useMemo(
    () => openDelegation
      ? presentation.journey.steps.filter((step) => {
          // Include steps that match the delegation's agent type
          const delegationAgentType = openDelegation.agents[0]?.agentType;
          return step.agentType === delegationAgentType;
        })
      : [],
    [openDelegation, presentation.journey.steps]
  );

  return (
    <div className={`mindflow-v2-chat-stream-feed ${className}`}>
      {/* ThinkingNotifierRow - Always visible */}
      <ThinkingNotifierRow
        activeAgents={presentation.activeAgents}
        statuses={presentation.thinkingStatuses}
        className="mb-4"
      />

      {/* AgentTodoList - Conditional: isStreaming && delegations.length > 0 */}
      {isStreaming && presentation.delegations.length > 0 && (
        <AgentTodoList
          delegations={presentation.delegations.map((d) => ({
            ...d,
            variant: 'simple' as const,
          }))}
          className="mb-4"
        />
      )}

      {/* StreamNotifier - Conditional: isStreaming && !hasHistory */}
      {isStreaming && !hasHistory && presentation.notifiers.length > 0 && (
        <div className="mb-4 flex flex-col gap-2">
          {presentation.notifiers.map((notifier) => (
            <StreamNotifier
              key={notifier.id}
              title={notifier.title}
              status={notifier.status}
              message={notifier.message}
              detail={notifier.detail}
              tone={notifier.tone}
            />
          ))}
        </div>
      )}

      {/* ThoughtBlock array */}
      {presentation.thoughts.length > 0 && (
        <div className="mb-4 flex flex-col gap-3">
          {presentation.thoughts.map((thought) => (
            <ThoughtBlock
              key={thought.id}
              agentType={thought.agentType}
              title={thought.title}
              status={thought.status}
              content={thought.content}
              summary={thought.summary}
              defaultExpanded={thought.defaultExpanded}
            />
          ))}
        </div>
      )}

      {/* DelegationCard array */}
      {presentation.delegations.length > 0 && (
        <div className="mb-4 flex flex-col gap-3">
          {presentation.delegations.map((delegation) => (
            <DelegationCard
              key={delegation.id}
              title={delegation.title}
              subtitle={delegation.subtitle}
              status={delegation.status}
              pipeline={delegation.pipeline}
              summary={delegation.summary}
              agents={delegation.agents}
              variant="rich"
              accent={delegation.accent}
              onOpenJourney={() => handleOpenJourney(delegation.id)}
            />
          ))}
        </div>
      )}

      {/* ToolEventCard array */}
      {presentation.toolEvents.length > 0 && (
        <div className="mb-4 flex flex-col gap-3">
          {presentation.toolEvents.map((tool) => (
            <ToolEventCard
              key={tool.id}
              toolName={tool.name}
              status={tool.status}
              args={tool.args}
              result={tool.result}
              error={tool.error}
              elapsed={tool.elapsed}
              agentName={tool.agentName}
            />
          ))}
        </div>
      )}

      {/* MemoryRecallCard array */}
      {presentation.memoryEvents.length > 0 && (
        <div className="mb-4 flex flex-col gap-3">
          {presentation.memoryEvents.map((memory) => (
            <MemoryRecallCard
              key={memory.id}
              source={memory.source}
              status={memory.status}
              label={memory.label}
              count={memory.count}
              detail={memory.detail}
              agentName={memory.agentName}
              done={memory.done}
            />
          ))}
        </div>
      )}

      {/* StreamNotifier array (for history mode) */}
      {hasHistory && presentation.notifiers.length > 0 && (
        <div className="mb-4 flex flex-col gap-2">
          {presentation.notifiers.map((notifier) => (
            <StreamNotifier
              key={notifier.id}
              title={notifier.title}
              status={notifier.status}
              message={notifier.message}
              detail={notifier.detail}
              tone={notifier.tone}
            />
          ))}
        </div>
      )}

      {/* DiagnosticNotifier for errors */}
      {presentation.errors.length > 0 && (
        <div className="mb-4 flex flex-col gap-2">
          {presentation.errors.map((error) => (
            <DiagnosticNotifier
              key={error.id}
              message={error.message}
              code={error.code}
              recoverable={error.recoverable}
            />
          ))}
        </div>
      )}

      {/* ChatDiagnostic - scope escape */}
      {presentation.diagnostics.scopeEscape && (
        <ChatDiagnostic variant="scope-escape" className="mb-4" />
      )}

      {/* ChatDiagnostic - slow run */}
      {isSlowRun && (
        <ChatDiagnostic
          variant="slow-run"
          elapsed={liveLabel}
          className="mb-4"
        />
      )}

      {/* JourneyTimeline - Conditional: journey.steps.length > 0 */}
      {presentation.journey.steps.length > 0 && (
        <Suspense fallback={<div className="mb-4 p-4 text-center text-sm text-gray-500">Loading timeline...</div>}>
          <JourneyTimeline
            title="Jornada de Execução"
            subtitle="Sequência completa de eventos e delegações"
            steps={presentation.journey.steps}
            summary={presentation.journey.summary}
            durationLabel={liveLabel}
            liveLabel={isStreaming ? 'ao vivo' : 'concluído'}
            activeStepId={presentation.journey.activeStepId}
            className="mb-4"
          />
        </Suspense>
      )}

      {/* AgentJourneyPanel - Conditional: openDelegationId !== null */}
      {openDelegation && (
        <Suspense fallback={null}>
          <AgentJourneyPanel
            delegation={openDelegation}
            steps={journeySteps}
            isStreaming={isStreaming}
            onClose={handleCloseJourney}
          />
        </Suspense>
      )}
    </div>
  );
};

ChatStreamFeed.displayName = 'ChatStreamFeed';
