/**
 * ============================================================================
 * 04 - MEMORY AND STATE MANAGEMENT EXAMPLES
 * ============================================================================
 *
 * This file contains comprehensive examples of memory and state management
 * patterns in LangChain and LangGraph applications. Proper memory management
 * is crucial for building conversational AI systems that can maintain context.
 *
 * Topics covered:
 * - Conversation buffer memory
 * - Conversation summary memory
 * - Token-based memory limits
 * - Entity memory
 * - LangGraph state persistence
 * - Checkpointing and recovery
 * - Session management patterns
 * - Memory with different storage backends
 * - Hybrid memory strategies
 * - Memory compression techniques
 *
 * @author OmniMind Team
 * @version 1.0.0
 */

import { ChatOpenAI } from "@langchain/openai";
import {
  HumanMessage,
  AIMessage,
  SystemMessage,
  BaseMessage,
  trimMessages,
} from "@langchain/core/messages";
import { ChatPromptTemplate, MessagesPlaceholder } from "@langchain/core/prompts";
import { StringOutputParser } from "@langchain/core/output_parsers";
import { RunnableWithMessageHistory, RunnablePassthrough } from "@langchain/core/runnables";
import { StateGraph, END, START, Annotation, MemorySaver } from "@langchain/langgraph";
import { InMemoryChatMessageHistory } from "@langchain/core/chat_history";
import { z } from "zod";
import { createLogger } from "../utils/logger";

const logger = createLogger("MemoryAndStateExamples");

// ============================================================================
// SECTION 1: BASIC CONVERSATION MEMORY
// ============================================================================

/**
 * Example 1.1: In-Memory Chat History
 *
 * The simplest form of memory - keeping messages in an array.
 * Suitable for single-session applications or development.
 */

// Global message stores (simulating a session store)
const messageStores: Record<string, InMemoryChatMessageHistory> = {};

function getMessageHistory(sessionId: string): InMemoryChatMessageHistory {
  if (!messageStores[sessionId]) {
    messageStores[sessionId] = new InMemoryChatMessageHistory();
  }
  return messageStores[sessionId];
}

export async function example_1_1_basicChatHistory(): Promise<{
  responses: string[];
  history: BaseMessage[];
}> {
  logger.info("Example 1.1: Basic Chat History");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0.7,
  });

  const prompt = ChatPromptTemplate.fromMessages([
    ["system", "You are a helpful assistant. Remember details from our conversation."],
    new MessagesPlaceholder("history"),
    ["human", "{input}"],
  ]);

  const chain = prompt.pipe(model).pipe(new StringOutputParser());

  // Wrap chain with message history
  const chainWithHistory = new RunnableWithMessageHistory({
    runnable: chain,
    getMessageHistory,
    inputMessagesKey: "input",
    historyMessagesKey: "history",
  });

  const sessionId = `session-${Date.now()}`;
  const config = { configurable: { sessionId } };

  const responses: string[] = [];

  // Turn 1: Introduction
  const response1 = await chainWithHistory.invoke(
    { input: "Hi! My name is Alex and I'm a software developer." },
    config
  );
  responses.push(response1);

  // Turn 2: Follow-up that requires memory
  const response2 = await chainWithHistory.invoke(
    { input: "What programming languages do you recommend for my profession?" },
    config
  );
  responses.push(response2);

  // Turn 3: Test memory recall
  const response3 = await chainWithHistory.invoke(
    { input: "Can you remind me what my name is and what I do?" },
    config
  );
  responses.push(response3);

  // Get the full history
  const history = await getMessageHistory(sessionId).getMessages();

  return { responses, history };
}

/**
 * Example 1.2: Conversation Buffer with Window
 *
 * Keep only the last N messages to prevent context overflow.
 * Essential for long conversations.
 */
export async function example_1_2_windowedMemory(): Promise<{
  response: string;
  keptMessages: number;
  trimmedMessages: number;
}> {
  logger.info("Example 1.2: Windowed Memory");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  // Simulate a long conversation history
  const fullHistory: BaseMessage[] = [];
  for (let i = 1; i <= 20; i++) {
    fullHistory.push(new HumanMessage(`This is message number ${i} from the user.`));
    fullHistory.push(new AIMessage(`This is response number ${i} from the assistant.`));
  }

  // Trim to keep only last 6 messages (3 exchanges)
  const windowSize = 6;
  const trimmedHistory = await trimMessages(fullHistory, {
    maxTokens: 1000, // Fallback to token limit
    strategy: "last",
    tokenCounter: (msgs) => msgs.length, // Simple counter for demo
    allowPartial: false,
  });

  // Alternative: Simple slice approach
  const simpleWindowedHistory = fullHistory.slice(-windowSize);

  const prompt = ChatPromptTemplate.fromMessages([
    ["system", "You are a helpful assistant. Summarize what you know from our conversation."],
    new MessagesPlaceholder("history"),
    ["human", "{input}"],
  ]);

  const response = await prompt.pipe(model).pipe(new StringOutputParser()).invoke({
    history: simpleWindowedHistory,
    input: "What message numbers can you see in our conversation?",
  });

  return {
    response,
    keptMessages: simpleWindowedHistory.length,
    trimmedMessages: fullHistory.length - simpleWindowedHistory.length,
  };
}

/**
 * Example 1.3: Token-Limited Memory
 *
 * Limit memory based on token count to stay within model limits.
 */
export async function example_1_3_tokenLimitedMemory(): Promise<{
  originalTokens: number;
  trimmedTokens: number;
  response: string;
}> {
  logger.info("Example 1.3: Token Limited Memory");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  // Simulate history with varying message lengths
  const history: BaseMessage[] = [
    new HumanMessage("Tell me about the history of artificial intelligence."),
    new AIMessage(
      "Artificial Intelligence has a rich history dating back to the 1950s. " +
      "Alan Turing's 1950 paper 'Computing Machinery and Intelligence' laid the groundwork. " +
      "The field was formally founded at the Dartmouth Conference in 1956. " +
      "Early AI focused on symbolic reasoning and expert systems. " +
      "The 1980s saw the rise of machine learning, and deep learning emerged in the 2010s."
    ),
    new HumanMessage("What about neural networks specifically?"),
    new AIMessage(
      "Neural networks were inspired by biological neurons. The perceptron was invented in 1958. " +
      "Backpropagation, discovered in the 1980s, enabled training deep networks. " +
      "Convolutional Neural Networks revolutionized image recognition in 2012. " +
      "Transformers, introduced in 2017, transformed natural language processing. " +
      "Today, large language models like GPT use massive transformer architectures."
    ),
    new HumanMessage("How do transformers work?"),
    new AIMessage(
      "Transformers use self-attention mechanisms to process sequences in parallel. " +
      "Unlike RNNs, they can look at all positions simultaneously. " +
      "The attention mechanism computes relevance scores between all token pairs. " +
      "This enables capturing long-range dependencies efficiently."
    ),
  ];

  // Simple token estimation (in production, use tiktoken)
  const estimateTokens = (messages: BaseMessage[]): number => {
    return messages.reduce((total, msg) => {
      const content = typeof msg.content === "string" ? msg.content : JSON.stringify(msg.content);
      return total + Math.ceil(content.length / 4); // Rough estimate: 4 chars per token
    }, 0);
  };

  const originalTokens = estimateTokens(history);
  const maxTokens = 200;

  // Trim messages to fit within token limit
  const trimmedHistory = await trimMessages(history, {
    maxTokens,
    tokenCounter: (msgs) => estimateTokens(msgs),
    strategy: "last",
    startOn: "human", // Always start with a human message
    allowPartial: false,
  });

  const trimmedTokens = estimateTokens(trimmedHistory);

  const prompt = ChatPromptTemplate.fromMessages([
    ["system", "Continue the conversation based on the recent context."],
    new MessagesPlaceholder("history"),
    ["human", "{input}"],
  ]);

  const response = await prompt.pipe(model).pipe(new StringOutputParser()).invoke({
    history: trimmedHistory,
    input: "Can you summarize what we discussed?",
  });

  return {
    originalTokens,
    trimmedTokens,
    response,
  };
}

// ============================================================================
// SECTION 2: ADVANCED MEMORY PATTERNS
// ============================================================================

/**
 * Example 2.1: Conversation Summary Memory
 *
 * Summarize old conversation parts to maintain context while saving tokens.
 */

interface SummaryMemoryState {
  summary: string;
  recentMessages: BaseMessage[];
  maxRecentMessages: number;
}

export class ConversationSummaryMemory {
  private state: SummaryMemoryState;
  private model: ChatOpenAI;

  constructor(maxRecentMessages: number = 4) {
    this.state = {
      summary: "",
      recentMessages: [],
      maxRecentMessages,
    };
    this.model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview", temperature: 0 });
  }

  async addMessage(message: BaseMessage): Promise<void> {
    this.state.recentMessages.push(message);

    // When we exceed the limit, summarize older messages
    if (this.state.recentMessages.length > this.state.maxRecentMessages) {
      await this.compressMemory();
    }
  }

  private async compressMemory(): Promise<void> {
    // Take oldest messages to summarize
    const toSummarize = this.state.recentMessages.splice(
      0,
      this.state.recentMessages.length - this.state.maxRecentMessages
    );

    // Create summary prompt
    const summaryPrompt = `
Current summary: ${this.state.summary || "No previous summary."}

New conversation to incorporate:
${toSummarize.map((m) => `${m._getType()}: ${m.content}`).join("\n")}

Provide an updated summary that captures all important information:`;

    const response = await this.model.invoke([new HumanMessage(summaryPrompt)]);
    this.state.summary = response.content as string;

    logger.info("Memory compressed", { summaryLength: this.state.summary.length });
  }

  getContext(): { summary: string; recentMessages: BaseMessage[] } {
    return {
      summary: this.state.summary,
      recentMessages: [...this.state.recentMessages],
    };
  }

  async getFormattedHistory(): Promise<BaseMessage[]> {
    const messages: BaseMessage[] = [];

    if (this.state.summary) {
      messages.push(
        new SystemMessage(`Summary of earlier conversation: ${this.state.summary}`)
      );
    }

    messages.push(...this.state.recentMessages);

    return messages;
  }
}

export async function example_2_1_summaryMemory(): Promise<{
  finalSummary: string;
  recentCount: number;
  responses: string[];
}> {
  logger.info("Example 2.1: Summary Memory");

  const memory = new ConversationSummaryMemory(4);
  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });
  const responses: string[] = [];

  // Simulate a longer conversation
  const exchanges = [
    "Tell me about your favorite programming language.",
    "What makes it better than others?",
    "Can you give me a code example?",
    "What about its performance characteristics?",
    "How does the community support look?",
    "What are the main drawbacks?",
    "Should I learn it as a beginner?",
  ];

  for (const userMessage of exchanges) {
    // Add user message
    await memory.addMessage(new HumanMessage(userMessage));

    // Get formatted history
    const history = await memory.getFormattedHistory();

    // Generate response
    const prompt = ChatPromptTemplate.fromMessages([
      ["system", "You are a helpful programming assistant."],
      ...history.map((m) => [m._getType(), m.content] as [string, string]),
      ["human", "{input}"],
    ]);

    const response = await prompt.pipe(model).pipe(new StringOutputParser()).invoke({
      input: userMessage,
    });

    responses.push(response);

    // Add AI response to memory
    await memory.addMessage(new AIMessage(response));
  }

  const context = memory.getContext();

  return {
    finalSummary: context.summary,
    recentCount: context.recentMessages.length,
    responses,
  };
}

/**
 * Example 2.2: Entity Memory
 *
 * Extract and store information about specific entities mentioned in conversation.
 */

interface EntityInfo {
  name: string;
  type: string;
  attributes: Record<string, string>;
  lastMentioned: Date;
}

export class EntityMemory {
  private entities: Map<string, EntityInfo> = new Map();
  private model: ChatOpenAI;

  constructor() {
    this.model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview", temperature: 0 });
  }

  async extractEntities(message: string): Promise<EntityInfo[]> {
    const prompt = `
Extract entities from this message and return as JSON array:
[{"name": "entity name", "type": "person|place|organization|product|concept", "attributes": {"key": "value"}}]

Message: "${message}"

If no entities found, return: []
JSON only, no explanation:`;

    try {
      const response = await this.model.invoke([new HumanMessage(prompt)]);
      const entities = JSON.parse(response.content as string);
      return entities.map((e: any) => ({
        ...e,
        lastMentioned: new Date(),
      }));
    } catch {
      return [];
    }
  }

  async updateFromMessage(message: string): Promise<void> {
    const newEntities = await this.extractEntities(message);

    for (const entity of newEntities) {
      const existing = this.entities.get(entity.name.toLowerCase());
      if (existing) {
        // Merge attributes
        this.entities.set(entity.name.toLowerCase(), {
          ...existing,
          attributes: { ...existing.attributes, ...entity.attributes },
          lastMentioned: new Date(),
        });
      } else {
        this.entities.set(entity.name.toLowerCase(), entity);
      }
    }

    logger.info("Entities updated", { count: this.entities.size });
  }

  getEntity(name: string): EntityInfo | undefined {
    return this.entities.get(name.toLowerCase());
  }

  getAllEntities(): EntityInfo[] {
    return Array.from(this.entities.values());
  }

  getRelevantEntities(message: string): EntityInfo[] {
    const messageLower = message.toLowerCase();
    return this.getAllEntities().filter(
      (entity) => messageLower.includes(entity.name.toLowerCase())
    );
  }

  formatEntityContext(): string {
    if (this.entities.size === 0) return "";

    const lines = ["Known entities:"];
    for (const entity of this.entities.values()) {
      const attrs = Object.entries(entity.attributes)
        .map(([k, v]) => `${k}: ${v}`)
        .join(", ");
      lines.push(`- ${entity.name} (${entity.type}): ${attrs || "no details"}`);
    }
    return lines.join("\n");
  }
}

export async function example_2_2_entityMemory(): Promise<{
  entities: EntityInfo[];
  response: string;
}> {
  logger.info("Example 2.2: Entity Memory");

  const memory = new EntityMemory();
  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  // Simulate conversation with entity mentions
  const messages = [
    "I'm Sarah, a data scientist at TechCorp. I work with my colleague John on ML projects.",
    "TechCorp is based in San Francisco and has about 500 employees.",
    "John specializes in computer vision and has a PhD from MIT.",
    "We're currently working on a project called 'Vision AI' for healthcare.",
  ];

  for (const msg of messages) {
    await memory.updateFromMessage(msg);
  }

  // Get all entities
  const entities = memory.getAllEntities();

  // Use entity context in a response
  const entityContext = memory.formatEntityContext();

  const prompt = ChatPromptTemplate.fromMessages([
    [
      "system",
      `You are a helpful assistant with knowledge about the user and their context.

${entityContext}`,
    ],
    ["human", "{input}"],
  ]);

  const response = await prompt.pipe(model).pipe(new StringOutputParser()).invoke({
    input: "Can you summarize what you know about my team and our project?",
  });

  return { entities, response };
}

/**
 * Example 2.3: Hybrid Memory (Summary + Entity + Recent)
 *
 * Combine multiple memory strategies for comprehensive context.
 */

interface HybridMemoryContext {
  summary: string;
  entities: EntityInfo[];
  recentMessages: BaseMessage[];
}

export class HybridMemory {
  private summaryMemory: ConversationSummaryMemory;
  private entityMemory: EntityMemory;

  constructor(maxRecentMessages: number = 4) {
    this.summaryMemory = new ConversationSummaryMemory(maxRecentMessages);
    this.entityMemory = new EntityMemory();
  }

  async addUserMessage(content: string): Promise<void> {
    const message = new HumanMessage(content);
    await this.summaryMemory.addMessage(message);
    await this.entityMemory.updateFromMessage(content);
  }

  async addAIMessage(content: string): Promise<void> {
    const message = new AIMessage(content);
    await this.summaryMemory.addMessage(message);
    // Optionally extract entities from AI messages too
  }

  getContext(): HybridMemoryContext {
    const summaryContext = this.summaryMemory.getContext();
    return {
      summary: summaryContext.summary,
      entities: this.entityMemory.getAllEntities(),
      recentMessages: summaryContext.recentMessages,
    };
  }

  formatForPrompt(): string {
    const context = this.getContext();
    const parts: string[] = [];

    if (context.summary) {
      parts.push(`## Conversation Summary\n${context.summary}`);
    }

    if (context.entities.length > 0) {
      parts.push(`## Known Entities\n${this.entityMemory.formatEntityContext()}`);
    }

    return parts.join("\n\n");
  }
}

export async function example_2_3_hybridMemory(): Promise<{
  context: HybridMemoryContext;
  response: string;
}> {
  logger.info("Example 2.3: Hybrid Memory");

  const memory = new HybridMemory(4);
  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  // Simulate conversation
  const conversation = [
    { role: "user", content: "I'm planning a trip to Tokyo with my friend Emma next month." },
    { role: "ai", content: "That sounds exciting! Tokyo is a wonderful destination. How long will you be staying?" },
    { role: "user", content: "We'll be there for 10 days. Emma is really into Japanese cuisine." },
    { role: "ai", content: "10 days is great for Tokyo! With Emma's interest in cuisine, you should visit Tsukiji Outer Market." },
    { role: "user", content: "Perfect! We're staying at the Park Hyatt in Shinjuku." },
    { role: "ai", content: "The Park Hyatt is excellent and centrally located. Shinjuku has great nightlife too." },
  ];

  for (const msg of conversation) {
    if (msg.role === "user") {
      await memory.addUserMessage(msg.content);
    } else {
      await memory.addAIMessage(msg.content);
    }
  }

  const context = memory.getContext();
  const memoryContext = memory.formatForPrompt();

  const prompt = ChatPromptTemplate.fromMessages([
    [
      "system",
      `You are a helpful travel assistant. Use this context about the user:

${memoryContext}`,
    ],
    ["human", "{input}"],
  ]);

  const response = await prompt.pipe(model).pipe(new StringOutputParser()).invoke({
    input: "What restaurant recommendations do you have near our hotel?",
  });

  return { context, response };
}

// ============================================================================
// SECTION 3: LANGGRAPH STATE PERSISTENCE
// ============================================================================

/**
 * Example 3.1: LangGraph with MemorySaver
 *
 * Using built-in checkpointing for state persistence.
 */

const ChatbotState = Annotation.Root({
  messages: Annotation<BaseMessage[]>({
    reducer: (current, update) => [...current, ...update],
    default: () => [],
  }),
  userName: Annotation<string>({
    default: () => "",
  }),
  preferences: Annotation<Record<string, any>>({
    reducer: (current, update) => ({ ...current, ...update }),
    default: () => ({}),
  }),
});

export async function example_3_1_langGraphMemorySaver(): Promise<{
  conversation: BaseMessage[];
  preferences: Record<string, any>;
}> {
  logger.info("Example 3.1: LangGraph MemorySaver");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  // Create memory saver for persistence
  const memorySaver = new MemorySaver();

  const graph = new StateGraph(ChatbotState)
    .addNode("chat", async (state) => {
      const response = await model.invoke([
        new SystemMessage(
          `You are a helpful assistant. User's name: ${state.userName || "Unknown"}.
          Preferences: ${JSON.stringify(state.preferences)}`
        ),
        ...state.messages,
      ]);

      // Extract preferences from conversation (simplified)
      const lastMessage = state.messages[state.messages.length - 1];
      const content = lastMessage?.content?.toString().toLowerCase() || "";
      const newPrefs: Record<string, any> = {};

      if (content.includes("prefer") || content.includes("like")) {
        if (content.includes("dark mode")) newPrefs.theme = "dark";
        if (content.includes("light mode")) newPrefs.theme = "light";
        if (content.includes("formal")) newPrefs.tone = "formal";
        if (content.includes("casual")) newPrefs.tone = "casual";
      }

      return {
        messages: [response],
        preferences: newPrefs,
      };
    })
    .addEdge(START, "chat")
    .addEdge("chat", END);

  // Compile with checkpointer
  const app = graph.compile({ checkpointer: memorySaver });

  const threadId = `thread-${Date.now()}`;
  const config = { configurable: { thread_id: threadId } };

  // First conversation turn
  await app.invoke(
    {
      messages: [new HumanMessage("Hi! My name is Chris.")],
      userName: "Chris",
    },
    config
  );

  // Second turn - state persists
  await app.invoke(
    {
      messages: [new HumanMessage("I prefer dark mode and a casual tone.")],
    },
    config
  );

  // Third turn - references stored preferences
  const result = await app.invoke(
    {
      messages: [new HumanMessage("What are my preferences?")],
    },
    config
  );

  return {
    conversation: result.messages,
    preferences: result.preferences,
  };
}

/**
 * Example 3.2: Checkpointing with Recovery
 *
 * Save and restore conversation state for fault tolerance.
 */

const RecoverableState = Annotation.Root({
  messages: Annotation<BaseMessage[]>({
    reducer: (current, update) => [...current, ...update],
    default: () => [],
  }),
  checkpointData: Annotation<{
    lastCheckpoint: string;
    messageCount: number;
  }>({
    reducer: (_, update) => update,
    default: () => ({ lastCheckpoint: "", messageCount: 0 }),
  }),
  error: Annotation<string | null>({
    default: () => null,
  }),
});

export async function example_3_2_checkpointRecovery(): Promise<{
  recovered: boolean;
  messageCount: number;
  lastCheckpoint: string;
}> {
  logger.info("Example 3.2: Checkpoint Recovery");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });
  const memorySaver = new MemorySaver();

  const graph = new StateGraph(RecoverableState)
    .addNode("process", async (state) => {
      // Simulate potential failure
      if (Math.random() < 0.1) {
        throw new Error("Simulated failure");
      }

      const response = await model.invoke(state.messages);

      return {
        messages: [response],
        checkpointData: {
          lastCheckpoint: new Date().toISOString(),
          messageCount: state.messages.length + 1,
        },
      };
    })
    .addNode("handleError", async (state) => {
      logger.error("Handling error in graph", { error: state.error });
      return {
        messages: [new AIMessage("I encountered an issue. Let me try again.")],
        error: null,
      };
    })
    .addEdge(START, "process")
    .addConditionalEdges("process", (state) => {
      if (state.error) return "handleError";
      return END;
    })
    .addEdge("handleError", END);

  const app = graph.compile({ checkpointer: memorySaver });

  const threadId = `recovery-${Date.now()}`;
  const config = { configurable: { thread_id: threadId } };

  // Run multiple turns
  try {
    await app.invoke(
      {
        messages: [new HumanMessage("Hello!")],
      },
      config
    );

    const result = await app.invoke(
      {
        messages: [new HumanMessage("How are you?")],
      },
      config
    );

    return {
      recovered: false,
      messageCount: result.checkpointData.messageCount,
      lastCheckpoint: result.checkpointData.lastCheckpoint,
    };
  } catch (error) {
    // Recovery scenario - get last known state
    const states = await memorySaver.list(config);
    const lastState = states[0];

    return {
      recovered: true,
      messageCount: lastState?.checkpoint?.channel_values?.checkpointData?.messageCount || 0,
      lastCheckpoint: lastState?.checkpoint?.channel_values?.checkpointData?.lastCheckpoint || "none",
    };
  }
}

/**
 * Example 3.3: Multi-Thread State Management
 *
 * Managing multiple conversation threads/sessions.
 */

export class MultiThreadManager {
  private memorySaver: MemorySaver;
  private activeThreads: Map<string, { lastActivity: Date; metadata: any }>;

  constructor() {
    this.memorySaver = new MemorySaver();
    this.activeThreads = new Map();
  }

  createThread(userId: string, metadata?: any): string {
    const threadId = `${userId}-${Date.now()}`;
    this.activeThreads.set(threadId, {
      lastActivity: new Date(),
      metadata: metadata || {},
    });
    logger.info("Thread created", { threadId, userId });
    return threadId;
  }

  updateThreadActivity(threadId: string): void {
    const thread = this.activeThreads.get(threadId);
    if (thread) {
      thread.lastActivity = new Date();
    }
  }

  getActiveThreads(userId?: string): string[] {
    const threads: string[] = [];
    for (const [threadId, data] of this.activeThreads) {
      if (!userId || threadId.startsWith(userId)) {
        threads.push(threadId);
      }
    }
    return threads;
  }

  cleanupInactiveThreads(maxAgeMs: number = 3600000): number {
    const now = new Date();
    let cleaned = 0;

    for (const [threadId, data] of this.activeThreads) {
      if (now.getTime() - data.lastActivity.getTime() > maxAgeMs) {
        this.activeThreads.delete(threadId);
        cleaned++;
      }
    }

    logger.info("Cleaned up inactive threads", { count: cleaned });
    return cleaned;
  }

  getMemorySaver(): MemorySaver {
    return this.memorySaver;
  }
}

export async function example_3_3_multiThreadManagement(): Promise<{
  threads: string[];
  responses: Record<string, string>;
}> {
  logger.info("Example 3.3: Multi-Thread Management");

  const manager = new MultiThreadManager();
  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  const SimpleState = Annotation.Root({
    messages: Annotation<BaseMessage[]>({
      reducer: (current, update) => [...current, ...update],
      default: () => [],
    }),
  });

  const graph = new StateGraph(SimpleState)
    .addNode("chat", async (state) => {
      const response = await model.invoke(state.messages);
      return { messages: [response] };
    })
    .addEdge(START, "chat")
    .addEdge("chat", END);

  const app = graph.compile({ checkpointer: manager.getMemorySaver() });

  // Create threads for different users
  const thread1 = manager.createThread("user-1", { topic: "cooking" });
  const thread2 = manager.createThread("user-2", { topic: "coding" });
  const thread3 = manager.createThread("user-1", { topic: "travel" });

  const responses: Record<string, string> = {};

  // Interact with different threads
  const result1 = await app.invoke(
    { messages: [new HumanMessage("What's a good pasta recipe?")] },
    { configurable: { thread_id: thread1 } }
  );
  responses[thread1] = result1.messages[result1.messages
