/**
 * System Prompt Router — dynamically composes agent-specific system prompts.
 *
 * Selects the appropriate template function based on agent role and injects
 * task context (description, project type, conventions) into the prompt.
 *
 * Design decision D5 from spec: prompts are build-time TypeScript template
 * literals, not runtime-loaded files. Claude Code prompt files serve as
 * design reference only.
 */

import type { SwarmAgentId } from "@/types/swarm";
import { buildCoderPrompt } from "./coder-prompt";
import { buildAnalystPrompt } from "./analyst-prompt";
import { buildReviewerPrompt } from "./reviewer-prompt";
import { buildOrchestratorPrompt } from "./orchestrator-prompt";

// ============================================================================
// Public types
// ============================================================================

/**
 * Project type detected from file paths or specified explicitly.
 */
export type ProjectType =
  | "rest-api"
  | "graphql"
  | "microservices"
  | "cli"
  | "frontend"
  | "general";

/**
 * Context passed into every prompt template to customize the system prompt
 * for the current task and project.
 */
export interface PromptContext {
  taskDescription: string;
  projectType?: ProjectType;
  existingFiles?: string[];
  conventions?: string[];
  workingPath?: string;
}

// ============================================================================
// Project type detection
// ============================================================================

/** File-path patterns that indicate a particular project type. */
const PROJECT_TYPE_PATTERNS: Record<ProjectType, RegExp[]> = {
  frontend: [
    /\.(tsx|jsx)$/,
    /\bcomponents\b/,
    /\bpages\b/,
    /\bapp\/.*page\./,
    /\bnext\.config\./,
    /\bvite\.config\./,
    /\bsrc\/app\b/,
  ],
  graphql: [
    /\.graphql$/,
    /\bschema\.graphql/,
    /\bresolvers?\b/,
    /\btypeDefs\b/,
    /graphql/i,
  ],
  microservices: [
    /docker-compose/,
    /Dockerfile/,
    /\bservices\//,
    /\bgateway\b/,
    /\bproto\b/,
    /\.proto$/,
  ],
  cli: [
    /\bcli\b/,
    /\bbin\//,
    /commander|yargs|inquirer/,
    /\.sh$/,
  ],
  "rest-api": [
    /\broutes?\b/,
    /\bcontrollers?\b/,
    /\bmiddleware\b/,
    /\bendpoints?\b/,
    /\bapi\//,
    /express|fastify|koa|hono/,
  ],
  general: [], // fallback — never matched directly
};

/**
 * Score each project type by how many file paths match its patterns.
 * Returns the highest-scoring type, or "general" on a tie / no match.
 */
export function detectProjectType(files: string[]): ProjectType {
  if (files.length === 0) return "general";

  const scores: Record<ProjectType, number> = {
    frontend: 0,
    graphql: 0,
    microservices: 0,
    cli: 0,
    "rest-api": 0,
    general: 0,
  };

  for (const file of files) {
    for (const [type, patterns] of Object.entries(PROJECT_TYPE_PATTERNS) as [
      ProjectType,
      RegExp[],
    ][]) {
      for (const pattern of patterns) {
        if (pattern.test(file)) {
          scores[type]++;
          break; // one match per pattern group per file
        }
      }
    }
  }

  let best: ProjectType = "general";
  let bestScore = 0;
  for (const [type, score] of Object.entries(scores) as [
    ProjectType,
    number,
  ][]) {
    if (type !== "general" && score > bestScore) {
      bestScore = score;
      best = type;
    }
  }

  return best;
}

// ============================================================================
// Prompt composition
// ============================================================================

/** Registry mapping agent IDs to their template builder functions. */
const PROMPT_BUILDERS: Record<
  SwarmAgentId,
  (context: PromptContext) => string
> = {
  coder: buildCoderPrompt,
  live_analyst: buildAnalystPrompt,
  reviewer: buildReviewerPrompt,
  orchestrator: buildOrchestratorPrompt,
  sandbox_renderer: buildOrchestratorPrompt, // sandbox_renderer is a pure-function node; reuse orchestrator stub
};

/**
 * Compose a complete system prompt for the given agent role.
 *
 * If `context.projectType` is not set but `context.existingFiles` is provided,
 * the project type is auto-detected from the file paths.
 *
 * @param agentId  - The swarm agent to generate the prompt for
 * @param context  - Task-specific context to inject into the prompt
 * @returns A fully-composed system prompt string
 */
export function composeSystemPrompt(
  agentId: SwarmAgentId,
  context: PromptContext,
): string {
  // Auto-detect project type when not explicitly set
  const resolvedContext: PromptContext = {
    ...context,
    projectType:
      context.projectType ??
      detectProjectType(context.existingFiles ?? []),
  };

  const builder = PROMPT_BUILDERS[agentId];
  return builder(resolvedContext);
}
