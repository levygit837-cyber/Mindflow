/**
 * SwarmState Annotation for LangGraph StateGraph
 *
 * Defines the shared state that flows through all swarm agent nodes.
 * Uses Annotation.Root with explicit reducers for each field.
 */

import { Annotation, messagesStateReducer } from "@langchain/langgraph";
import { BaseMessage } from "@langchain/core/messages";
import type {
  TaskStatus,
  AnalystAlertLevel,
  TokenStreamEntry,
  ToolCallEntry,
  FileChangeEntry,
  InterruptionRequest,
  ReviewImprovement,
  NotificationEvent,
} from "@shared/types/swarm";

const TOKEN_STREAM_CAP = 10_000;
const NOTIFICATION_CAP = 500;

/**
 * Append reducer: concatenates new items onto the existing array.
 */
function appendReducer<T>(existing: T[], incoming: T[]): T[] {
  return existing.concat(incoming);
}

/**
 * Append reducer with a maximum cap. When exceeded, trims from the front.
 */
function cappedAppendReducer<T>(cap: number) {
  return (existing: T[], incoming: T[]): T[] => {
    const combined = existing.concat(incoming);
    if (combined.length > cap) {
      return combined.slice(combined.length - cap);
    }
    return combined;
  };
}

/**
 * The SwarmState Annotation defines every field in the shared graph state,
 * along with reducers that control how concurrent or sequential node
 * outputs are merged.
 *
 * Scalar fields use last-write-wins (no reducer needed — Annotation<T>).
 * List fields use append reducers, some with caps for bounded memory.
 */
export const SwarmStateAnnotation = Annotation.Root({
  // -- Scalar fields (last-write-wins) --
  task_id: Annotation<string>,
  task_description: Annotation<string>,
  task_status: Annotation<TaskStatus>,

  coder_plan: Annotation<string | null>,
  coder_output: Annotation<string | null>,

  analyst_state: Annotation<AnalystAlertLevel>,
  analyst_report_md: Annotation<string>,
  analyst_interruption_request: Annotation<InterruptionRequest | null>,

  reviewer_report_md: Annotation<string>,

  sandbox_display: Annotation<string>,

  // -- List fields with append reducers --
  coder_token_stream: Annotation<TokenStreamEntry[]>({
    reducer: cappedAppendReducer<TokenStreamEntry>(TOKEN_STREAM_CAP),
    default: () => [],
  }),

  coder_tool_calls: Annotation<ToolCallEntry[]>({
    reducer: appendReducer,
    default: () => [],
  }),

  coder_file_changes: Annotation<FileChangeEntry[]>({
    reducer: appendReducer,
    default: () => [],
  }),

  reviewer_improvements: Annotation<ReviewImprovement[]>({
    reducer: appendReducer,
    default: () => [],
  }),

  notifications: Annotation<NotificationEvent[]>({
    reducer: cappedAppendReducer<NotificationEvent>(NOTIFICATION_CAP),
    default: () => [],
  }),

  messages: Annotation<BaseMessage[]>({
    reducer: messagesStateReducer,
    default: () => [],
  }),
});

/**
 * Inferred state type from the annotation — use this in node signatures.
 */
export type SwarmState = typeof SwarmStateAnnotation.State;

/**
 * Inferred update type — what nodes return as partial state updates.
 */
export type SwarmStateUpdate = typeof SwarmStateAnnotation.Update;
