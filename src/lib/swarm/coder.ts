/**
 * Coder Agent Node — LLM-based graph node that plans and implements code.
 *
 * The Coder Agent is the primary implementation engine of the swarm:
 *   1. Composes a system prompt via the prompt router
 *   2. Creates a DeepAgent with coder tools
 *   3. Invokes the agent with the task description (+ any interruption messages)
 *   4. Parses structured output to extract plan, file changes, and tool calls
 *   5. Updates SwarmState and emits notifications
 *
 * On completion it sets task_status to "reviewing" so the Reviewer takes over.
 * On failure it sets task_status to "error" and emits an ERROR notification.
 */

import { createDeepAgent } from "deepagents";
import { HumanMessage, AIMessage } from "@langchain/core/messages";
import { getModelForProvider } from "@/lib/agent/providers";
import { coderTools } from "./tools/coder-tools";
import { deduplicateTools } from "./utils/deduplicate-tools";
import { composeSystemPrompt } from "./prompts/router";
import type { PromptContext } from "./prompts/router";
import { createLogger } from "@/utils/logger";
import type { NotifierService } from "./notifier";
import type { SwarmState, SwarmStateUpdate } from "./state";
import type { LLMProvider } from "@/types/agent";
import type {
  TokenStreamEntry,
  ToolCallEntry,
  FileChangeEntry,
  NotificationEvent,
} from "@/types/swarm";

const logger = createLogger("swarm:coder");

// ---------------------------------------------------------------------------
// Structured output parsing helpers
// ---------------------------------------------------------------------------

/** Extract plan text from the agent's output (looks for PLAN: ... blocks). */
function extractPlan(text: string): string | null {
  const planMatch = text.match(/PLAN:\s*\n([\s\S]*?)(?=\n(?:FILE_CHANGE:|STATUS:|$))/);
  if (planMatch) return planMatch[1].trim();

  // Fallback: look for a numbered list that appears plan-like
  const numberedList = text.match(
    /(?:^|\n)((?:\d+\.\s+.+\n?)+)/,
  );
  return numberedList ? numberedList[1].trim() : null;
}

/**
 * Extract FILE_CHANGE reports from the agent's output.
 *
 * Expected format:
 *   FILE_CHANGE: path/to/file action — summary
 */
function extractFileChanges(text: string): FileChangeEntry[] {
  const changes: FileChangeEntry[] = [];
  const regex = /FILE_CHANGE:\s*(\S+)\s+(create|modify|delete)\s*[—-]\s*(.+)/gi;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(text)) !== null) {
    changes.push({
      filepath: match[1],
      action: match[2].toLowerCase() as FileChangeEntry["action"],
      diff_summary: match[3].trim(),
    });
  }
  return changes;
}

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------

/**
 * Create a Coder Agent node function bound to the given dependencies.
 *
 * @param notifier  - NotifierService for emitting events
 * @param provider  - LLM provider identifier
 * @param model     - LLM model name
 * @param context   - Prompt context (task description, project info)
 * @returns An async node function compatible with LangGraph StateGraph
 */
export function createCoderNode(
  notifier: NotifierService,
  provider: LLMProvider,
  model: string,
  context: PromptContext,
) {
  return async function coderNode(
    state: SwarmState,
  ): Promise<SwarmStateUpdate> {
    logger.info("Coder node invoked", {
      task_status: state.task_status,
      task_id: state.task_id,
    });

    const notifications: NotificationEvent[] = [];

    // ---- Emit state change: → coding ----
    notifications.push(
      notifier.emit("AGENT_STATE_CHANGE", "coder", {
        old_state: state.task_status,
        new_state: "coding",
      }),
    );

    try {
      // 1. Compose system prompt (add <think> tag instruction for Gemini)
      const isGemini = provider === "google" || provider === "vertexai";
      const thinkInstruction = isGemini
        ? "\n\nWhen reasoning through complex questions or planning your approach, wrap your internal thinking process in <think> and </think> tags. This thinking will be shown to the user in a separate \"Thinking\" section. Only use these tags for genuine reasoning — your final answer should be outside these tags."
        : "";
      const systemPrompt = composeSystemPrompt("coder", context) + thinkInstruction;

      // 2. Create DeepAgent
      const llm = getModelForProvider(provider, model);
      const agent = createDeepAgent({
        model: llm,
        tools: deduplicateTools(coderTools),
        systemPrompt,
        name: "coder-agent",
      });

      // 3. Build input messages
      //    Start with the task description; append any interruption messages
      //    that the orchestrator may have injected into state.messages.
      const inputMessages = [
        new HumanMessage(
          `Task:\n${state.task_description}`,
        ),
        ...state.messages,
      ];

      // 4. Emit plan update: starting
      notifications.push(
        notifier.emit("PLAN_UPDATE", "coder", {
          plan_step: "agent_invocation",
          status: "started",
          detail: "Coder Agent is starting work on the task.",
        }),
      );

      // 5. Invoke the agent and stream events
      const tokenStream: TokenStreamEntry[] = [];
      const toolCalls: ToolCallEntry[] = [];
      let fullResponse = "";

      // Track in-flight tool calls by run_id so we can match start→end
      const pendingTools = new Map<
        string,
        { name: string; input: Record<string, unknown>; timestamp: string }
      >();

      const eventStream = agent.streamEvents(
        { messages: inputMessages },
        { version: "v2" },
      );

      for await (const event of eventStream) {
        const { event: eventType, data, run_id } = event as {
          event: string;
          data: Record<string, unknown>;
          run_id?: string;
        };

        // -- Token streaming --
        if (eventType === "on_chat_model_stream") {
          const chunk = data?.chunk as Record<string, unknown> | undefined;
          const content = chunk?.content;
          if (content) {
            const text =
              typeof content === "string"
                ? content
                : Array.isArray(content)
                  ? (content as Record<string, unknown>[])
                      .filter((c) => c.type === "text")
                      .map((c) => String(c.text || ""))
                      .join("")
                  : "";

            if (text) {
              fullResponse += text;
              const entry: TokenStreamEntry = {
                token: text,
                timestamp: new Date().toISOString(),
              };
              tokenStream.push(entry);

              notifier.emit("TOKEN_STREAM", "coder", {
                token: text,
                cumulative_length: fullResponse.length,
                timestamp: entry.timestamp,
              });
            }
          }
        }

        // -- Tool call start --
        if (eventType === "on_tool_start") {
          const toolName = String(data?.name || "unknown");
          const toolInput = (data?.input ?? {}) as Record<string, unknown>;
          const ts = new Date().toISOString();

          if (run_id) {
            pendingTools.set(run_id, {
              name: toolName,
              input: toolInput,
              timestamp: ts,
            });
          }

          notifications.push(
            notifier.emit("TOOL_CALL", "coder", {
              tool_name: toolName,
              tool_input: toolInput,
              timestamp: ts,
            }),
          );
        }

        // -- Tool call end --
        if (eventType === "on_tool_end") {
          const output = data?.output;
          const outputStr =
            typeof output === "string" ? output : JSON.stringify(output);
          const ts = new Date().toISOString();

          // Match with pending start
          const pending = run_id ? pendingTools.get(run_id) : undefined;
          const toolName = pending?.name ?? String(data?.name || "unknown");
          const toolInput = pending?.input ?? {};
          if (run_id) pendingTools.delete(run_id);

          toolCalls.push({
            name: toolName,
            input: toolInput,
            output: outputStr,
            timestamp: ts,
          });

          notifications.push(
            notifier.emit("TOOL_RESULT", "coder", {
              tool_name: toolName,
              tool_output:
                outputStr.length > 500
                  ? outputStr.slice(0, 500) + "…"
                  : outputStr,
              timestamp: ts,
              success: true,
            }),
          );
        }
      }

      // 6. Parse structured output
      const plan = extractPlan(fullResponse);
      const fileChanges = extractFileChanges(fullResponse);

      // Emit plan content for frontend consumption
      if (plan) {
        notifications.push(
          notifier.emit("PLAN_UPDATE", "coder", {
            plan_step: "plan_extracted",
            status: "complete",
            detail: plan,
          }),
        );
      }

      // Emit file change notifications
      for (const fc of fileChanges) {
        notifications.push(
          notifier.emit("FILE_CHANGE", "coder", {
            filepath: fc.filepath,
            action: fc.action,
            diff_summary: fc.diff_summary,
          }),
        );
      }

      // 7. Emit plan update: complete
      notifications.push(
        notifier.emit("PLAN_UPDATE", "coder", {
          plan_step: "implementation",
          status: "complete",
          detail: `Coder Agent finished. ${fileChanges.length} file(s) changed.`,
        }),
      );

      logger.info("Coder node completed", {
        response_length: fullResponse.length,
        tool_calls: toolCalls.length,
        file_changes: fileChanges.length,
      });

      // 8. Return state update
      return {
        task_status: "reviewing",
        coder_plan: plan,
        coder_output: fullResponse,
        coder_token_stream: tokenStream,
        coder_tool_calls: toolCalls,
        coder_file_changes: fileChanges,
        messages: [new AIMessage(fullResponse)],
        notifications,
      } as SwarmStateUpdate;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      const stack = err instanceof Error ? err.stack : undefined;

      logger.error("Coder node failed", { error: message, stack });

      notifications.push(
        notifier.emit("ERROR", "coder", {
          error_type: "agent_failure",
          message,
          stack_trace: stack ?? null,
        }),
      );

      return {
        task_status: "error",
        coder_output: `Error: ${message}`,
        notifications,
      } as SwarmStateUpdate;
    }
  };
}
