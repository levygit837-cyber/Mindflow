/**
 * Live Analyst Agent Node — stealth monitoring LLM agent that analyzes
 * the Coder's output for quality, security, and correctness issues.
 *
 * The Live Analyst operates in read-only mode:
 *   1. Reads the Coder's buffered token stream, tool calls, and file changes
 *   2. If buffers are empty → returns IDLE immediately (no LLM invocation)
 *   3. Summarises the buffered data into an analysis prompt
 *   4. Invokes a DeepAgent with analyst tools to produce a structured report
 *   5. Parses the report for severity levels and interruption requests
 *   6. Updates SwarmState (analyst_state, analyst_report_md, analyst_interruption_request)
 *   7. Emits ANALYST_FINDING and ANALYST_STATE_CHANGE notifications
 *
 * On failure the node sets analyst_state to "IDLE", emits an ERROR
 * notification, and does NOT block the workflow.
 */

import { createDeepAgent } from "deepagents";
import { HumanMessage } from "@langchain/core/messages";
import { getModelForProvider } from "@backend/agent/providers";
import { analystTools } from "./tools/analyst-tools";
import { deduplicateTools } from "./utils/deduplicate-tools";
import { composeSystemPrompt } from "./prompts/router";
import type { PromptContext } from "./prompts/router";
import { createLogger } from "@backend/utils/logger";
import type { NotifierService } from "./notifier";
import type { SwarmState, SwarmStateUpdate } from "./state";
import type { LLMProvider } from "@shared/types/agent";
import type {
  AnalystAlertLevel,
  InterruptionRequest,
  NotificationEvent,
} from "@shared/types/swarm";

const logger = createLogger("swarm:live-analyst");

// ---------------------------------------------------------------------------
// Coder buffer → analyst input summarisation
// ---------------------------------------------------------------------------

/**
 * Build a text summary of the Coder's buffered output that the analyst LLM
 * can reason about. Includes token stream (truncated), tool calls, and file
 * changes.
 */
function summariseCoderBuffers(state: SwarmState): string {
  const sections: string[] = [];

  // --- Coder plan ---
  if (state.coder_plan) {
    sections.push(`## Coder Plan\n${state.coder_plan}`);
  }

  // --- Token stream (cumulative text, truncated to 8K chars) ---
  if (state.coder_token_stream.length > 0) {
    const fullText = state.coder_token_stream.map((t) => t.token).join("");
    const truncated =
      fullText.length > 8000
        ? fullText.slice(0, 8000) + "\n... [truncated]"
        : fullText;
    sections.push(`## Coder Output (Token Stream)\n\`\`\`\n${truncated}\n\`\`\``);
  }

  // --- Tool calls ---
  if (state.coder_tool_calls.length > 0) {
    const toolSummaries = state.coder_tool_calls.map((tc) => {
      const inputStr = JSON.stringify(tc.input);
      const outputStr =
        typeof tc.output === "string" ? tc.output : JSON.stringify(tc.output);
      const outputTruncated =
        outputStr.length > 500 ? outputStr.slice(0, 500) + "…" : outputStr;
      return `- **${tc.name}** (${tc.timestamp})\n  Input: \`${inputStr}\`\n  Output: \`${outputTruncated}\``;
    });
    sections.push(`## Tool Calls\n${toolSummaries.join("\n\n")}`);
  }

  // --- File changes ---
  if (state.coder_file_changes.length > 0) {
    const changeSummaries = state.coder_file_changes.map(
      (fc) => `- **${fc.action}** \`${fc.filepath}\` — ${fc.diff_summary}`,
    );
    sections.push(`## File Changes\n${changeSummaries.join("\n")}`);
  }

  // --- Coder final output ---
  if (state.coder_output) {
    const coderOut =
      state.coder_output.length > 4000
        ? state.coder_output.slice(0, 4000) + "\n... [truncated]"
        : state.coder_output;
    sections.push(`## Coder Final Output\n\`\`\`\n${coderOut}\n\`\`\``);
  }

  return sections.join("\n\n");
}

// ---------------------------------------------------------------------------
// Output parsing helpers
// ---------------------------------------------------------------------------

/** Valid alert levels the analyst can set via its report. */
const ALERT_LEVELS: AnalystAlertLevel[] = [
  "IDLE",
  "MONITORING",
  "ALERT_LOW",
  "ALERT_MODERATE",
  "ALERT_CRITICAL",
];

/**
 * Parse the analyst's report to determine the highest alert level.
 *
 * The analyst prompt instructs the LLM to include a `**Status:** LEVEL` line.
 * We also look for the presence of CRITICAL / MODERATE table rows as fallback.
 */
function parseAlertLevel(report: string): AnalystAlertLevel {
  // 1. Look for explicit Status line
  const statusMatch = report.match(
    /\*\*Status:\*\*\s*(MONITORING|ALERT_LOW|ALERT_MODERATE|ALERT_CRITICAL|IDLE)/i,
  );
  if (statusMatch) {
    const raw = statusMatch[1].toUpperCase() as AnalystAlertLevel;
    if (ALERT_LEVELS.includes(raw)) return raw;
  }

  // 2. Fallback: scan for severity indicators in the report body
  if (/### CRITICAL[\s\S]*?\|\s*\d+\s*\|/.test(report)) {
    return "ALERT_CRITICAL";
  }
  if (/### MODERATE[\s\S]*?\|\s*\d+\s*\|/.test(report)) {
    return "ALERT_MODERATE";
  }
  if (/### LOW[\s\S]*?\|\s*\d+\s*\|/.test(report)) {
    return "ALERT_LOW";
  }

  return "MONITORING";
}

/**
 * If the analyst flagged a CRITICAL issue, try to extract a structured
 * InterruptionRequest from the report.
 */
function parseInterruptionRequest(
  report: string,
): InterruptionRequest | null {
  // Look for the first row in the CRITICAL table
  const criticalSection = report.match(
    /### CRITICAL[\s\S]*?\|[^|]*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|/,
  );
  if (!criticalSection) return null;

  const file = criticalSection[1].trim();
  const line = criticalSection[2].trim();
  const issue = criticalSection[3].trim();
  const impact = criticalSection[4].trim();
  const suggestedFix = criticalSection[5].trim();

  return {
    urgency: "CRITICAL",
    issue: `${issue} (Impact: ${impact})`,
    file: file || "unknown",
    suggested_action: suggestedFix || "Review and fix the critical issue",
    evidence: `Line ${line} in ${file}`,
  };
}

/**
 * Extract individual findings from the analyst report for notification
 * purposes. Returns an array of {severity, description, file_ref} objects.
 */
function parseFindings(
  report: string,
): Array<{
  severity: "LEVE" | "MODERADO" | "CRITICO";
  description: string;
  file_ref: string;
}> {
  const findings: Array<{
    severity: "LEVE" | "MODERADO" | "CRITICO";
    description: string;
    file_ref: string;
  }> = [];

  const sections: Array<{
    header: string;
    severity: "LEVE" | "MODERADO" | "CRITICO";
  }> = [
    { header: "### CRITICAL", severity: "CRITICO" },
    { header: "### MODERATE", severity: "MODERADO" },
    { header: "### LOW", severity: "LEVE" },
  ];

  for (const { header, severity } of sections) {
    // Match table rows (| # | File | Line | Issue | Impact | Suggested Fix |)
    const sectionRegex = new RegExp(
      header.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") +
        "[\\s\\S]*?(?=### |## |$)",
    );
    const sectionMatch = report.match(sectionRegex);
    if (!sectionMatch) continue;

    const rowRegex =
      /\|\s*\d+\s*\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|/g;
    let row: RegExpExecArray | null;
    while ((row = rowRegex.exec(sectionMatch[0])) !== null) {
      const file = row[1].trim();
      const issue = row[3].trim();
      if (issue) {
        findings.push({
          severity,
          description: issue,
          file_ref: file || "unknown",
        });
      }
    }
  }

  return findings;
}

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------

/**
 * Create a Live Analyst node function bound to the given dependencies.
 *
 * @param notifier  - NotifierService for emitting events
 * @param provider  - LLM provider identifier
 * @param model     - LLM model name
 * @param context   - Prompt context (task description, project info)
 * @returns An async node function compatible with LangGraph StateGraph
 */
export function createAnalystNode(
  notifier: NotifierService,
  provider: LLMProvider,
  model: string,
  context: PromptContext,
) {
  return async function liveAnalystNode(
    state: SwarmState,
  ): Promise<SwarmStateUpdate> {
    logger.info("Live Analyst node invoked", {
      task_id: state.task_id,
      coder_tokens: state.coder_token_stream.length,
      coder_tool_calls: state.coder_tool_calls.length,
      coder_file_changes: state.coder_file_changes.length,
    });

    const notifications: NotificationEvent[] = [];

    // ---- Early return: nothing to analyse ----
    if (
      state.coder_token_stream.length === 0 &&
      state.coder_tool_calls.length === 0 &&
      state.coder_file_changes.length === 0
    ) {
      logger.info("Live Analyst: no coder data to analyse, returning IDLE");

      notifications.push(
        notifier.emit("ANALYST_STATE_CHANGE", "live_analyst", {
          old_state: state.analyst_state,
          new_state: "IDLE",
          reason: "No coder output to analyse",
        }),
      );

      return {
        analyst_state: "IDLE",
        notifications,
      } as SwarmStateUpdate;
    }

    // ---- Emit state change: → MONITORING ----
    const previousState = state.analyst_state;
    notifications.push(
      notifier.emit("ANALYST_STATE_CHANGE", "live_analyst", {
        old_state: previousState,
        new_state: "MONITORING",
        reason: "Starting analysis of Coder output",
      }),
    );

    try {
      // 1. Summarise the coder's buffered output
      const coderSummary = summariseCoderBuffers(state);

      // 2. Compose system prompt
      const systemPrompt = composeSystemPrompt("live_analyst", context);

      // 3. Create DeepAgent with analyst tools
      const llm = getModelForProvider(provider, model);
      const agent = createDeepAgent({
        model: llm,
        tools: deduplicateTools(analystTools),
        systemPrompt,
        name: "live-analyst-agent",
      });

      // 4. Build input message
      const inputMessages = [
        new HumanMessage(
          `Analyse the following Coder output and produce a structured analysis report.\n\n${coderSummary}`,
        ),
      ];

      // 5. Invoke the agent — stream events to capture the full response
      //    and any tool calls the analyst makes (e.g. search_web, write_report)
      let fullResponse = "";
      let reportFromTool: string | null = null;

      const eventStream = agent.streamEvents(
        { messages: inputMessages },
        { version: "v2" },
      );

      for await (const event of eventStream) {
        const { event: eventType, data } = event as {
          event: string;
          data: Record<string, unknown>;
        };

        // Capture token stream
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
            }
          }
        }

        // Capture write_report tool output (the pseudo-tool returns report content)
        if (eventType === "on_tool_end") {
          const toolName = String(data?.name || "");
          if (toolName === "write_report") {
            const output = data?.output;
            reportFromTool =
              typeof output === "string" ? output : JSON.stringify(output);
          }
        }
      }

      // 6. Determine the final report content
      //    Prefer the write_report tool output; fall back to the full LLM response
      const analysisReport = reportFromTool || fullResponse;

      // 7. Parse alert level and findings
      const alertLevel = parseAlertLevel(analysisReport);
      const findings = parseFindings(analysisReport);

      // 8. Parse interruption request if CRITICAL
      let interruptionRequest: InterruptionRequest | null = null;
      if (alertLevel === "ALERT_CRITICAL") {
        interruptionRequest = parseInterruptionRequest(analysisReport);
      }

      // 9. Emit finding notifications
      for (const finding of findings) {
        notifications.push(
          notifier.emit("ANALYST_FINDING", "live_analyst", {
            severity: finding.severity,
            description: finding.description,
            suggestion: "",
            file_ref: finding.file_ref,
          }),
        );
      }

      // 10. Emit final state change with report for frontend consumption
      notifications.push(
        notifier.emit("ANALYST_STATE_CHANGE", "live_analyst", {
          old_state: "MONITORING",
          new_state: alertLevel,
          reason: `Analysis complete. ${findings.length} finding(s) detected.`,
          report_md: analysisReport,
        }),
      );

      logger.info("Live Analyst node completed", {
        alert_level: alertLevel,
        findings_count: findings.length,
        has_interruption: interruptionRequest !== null,
        report_length: analysisReport.length,
      });

      // 11. Return state update
      return {
        analyst_state: alertLevel,
        analyst_report_md: analysisReport,
        analyst_interruption_request: interruptionRequest,
        notifications,
      } as SwarmStateUpdate;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      const stack = err instanceof Error ? err.stack : undefined;

      logger.error("Live Analyst node failed", { error: message, stack });

      notifications.push(
        notifier.emit("ERROR", "live_analyst", {
          error_type: "agent_failure",
          message,
          stack_trace: stack ?? null,
        }),
      );

      // Non-blocking: return IDLE so the workflow continues
      return {
        analyst_state: "IDLE",
        notifications,
      } as SwarmStateUpdate;
    }
  };
}
