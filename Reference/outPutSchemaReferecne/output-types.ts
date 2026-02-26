import { z } from "zod";

// ============================================================================
// ENUMS & SHARED PRIMITIVES
// ============================================================================

export const OutputCategory = z.enum([
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
]);

export const Priority = z.enum(["critical", "high", "medium", "low", "none"]);
export const Sentiment = z.enum(["positive", "negative", "neutral", "mixed"]);
export const Confidence = z.enum(["high", "medium", "low", "uncertain"]);

// ============================================================================
// 1. BASE OUTPUT — every output extends this
// ============================================================================

export const BaseAgentOutput = z.object({
  category: OutputCategory.describe("The primary category of this output"),
  title: z.string().describe("A short, descriptive title for this output"),
  confidence: Confidence.describe("How confident the agent is in this output"),
  reasoning: z
    .string()
    .optional()
    .describe("Brief reasoning behind the output or approach taken"),
  followUpSuggestions: z
    .array(z.string())
    .optional()
    .describe("Suggested next actions or questions the user might want to ask"),
  metadata: z
    .record(z.string(), z.unknown())
    .optional()
    .describe("Arbitrary metadata for extensibility"),
});

export type BaseAgentOutput = z.infer<typeof BaseAgentOutput>;

// ============================================================================
// 2. CODE OUTPUT — code generation, review, refactoring, debugging
// ============================================================================

export const CodeFragment = z.object({
  filePath: z
    .string()
    .optional()
    .describe("Target file path for this code fragment"),
  language: z.string().describe("Programming language (e.g., typescript, python, rust)"),
  code: z.string().describe("The actual code content"),
  explanation: z
    .string()
    .optional()
    .describe("Brief explanation of what this code does"),
  startLine: z
    .number()
    .optional()
    .describe("Starting line number if modifying existing code"),
  endLine: z
    .number()
    .optional()
    .describe("Ending line number if modifying existing code"),
  operation: z
    .enum(["create", "replace", "insert", "delete", "append"])
    .optional()
    .describe("Type of file operation"),
});

export const CodeDependency = z.object({
  name: z.string().describe("Package or module name"),
  version: z.string().optional().describe("Version constraint"),
  registry: z
    .enum(["npm", "pip", "cargo", "gem", "maven", "nuget", "go", "other"])
    .optional()
    .describe("Package registry"),
  isDev: z.boolean().optional().describe("Whether this is a dev dependency"),
});

export const CodeOutput = BaseAgentOutput.extend({
  category: z.literal("code"),
  fragments: z
    .array(CodeFragment)
    .describe("One or more code fragments produced"),
  dependencies: z
    .array(CodeDependency)
    .optional()
    .describe("Dependencies required by the generated code"),
  architectureNotes: z
    .string()
    .optional()
    .describe("High-level architecture or design notes"),
  breakingChanges: z
    .array(z.string())
    .optional()
    .describe("List of breaking changes introduced"),
  testSuggestions: z
    .array(z.string())
    .optional()
    .describe("Suggested tests to write for this code"),
  securityConsiderations: z
    .array(z.string())
    .optional()
    .describe("Security concerns or recommendations"),
  performanceNotes: z
    .string()
    .optional()
    .describe("Performance implications or optimizations"),
  codeQuality: z
    .object({
      complexity: z.enum(["low", "medium", "high"]).optional(),
      maintainability: z.enum(["low", "medium", "high"]).optional(),
      patterns: z.array(z.string()).optional().describe("Design patterns used"),
    })
    .optional()
    .describe("Code quality assessment"),
});

export type CodeOutput = z.infer<typeof CodeOutput>;

// ============================================================================
// 3. EXPLANATION OUTPUT — technical explanations, how-things-work
// ============================================================================

export const ExplanationSection = z.object({
  heading: z.string().describe("Section heading"),
  content: z.string().describe("Section content in markdown"),
  depth: z
    .enum(["beginner", "intermediate", "advanced", "expert"])
    .optional()
    .describe("Technical depth of this section"),
});

export const ExplanationOutput = BaseAgentOutput.extend({
  category: z.literal("explanation"),
  summary: z.string().describe("A concise TL;DR summary"),
  sections: z
    .array(ExplanationSection)
    .describe("Structured explanation sections"),
  analogies: z
    .array(z.string())
    .optional()
    .describe("Analogies to help understand the concept"),
  relatedTopics: z
    .array(z.string())
    .optional()
    .describe("Related topics for further exploration"),
  references: z
    .array(
      z.object({
        title: z.string(),
        url: z.string().optional(),
        description: z.string().optional(),
      })
    )
    .optional()
    .describe("Reference materials and links"),
  targetAudience: z
    .enum(["beginner", "intermediate", "advanced", "expert"])
    .optional()
    .describe("Intended audience level"),
});

export type ExplanationOutput = z.infer<typeof ExplanationOutput>;

// ============================================================================
// 4. PROJECT OUTPUT — project info, architecture, status, roadmap
// ============================================================================

export const ProjectOutput = BaseAgentOutput.extend({
  category: z.literal("project"),
  projectName: z.string().describe("Name of the project"),
  status: z
    .enum([
      "planning",
      "in_progress",
      "review",
      "blocked",
      "completed",
      "archived",
    ])
    .optional()
    .describe("Current project status"),
  description: z.string().optional().describe("Project description"),
  techStack: z
    .array(
      z.object({
        name: z.string(),
        role: z.string().describe("Role in the project (e.g., 'frontend framework', 'database')"),
        version: z.string().optional(),
      })
    )
    .optional()
    .describe("Technologies used in the project"),
  architecture: z
    .object({
      pattern: z.string().optional().describe("Architecture pattern (e.g., microservices, monolith, serverless)"),
      components: z
        .array(
          z.object({
            name: z.string(),
            description: z.string(),
            dependencies: z.array(z.string()).optional(),
          })
        )
        .optional(),
      diagram: z
        .string()
        .optional()
        .describe("Mermaid diagram or ASCII art of the architecture"),
    })
    .optional()
    .describe("Architecture overview"),
  risks: z
    .array(
      z.object({
        description: z.string(),
        severity: Priority,
        mitigation: z.string().optional(),
      })
    )
    .optional()
    .describe("Known risks and mitigations"),
  milestones: z
    .array(
      z.object({
        name: z.string(),
        dueDate: z.string().optional(),
        status: z.enum(["pending", "in_progress", "completed", "overdue"]),
        progress: z.number().min(0).max(100).optional(),
      })
    )
    .optional()
    .describe("Project milestones"),
  metrics: z
    .record(z.string(), z.union([z.string(), z.number()]))
    .optional()
    .describe("Key project metrics"),
});

export type ProjectOutput = z.infer<typeof ProjectOutput>;

// ============================================================================
// 5. PEOPLE OUTPUT — contacts, team members, person info
// ============================================================================

export const PersonInfo = z.object({
  name: z.string().describe("Full name"),
  role: z.string().optional().describe("Role or job title"),
  organization: z.string().optional().describe("Company or organization"),
  email: z.string().optional().describe("Email address"),
  phone: z.string().optional().describe("Phone number"),
  location: z.string().optional().describe("Geographic location"),
  timezone: z.string().optional().describe("Timezone (e.g., America/Sao_Paulo)"),
  socialLinks: z
    .record(z.string(), z.string())
    .optional()
    .describe("Social media or professional links"),
  notes: z.string().optional().describe("Additional notes about this person"),
  tags: z.array(z.string()).optional().describe("Tags for categorization"),
  relationship: z
    .string()
    .optional()
    .describe("Relationship context (e.g., colleague, client, friend)"),
  lastInteraction: z
    .string()
    .optional()
    .describe("Date/description of last interaction"),
});

export const PeopleOutput = BaseAgentOutput.extend({
  category: z.literal("people"),
  people: z.array(PersonInfo).describe("List of people referenced"),
  context: z
    .string()
    .optional()
    .describe("Context for why these people are being referenced"),
  interactionSuggestions: z
    .array(z.string())
    .optional()
    .describe("Suggested actions related to these people"),
});

export type PeopleOutput = z.infer<typeof PeopleOutput>;

// ============================================================================
// 6. TASK OUTPUT — todos, action items, workflow steps
// ============================================================================

export const TaskItem = z.object({
  id: z.string().describe("Unique task identifier"),
  title: z.string().describe("Task title"),
  description: z.string().optional().describe("Detailed task description"),
  status: z
    .enum(["todo", "in_progress", "blocked", "review", "done", "cancelled"])
    .describe("Current task status"),
  priority: Priority,
  assignee: z.string().optional().describe("Person assigned to this task"),
  dueDate: z.string().optional().describe("Due date in ISO format"),
  estimatedHours: z.number().optional().describe("Estimated hours to complete"),
  tags: z.array(z.string()).optional(),
  dependencies: z
    .array(z.string())
    .optional()
    .describe("IDs of tasks this depends on"),
  subtasks: z
    .array(
      z.object({
        title: z.string(),
        completed: z.boolean(),
      })
    )
    .optional(),
  project: z.string().optional().describe("Associated project name"),
});

export const TaskOutput = BaseAgentOutput.extend({
  category: z.literal("task"),
  tasks: z.array(TaskItem).describe("List of tasks"),
  workflowSummary: z
    .string()
    .optional()
    .describe("Summary of the overall workflow or sprint"),
  totalEstimatedHours: z
    .number()
    .optional()
    .describe("Total estimated hours across all tasks"),
  criticalPath: z
    .array(z.string())
    .optional()
    .describe("Task IDs forming the critical path"),
});

export type TaskOutput = z.infer<typeof TaskOutput>;

// ============================================================================
// 7. DEBUG OUTPUT — error analysis, stack traces, fixes
// ============================================================================

export const DebugOutput = BaseAgentOutput.extend({
  category: z.literal("debug"),
  errorType: z
    .string()
    .describe("Type/category of the error (e.g., TypeError, NetworkError, LogicError)"),
  errorMessage: z.string().describe("The original error message"),
  rootCause: z
    .string()
    .describe("Analysis of the root cause"),
  stackTraceAnalysis: z
    .string()
    .optional()
    .describe("Interpretation of the stack trace"),
  affectedFiles: z
    .array(
      z.object({
        path: z.string(),
        line: z.number().optional(),
        issue: z.string(),
      })
    )
    .optional()
    .describe("Files involved in the error"),
  fix: z
    .object({
      description: z.string().describe("Description of the fix"),
      code: z.array(CodeFragment).optional().describe("Code changes to apply"),
      steps: z
        .array(z.string())
        .optional()
        .describe("Manual steps required beyond code changes"),
    })
    .describe("The proposed fix"),
  preventionTips: z
    .array(z.string())
    .optional()
    .describe("How to prevent this error in the future"),
  relatedIssues: z
    .array(z.string())
    .optional()
    .describe("Links or references to related known issues"),
  severity: Priority.describe("Severity of the issue"),
});

export type DebugOutput = z.infer<typeof DebugOutput>;

// ============================================================================
// 8. DATA ANALYSIS OUTPUT — metrics, charts, insights
// ============================================================================

export const DataPoint = z.object({
  label: z.string(),
  value: z.union([z.number(), z.string()]),
  unit: z.string().optional(),
  change: z.number().optional().describe("Percentage change"),
  trend: z.enum(["up", "down", "stable"]).optional(),
});

export const DataAnalysisOutput = BaseAgentOutput.extend({
  category: z.literal("data_analysis"),
  summary: z.string().describe("Executive summary of the analysis"),
  keyFindings: z
    .array(z.string())
    .describe("Top insights from the data"),
  dataPoints: z
    .array(DataPoint)
    .optional()
    .describe("Key data points"),
  charts: z
    .array(
      z.object({
        type: z.enum([
          "bar",
          "line",
          "pie",
          "scatter",
          "heatmap",
          "table",
          "funnel",
          "gauge",
        ]),
        title: z.string(),
        data: z.unknown().describe("Chart-specific data payload"),
        description: z.string().optional(),
      })
    )
    .optional()
    .describe("Suggested chart visualizations"),
  anomalies: z
    .array(
      z.object({
        description: z.string(),
        severity: Priority,
        dataPoint: z.string().optional(),
      })
    )
    .optional()
    .describe("Data anomalies detected"),
  recommendations: z
    .array(z.string())
    .optional()
    .describe("Data-driven recommendations"),
  methodology: z
    .string()
    .optional()
    .describe("Methodology used for the analysis"),
  limitations: z
    .array(z.string())
    .optional()
    .describe("Limitations of this analysis"),
});

export type DataAnalysisOutput = z.infer<typeof DataAnalysisOutput>;

// ============================================================================
// 9. DECISION OUTPUT — pros/cons, comparisons, recommendations
// ============================================================================

export const DecisionOption = z.object({
  name: z.string().describe("Option name"),
  description: z.string().describe("Option description"),
  pros: z.array(z.string()).describe("Advantages"),
  cons: z.array(z.string()).describe("Disadvantages"),
  score: z
    .number()
    .min(0)
    .max(100)
    .optional()
    .describe("Score from 0-100"),
  risks: z.array(z.string()).optional(),
  costs: z
    .object({
      money: z.string().optional(),
      time: z.string().optional(),
      effort: z.enum(["low", "medium", "high"]).optional(),
    })
    .optional(),
  tags: z.array(z.string()).optional(),
});

export const DecisionOutput = BaseAgentOutput.extend({
  category: z.literal("decision"),
  question: z.string().describe("The decision question being addressed"),
  options: z
    .array(DecisionOption)
    .describe("Available options to choose from"),
  recommendation: z
    .object({
      option: z.string().describe("Recommended option name"),
      reasoning: z.string().describe("Why this option is recommended"),
      caveats: z
        .array(z.string())
        .optional()
        .describe("Conditions under which this recommendation changes"),
    })
    .optional()
    .describe("The agent's recommendation"),
  criteria: z
    .array(
      z.object({
        name: z.string(),
        weight: z.number().min(0).max(1).describe("Weight from 0-1"),
        description: z.string().optional(),
      })
    )
    .optional()
    .describe("Evaluation criteria used"),
  decisionMatrix: z
    .array(z.record(z.string(), z.union([z.string(), z.number()])))
    .optional()
    .describe("Decision matrix with options × criteria scores"),
});

export type DecisionOutput = z.infer<typeof DecisionOutput>;

// ============================================================================
// 10. LEARNING OUTPUT — tutorials, step-by-step, educational
// ============================================================================

export const LearningStep = z.object({
  stepNumber: z.number(),
  title: z.string(),
  content: z.string().describe("Step content in markdown"),
  code: z.string().optional().describe("Code example for this step"),
  tip: z.string().optional().describe("Pro tip for this step"),
  commonMistakes: z
    .array(z.string())
    .optional()
    .describe("Common mistakes to avoid at this step"),
  checkpoint: z
    .string()
    .optional()
    .describe("What the user should see/verify at this point"),
});

export const LearningOutput = BaseAgentOutput.extend({
  category: z.literal("learning"),
  topic: z.string().describe("The topic being taught"),
  targetLevel: z
    .enum(["beginner", "intermediate", "advanced", "expert"])
    .describe("Target knowledge level"),
  prerequisites: z
    .array(z.string())
    .optional()
    .describe("Knowledge prerequisites"),
  estimatedTime: z
    .string()
    .optional()
    .describe("Estimated time to complete (e.g., '30 minutes')"),
  learningObjectives: z
    .array(z.string())
    .describe("What the user will learn"),
  steps: z.array(LearningStep).describe("Sequential learning steps"),
  exercises: z
    .array(
      z.object({
        prompt: z.string().describe("Exercise description"),
        difficulty: z.enum(["easy", "medium", "hard"]),
        solution: z.string().optional().describe("Solution (hidden by default)"),
        hints: z.array(z.string()).optional(),
      })
    )
    .optional()
    .describe("Practice exercises"),
  resources: z
    .array(
      z.object({
        title: z.string(),
        url: z.string().optional(),
        type: z.enum(["article", "video", "course", "book", "documentation", "tool"]),
      })
    )
    .optional()
    .describe("Additional learning resources"),
});

export type LearningOutput = z.infer<typeof LearningOutput>;

// ============================================================================
// 11. CALENDAR / SCHEDULE OUTPUT
// ============================================================================

export const CalendarEvent = z.object({
  title: z.string(),
  description: z.string().optional(),
  startTime: z.string().describe("ISO datetime string"),
  endTime: z.string().optional().describe("ISO datetime string"),
  location: z.string().optional(),
  attendees: z.array(z.string()).optional(),
  isRecurring: z.boolean().optional(),
  recurrenceRule: z.string().optional().describe("RRULE string if recurring"),
  reminders: z
    .array(
      z.object({
        minutesBefore: z.number(),
        method: z.enum(["notification", "email", "sms"]),
      })
    )
    .optional(),
  tags: z.array(z.string()).optional(),
  priority: Priority.optional(),
  status: z
    .enum(["confirmed", "tentative", "cancelled"])
    .optional(),
});

export const CalendarOutput = BaseAgentOutput.extend({
  category: z.literal("calendar"),
  events: z.array(CalendarEvent).describe("Calendar events"),
  conflicts: z
    .array(
      z.object({
        event1: z.string().describe("First conflicting event title"),
        event2: z.string().describe("Second conflicting event title"),
        resolution: z.string().optional(),
      })
    )
    .optional()
    .describe("Detected scheduling conflicts"),
  freeSlots: z
    .array(
      z.object({
        start: z.string(),
        end: z.string(),
        duration: z.string().describe("Human-readable duration"),
      })
    )
    .optional()
    .describe("Available time slots"),
  scheduleSummary: z
    .string()
    .optional()
    .describe("Natural language summary of the schedule"),
});

export type CalendarOutput = z.infer<typeof CalendarOutput>;

// ============================================================================
// 12. FILE OPERATION OUTPUT
// ============================================================================

export const FileOperationOutput = BaseAgentOutput.extend({
  category: z.literal("file_operation"),
  operations: z
    .array(
      z.object({
        type: z.enum([
          "create",
          "read",
          "update",
          "delete",
          "move",
          "rename",
          "copy",
        ]),
        sourcePath: z.string(),
        destinationPath: z.string().optional(),
        content: z.string().optional().describe("File content for create/update"),
        status: z.enum(["pending", "success", "failed", "skipped"]),
        error: z.string().optional(),
        size: z.string().optional().describe("File size"),
      })
    )
    .describe("File operations performed or to be performed"),
  affectedPaths: z
    .array(z.string())
    .describe("All file paths affected"),
  requiresConfirmation: z
    .boolean()
    .optional()
    .describe("Whether user confirmation is needed before executing"),
  rollbackSteps: z
    .array(z.string())
    .optional()
    .describe("Steps to undo these operations"),
});

export type FileOperationOutput = z.infer<typeof FileOperationOutput>;

// ============================================================================
// 13. SEARCH RESULT OUTPUT
// ============================================================================

export const SearchResultOutput = BaseAgentOutput.extend({
  category: z.literal("search_result"),
  query: z.string().describe("The search query performed"),
  results: z
    .array(
      z.object({
        title: z.string(),
        snippet: z.string(),
        url: z.string().optional(),
        source: z.string().optional().describe("Source name or type"),
        relevanceScore: z.number().min(0).max(1).optional(),
        date: z.string().optional(),
        type: z
          .enum([
            "web",
            "code",
            "documentation",
            "forum",
            "internal",
            "file",
            "note",
          ])
          .optional(),
      })
    )
    .describe("Search results"),
  totalResults: z.number().optional(),
  synthesizedAnswer: z
    .string()
    .optional()
    .describe("AI-synthesized answer from the results"),
  suggestedQueries: z
    .array(z.string())
    .optional()
    .describe("Related queries to try"),
});

export type SearchResultOutput = z.infer<typeof SearchResultOutput>;

// ============================================================================
// 14. CONVERSATION OUTPUT — casual chat, personal assistant
// ============================================================================

export const ConversationOutput = BaseAgentOutput.extend({
  category: z.literal("conversation"),
  message: z.string().describe("The conversational response"),
  tone: z
    .enum([
      "friendly",
      "professional",
      "empathetic",
      "humorous",
      "motivational",
      "informative",
      "cautious",
    ])
    .optional()
    .describe("Tone of the response"),
  sentiment: Sentiment.optional().describe("Detected sentiment of the user's input"),
  topicShift: z
    .boolean()
    .optional()
    .describe("Whether the conversation topic changed"),
  contextTags: z
    .array(z.string())
    .optional()
    .describe("Tags for conversation context tracking"),
  emotionalState: z
    .object({
      detected: z.string().optional().describe("User's detected emotional state"),
      responseStrategy: z.string().optional().describe("Strategy used to respond"),
    })
    .optional(),
});

export type ConversationOutput = z.infer<typeof ConversationOutput>;

// ============================================================================
// 15. SUMMARY OUTPUT — document summaries, meeting notes, digests
// ============================================================================

export const SummaryOutput = BaseAgentOutput.extend({
  category: z.literal("summary"),
  sourceType: z
    .enum([
      "document",
      "meeting",
      "conversation",
      "article",
      "codebase",
      "email_thread",
      "report",
      "video",
      "multiple_sources",
    ])
    .describe("Type of content being summarized"),
  sourceName: z.string().optional().describe("Name/title of the source"),
  tldr: z.string().describe("One-line TL;DR"),
  keyPoints: z
    .array(z.string())
    .describe("Key points extracted"),
  detailedSummary: z
    .string()
    .describe("Detailed summary in markdown"),
  actionItems: z
    .array(
      z.object({
        action: z.string(),
        owner: z.string().optional(),
        deadline: z.string().optional(),
      })
    )
    .optional()
    .describe("Action items extracted"),
  decisions: z
    .array(z.string())
    .optional()
    .describe("Decisions that were made"),
  openQuestions: z
    .array(z.string())
    .optional()
    .describe("Unresolved questions"),
  sentiment: Sentiment.optional(),
  wordCount: z
    .number()
    .optional()
    .describe("Approximate word count of the original"),
});

export type SummaryOutput = z.infer<typeof SummaryOutput>;

// ============================================================================
// 16. RECOMMENDATION OUTPUT
// ============================================================================

export const RecommendationItem = z.object({
  name: z.string(),
  description: z.string(),
  matchScore: z
    .number()
    .min(0)
    .max(100)
    .optional()
    .describe("How well it matches the user's criteria (0-100)"),
  reasoning: z.string().describe("Why this is recommended"),
  category: z.string().optional(),
  url: z.string().optional(),
  price: z.string().optional(),
  tags: z.array(z.string()).optional(),
  highlights: z.array(z.string()).optional().describe("Key selling points"),
  drawbacks: z.array(z.string()).optional().describe("Known downsides"),
});

export const RecommendationOutput = BaseAgentOutput.extend({
  category: z.literal("recommendation"),
  context: z
    .string()
    .describe("What the user is looking for"),
  criteria: z
    .array(z.string())
    .optional()
    .describe("Criteria used for evaluation"),
  recommendations: z
    .array(RecommendationItem)
    .describe("Ranked recommendations"),
  topPick: z
    .object({
      name: z.string(),
      reason: z.string(),
    })
    .optional()
    .describe("The single best recommendation if one stands out"),
  alternatives: z
    .array(z.string())
    .optional()
    .describe("Categories or areas not explored"),
});

export type RecommendationOutput = z.infer<typeof RecommendationOutput>;

// ============================================================================
// 17. NOTIFICATION OUTPUT — alerts, reminders, status updates
// ============================================================================

export const NotificationOutput = BaseAgentOutput.extend({
  category: z.literal("notification"),
  type: z.enum([
    "alert",
    "reminder",
    "status_update",
    "warning",
    "info",
    "success",
    "error",
  ]),
  urgency: Priority,
  message: z.string().describe("The notification message"),
  source: z
    .string()
    .optional()
    .describe("Where this notification originates from"),
  actionRequired: z.boolean().describe("Whether the user needs to take action"),
  actionUrl: z.string().optional().describe("Link to take action"),
  expiresAt: z.string().optional().describe("When this notification expires"),
  relatedEntities: z
    .array(
      z.object({
        type: z.string(),
        name: z.string(),
        id: z.string().optional(),
      })
    )
    .optional()
    .describe("Entities related to this notification"),
});

export type NotificationOutput = z.infer<typeof NotificationOutput>;

// ============================================================================
// 18. CREATIVE OUTPUT — writing, brainstorming, content creation
// ============================================================================

export const CreativeOutput = BaseAgentOutput.extend({
  category: z.literal("creative"),
  contentType: z.enum([
    "blog_post",
    "email_draft",
    "social_media",
    "brainstorm",
    "naming",
    "copy",
    "story",
    "script",
    "outline",
    "tagline",
    "other",
  ]),
  content: z.string().describe("The creative content produced"),
  variants: z
    .array(
      z.object({
        label: z.string().describe("Variant label (e.g., 'formal', 'casual')"),
        content: z.string(),
      })
    )
    .optional()
    .describe("Alternative versions of the content"),
  tone: z.string().optional().describe("Tone used"),
  targetAudience: z.string().optional(),
  wordCount: z.number().optional(),
  keywords: z
    .array(z.string())
    .optional()
    .describe("SEO or thematic keywords"),
  editingSuggestions: z
    .array(z.string())
    .optional()
    .describe("Suggestions for improvement"),
});

export type CreativeOutput = z.infer<typeof CreativeOutput>;

// ============================================================================
// 19. FINANCE OUTPUT — budgets, expenses, financial analysis
// ============================================================================

export const FinanceOutput = BaseAgentOutput.extend({
  category: z.literal("finance"),
  type: z.enum([
    "expense_report",
    "budget",
    "forecast",
    "invoice",
    "comparison",
    "investment",
    "tax",
    "other",
  ]),
  currency: z.string().describe("Currency code (e.g., BRL, USD, EUR)"),
  summary: z.string().describe("Financial summary"),
  lineItems: z
    .array(
      z.object({
        description: z.string(),
        amount: z.number(),
        category: z.string().optional(),
        date: z.string().optional(),
        recurring: z.boolean().optional(),
      })
    )
    .optional()
    .describe("Individual financial line items"),
  totals: z
    .object({
      income: z.number().optional(),
      expenses: z.number().optional(),
      net: z.number().optional(),
      savings: z.number().optional(),
    })
    .optional()
    .describe("Totals and aggregations"),
  insights: z
    .array(z.string())
    .optional()
    .describe("Financial insights and observations"),
  alerts: z
    .array(
      z.object({
        type: z.enum(["overspend", "unusual", "opportunity", "deadline", "goal"]),
        message: z.string(),
      })
    )
    .optional()
    .describe("Financial alerts"),
});

export type FinanceOutput = z.infer<typeof FinanceOutput>;

// ============================================================================
// 20. HEALTH & WELLNESS OUTPUT
// ============================================================================

export const HealthOutput = BaseAgentOutput.extend({
  category: z.literal("health"),
  type: z.enum([
    "fitness_plan",
    "nutrition",
    "wellness_check",
    "habit_tracking",
    "sleep",
    "mental_health",
    "medication_reminder",
    "other",
  ]),
  summary: z.string().describe("Health-related summary"),
  recommendations: z
    .array(
      z.object({
        action: z.string(),
        frequency: z.string().optional(),
        duration: z.string().optional(),
        notes: z.string().optional(),
      })
    )
    .optional(),
  metrics: z
    .array(DataPoint)
    .optional()
    .describe("Health metrics tracked"),
  disclaimer: z
    .string()
    .default("This is not medical advice. Consult a healthcare professional.")
    .describe("Health disclaimer"),
});

export type HealthOutput = z.infer<typeof HealthOutput>;
