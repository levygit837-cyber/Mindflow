/**
 * ============================================================================
 * LANGCHAIN INTEGRATION — using structured output schemas with createAgent
 * ============================================================================
 *
 * This file demonstrates how to integrate the structured output schemas
 * with LangChain's createAgent and structured output features.
 *
 * Three strategies are shown:
 *   1. Single-schema agent   — always returns one output type
 *   2. Union-type agent      — model picks the best output type
 *   3. Router-based agent    — classify first, then use specific schema
 */

import { createAgent, toolStrategy, providerStrategy } from "langchain";

import {
  AgentOutput,
  OutputSchemaMap,
  getOutputSchema,
  type OutputCategory,
} from "../schemas/agent-output";
import {
  CodeOutput,
  ExplanationOutput,
  TaskOutput,
  ConversationOutput,
  DebugOutput,
  PeopleOutput,
  ProjectOutput,
} from "../schemas/output-types";

// ============================================================================
// STRATEGY 1: Single-schema agents (specialized)
// ============================================================================
// Use when the agent has a specific role and always returns the same type.

export function createCodingAgent() {
  return createAgent({
    model: "claude-sonnet-4-5-20250929",
    tools: [
      /* your coding tools: file_read, file_write, terminal, etc. */
    ],
    responseFormat: toolStrategy(CodeOutput),
  });
}

export function createTaskAgent() {
  return createAgent({
    model: "claude-sonnet-4-5-20250929",
    tools: [
      /* your task tools: calendar_api, project_management, etc. */
    ],
    responseFormat: toolStrategy(TaskOutput),
  });
}

export function createDebugAgent() {
  return createAgent({
    model: "claude-sonnet-4-5-20250929",
    tools: [
      /* debugging tools: log_reader, stack_trace_parser, etc. */
    ],
    responseFormat: toolStrategy(DebugOutput),
  });
}

// ============================================================================
// STRATEGY 2: Union-type agent (the model decides the output type)
// ============================================================================
// Use when you want a single agent to handle everything.
// The model will pick the most appropriate schema based on the query.

export function createUniversalAgent() {
  return createAgent({
    model: "claude-sonnet-4-5-20250929",
    tools: [
      /* all available tools */
    ],
    // Pass the discriminated union — LangChain will present ALL schemas
    // as possible tool calls and the model picks the right one.
    responseFormat: toolStrategy(AgentOutput),
  });
}

// ============================================================================
// STRATEGY 3: Router-based agent (classify → specialize)
// ============================================================================
// Use when you want maximum control and accuracy.
// Step 1: A lightweight classification determines the output category.
// Step 2: A specialized agent runs with only the relevant schema.

import { z } from "zod";

const ClassificationSchema = z.object({
  category: z
    .enum([
      "code",
      "explanation",
      "project",
      "people",
      "task",
      "debug",
      "data_analysis",
      "decision",
      "learning",
      "calendar",
      "file_operation",
      "search_result",
      "conversation",
      "summary",
      "recommendation",
      "notification",
      "creative",
      "finance",
      "health",
    ])
    .describe("The most appropriate output category for this query"),
  reasoning: z
    .string()
    .describe("Brief explanation of why this category was chosen"),
});

const classifierAgent = createAgent({
  model: "claude-haiku-4-5-20251001", // fast + cheap for classification
  tools: [],
  responseFormat: providerStrategy(ClassificationSchema),
});

export async function routedAgentInvoke(userMessage: string) {
  // Step 1: Classify the intent
  const classification = await classifierAgent.invoke({
    messages: [
      {
        role: "system",
        content: `You are a query classifier. Determine the best output category for the user's request.
        
Categories:
- code: Code generation, review, refactoring, scripts
- explanation: Technical explanations, how things work
- project: Project status, architecture, planning
- people: Contact info, team members, person lookups
- task: Todos, action items, sprints, workflow
- debug: Errors, bugs, stack traces, fixes
- data_analysis: Metrics, analytics, charts
- decision: Comparing options, pros/cons
- learning: Tutorials, step-by-step guides
- calendar: Events, scheduling, availability
- file_operation: Creating, moving, editing files
- search_result: Web search, document search
- conversation: Casual chat, greetings, personal
- summary: Summarizing documents, meetings
- recommendation: Suggesting tools, products, approaches
- notification: Alerts, reminders, status updates
- creative: Writing, brainstorming, naming, copy
- finance: Budgets, expenses, financial planning
- health: Fitness, nutrition, wellness`,
      },
      { role: "user", content: userMessage },
    ],
  });

  const { category } = classification.structuredResponse;

  // Step 2: Run the specialized agent with the correct schema
  const schema = getOutputSchema(category as OutputCategory);

  const specializedAgent = createAgent({
    model: "claude-sonnet-4-5-20250929",
    tools: [
      /* tools relevant to this category */
    ],
    responseFormat: toolStrategy(schema),
  });

  const result = await specializedAgent.invoke({
    messages: [{ role: "user", content: userMessage }],
  });

  return {
    category,
    output: result.structuredResponse,
    messages: result.messages,
  };
}

// ============================================================================
// STRATEGY 4: Multi-schema with union types (subset of categories)
// ============================================================================
// Use when you want the model to pick from a SUBSET of output types.

export function createPersonalAssistantAgent() {
  return createAgent({
    model: "claude-sonnet-4-5-20250929",
    tools: [
      /* personal assistant tools */
    ],
    responseFormat: toolStrategy([
      ConversationOutput,
      TaskOutput,
      CalendarOutput,
      PeopleOutput,
      ProjectOutput,
    ]),
  });
}

export function createDevAgent() {
  return createAgent({
    model: "claude-sonnet-4-5-20250929",
    tools: [
      /* developer tools */
    ],
    responseFormat: toolStrategy([
      CodeOutput,
      DebugOutput,
      ExplanationOutput,
      ProjectOutput,
    ]),
  });
}

// ============================================================================
// USAGE EXAMPLES
// ============================================================================

async function examples() {
  // --- Example 1: Universal agent ---
  const universal = createUniversalAgent();

  const codeResult = await universal.invoke({
    messages: [
      {
        role: "user",
        content: "Create a React hook for infinite scrolling",
      },
    ],
  });
  // codeResult.structuredResponse → CodeOutput

  const taskResult = await universal.invoke({
    messages: [
      {
        role: "user",
        content: "Break down the auth system implementation into tasks",
      },
    ],
  });
  // taskResult.structuredResponse → TaskOutput

  // --- Example 2: Routed agent ---
  const routed = await routedAgentInvoke(
    "What are the pros and cons of using PostgreSQL vs MongoDB for our project?"
  );
  // routed.category → "decision"
  // routed.output → DecisionOutput

  // --- Example 3: Type narrowing on the result ---
  const result = codeResult.structuredResponse as AgentOutput;

  switch (result.category) {
    case "code":
      console.log("Files to create:", result.fragments.length);
      console.log("Dependencies:", result.dependencies);
      break;
    case "debug":
      console.log("Root cause:", result.rootCause);
      console.log("Fix:", result.fix.description);
      break;
    case "people":
      console.log("People found:", result.people.map((p) => p.name));
      break;
    case "task":
      console.log("Tasks:", result.tasks.map((t) => t.title));
      break;
    // TypeScript narrows the type automatically in each case
  }
}
