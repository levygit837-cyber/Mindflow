import "server-only";
/**
 * Orchestrator Node — pure-function graph node that routes tasks through the swarm.
 *
 * The orchestrator is NOT an LLM agent. It is a deterministic routing function
 * that inspects the current state and decides the next action:
 *
 *   - pending → set to "planning", emit AGENT_STATE_CHANGE
 *   - analyst_interruption_request present → inject interruption into messages,
 *     clear the request, set status to "coding"
 *   - otherwise → pass through
 */

import { HumanMessage } from "@langchain/core/messages";
import { createLogger } from "@backend/utils/logger";
import type { NotifierService } from "./notifier";
import type { SwarmState, SwarmStateUpdate } from "./state";

const logger = createLogger("swarm:orchestrator");

/**
 * Create an orchestrator node function bound to the given NotifierService.
 *
 * The returned function can be used directly as a LangGraph node.
 */
export function createOrchestratorNode(notifier: NotifierService) {
  return function orchestratorNode(state: SwarmState): SwarmStateUpdate {
    logger.info("Orchestrator invoked", {
      task_status: state.task_status,
      has_interruption: state.analyst_interruption_request !== null,
    });

    // --- Handle pending tasks: transition to planning ---
    if (state.task_status === "pending") {
      logger.info("Task pending — transitioning to planning");

      notifier.emit("AGENT_STATE_CHANGE", "orchestrator", {
        old_state: "pending",
        new_state: "planning",
      });

      return {
        task_status: "planning",
        notifications: [
          notifier.emit("PLAN_UPDATE", "orchestrator", {
            plan_step: "initialization",
            status: "started",
            detail: "Task received. Routing to Coder Agent for planning.",
          }),
        ],
      } as SwarmStateUpdate;
    }

    // --- Handle analyst interruption requests ---
    if (state.analyst_interruption_request !== null) {
      const interruption = state.analyst_interruption_request;
      logger.warn("Analyst interruption received", {
        urgency: interruption.urgency,
        issue: interruption.issue,
        file: interruption.file,
      });

      const interruptionMessage = new HumanMessage(
        `⚠️ CRITICAL INTERRUPTION FROM LIVE ANALYST\n\n` +
          `**Urgency:** ${interruption.urgency}\n` +
          `**Issue:** ${interruption.issue}\n` +
          `**File:** ${interruption.file}\n` +
          `**Suggested Action:** ${interruption.suggested_action}\n` +
          `**Evidence:**\n\`\`\`\n${interruption.evidence}\n\`\`\`\n\n` +
          `Please address this critical issue before continuing.`
      );

      notifier.emit("AGENT_STATE_CHANGE", "orchestrator", {
        old_state: state.task_status,
        new_state: "coding",
        reason: "analyst_interruption",
      });

      return {
        task_status: "coding",
        analyst_interruption_request: null,
        messages: [interruptionMessage],
        notifications: [
          notifier.emit("ANALYST_STATE_CHANGE", "orchestrator", {
            old_state: "ALERT_CRITICAL",
            new_state: "MONITORING",
            reason: "Interruption delivered to coder. Resuming monitoring.",
          }),
        ],
      } as SwarmStateUpdate;
    }

    // --- Default: pass through with no changes ---
    logger.debug("Orchestrator pass-through", {
      task_status: state.task_status,
    });

    return {} as SwarmStateUpdate;
  };
}
