/**
 * ============================================================================
 * 02 - LANGGRAPH WORKFLOWS EXAMPLES
 * ============================================================================
 *
 * This file contains comprehensive examples of LangGraph workflows.
 * LangGraph is a library for building stateful, multi-step AI applications.
 *
 * Topics covered:
 * - Basic graph creation and structure
 * - State management and channels
 * - Nodes and edges
 * - Conditional routing
 * - Cycles and loops
 * - Subgraphs and composition
 * - Checkpointing and persistence
 * - Human-in-the-loop patterns
 * - Parallel node execution
 * - Error handling in graphs
 * - Streaming from graphs
 *
 * @author OmniMind Team
 * @version 1.0.0
 */

import {
  StateGraph,
  END,
  START,
  Annotation,
  MemorySaver,
} from "@langchain/langgraph";
import { ChatOpenAI } from "@langchain/openai";
import {
  HumanMessage,
  AIMessage,
  BaseMessage,
  SystemMessage,
} from "@langchain/core/messages";
import { ChatPromptTemplate } from "@langchain/core/prompts";
import { StringOutputParser } from "@langchain/core/output_parsers";
import { ToolMessage } from "@langchain/core/messages";
import { z } from "zod";
import { createLogger } from "../utils/logger";

const logger = createLogger("LangGraphWorkflowsExamples");

// ============================================================================
// SECTION 1: BASIC GRAPH CREATION
// ============================================================================

/**
 * Example 1.1: Minimal Graph
 *
 * The simplest possible LangGraph - a single node that processes input.
 * This demonstrates the fundamental structure of a graph.
 */

// Define state using Annotation (LangGraph v0.2+ pattern)
const MinimalGraphState = Annotation.Root({
  input: Annotation<string>,
  output: Annotation<string>,
});

export async function example_1_1_minimalGraph(): Promise<string> {
  logger.info("Example 1.1: Minimal Graph");

  // Create the graph with typed state
  const graph = new StateGraph(MinimalGraphState)
    // Add a single node
    .addNode("process", async (state) => {
      return { output: `Processed: ${state.input.toUpperCase()}` };
    })
    // Define the flow
    .addEdge(START, "process")
    .addEdge("process", END);

  // Compile the graph
  const app = graph.compile();

  // Invoke the graph
  const result = await app.invoke({ input: "hello world" });

  logger.info("Minimal graph result", { output: result.output });

  return result.output;
}

/**
 * Example 1.2: Multi-Node Linear Graph
 *
 * A graph with multiple nodes that execute in sequence.
 * Data flows from one node to the next in a linear fashion.
 */

const LinearGraphState = Annotation.Root({
  text: Annotation<string>,
  wordCount: Annotation<number>,
  sentiment: Annotation<string>,
  summary: Annotation<string>,
});

export async function example_1_2_multiNodeLinearGraph(): Promise<{
  wordCount: number;
  sentiment: string;
  summary: string;
}> {
  logger.info("Example 1.2: Multi-Node Linear Graph");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  const graph = new StateGraph(LinearGraphState)
    // Node 1: Count words
    .addNode("countWords", async (state) => {
      const wordCount = state.text.split(/\s+/).length;
      return { wordCount };
    })
    // Node 2: Analyze sentiment
    .addNode("analyzeSentiment", async (state) => {
      const response = await model.invoke([
        new HumanMessage(
          `Analyze the sentiment of this text and respond with just one word (positive/negative/neutral): "${state.text}"`
        ),
      ]);
      return { sentiment: (response.content as string).toLowerCase().trim() };
    })
    // Node 3: Generate summary
    .addNode("generateSummary", async (state) => {
      const response = await model.invoke([
        new HumanMessage(
          `Summarize this text in one sentence: "${state.text}"`
        ),
      ]);
      return { summary: response.content as string };
    })
    // Define linear flow
    .addEdge(START, "countWords")
    .addEdge("countWords", "analyzeSentiment")
    .addEdge("analyzeSentiment", "generateSummary")
    .addEdge("generateSummary", END);

  const app = graph.compile();

  const result = await app.invoke({
    text: "I absolutely love this new feature! It makes my work so much easier and more enjoyable. Great job team!",
  });

  return {
    wordCount: result.wordCount,
    sentiment: result.sentiment,
    summary: result.summary,
  };
}

/**
 * Example 1.3: Graph with Shared State Updates
 *
 * Demonstrates how multiple nodes can read and update shared state.
 * Uses reducer functions to handle state updates properly.
 */

const SharedStateGraphState = Annotation.Root({
  messages: Annotation<BaseMessage[]>({
    reducer: (current, update) => [...current, ...update],
    default: () => [],
  }),
  metadata: Annotation<Record<string, any>>({
    reducer: (current, update) => ({ ...current, ...update }),
    default: () => ({}),
  }),
  currentStep: Annotation<string>({
    reducer: (_, update) => update,
    default: () => "start",
  }),
});

export async function example_1_3_sharedStateGraph(): Promise<{
  messages: BaseMessage[];
  metadata: Record<string, any>;
}> {
  logger.info("Example 1.3: Shared State Graph");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  const graph = new StateGraph(SharedStateGraphState)
    .addNode("initialize", async (state) => {
      return {
        metadata: {
          startTime: new Date().toISOString(),
          source: "example",
        },
        currentStep: "initialized",
      };
    })
    .addNode("process", async (state) => {
      const lastMessage = state.messages[state.messages.length - 1];
      const response = await model.invoke([lastMessage]);

      return {
        messages: [response],
        currentStep: "processed",
      };
    })
    .addNode("finalize", async (state) => {
      return {
        metadata: {
          endTime: new Date().toISOString(),
          totalMessages: state.messages.length,
        },
        currentStep: "completed",
      };
    })
    .addEdge(START, "initialize")
    .addEdge("initialize", "process")
    .addEdge("process", "finalize")
    .addEdge("finalize", END);

  const app = graph.compile();

  const result = await app.invoke({
    messages: [new HumanMessage("Tell me a fun fact about dolphins.")],
  });

  return {
    messages: result.messages,
    metadata: result.metadata,
  };
}

// ============================================================================
// SECTION 2: CONDITIONAL ROUTING
// ============================================================================

/**
 * Example 2.1: Simple Conditional Edge
 *
 * Route to different nodes based on a condition.
 * This is the bread and butter of dynamic workflows.
 */

const ConditionalGraphState = Annotation.Root({
  query: Annotation<string>,
  queryType: Annotation<string>,
  response: Annotation<string>,
});

export async function example_2_1_simpleConditionalEdge(): Promise<string> {
  logger.info("Example 2.1: Simple Conditional Edge");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  const graph = new StateGraph(ConditionalGraphState)
    // Classify the query type
    .addNode("classify", async (state) => {
      const response = await model.invoke([
        new SystemMessage(
          "Classify the query as one of: question, command, statement. Respond with just the classification word."
        ),
        new HumanMessage(state.query),
      ]);
      return { queryType: (response.content as string).toLowerCase().trim() };
    })
    // Handle questions
    .addNode("handleQuestion", async (state) => {
      const response = await model.invoke([
        new SystemMessage("You are a helpful assistant. Answer the question concisely."),
        new HumanMessage(state.query),
      ]);
      return { response: response.content as string };
    })
    // Handle commands
    .addNode("handleCommand", async (state) => {
      return {
        response: `I understood your command: "${state.query}". In a real app, I would execute this.`,
      };
    })
    // Handle statements
    .addNode("handleStatement", async (state) => {
      return {
        response: `Thank you for sharing: "${state.query}". I've noted that.`,
      };
    })
    .addEdge(START, "classify")
    // Conditional routing based on classification
    .addConditionalEdges("classify", (state) => {
      switch (state.queryType) {
        case "question":
          return "handleQuestion";
        case "command":
          return "handleCommand";
        default:
          return "handleStatement";
      }
    })
    .addEdge("handleQuestion", END)
    .addEdge("handleCommand", END)
    .addEdge("handleStatement", END);

  const app = graph.compile();

  const result = await app.invoke({
    query: "What is the capital of Japan?",
  });

  return result.response;
}

/**
 * Example 2.2: Multi-path Conditional Routing
 *
 * More complex routing with multiple possible paths and conditions.
 */

const MultiPathState = Annotation.Root({
  userInput: Annotation<string>,
  userIntent: Annotation<string>,
  priority: Annotation<"low" | "medium" | "high">,
  response: Annotation<string>,
  escalated: Annotation<boolean>({
    default: () => false,
  }),
});

export async function example_2_2_multiPathRouting(): Promise<{
  response: string;
  escalated: boolean;
}> {
  logger.info("Example 2.2: Multi-path Conditional Routing");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  // Router function that returns the next node name
  function routeByIntentAndPriority(state: typeof MultiPathState.State): string {
    // High priority always goes to escalation
    if (state.priority === "high") {
      return "escalate";
    }

    // Route based on intent
    switch (state.userIntent) {
      case "billing":
        return "handleBilling";
      case "technical":
        return "handleTechnical";
      case "general":
        return "handleGeneral";
      default:
        return "handleUnknown";
    }
  }

  const graph = new StateGraph(MultiPathState)
    .addNode("analyze", async (state) => {
      const response = await model.invoke([
        new SystemMessage(
          `Analyze this customer message and respond in JSON format:
           {"intent": "billing|technical|general|unknown", "priority": "low|medium|high"}
           Only respond with the JSON, nothing else.`
        ),
        new HumanMessage(state.userInput),
      ]);

      try {
        const analysis = JSON.parse(response.content as string);
        return {
          userIntent: analysis.intent,
          priority: analysis.priority,
        };
      } catch {
        return { userIntent: "unknown", priority: "low" as const };
      }
    })
    .addNode("handleBilling", async (state) => ({
      response: "Connecting you to our billing department. They can help with payments, invoices, and subscription questions.",
    }))
    .addNode("handleTechnical", async (state) => ({
      response: "Our technical support team will assist you with any product issues or bugs.",
    }))
    .addNode("handleGeneral", async (state) => ({
      response: "I'd be happy to help with your general inquiry!",
    }))
    .addNode("handleUnknown", async (state) => ({
      response: "I'm not sure I understood. Could you please rephrase your question?",
    }))
    .addNode("escalate", async (state) => ({
      response: "This has been marked as high priority. A senior representative will contact you within 1 hour.",
      escalated: true,
    }))
    .addEdge(START, "analyze")
    .addConditionalEdges("analyze", routeByIntentAndPriority)
    .addEdge("handleBilling", END)
    .addEdge("handleTechnical", END)
    .addEdge("handleGeneral", END)
    .addEdge("handleUnknown", END)
    .addEdge("escalate", END);

  const app = graph.compile();

  const result = await app.invoke({
    userInput: "URGENT! My payment was charged twice and I need a refund immediately!",
  });

  return {
    response: result.response,
    escalated: result.escalated,
  };
}

/**
 * Example 2.3: Conditional Edge with Map (Multiple Targets)
 *
 * Using a map to define all possible routing destinations explicitly.
 */

const TaskRouterState = Annotation.Root({
  task: Annotation<string>,
  taskCategory: Annotation<string>,
  result: Annotation<string>,
});

export async function example_2_3_conditionalWithMap(): Promise<string> {
  logger.info("Example 2.3: Conditional Edge with Map");

  const graph = new StateGraph(TaskRouterState)
    .addNode("categorize", async (state) => {
      const categories = ["math", "writing", "coding", "other"];
      const task = state.task.toLowerCase();

      let category = "other";
      if (task.includes("calculate") || task.includes("math") || task.includes("number")) {
        category = "math";
      } else if (task.includes("write") || task.includes("essay") || task.includes("story")) {
        category = "writing";
      } else if (task.includes("code") || task.includes("program") || task.includes("function")) {
        category = "coding";
      }

      return { taskCategory: category };
    })
    .addNode("mathTask", async (state) => ({
      result: `[Math Agent] Processing mathematical task: ${state.task}`,
    }))
    .addNode("writingTask", async (state) => ({
      result: `[Writing Agent] Processing writing task: ${state.task}`,
    }))
    .addNode("codingTask", async (state) => ({
      result: `[Coding Agent] Processing coding task: ${state.task}`,
    }))
    .addNode("generalTask", async (state) => ({
      result: `[General Agent] Processing task: ${state.task}`,
    }))
    .addEdge(START, "categorize")
    // Use explicit map for routing
    .addConditionalEdges(
      "categorize",
      (state) => state.taskCategory,
      {
        math: "mathTask",
        writing: "writingTask",
        coding: "codingTask",
        other: "generalTask",
      }
    )
    .addEdge("mathTask", END)
    .addEdge("writingTask", END)
    .addEdge("codingTask", END)
    .addEdge("generalTask", END);

  const app = graph.compile();

  const result = await app.invoke({
    task: "Write a function to calculate fibonacci numbers",
  });

  return result.result;
}

// ============================================================================
// SECTION 3: CYCLES AND LOOPS
// ============================================================================

/**
 * Example 3.1: Simple Loop with Counter
 *
 * A graph that loops until a condition is met.
 * Essential for iterative refinement patterns.
 */

const LoopCounterState = Annotation.Root({
  value: Annotation<number>,
  iterations: Annotation<number>({
    default: () => 0,
  }),
  maxIterations: Annotation<number>({
    default: () => 5,
  }),
  history: Annotation<number[]>({
    reducer: (current, update) => [...current, ...update],
    default: () => [],
  }),
});

export async function example_3_1_simpleLoopWithCounter(): Promise<{
  finalValue: number;
  iterations: number;
  history: number[];
}> {
  logger.info("Example 3.1: Simple Loop with Counter");

  const graph = new StateGraph(LoopCounterState)
    .addNode("process", async (state) => {
      // Double the value each iteration
      const newValue = state.value * 2;
      return {
        value: newValue,
        iterations: state.iterations + 1,
        history: [newValue],
      };
    })
    .addEdge(START, "process")
    .addConditionalEdges("process", (state) => {
      // Continue looping until max iterations reached
      if (state.iterations < state.maxIterations) {
        return "process"; // Loop back
      }
      return END;
    });

  const app = graph.compile();

  const result = await app.invoke({
    value: 1,
    maxIterations: 5,
  });

  return {
    finalValue: result.value,
    iterations: result.iterations,
    history: result.history,
  };
}

/**
 * Example 3.2: Iterative Refinement Loop
 *
 * A common pattern where output is refined until it meets quality criteria.
 */

const RefinementState = Annotation.Root({
  task: Annotation<string>,
  currentDraft: Annotation<string>({
    default: () => "",
  }),
  feedback: Annotation<string>({
    default: () => "",
  }),
  qualityScore: Annotation<number>({
    default: () => 0,
  }),
  refinementCount: Annotation<number>({
    default: () => 0,
  }),
  maxRefinements: Annotation<number>({
    default: () => 3,
  }),
});

export async function example_3_2_iterativeRefinement(): Promise<{
  finalDraft: string;
  refinements: number;
  finalScore: number;
}> {
  logger.info("Example 3.2: Iterative Refinement Loop");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  const graph = new StateGraph(RefinementState)
    // Generate or refine the draft
    .addNode("generate", async (state) => {
      let prompt: string;

      if (state.currentDraft === "") {
        // First generation
        prompt = `Write a short paragraph about: ${state.task}`;
      } else {
        // Refinement based on feedback
        prompt = `Improve this text based on the feedback.

                  Current text: ${state.currentDraft}

                  Feedback: ${state.feedback}

                  Write an improved version:`;
      }

      const response = await model.invoke([new HumanMessage(prompt)]);

      return {
        currentDraft: response.content as string,
        refinementCount: state.refinementCount + 1,
      };
    })
    // Evaluate the quality
    .addNode("evaluate", async (state) => {
      const response = await model.invoke([
        new SystemMessage(
          "You are a strict editor. Rate the text quality from 1-10 and provide brief feedback. " +
          "Respond in JSON format: {\"score\": number, \"feedback\": string}"
        ),
        new HumanMessage(`Evaluate this text:\n\n${state.currentDraft}`),
      ]);

      try {
        const evaluation = JSON.parse(response.content as string);
        return {
          qualityScore: evaluation.score,
          feedback: evaluation.feedback,
        };
      } catch {
        return {
          qualityScore: 5,
          feedback: "Could not parse evaluation, please try again.",
        };
      }
    })
    .addEdge(START, "generate")
    .addEdge("generate", "evaluate")
    .addConditionalEdges("evaluate", (state) => {
      // Stop if quality is good enough or max refinements reached
      if (state.qualityScore >= 8 || state.refinementCount >= state.maxRefinements) {
        return END;
      }
      // Loop back for another refinement
      return "generate";
    });

  const app = graph.compile();

  const result = await app.invoke({
    task: "The importance of clean code in software development",
    maxRefinements: 3,
  });

  return {
    finalDraft: result.currentDraft,
    refinements: result.refinementCount,
    finalScore: result.qualityScore,
  };
}

/**
 * Example 3.3: Agent Loop with Tool Execution
 *
 * The classic ReAct pattern - reason, act, observe, repeat.
 */

const AgentLoopState = Annotation.Root({
  messages: Annotation<BaseMessage[]>({
    reducer: (current, update) => [...current, ...update],
    default: () => [],
  }),
  pendingToolCalls: Annotation<any[]>({
    default: () => [],
  }),
  iterationCount: Annotation<number>({
    default: () => 0,
  }),
  maxIterations: Annotation<number>({
    default: () => 10,
  }),
});

// Simulated tools for the example
const simulatedTools = {
  calculator: async (expression: string): Promise<string> => {
    try {
      // Simple safe eval for basic math
      const result = Function(`"use strict"; return (${expression})`)();
      return `Result: ${result}`;
    } catch {
      return "Error: Could not evaluate expression";
    }
  },
  weather: async (city: string): Promise<string> => {
    // Simulated weather data
    const weatherData: Record<string, string> = {
      "new york": "72°F, Partly Cloudy",
      "london": "59°F, Rainy",
      "tokyo": "68°F, Sunny",
    };
    return weatherData[city.toLowerCase()] || "Weather data not available";
  },
};

export async function example_3_3_agentLoopWithTools(): Promise<{
  messages: BaseMessage[];
  iterations: number;
}> {
  logger.info("Example 3.3: Agent Loop with Tool Execution");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
  }).bind({
    tools: [
      {
        type: "function",
        function: {
          name: "calculator",
          description: "Perform mathematical calculations",
          parameters: {
            type: "object",
            properties: {
              expression: {
                type: "string",
                description: "The mathematical expression to evaluate",
              },
            },
            required: ["expression"],
          },
        },
      },
      {
        type: "function",
        function: {
          name: "weather",
          description: "Get weather for a city",
          parameters: {
            type: "object",
            properties: {
              city: {
                type: "string",
                description: "The city name",
              },
            },
            required: ["city"],
          },
        },
      },
    ],
  });

  const graph = new StateGraph(AgentLoopState)
    // Agent node - decides what to do
    .addNode("agent", async (state) => {
      const response = await model.invoke(state.messages);
      const toolCalls = response.tool_calls || [];

      return {
        messages: [response],
        pendingToolCalls: toolCalls,
        iterationCount: state.iterationCount + 1,
      };
    })
    // Tool execution node
    .addNode("tools", async (state) => {
      const toolMessages: ToolMessage[] = [];

      for (const toolCall of state.pendingToolCalls) {
        let result: string;

        if (toolCall.name === "calculator") {
          result = await simulatedTools.calculator(toolCall.args.expression);
        } else if (toolCall.name === "weather") {
          result = await simulatedTools.weather(toolCall.args.city);
        } else {
          result = "Unknown tool";
        }

        toolMessages.push(
          new ToolMessage({
            content: result,
            tool_call_id: toolCall.id,
          })
        );
      }

      return {
        messages: toolMessages,
        pendingToolCalls: [],
      };
    })
    .addEdge(START, "agent")
    .addConditionalEdges("agent", (state) => {
      // Check iteration limit
      if (state.iterationCount >= state.maxIterations) {
        return END;
      }

      // If there are tool calls, execute them
      if (state.pendingToolCalls.length > 0) {
        return "tools";
      }

      // No tool calls = agent is done
      return END;
    })
    .addEdge("tools", "agent"); // After tools, go back to agent

  const app = graph.compile();

  const result = await app.invoke({
    messages: [
      new HumanMessage(
        "What's 15 * 7 + 23? Also, what's the weather in Tokyo?"
      ),
    ],
    maxIterations: 5,
  });

  return {
    messages: result.messages,
    iterations: result.iterationCount,
  };
}

// ============================================================================
// SECTION 4: PARALLEL EXECUTION
// ============================================================================

/**
 * Example 4.1: Parallel Node Execution with Fan-out/Fan-in
 *
 * Execute multiple nodes in parallel and combine their results.
 */

const ParallelAnalysisState = Annotation.Root({
  text: Annotation<string>,
  sentimentResult: Annotation<string>({
    default: () => "",
  }),
  keywordsResult: Annotation<string[]>({
    default: () => [],
  }),
  summaryResult: Annotation<string>({
    default: () => "",
  }),
  combinedAnalysis: Annotation<string>({
    default: () => "",
  }),
});

export async function example_4_1_parallelFanOutFanIn(): Promise<{
  sentiment: string;
  keywords: string[];
  summary: string;
  combined: string;
}> {
  logger.info("Example 4.1: Parallel Fan-out/Fan-in");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  const graph = new StateGraph(ParallelAnalysisState)
    // Parallel analysis nodes
    .addNode("analyzeSentiment", async (state) => {
      const response = await model.invoke([
        new HumanMessage(
          `Analyze the sentiment of this text. Respond with just: positive, negative, or neutral.\n\nText: ${state.text}`
        ),
      ]);
      return { sentimentResult: (response.content as string).trim() };
    })
    .addNode("extractKeywords", async (state) => {
      const response = await model.invoke([
        new HumanMessage(
          `Extract 5 key words from this text. Respond with just the words separated by commas.\n\nText: ${state.text}`
        ),
      ]);
      const keywords = (response.content as string).split(",").map((k) => k.trim());
      return { keywordsResult: keywords };
    })
    .addNode("generateSummary", async (state) => {
      const response = await model.invoke([
        new HumanMessage(
          `Summarize this text in one sentence.\n\nText: ${state.text}`
        ),
      ]);
      return { summaryResult: response.content as string };
    })
    // Fan-in node - combines all results
    .addNode("combineResults", async (state) => {
      const combined = `
        Analysis Complete:
        - Sentiment: ${state.sentimentResult}
        - Keywords: ${state.keywordsResult.join(", ")}
        - Summary: ${state.summaryResult}
      `.trim();
      return { combinedAnalysis: combined };
    })
    // Fan-out: START goes to all analysis nodes
    .addEdge(START, "analyzeSentiment")
    .addEdge(START, "extractKeywords")
    .addEdge(START, "generateSummary")
    // Fan-in: all analysis nodes go to combine
    .addEdge("analyzeSentiment", "combineResults")
    .addEdge("extractKeywords", "combineResults")
    .addEdge("generateSummary", "combineResults")
    .addEdge("combineResults", END);

  const app = graph.compile();

  const result = await app.invoke({
    text: `Artificial intelligence is revolutionizing healthcare by enabling faster
           diagnosis, personalized treatment plans, and drug discovery. Machine learning
           algorithms can analyze medical images with remarkable accuracy, sometimes
           outperforming human doctors. However, concerns about data privacy and the
           need for human oversight remain important considerations.`,
  });

  return {
    sentiment: result.sentimentResult,
    keywords: result.keywordsResult,
    summary: result.summaryResult,
    combined: result.combinedAnalysis,
  };
}

/**
 * Example 4.2: Dynamic Parallel Execution
 *
 * Execute tasks in parallel based on dynamic input.
 */

const DynamicParallelState = Annotation.Root({
  questions: Annotation<string[]>,
  answers: Annotation<Record<string, string>>({
    reducer: (current, update) => ({ ...current, ...update }),
    default: () => ({}),
  }),
  completed: Annotation<boolean>({
    default: () => false,
  }),
});

export async function example_4_2_dynamicParallelExecution(): Promise<Record<string, string>> {
  logger.info("Example 4.2: Dynamic Parallel Execution");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  const graph = new StateGraph(DynamicParallelState)
    .addNode("processQuestions", async (state) => {
      // Process all questions in parallel using Promise.all
      const answerPromises = state.questions.map(async (question) => {
        const response = await model.invoke([
          new HumanMessage(`Answer briefly: ${question}`),
        ]);
        return { question, answer: response.content as string };
      });

      const results = await Promise.all(answerPromises);

      const answers: Record<string, string> = {};
      for (const result of results) {
        answers[result.question] = result.answer;
      }

      return {
        answers,
        completed: true,
      };
    })
    .addEdge(START, "processQuestions")
    .addEdge("processQuestions", END);

  const app = graph.compile();

  const result = await app.invoke({
    questions: [
