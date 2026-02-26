import { z } from "zod";
import {
  BaseAgentOutput,
  CodeOutput,
  ExplanationOutput,
  ProjectOutput,
  PeopleOutput,
  TaskOutput,
  DebugOutput,
  DataAnalysisOutput,
  DecisionOutput,
  LearningOutput,
  CalendarOutput,
  FileOperationOutput,
  SearchResultOutput,
  ConversationOutput,
  SummaryOutput,
  RecommendationOutput,
  NotificationOutput,
  CreativeOutput,
  FinanceOutput,
  HealthOutput,
} from "./output-types";

// ============================================================================
// DISCRIMINATED UNION — one schema to rule them all
// ============================================================================
// Use z.discriminatedUnion on the "category" field so LangChain and Zod
// can narrow the type at runtime based on which category the model returns.
// ============================================================================

export const AgentOutput = z.discriminatedUnion("category", [
  CodeOutput,
  ExplanationOutput,
  ProjectOutput,
  PeopleOutput,
  TaskOutput,
  DebugOutput,
  DataAnalysisOutput,
  DecisionOutput,
  LearningOutput,
  CalendarOutput,
  FileOperationOutput,
  SearchResultOutput,
  ConversationOutput,
  SummaryOutput,
  RecommendationOutput,
  NotificationOutput,
  CreativeOutput,
  FinanceOutput,
  HealthOutput,
]);

export type AgentOutput = z.infer<typeof AgentOutput>;

// ============================================================================
// CATEGORY → SCHEMA MAP (useful for dynamic routing)
// ============================================================================

export const OutputSchemaMap = {
  code: CodeOutput,
  explanation: ExplanationOutput,
  project: ProjectOutput,
  people: PeopleOutput,
  task: TaskOutput,
  debug: DebugOutput,
  data_analysis: DataAnalysisOutput,
  decision: DecisionOutput,
  learning: LearningOutput,
  calendar: CalendarOutput,
  file_operation: FileOperationOutput,
  search_result: SearchResultOutput,
  conversation: ConversationOutput,
  summary: SummaryOutput,
  recommendation: RecommendationOutput,
  notification: NotificationOutput,
  creative: CreativeOutput,
  finance: FinanceOutput,
  health: HealthOutput,
} as const;

export type OutputCategory = keyof typeof OutputSchemaMap;

// ============================================================================
// HELPER: get schema by category string
// ============================================================================

export function getOutputSchema<C extends OutputCategory>(
  category: C
): (typeof OutputSchemaMap)[C] {
  const schema = OutputSchemaMap[category];
  if (!schema) {
    throw new Error(`Unknown output category: ${category}`);
  }
  return schema;
}

// ============================================================================
// HELPER: validate raw output against the correct schema
// ============================================================================

export function validateAgentOutput(raw: unknown): AgentOutput {
  return AgentOutput.parse(raw);
}

export function safeValidateAgentOutput(raw: unknown): {
  success: boolean;
  data?: AgentOutput;
  error?: z.ZodError;
} {
  const result = AgentOutput.safeParse(raw);
  if (result.success) {
    return { success: true, data: result.data };
  }
  return { success: false, error: result.error };
}
