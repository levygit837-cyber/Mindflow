/**
 * ============================================================================
 * OMNIMIND EXAMPLES INDEX
 * ============================================================================
 *
 * This file exports all examples for easy discovery and usage.
 * Each example file covers a specific topic with comprehensive demonstrations.
 *
 * HOW TO USE THESE EXAMPLES:
 * --------------------------
 * 1. Import specific examples: import { example_1_1_simpleChatInvocation } from './examples'
 * 2. Import by topic: import { LangChainBasics } from './examples'
 * 3. Run examples in your code or tests to learn the patterns
 *
 * FILE STRUCTURE:
 * ---------------
 * 01-langchain-basics.examples.ts     - LangChain fundamentals
 * 02-langgraph-workflows.examples.ts  - LangGraph state machines and graphs
 * 03-tools-and-agents.examples.ts     - Tool creation and agent patterns
 * 04-memory-and-state.examples.ts     - Memory management and persistence
 * 05-api-patterns.examples.ts         - API integration patterns
 * 06-advanced-patterns.examples.ts    - RAG, chains, and advanced AI patterns
 * 07-typescript-patterns.examples.ts  - TypeScript best practices
 * 08-real-world-scenarios.examples.ts - Production-ready scenarios
 *
 * @author OmniMind Team
 * @version 1.0.0
 */

// ============================================================================
// 01 - LANGCHAIN BASICS
// ============================================================================
// Covers: LLM invocations, prompts, output parsers, chains, streaming
export * from "./01-langchain-basics.examples";

export {
  // Basic invocations
  example_1_1_simpleChatInvocation,
  example_1_2_chatWithSystemMessage,
  example_1_3_multiTurnConversation,
  example_1_4_modelParameters,
  // Prompt templates
  example_2_1_basicPromptTemplate,
  example_2_2_complexPromptTemplate,
  example_2_3_templateWithHistory,
  example_2_4_fewShotPrompting,
  // Output parsers
  example_3_1_stringOutputParser,
  example_3_2_jsonOutputParser,
  example_3_3_structuredOutputWithZod,
  example_3_4_customOutputParser,
  // Chains
  example_4_1_simpleChain,
  example_4_2_sequentialChain,
  example_4_3_runnableSequence,
  example_4_4_parallelExecution,
  // Streaming
  example_5_1_basicStreaming,
  example_5_2_streamingWithChain,
  example_5_3_streamingWithCallback,
  // Error handling
  example_6_1_basicErrorHandling,
  example_6_2_retryWithBackoff,
  example_6_2_usage,
  example_6_3_fallbackModel,
  example_6_4_withTimeout,
} from "./01-langchain-basics.examples";

// ============================================================================
// 02 - LANGGRAPH WORKFLOWS
// ============================================================================
// Covers: State graphs, nodes, edges, conditional routing, cycles, parallel execution
export * from "./02-langgraph-workflows.examples";

export {
  // Basic graph creation
  example_1_1_minimalGraph,
  example_1_2_multiNodeLinearGraph,
  example_1_3_sharedStateGraph,
  // Conditional routing
  example_2_1_simpleConditionalEdge,
  example_2_2_multiPathRouting,
  example_2_3_conditionalWithMap,
  // Cycles and loops
  example_3_1_simpleLoopWithCounter,
  example_3_2_iterativeRefinement,
  example_3_3_agentLoopWithTools,
  // Parallel execution
  example_4_1_parallelFanOutFanIn,
  example_4_2_dynamicParallelExecution,
} from "./02-langgraph-workflows.examples";

// ============================================================================
// 03 - TOOLS AND AGENTS
// ============================================================================
// Covers: Tool creation, agents, ReAct pattern, tool binding
export * from "./03-tools-and-agents.examples";

export {
  // Basic tools
  calculatorTool,
  temperatureConverterTool,
  weatherTool,
  // Class-based tools
  SearchDatabaseTool,
  ShoppingCartTool,
  EmailSenderTool,
  // Dynamic tools
  currentTimeTool,
  scheduleMeetingTool,
  createApiTool,
  userApiTool,
  // Tool binding examples
  example_4_1_bindToolsToModel,
  example_4_2_handleToolCalls,
  example_4_3_toolChoice,
  // Agent executors
  example_5_1_toolCallingAgent,
  example_5_2_agentWithMemory,
  example_5_3_agentWithErrorHandling,
} from "./03-tools-and-agents.examples";

// ============================================================================
// 04 - MEMORY AND STATE
// ============================================================================
// Covers: Chat history, memory patterns, checkpointing, session management
export * from "./04-memory-and-state.examples";

export {
  // Basic memory
  example_1_1_basicChatHistory,
  example_1_2_windowedMemory,
  example_1_3_tokenLimitedMemory,
  // Advanced memory patterns
  ConversationSummaryMemory,
  example_2_1_summaryMemory,
  EntityMemory,
  example_2_2_entityMemory,
  HybridMemory,
  example_2_3_hybridMemory,
  // LangGraph persistence
  example_3_1_langGraphMemorySaver,
  example_3_2_checkpointRecovery,
  MultiThreadManager,
  example_3_3_multiThreadManagement,
} from "./04-memory-and-state.examples";

// ============================================================================
// 05 - API PATTERNS
// ============================================================================
// Covers: REST clients, error handling, rate limiting, auth, streaming
export * from "./05-api-patterns.examples";

export {
  // API client
  APIClient,
  APIError,
  TypedAPIClient,
  example_1_2_typedApiClient,
  // Retry and circuit breaker
  withRetry,
  example_2_1_retryWithBackoff,
  CircuitBreaker,
  CircuitState,
  example_2_2_circuitBreaker,
  // Rate limiting
  TokenBucketRateLimiter,
  RateLimitedAPIClient,
  example_3_1_tokenBucketRateLimiter,
  SlidingWindowRateLimiter,
  // Authentication
  createApiKeyAuthClient,
  OAuth2Client,
  JWTManager,
  // Streaming
  SSEClient,
  streamLLMResponse,
  example_5_2_streamingFetch,
  WebhookHandler,
} from "./05-api-patterns.examples";

// ============================================================================
// 06 - ADVANCED PATTERNS
// ============================================================================
// Covers: RAG, document processing, chains, extraction
export * from "./06-advanced-patterns.examples";

export {
  // RAG patterns
  example_1_1_basicRAG,
  example_1_2_documentChunking,
  example_1_3_multiQueryRAG,
  example_1_4_ragWithReranking,
  // Advanced chains
  example_2_1_mapReduceChain,
  example_2_2_routingChain,
  example_2_3_fallbackChain,
  example_2_4_parallelChains,
  // Extraction
  example_3_1_entityExtraction,
  example_3_2_dataTransformation,
} from "./06-advanced-patterns.examples";

// ============================================================================
// 07 - TYPESCRIPT PATTERNS
// ============================================================================
// Covers: Generics, utility types, patterns, error handling
export * from "./07-typescript-patterns.examples";

export {
  // Generics
  identity,
  pair,
  firstElement,
  filterByType,
  logLength,
  getProperty,
  createArray,
  updateEntity,
  Stack,
  KeyValueStore,
  // Type utilities (types are auto-exported with export *)
  // Design patterns
  EmailBuilder,
  LoggerFactory,
  ConsoleLogger,
  JsonLogger,
  InMemoryRepository,
  Container,
  // Error handling
  AppError,
  ValidationError,
  NotFoundError,
  UnauthorizedError,
  ForbiddenError,
  ConflictError,
  Result,
} from "./07-typescript-patterns.examples";

// ============================================================================
// 08 - REAL WORLD SCENARIOS
// ============================================================================
// Covers: Customer support, Q&A, moderation, email handling, code review
export * from "./08-real-world-scenarios.examples";

export {
  // Customer support
  createCustomerSupportBot,
  example_1_1_customerSupportBot,
  // Document Q&A
  DocumentQASystem,
  example_2_1_documentQA,
  // Content moderation
  ContentModerationSystem,
  example_3_1_contentModeration,
  // Email handling
  IntelligentEmailHandler,
  example_4_1_emailHandler,
  // Code review
  CodeReviewAssistant,
} from "./08-real-world-scenarios.examples";

// ============================================================================
// GROUPED EXPORTS FOR CONVENIENCE
// ============================================================================

/**
 * LangChain basics examples grouped together
 */
export const LangChainBasics = {
  simpleChatInvocation: () => import("./01-langchain-basics.examples").then(m => m.example_1_1_simpleChatInvocation),
  chatWithSystemMessage: () => import("./01-langchain-basics.examples").then(m => m.example_1_2_chatWithSystemMessage),
  multiTurnConversation: () => import("./01-langchain-basics.examples").then(m => m.example_1_3_multiTurnConversation),
};

/**
 * LangGraph workflow examples grouped together
 */
export const LangGraphWorkflows = {
  minimalGraph: () => import("./02-langgraph-workflows.examples").then(m => m.example_1_1_minimalGraph),
  conditionalEdge: () => import("./02-langgraph-workflows.examples").then(m => m.example_2_1_simpleConditionalEdge),
  iterativeRefinement: () => import("./02-langgraph-workflows.examples").then(m => m.example_3_2_iterativeRefinement),
};

/**
 * Tools and agents examples grouped together
 */
export const ToolsAndAgents = {
  calculatorTool: () => import("./03-tools-and-agents.examples").then(m => m.calculatorTool),
  weatherTool: () => import("./03-tools-and-agents.examples").then(m => m.weatherTool),
  toolCallingAgent: () => import("./03-tools-and-agents.examples").then(m => m.example_5_1_toolCallingAgent),
};

/**
 * Real world scenario examples grouped together
 */
export const RealWorldScenarios = {
  customerSupport: () => import("./08-real-world-scenarios.examples").then(m => m.example_1_1_customerSupportBot),
  documentQA: () => import("./08-real-world-scenarios.examples").then(m => m.example_2_1_documentQA),
  contentModeration: () => import("./08-real-world-scenarios.examples").then(m => m.example_3_1_contentModeration),
  emailHandler: () => import("./08-real-world-scenarios.examples").then(m => m.example_4_1_emailHandler),
};

// ============================================================================
// QUICK REFERENCE
// ============================================================================

/**
 * Quick reference of all available examples by category
 */
export const ExamplesReference = {
  categories: [
    {
      name: "LangChain Basics",
      file: "01-langchain-basics.examples.ts",
      topics: ["LLM invocations", "Prompts", "Output parsers", "Chains", "Streaming", "Error handling"],
    },
    {
      name: "LangGraph Workflows",
      file: "02-langgraph-workflows.examples.ts",
      topics: ["State graphs", "Nodes/Edges", "Conditional routing", "Cycles", "Parallel execution"],
    },
    {
      name: "Tools and Agents",
      file: "03-tools-and-agents.examples.ts",
      topics: ["Tool creation", "Structured tools", "Dynamic tools", "Agents", "ReAct pattern"],
    },
    {
      name: "Memory and State",
      file: "04-memory-and-state.examples.ts",
      topics: ["Chat history", "Summary memory", "Entity memory", "Checkpointing", "Sessions"],
    },
    {
      name: "API Patterns",
      file: "05-api-patterns.examples.ts",
      topics: ["REST clients", "Retry/backoff", "Circuit breaker", "Rate limiting", "Auth", "SSE"],
    },
    {
      name: "Advanced Patterns",
      file: "06-advanced-patterns.examples.ts",
      topics: ["RAG", "Document chunking", "Multi-query", "Map-reduce", "Routing", "Extraction"],
    },
    {
      name: "TypeScript Patterns",
      file: "07-typescript-patterns.examples.ts",
      topics: ["Generics", "Utility types", "Type guards", "Design patterns", "Error handling"],
    },
    {
      name: "Real World Scenarios",
      file: "08-real-world-scenarios.examples.ts",
      topics: ["Customer support", "Document Q&A", "Moderation", "Email handling", "Code review"],
    },
  ],
};

export default ExamplesReference;
