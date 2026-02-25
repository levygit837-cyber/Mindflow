import "server-only";
/**
 * Swarm StateGraph — wires all agent and pure-function nodes into a
 * compiled LangGraph StateGraph with conditional routing edges.
 *
 * Graph topology (from spec §5.3):
 *
 *   __start__ → orchestrator
 *       ├─(error)─────────────────────────────────────▶ notifier → __end__
 *       └─(normal)─▶ coder
 *                       ├─(error)─────────────────────▶ notifier → __end__
 *                       └─(normal)─▶ live_analyst
 *                                       ├─(CRITICAL)─▶ orchestrator (loop)
 *                                       └─(normal)───▶ sandbox_renderer
 *                                                          └──▶ reviewer
 *                                                                  └──▶ notifier → __end__
 */

import { StateGraph, START, END } from "@langchain/langgraph";
import { SwarmStateAnnotation } from "./state";
import type { SwarmState, SwarmStateUpdate } from "./state";
import { NotifierService } from "./notifier";
import { createOrchestratorNode } from "./orchestrator";
import { createCoderNode } from "./coder";
import { createAnalystNode } from "./live-analyst";
import { createReviewerNode } from "./reviewer";
import { createSandboxRendererNode } from "./sandbox-renderer";
import type { PromptContext } from "./prompts/router";
import type { LLMProvider } from "@shared/types/agent";
import { getCheckpointer } from "@backend/db/postgres";
import { createLogger } from "@backend/utils/logger";

const logger = createLogger("swarm:graph");

// ---------------------------------------------------------------------------
// Routing functions — determine the next node based on current state
// ---------------------------------------------------------------------------

/**
 * After the orchestrator: route to coder (normal) or notifier (error).
 */
function routeAfterOrchestrator(state: SwarmState): string {
  if (state.task_status === "error") return "notifier";
  return "coder";
}

/**
 * After the coder: route to live_analyst (normal) or notifier (error).
 */
function routeAfterCoder(state: SwarmState): string {
  if (state.task_status === "error") return "notifier";
  return "live_analyst";
}

/**
 * After the live analyst:
 *   - CRITICAL interruption → loop back to orchestrator
 *   - Otherwise → sandbox_renderer
 */
function routeAfterAnalyst(state: SwarmState): string {
  if (state.analyst_interruption_request !== null) return "orchestrator";
  return "sandbox_renderer";
}

// ---------------------------------------------------------------------------
// Notifier graph node (distinct from NotifierService)
// ---------------------------------------------------------------------------

/**
 * Create the notifier graph node — a pure function that flushes accumulated
 * notifications from state through the NotifierService for SSE broadcast,
 * then clears them from the graph state.
 *
 * If the task has reached a terminal status (complete or error), the node
 * emits a final AGENT_STATE_CHANGE to signal stream closure.
 */
function createNotifierNode(notifier: NotifierService) {
  return function notifierNode(state: SwarmState): SwarmStateUpdate {
    const pending = state.notifications;

    logger.info("Notifier node invoked", {
      pending_notifications: pending.length,
      task_status: state.task_status,
    });

    // Broadcast each queued notification through the service.
    // The individual agent nodes already called notifier.emit() when they
    // created these events, so subscribers already received them in real-time.
    // This node exists to clear the state buffer and handle terminal signals.

    // Signal stream closure on terminal states
    if (
      state.task_status === "complete" ||
      state.task_status === "error"
    ) {
      notifier.emit("AGENT_STATE_CHANGE", "orchestrator", {
        old_state: state.task_status,
        new_state: state.task_status,
        terminal: true,
        detail: `Task reached terminal state: ${state.task_status}`,
      });
    }

    // Clear the notification buffer from graph state
    // Return an empty notifications array — the reducer will overwrite
    // because we return an empty list (appended to current, but we want
    // to signal "processed"). Since the reducer is append-based, we
    // cannot clear. Instead, we leave notifications as-is; they are
    // already published. The buffer cap in the reducer handles memory.
    return {} as SwarmStateUpdate;
  };
}

// ---------------------------------------------------------------------------
// Graph factory
// ---------------------------------------------------------------------------

export interface SwarmGraphOptions {
  /** LLM provider (default: "anthropic") */
  provider?: LLMProvider;
  /** Model name (default: "claude-sonnet-4-20250514") */
  model?: string;
  /** Prompt context overrides */
  context?: Partial<PromptContext>;
}

/**
 * Create and compile the swarm StateGraph.
 *
 * Returns the compiled graph and the NotifierService instance so the
 * API route can subscribe to events for SSE streaming.
 *
 * @param taskId          - Unique task identifier
 * @param taskDescription - The user's task description
 * @param options         - Provider, model, and context overrides
 */
export function createSwarmGraph(
  taskId: string,
  taskDescription: string,
  options: SwarmGraphOptions = {},
) {
  const {
    provider = "vertexai",
    model = "gemini-3-flash-preview",
    context: contextOverrides = {},
  } = options;

  logger.info("Creating swarm graph", {
    taskId,
    provider,
    model,
  });

  // --- Services ---
  const notifier = new NotifierService(taskId);

  // --- Prompt context ---
  const promptContext: PromptContext = {
    taskDescription,
    ...contextOverrides,
  };

  // --- Create bound node functions ---
  const orchestratorNode = createOrchestratorNode(notifier);
  const coderNode = createCoderNode(notifier, provider, model, promptContext);
  const liveAnalystNode = createAnalystNode(notifier, provider, model, promptContext);
  const reviewerNode = createReviewerNode(notifier, provider, model, promptContext);
  const sandboxRendererNode = createSandboxRendererNode(notifier);
  const notifierNode = createNotifierNode(notifier);

  // --- Build the StateGraph ---
  const graph = new StateGraph(SwarmStateAnnotation)
    // Nodes
    .addNode("orchestrator", orchestratorNode)
    .addNode("coder", coderNode)
    .addNode("live_analyst", liveAnalystNode)
    .addNode("reviewer", reviewerNode)
    .addNode("sandbox_renderer", sandboxRendererNode)
    .addNode("notifier", notifierNode)

    // Entry edge
    .addEdge(START, "orchestrator")

    // Conditional edges
    .addConditionalEdges("orchestrator", routeAfterOrchestrator, {
      coder: "coder",
      notifier: "notifier",
    })
    .addConditionalEdges("coder", routeAfterCoder, {
      live_analyst: "live_analyst",
      notifier: "notifier",
    })
    .addConditionalEdges("live_analyst", routeAfterAnalyst, {
      orchestrator: "orchestrator",
      sandbox_renderer: "sandbox_renderer",
    })

    // Fixed edges
    .addEdge("sandbox_renderer", "reviewer")
    .addEdge("reviewer", "notifier")
    .addEdge("notifier", END)

    // Compile with PostgreSQL checkpointer
    .compile({ checkpointer: getCheckpointer() });

  logger.info("Swarm graph compiled successfully", { taskId });

  return { graph, notifier };
}

/**
 * Build the initial state for a new swarm task invocation.
 */
export function buildInitialState(
  taskId: string,
  taskDescription: string,
): Partial<SwarmState> {
  return {
    task_id: taskId,
    task_description: taskDescription,
    task_status: "pending",
    coder_plan: null,
    coder_output: null,
    analyst_state: "IDLE",
    analyst_report_md: "",
    analyst_interruption_request: null,
    reviewer_report_md: "",
    sandbox_display: "",
  };
}
