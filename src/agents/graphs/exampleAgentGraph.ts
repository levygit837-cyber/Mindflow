import { StateGraph, END } from "@langchain/langgraph";
import { ChatOpenAI } from "@langchain/openai";
import { HumanMessage, AIMessage, BaseMessage } from "@langchain/core/messages";
import { config } from "../../config";
import { createLogger } from "../../utils/logger";

const logger = createLogger("ExampleAgentGraph");

/**
 * Define the state structure for our agent
 * This represents the data that flows through the graph
 */
export interface AgentState {
  messages: BaseMessage[];
  currentStep: string;
  context?: Record<string, any>;
  error?: string;
}

/**
 * Node: Process user input and prepare for analysis
 */
async function inputProcessorNode(state: AgentState): Promise<Partial<AgentState>> {
  logger.info("Processing input...");

  const lastMessage = state.messages[state.messages.length - 1];

  return {
    currentStep: "input_processed",
    context: {
      ...state.context,
      processedAt: new Date().toISOString(),
      inputLength: lastMessage.content.toString().length,
    },
  };
}

/**
 * Node: Analyze the input using LLM
 */
async function analyzerNode(state: AgentState): Promise<Partial<AgentState>> {
  logger.info("Analyzing input with LLM...");

  try {
    const model = new ChatOpenAI({
      modelName: config.agent.defaultModel,
      temperature: config.agent.defaultTemperature,
      maxTokens: config.agent.maxTokens,
      apiKey: config.apiKeys.openai,
    });

    const response = await model.invoke(state.messages);

    return {
      messages: [...state.messages, response],
      currentStep: "analyzed",
      context: {
        ...state.context,
        analyzedAt: new Date().toISOString(),
      },
    };
  } catch (error: any) {
    logger.error("Error in analyzer node", { error: error.message });
    return {
      currentStep: "error",
      error: error.message,
    };
  }
}

/**
 * Node: Post-process the response
 */
async function postProcessorNode(state: AgentState): Promise<Partial<AgentState>> {
  logger.info("Post-processing response...");

  return {
    currentStep: "completed",
    context: {
      ...state.context,
      completedAt: new Date().toISOString(),
      totalMessages: state.messages.length,
    },
  };
}

/**
 * Conditional edge: Decide next step based on state
 */
function shouldContinue(state: AgentState): string {
  if (state.error) {
    return "error";
  }

  if (state.currentStep === "analyzed") {
    return "postprocess";
  }

  return END;
}

/**
 * Build and configure the agent graph
 */
export function createExampleAgentGraph() {
  logger.info("Creating example agent graph...");

  // Define the graph
  const workflow = new StateGraph<AgentState>({
    channels: {
      messages: {
        value: (x: BaseMessage[], y: BaseMessage[]) => x.concat(y),
        default: () => [],
      },
      currentStep: {
        value: (x?: string, y?: string) => y ?? x ?? "start",
        default: () => "start",
      },
      context: {
        value: (x?: Record<string, any>, y?: Record<string, any>) => ({ ...x, ...y }),
        default: () => ({}),
      },
      error: {
        value: (x?: string, y?: string) => y ?? x,
        default: () => undefined,
      },
    },
  });

  // Add nodes to the graph
  workflow.addNode("input_processor", inputProcessorNode);
  workflow.addNode("analyzer", analyzerNode);
  workflow.addNode("postprocessor", postProcessorNode);

  // Define the edges (flow between nodes)
  workflow.addEdge("input_processor", "analyzer");
  workflow.addConditionalEdges(
    "analyzer",
    shouldContinue,
    {
      postprocess: "postprocessor",
      error: END,
    }
  );
  workflow.addEdge("postprocessor", END);

  // Set the entry point
  workflow.setEntryPoint("input_processor");

  // Compile the graph
  const app = workflow.compile();

  logger.info("Example agent graph created successfully");

  return app;
}

/**
 * Helper function to invoke the agent with a message
 */
export async function invokeExampleAgent(userMessage: string): Promise<AgentState> {
  const graph = createExampleAgentGraph();

  const initialState: AgentState = {
    messages: [new HumanMessage(userMessage)],
    currentStep: "start",
    context: {},
  };

  logger.info("Invoking example agent", { message: userMessage });

  const result = await graph.invoke(initialState);

  logger.info("Agent invocation completed", {
    finalStep: result.currentStep,
    messageCount: result.messages.length
  });

  return result;
}

/**
 * Helper function to stream agent responses
 */
export async function* streamExampleAgent(userMessage: string): AsyncGenerator<Partial<AgentState>> {
  const graph = createExampleAgentGraph();

  const initialState: AgentState = {
    messages: [new HumanMessage(userMessage)],
    currentStep: "start",
    context: {},
  };

  logger.info("Streaming example agent", { message: userMessage });

  for await (const chunk of await graph.stream(initialState)) {
    yield chunk;
  }

  logger.info("Agent streaming completed");
}
