/**
 * Sandbox Renderer Node — pure-function graph node that generates ASCII art
 * visualizations of the coder's file changes.
 *
 * This node is NOT an LLM agent. It reads the file changes from state,
 * selects the appropriate ASCII template based on project type, and
 * renders a parameterized visualization for the sandbox panel.
 */

import { createLogger } from "@backend/utils/logger";
import type { NotifierService } from "./notifier";
import type { SwarmState, SwarmStateUpdate } from "./state";
import { selectTemplate } from "./templates/index";

const logger = createLogger("swarm:sandbox-renderer");

/**
 * Create a sandbox renderer node function bound to the given NotifierService.
 *
 * The returned function can be used directly as a LangGraph node.
 */
export function createSandboxRendererNode(notifier: NotifierService) {
  return function sandboxRendererNode(state: SwarmState): SwarmStateUpdate {
    const fileChanges = state.coder_file_changes;

    logger.info("Sandbox renderer invoked", {
      file_change_count: fileChanges.length,
      task_status: state.task_status,
    });

    // Nothing to render if no file changes
    if (fileChanges.length === 0) {
      logger.debug("No file changes — skipping render");
      return {} as SwarmStateUpdate;
    }

    // Select template based on file patterns
    const template = selectTemplate(fileChanges);

    // Derive project name from task description (first 30 chars)
    const projectName =
      state.task_description.length > 30
        ? state.task_description.slice(0, 27) + "..."
        : state.task_description;

    // Calculate progress based on task status
    const progress = computeProgress(state.task_status);
    const statusMessage = computeStatusMessage(state.task_status);

    // Render the ASCII visualization
    const display = template({
      projectName,
      timestamp: new Date().toISOString().replace("T", " ").slice(0, 19),
      fileChanges,
      progress,
      statusMessage,
    });

    logger.info("Sandbox rendered", {
      display_length: display.length,
      template_selected: template.name || "anonymous",
    });

    // Emit notification
    notifier.emit("SANDBOX_UPDATE", "sandbox_renderer", {
      display_type: "ascii",
      content: display,
      timestamp: new Date().toISOString(),
    });

    return {
      sandbox_display: display,
      notifications: [
        notifier.emit("AGENT_STATE_CHANGE", "sandbox_renderer", {
          old_state: "rendering",
          new_state: "idle",
          file_count: fileChanges.length,
        }),
      ],
    } as SwarmStateUpdate;
  };
}

/**
 * Map task status to a rough progress percentage.
 */
function computeProgress(
  status: SwarmState["task_status"]
): number {
  switch (status) {
    case "pending":
      return 0;
    case "planning":
      return 15;
    case "coding":
      return 50;
    case "reviewing":
      return 80;
    case "complete":
      return 100;
    case "error":
      return 0;
    default:
      return 0;
  }
}

/**
 * Map task status to a human-readable status message.
 */
function computeStatusMessage(
  status: SwarmState["task_status"]
): string {
  switch (status) {
    case "pending":
      return "Waiting...";
    case "planning":
      return "Planning implementation...";
    case "coding":
      return "Implementing...";
    case "reviewing":
      return "Code review in progress...";
    case "complete":
      return "Complete!";
    case "error":
      return "Error occurred";
    default:
      return "Unknown";
  }
}
