/**
 * Reviewer Agent Node — isolated, read-only LLM agent that performs
 * multi-pass code review on the Coder's output.
 *
 * The Reviewer:
 *   1. Reads coder_plan, coder_output, coder_file_changes, and analyst_report_md from state
 *   2. Composes a comprehensive review input for multi-pass analysis
 *   3. Invokes a DeepAgent with reviewer (read-only) tools
 *   4. Parses structured findings from the review report
 *   5. Updates SwarmState: reviewer_report_md, reviewer_improvements, task_status → "complete"
 *   6. Emits REVIEW_FINDING notifications for each finding
 *
 * On failure it sets task_status to "error" and emits an ERROR notification.
 */

import { createDeepAgent } from "deepagents";
import { HumanMessage } from "@langchain/core/messages";
import { getModelForProvider } from "@/lib/agent/providers";
import { reviewerTools } from "./tools/reviewer-tools";
import { deduplicateTools } from "./utils/deduplicate-tools";
import { composeSystemPrompt } from "./prompts/router";
import type { PromptContext } from "./prompts/router";
import { createLogger } from "@/utils/logger";
import type { NotifierService } from "./notifier";
import type { SwarmState, SwarmStateUpdate } from "./state";
import type { LLMProvider } from "@/types/agent";
import type {
  ReviewImprovement,
  ReviewAssessment,
  NotificationEvent,
} from "@/types/swarm";

const logger = createLogger("swarm:reviewer");

// ---------------------------------------------------------------------------
// Review context builder
// ---------------------------------------------------------------------------

/**
 * Build a comprehensive review input that gives the Reviewer LLM all the
 * context it needs for a multi-pass review: the coder's plan, output,
 * file changes, and the analyst's real-time report.
 */
function buildReviewInput(state: SwarmState): string {
  const sections: string[] = [];

  // --- Task description ---
  sections.push(`## Task Description\n${state.task_description}`);

  // --- Coder plan ---
  if (state.coder_plan) {
    sections.push(`## Coder Plan\n${state.coder_plan}`);
  }

  // --- Coder output ---
  if (state.coder_output) {
    const coderOut =
      state.coder_output.length > 12_000
        ? state.coder_output.slice(0, 12_000) + "\n... [truncated]"
        : state.coder_output;
    sections.push(`## Coder Output\n\`\`\`\n${coderOut}\n\`\`\``);
  }

  // --- File changes ---
  if (state.coder_file_changes.length > 0) {
    const changeSummaries = state.coder_file_changes.map(
      (fc) => `- **${fc.action}** \`${fc.filepath}\` — ${fc.diff_summary}`,
    );
    sections.push(`## Files Changed\n${changeSummaries.join("\n")}`);
  }

  // --- Tool calls summary ---
  if (state.coder_tool_calls.length > 0) {
    const toolSummaries = state.coder_tool_calls.map((tc) => {
      const outputStr =
        typeof tc.output === "string" ? tc.output : JSON.stringify(tc.output);
      const outputTruncated =
        outputStr.length > 300 ? outputStr.slice(0, 300) + "..." : outputStr;
      return `- **${tc.name}** → ${outputTruncated}`;
    });
    sections.push(`## Coder Tool Calls\n${toolSummaries.join("\n")}`);
  }

  // --- Analyst report ---
  if (state.analyst_report_md) {
    sections.push(
      `## Live Analyst Report\n${state.analyst_report_md}`,
    );
  }

  return sections.join("\n\n");
}

// ---------------------------------------------------------------------------
// Output parsing helpers
// ---------------------------------------------------------------------------

/** Valid review assessment values. */
const ASSESSMENTS: ReviewAssessment[] = [
  "APPROVED",
  "APPROVED_WITH_SUGGESTIONS",
  "CHANGES_REQUESTED",
];

/**
 * Parse the overall assessment from the review report.
 * Looks for the **Overall Assessment:** line.
 */
function parseAssessment(report: string): ReviewAssessment {
  const match = report.match(
    /\*\*Overall Assessment:\*\*\s*(APPROVED_WITH_SUGGESTIONS|APPROVED|CHANGES_REQUESTED)/i,
  );
  if (match) {
    const raw = match[1].toUpperCase() as ReviewAssessment;
    if (ASSESSMENTS.includes(raw)) return raw;
  }

  // Fallback: if there are Must Fix findings, it's CHANGES_REQUESTED
  if (/### Must Fix/i.test(report)) return "CHANGES_REQUESTED";
  if (/### Should Fix|### Nice to Have/i.test(report))
    return "APPROVED_WITH_SUGGESTIONS";

  return "APPROVED";
}

/**
 * Parse structured findings from the review report.
 *
 * Expected format per finding:
 *   #### Finding #N: [title]
 *   - **File:** `path/to/file`
 *   - **Lines:** 42-58
 *   - **Issue:** [description]
 *   - ...
 *   - **Suggested Fix:** ...
 *
 * We extract these into ReviewImprovement objects.
 */
function parseImprovements(report: string): ReviewImprovement[] {
  const improvements: ReviewImprovement[] = [];

  // Map section headers to categories
  const sectionCategories: Array<{
    header: RegExp;
    category: string;
  }> = [
    { header: /### Must Fix/i, category: "must_fix" },
    { header: /### Should Fix/i, category: "should_fix" },
    { header: /### Nice to Have/i, category: "nice_to_have" },
  ];

  for (const { header, category } of sectionCategories) {
    // Extract the section content (up to the next ## heading)
    const sectionRegex = new RegExp(
      header.source + "[\\s\\S]*?(?=\\n## |\\n### (?!Finding)|$)",
      "i",
    );
    const sectionMatch = report.match(sectionRegex);
    if (!sectionMatch) continue;

    const sectionText = sectionMatch[0];

    // Extract individual findings
    const findingRegex =
      /#### Finding #\d+:\s*(.+?)(?=\n####|\n##|$)/gi;
    let findingMatch: RegExpExecArray | null;

    while ((findingMatch = findingRegex.exec(sectionText)) !== null) {
      const findingText = findingMatch[0];
      const title = findingMatch[1].trim();

      // Parse fields from the finding block
      const fileMatch = findingText.match(
        /\*\*File:\*\*\s*`?([^`\n]+)`?/,
      );
      const linesMatch = findingText.match(
        /\*\*Lines?:\*\*\s*(\S+)/,
      );
      const issueMatch = findingText.match(
        /\*\*Issue:\*\*\s*([\s\S]+?)(?=\n\s*-\s*\*\*|$)/,
      );
      const fixMatch = findingText.match(
        /\*\*Suggested Fix:\*\*\s*([\s\S]*?)(?=\n####|\n##|$)/,
      );

      improvements.push({
        category,
        filepath: fileMatch?.[1]?.trim() ?? "unknown",
        line_range: linesMatch?.[1]?.trim() ?? "unknown",
        description: issueMatch?.[1]?.trim() ?? title,
        improvement: fixMatch?.[1]?.trim() ?? "",
      });
    }
  }

  return improvements;
}

/**
 * Map a finding category to the notification severity.
 */
function categoryToSeverity(
  category: string,
): "must_fix" | "should_fix" | "nice_to_have" {
  if (category === "must_fix") return "must_fix";
  if (category === "should_fix") return "should_fix";
  return "nice_to_have";
}

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------

/**
 * Create a Reviewer Agent node function bound to the given dependencies.
 *
 * @param notifier  - NotifierService for emitting events
 * @param provider  - LLM provider identifier
 * @param model     - LLM model name
 * @param context   - Prompt context (task description, project info)
 * @returns An async node function compatible with LangGraph StateGraph
 */
export function createReviewerNode(
  notifier: NotifierService,
  provider: LLMProvider,
  model: string,
  context: PromptContext,
) {
  return async function reviewerNode(
    state: SwarmState,
  ): Promise<SwarmStateUpdate> {
    logger.info("Reviewer node invoked", {
      task_id: state.task_id,
      file_changes: state.coder_file_changes.length,
      has_analyst_report: !!state.analyst_report_md,
    });

    const notifications: NotificationEvent[] = [];

    // ---- Emit state change: → reviewing ----
    notifications.push(
      notifier.emit("AGENT_STATE_CHANGE", "reviewer", {
        old_state: state.task_status,
        new_state: "reviewing",
      }),
    );

    try {
      // 1. Build comprehensive review input
      const reviewInput = buildReviewInput(state);

      // 2. Compose system prompt
      const systemPrompt = composeSystemPrompt("reviewer", context);

      // 3. Create DeepAgent with reviewer (read-only) tools
      const llm = getModelForProvider(provider, model);
      const agent = createDeepAgent({
        model: llm,
        tools: deduplicateTools(reviewerTools),
        systemPrompt,
        name: "reviewer-agent",
      });

      // 4. Build input messages
      const inputMessages = [
        new HumanMessage(
          `Perform a comprehensive multi-pass code review of the following implementation.\n\n${reviewInput}`,
        ),
      ];

      // 5. Invoke the agent — stream events to capture the full response
      //    and any tool calls (read_file, search_web, write_report)
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

        // Capture write_report tool output (pseudo-tool returns report content)
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
      const reviewReport = reportFromTool || fullResponse;

      // 7. Parse assessment and improvements
      const assessment = parseAssessment(reviewReport);
      const improvements = parseImprovements(reviewReport);

      // 8. Emit REVIEW_FINDING notifications for each finding
      for (const imp of improvements) {
        notifications.push(
          notifier.emit("REVIEW_FINDING", "reviewer", {
            category: categoryToSeverity(imp.category),
            filepath: imp.filepath,
            line_range: imp.line_range,
            description: imp.description,
            improvement: imp.improvement,
          }),
        );
      }

      // 9. Emit state change: → complete (include report for frontend consumption)
      notifications.push(
        notifier.emit("AGENT_STATE_CHANGE", "reviewer", {
          old_state: "reviewing",
          new_state: "complete",
          assessment,
          report_md: reviewReport,
        }),
      );

      logger.info("Reviewer node completed", {
        assessment,
        improvements_count: improvements.length,
        report_length: reviewReport.length,
      });

      // 10. Return state update
      return {
        task_status: "complete",
        reviewer_report_md: reviewReport,
        reviewer_improvements: improvements,
        notifications,
      } as SwarmStateUpdate;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      const stack = err instanceof Error ? err.stack : undefined;

      logger.error("Reviewer node failed", { error: message, stack });

      notifications.push(
        notifier.emit("ERROR", "reviewer", {
          error_type: "agent_failure",
          message,
          stack_trace: stack ?? null,
        }),
      );

      return {
        task_status: "error",
        reviewer_report_md: `Error: ${message}`,
        notifications,
      } as SwarmStateUpdate;
    }
  };
}
