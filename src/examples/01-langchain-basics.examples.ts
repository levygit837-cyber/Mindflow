/**
 * ============================================================================
 * 01 - LANGCHAIN BASICS EXAMPLES
 * ============================================================================
 *
 * This file contains comprehensive examples of LangChain fundamentals.
 * Each example is self-contained and demonstrates a specific concept.
 *
 * Topics covered:
 * - Basic LLM invocations
 * - Chat models and message types
 * - Prompt templates
 * - Output parsers
 * - Simple chains
 * - Streaming responses
 * - Error handling patterns
 * - Multiple model providers
 *
 * @author OmniMind Team
 * @version 1.0.0
 */

import { ChatOpenAI } from "@langchain/openai";
import { ChatAnthropic } from "@langchain/anthropic";
import {
  HumanMessage,
  AIMessage,
  SystemMessage,
  BaseMessage,
} from "@langchain/core/messages";
import {
  ChatPromptTemplate,
  HumanMessagePromptTemplate,
  SystemMessagePromptTemplate,
  MessagesPlaceholder,
} from "@langchain/core/prompts";
import {
  StringOutputParser,
  JsonOutputParser,
} from "@langchain/core/output_parsers";
import { StructuredOutputParser } from "langchain/output_parsers";
import { RunnableSequence, RunnablePassthrough } from "@langchain/core/runnables";
import { z } from "zod";
import { createLogger } from "../utils/logger";

const logger = createLogger("LangChainBasicsExamples");

// ============================================================================
// SECTION 1: BASIC LLM INVOCATIONS
// ============================================================================

/**
 * Example 1.1: Simple Chat Model Invocation
 *
 * The most basic way to use a chat model - just send a message and get a response.
 * This is the foundation of all LLM interactions.
 */
export async function example_1_1_simpleChatInvocation(): Promise<string> {
  logger.info("Example 1.1: Simple Chat Invocation");

  // Initialize the model with basic configuration
  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0.7, // Controls randomness (0 = deterministic, 2 = very random)
  });

  // Create a simple human message
  const message = new HumanMessage("What is the capital of France?");

  // Invoke the model and get the response
  const response = await model.invoke([message]);

  logger.info("Response received", { content: response.content });

  return response.content as string;
}

/**
 * Example 1.2: Chat with System Message
 *
 * System messages set the behavior and context for the AI assistant.
 * They're like giving instructions to the AI before the conversation starts.
 */
export async function example_1_2_chatWithSystemMessage(): Promise<string> {
  logger.info("Example 1.2: Chat with System Message");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0.3,
  });

  // System message defines the AI's personality and constraints
  const messages: BaseMessage[] = [
    new SystemMessage(
      "You are a helpful assistant that specializes in explaining complex topics " +
      "in simple terms. Always use analogies and examples. Keep responses concise."
    ),
    new HumanMessage("Explain quantum entanglement to a 10-year-old."),
  ];

  const response = await model.invoke(messages);

  return response.content as string;
}

/**
 * Example 1.3: Multi-turn Conversation
 *
 * Chat models can handle conversation history, allowing for context-aware responses.
 * Each message in the array represents a turn in the conversation.
 */
export async function example_1_3_multiTurnConversation(): Promise<string> {
  logger.info("Example 1.3: Multi-turn Conversation");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0.7,
  });

  // Build a conversation history
  const conversationHistory: BaseMessage[] = [
    new SystemMessage("You are a cooking assistant. Be friendly and helpful."),
    new HumanMessage("I want to make pasta tonight."),
    new AIMessage(
      "Great choice! What type of pasta dish are you thinking? " +
      "I can help with anything from a simple aglio e olio to a creamy carbonara."
    ),
    new HumanMessage("Let's do carbonara. What ingredients do I need?"),
    new AIMessage(
      "For authentic carbonara, you'll need: spaghetti (400g), guanciale or pancetta (200g), " +
      "eggs (4 whole + 2 yolks), Pecorino Romano cheese (100g), black pepper, and salt. " +
      "Would you like me to walk you through the steps?"
    ),
    new HumanMessage("Yes, but I don't have guanciale. Can I use bacon?"),
  ];

  const response = await model.invoke(conversationHistory);

  return response.content as string;
}

/**
 * Example 1.4: Adjusting Model Parameters
 *
 * Different parameters affect the model's output in various ways.
 * Understanding these helps you get the right response for your use case.
 */
export async function example_1_4_modelParameters(): Promise<{
  creative: string;
  precise: string;
  balanced: string;
}> {
  logger.info("Example 1.4: Model Parameters Comparison");

  const prompt = "Write a one-sentence tagline for a coffee shop.";

  // Creative/Random - High temperature
  const creativeModel = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 1.5, // Very creative/random
    maxTokens: 50,
  });

  // Precise/Deterministic - Low temperature
  const preciseModel = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0, // Deterministic
    maxTokens: 50,
  });

  // Balanced - Medium temperature
  const balancedModel = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0.5,
    maxTokens: 50,
  });

  const [creative, precise, balanced] = await Promise.all([
    creativeModel.invoke([new HumanMessage(prompt)]),
    preciseModel.invoke([new HumanMessage(prompt)]),
    balancedModel.invoke([new HumanMessage(prompt)]),
  ]);

  return {
    creative: creative.content as string,
    precise: precise.content as string,
    balanced: balanced.content as string,
  };
}

// ============================================================================
// SECTION 2: PROMPT TEMPLATES
// ============================================================================

/**
 * Example 2.1: Basic Prompt Template
 *
 * Prompt templates allow you to create reusable prompts with placeholders.
 * They're like function templates - define once, use many times with different values.
 */
export async function example_2_1_basicPromptTemplate(): Promise<string> {
  logger.info("Example 2.1: Basic Prompt Template");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  // Create a prompt template with a placeholder
  const promptTemplate = ChatPromptTemplate.fromMessages([
    ["system", "You are a helpful translator. Translate text accurately."],
    ["human", "Translate the following {source_language} text to {target_language}: {text}"],
  ]);

  // Format the prompt with actual values
  const formattedPrompt = await promptTemplate.formatMessages({
    source_language: "English",
    target_language: "Spanish",
    text: "Hello, how are you today?",
  });

  const response = await model.invoke(formattedPrompt);

  return response.content as string;
}

/**
 * Example 2.2: Complex Prompt Template with Multiple Variables
 *
 * Templates can have multiple variables and complex structures.
 * This is useful for creating sophisticated, reusable prompts.
 */
export async function example_2_2_complexPromptTemplate(): Promise<string> {
  logger.info("Example 2.2: Complex Prompt Template");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  // Create a complex prompt template for code review
  const codeReviewTemplate = ChatPromptTemplate.fromMessages([
    SystemMessagePromptTemplate.fromTemplate(
      `You are an expert {language} developer performing a code review.
       Focus on: {focus_areas}
       Severity levels: critical, warning, suggestion
       Be constructive and provide examples when suggesting improvements.`
    ),
    HumanMessagePromptTemplate.fromTemplate(
      `Please review the following {language} code:

       \`\`\`{language}
       {code}
       \`\`\`

       Context: {context}`
    ),
  ]);

  const formattedPrompt = await codeReviewTemplate.formatMessages({
    language: "TypeScript",
    focus_areas: "type safety, error handling, performance",
    code: `
      async function fetchUser(id) {
        const response = await fetch('/api/users/' + id);
        return response.json();
      }
    `,
    context: "This function is called frequently in a high-traffic web application.",
  });

  const response = await model.invoke(formattedPrompt);

  return response.content as string;
}

/**
 * Example 2.3: Prompt Template with Conversation History
 *
 * MessagesPlaceholder allows you to inject dynamic conversation history
 * into your prompt templates.
 */
export async function example_2_3_templateWithHistory(
  userMessage: string,
  conversationHistory: BaseMessage[] = []
): Promise<string> {
  logger.info("Example 2.3: Template with Conversation History");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  // Template with a placeholder for conversation history
  const templateWithHistory = ChatPromptTemplate.fromMessages([
    ["system", "You are a helpful AI assistant with memory of previous conversations."],
    new MessagesPlaceholder("history"),
    ["human", "{input}"],
  ]);

  const formattedPrompt = await templateWithHistory.formatMessages({
    history: conversationHistory,
    input: userMessage,
  });

  const response = await model.invoke(formattedPrompt);

  return response.content as string;
}

/**
 * Example 2.4: Few-Shot Prompting Template
 *
 * Few-shot prompting provides examples to the model to guide its responses.
 * This is incredibly useful for teaching the model a specific format or style.
 */
export async function example_2_4_fewShotPrompting(): Promise<string> {
  logger.info("Example 2.4: Few-Shot Prompting");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  // Few-shot examples to demonstrate the expected format
  const fewShotTemplate = ChatPromptTemplate.fromMessages([
    ["system", "You analyze sentiment and respond in a specific JSON format."],
    // Example 1
    ["human", "Analyze: 'I love this product! Best purchase ever!'"],
    ["assistant", '{"sentiment": "positive", "confidence": 0.95, "keywords": ["love", "best"]}'],
    // Example 2
    ["human", "Analyze: 'This is the worst experience I have ever had.'"],
    ["assistant", '{"sentiment": "negative", "confidence": 0.92, "keywords": ["worst"]}'],
    // Example 3
    ["human", "Analyze: 'The product is okay, nothing special.'"],
    ["assistant", '{"sentiment": "neutral", "confidence": 0.78, "keywords": ["okay", "nothing special"]}'],
    // Actual query
    ["human", "Analyze: '{text}'"],
  ]);

  const formattedPrompt = await fewShotTemplate.formatMessages({
    text: "I'm somewhat disappointed but it could be worse I suppose.",
  });

  const response = await model.invoke(formattedPrompt);

  return response.content as string;
}

// ============================================================================
// SECTION 3: OUTPUT PARSERS
// ============================================================================

/**
 * Example 3.1: String Output Parser
 *
 * The simplest output parser - just returns the content as a string.
 * Useful when you just need the raw text response.
 */
export async function example_3_1_stringOutputParser(): Promise<string> {
  logger.info("Example 3.1: String Output Parser");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });
  const parser = new StringOutputParser();

  // Chain the model with the parser
  const chain = model.pipe(parser);

  const result = await chain.invoke([
    new HumanMessage("What are the three primary colors?"),
  ]);

  // Result is now a plain string, not an AIMessage
  return result;
}

/**
 * Example 3.2: JSON Output Parser
 *
 * Parses the model's response as JSON.
 * You need to instruct the model to output valid JSON.
 */
export async function example_3_2_jsonOutputParser<T>(): Promise<T> {
  logger.info("Example 3.2: JSON Output Parser");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0, // Lower temperature for more consistent JSON output
  });

  const parser = new JsonOutputParser<T>();

  const prompt = ChatPromptTemplate.fromMessages([
    [
      "system",
      "You are a helpful assistant that always responds in valid JSON format.",
    ],
    [
      "human",
      `Extract information about the following person and return as JSON with keys:
       name, age, occupation, skills (array).

       Person description: {description}`,
    ],
  ]);

  const chain = prompt.pipe(model).pipe(parser);

  const result = await chain.invoke({
    description:
      "John Smith is a 35-year-old software engineer who specializes in Python, " +
      "TypeScript, and machine learning.",
  });

  return result;
}

/**
 * Example 3.3: Structured Output Parser with Zod Schema
 *
 * Use Zod schemas to define and validate the expected output structure.
 * This ensures type safety and proper validation.
 */
export async function example_3_3_structuredOutputWithZod(): Promise<{
  title: string;
  summary: string;
  keyPoints: string[];
  sentiment: "positive" | "negative" | "neutral";
  confidence: number;
}> {
  logger.info("Example 3.3: Structured Output with Zod");

  // Define the expected output schema
  const outputSchema = z.object({
    title: z.string().describe("A brief title summarizing the content"),
    summary: z.string().describe("A 2-3 sentence summary"),
    keyPoints: z.array(z.string()).describe("Main takeaways as bullet points"),
    sentiment: z.enum(["positive", "negative", "neutral"]).describe("Overall sentiment"),
    confidence: z.number().min(0).max(1).describe("Confidence score between 0 and 1"),
  });

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0,
  });

  // Use the model's built-in structured output capability
  const structuredModel = model.withStructuredOutput(outputSchema);

  const result = await structuredModel.invoke(
    "Analyze this article: " +
    "The new electric vehicle from Tesla has exceeded all expectations. " +
    "Sales are up 200% compared to last quarter, and customer satisfaction " +
    "ratings are at an all-time high. Industry analysts predict this could " +
    "revolutionize the EV market."
  );

  return result;
}

/**
 * Example 3.4: Custom Output Parser
 *
 * Sometimes you need custom parsing logic for specific formats.
 * This example shows how to create a custom parser.
 */
export class MarkdownListParser {
  async parse(text: string): Promise<string[]> {
    // Extract items from markdown list format
    const lines = text.split("\n");
    const items: string[] = [];

    for (const line of lines) {
      // Match lines starting with - or * or numbered lists
      const match = line.match(/^[\s]*[-*•][\s]+(.+)$/) ||
                    line.match(/^[\s]*\d+[.)]\s+(.+)$/);
      if (match) {
        items.push(match[1].trim());
      }
    }

    return items;
  }
}

export async function example_3_4_customOutputParser(): Promise<string[]> {
  logger.info("Example 3.4: Custom Output Parser");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });
  const parser = new MarkdownListParser();

  const response = await model.invoke([
    new SystemMessage("Always respond with a markdown bullet list."),
    new HumanMessage("List 5 benefits of regular exercise."),
  ]);

  const items = await parser.parse(response.content as string);

  return items;
}

// ============================================================================
// SECTION 4: CHAINS AND RUNNABLES
// ============================================================================

/**
 * Example 4.1: Simple Chain with Pipe
 *
 * Chains allow you to combine multiple components into a pipeline.
 * The .pipe() method connects components together.
 */
export async function example_4_1_simpleChain(): Promise<string> {
  logger.info("Example 4.1: Simple Chain");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  const prompt = ChatPromptTemplate.fromMessages([
    ["system", "You are a creative writer who writes in the style of {style}."],
    ["human", "Write a short paragraph about {topic}."],
  ]);

  const outputParser = new StringOutputParser();

  // Create a chain: prompt -> model -> parser
  const chain = prompt.pipe(model).pipe(outputParser);

  const result = await chain.invoke({
    style: "Ernest Hemingway",
    topic: "a morning cup of coffee",
  });

  return result;
}

/**
 * Example 4.2: Sequential Chain (Multi-step processing)
 *
 * Sometimes you need multiple LLM calls in sequence,
 * where each step uses the output of the previous step.
 */
export async function example_4_2_sequentialChain(): Promise<{
  original: string;
  translated: string;
  summary: string;
}> {
  logger.info("Example 4.2: Sequential Chain");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  // Step 1: Generate a story
  const storyPrompt = ChatPromptTemplate.fromMessages([
    ["human", "Write a very short story (2-3 sentences) about a {character}."],
  ]);

  // Step 2: Translate the story
  const translatePrompt = ChatPromptTemplate.fromMessages([
    ["human", "Translate this text to French:\n\n{story}"],
  ]);

  // Step 3: Summarize in one sentence
  const summaryPrompt = ChatPromptTemplate.fromMessages([
    ["human", "Summarize this in exactly one sentence:\n\n{translated}"],
  ]);

  // Create chains for each step
  const storyChain = storyPrompt.pipe(model).pipe(new StringOutputParser());
  const translateChain = translatePrompt.pipe(model).pipe(new StringOutputParser());
  const summaryChain = summaryPrompt.pipe(model).pipe(new StringOutputParser());

  // Execute sequentially
  const original = await storyChain.invoke({ character: "brave robot" });
  const translated = await translateChain.invoke({ story: original });
  const summary = await summaryChain.invoke({ translated });

  return { original, translated, summary };
}

/**
 * Example 4.3: RunnableSequence for Complex Workflows
 *
 * RunnableSequence provides more control over complex workflows
 * and makes it easier to compose multiple operations.
 */
export async function example_4_3_runnableSequence(): Promise<{
  analysis: string;
  recommendations: string;
}> {
  logger.info("Example 4.3: RunnableSequence");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  // Create a sequence that analyzes and then provides recommendations
  const analysisChain = RunnableSequence.from([
    {
      // First, pass through the input and add analysis
      input: new RunnablePassthrough(),
      analysis: ChatPromptTemplate.fromMessages([
        ["human", "Analyze the business situation:\n\n{situation}"],
      ])
        .pipe(model)
        .pipe(new StringOutputParser()),
    },
    {
      // Then use the analysis to generate recommendations
      analysis: (prev: { analysis: string }) => prev.analysis,
      recommendations: RunnableSequence.from([
        (prev: { input: { situation: string }; analysis: string }) => ({
          situation: prev.input.situation,
          analysis: prev.analysis,
        }),
        ChatPromptTemplate.fromMessages([
          [
            "human",
            "Based on this analysis:\n{analysis}\n\nProvide 3 specific recommendations.",
          ],
        ]),
        model,
        new StringOutputParser(),
      ]),
    },
  ]);

  const result = await analysisChain.invoke({
    situation:
      "Our e-commerce startup is experiencing 50% month-over-month growth " +
      "but customer support tickets are increasing faster than revenue.",
  });

  return result as { analysis: string; recommendations: string };
}

/**
 * Example 4.4: Parallel Execution
 *
 * Sometimes you need to run multiple operations in parallel
 * to improve performance when they don't depend on each other.
 */
export async function example_4_4_parallelExecution(): Promise<{
  pros: string;
  cons: string;
  neutralAnalysis: string;
}> {
  logger.info("Example 4.4: Parallel Execution");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  const topic = "Remote work becoming permanent for tech companies";

  // Create three different analysis chains
  const prosChain = ChatPromptTemplate.fromMessages([
    ["human", "List the top 3 advantages of: {topic}"],
  ])
    .pipe(model)
    .pipe(new StringOutputParser());

  const consChain = ChatPromptTemplate.fromMessages([
    ["human", "List the top 3 disadvantages of: {topic}"],
  ])
    .pipe(model)
    .pipe(new StringOutputParser());

  const neutralChain = ChatPromptTemplate.fromMessages([
    ["human", "Provide a balanced, neutral analysis of: {topic}"],
  ])
    .pipe(model)
    .pipe(new StringOutputParser());

  // Execute all chains in parallel
  const [pros, cons, neutralAnalysis] = await Promise.all([
    prosChain.invoke({ topic }),
    consChain.invoke({ topic }),
    neutralChain.invoke({ topic }),
  ]);

  return { pros, cons, neutralAnalysis };
}

// ============================================================================
// SECTION 5: STREAMING
// ============================================================================

/**
 * Example 5.1: Basic Streaming
 *
 * Streaming allows you to receive the response token by token,
 * providing a better user experience for longer responses.
 */
export async function example_5_1_basicStreaming(): Promise<string> {
  logger.info("Example 5.1: Basic Streaming");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    streaming: true,
  });

  const chunks: string[] = [];

  // Stream the response
  const stream = await model.stream([
    new HumanMessage("Write a haiku about programming."),
  ]);

  for await (const chunk of stream) {
    const content = chunk.content as string;
    chunks.push(content);
    // In a real app, you might send this to a client via WebSocket or SSE
    process.stdout.write(content);
  }

  console.log("\n"); // New line after streaming

  return chunks.join("");
}

/**
 * Example 5.2: Streaming with Chain
 *
 * You can also stream through a chain of operations.
 */
export async function example_5_2_streamingWithChain(): Promise<string> {
  logger.info("Example 5.2: Streaming with Chain");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    streaming: true,
  });

  const prompt = ChatPromptTemplate.fromMessages([
    ["system", "You are a storyteller who writes engaging short stories."],
    ["human", "Write a very short story about {character} in {setting}."],
  ]);

  const chain = prompt.pipe(model).pipe(new StringOutputParser());

  const chunks: string[] = [];

  const stream = await chain.stream({
    character: "a curious cat",
    setting: "a mysterious library",
  });

  for await (const chunk of stream) {
    chunks.push(chunk);
    process.stdout.write(chunk);
  }

  console.log("\n");

  return chunks.join("");
}

/**
 * Example 5.3: Streaming with Callback Handler
 *
 * Using callbacks gives you more control over streaming events.
 */
export async function example_5_3_streamingWithCallback(
  onToken: (token: string) => void,
  onComplete: (fullResponse: string) => void
): Promise<void> {
  logger.info("Example 5.3: Streaming with Callback");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    streaming: true,
    callbacks: [
      {
        handleLLMNewToken(token: string) {
          onToken(token);
        },
        handleLLMEnd(output) {
          const fullResponse = output.generations[0][0].text;
          onComplete(fullResponse);
        },
      },
    ],
  });

  await model.invoke([
    new HumanMessage("Explain the concept of recursion in programming."),
  ]);
}

// ============================================================================
// SECTION 6: ERROR HANDLING
// ============================================================================

/**
 * Example 6.1: Basic Error Handling
 *
 * Always wrap LLM calls in try-catch to handle potential errors gracefully.
 */
export async function example_6_1_basicErrorHandling(): Promise<string> {
  logger.info("Example 6.1: Basic Error Handling");

  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  try {
    const response = await model.invoke([
      new HumanMessage("What is 2 + 2?"),
    ]);
    return response.content as string;
  } catch (error: any) {
    // Log the error for debugging
    logger.error("LLM invocation failed", { error: error.message });

    // Check for specific error types
    if (error.message?.includes("rate limit")) {
      throw new Error("Rate limit exceeded. Please try again later.");
    }
    if (error.message?.includes("invalid_api_key")) {
      throw new Error("Invalid API key. Please check your configuration.");
    }
    if (error.message?.includes("context_length_exceeded")) {
      throw new Error("Input too long. Please reduce the message length.");
    }

    // Generic error
    throw new Error(`LLM error: ${error.message}`);
  }
}

/**
 * Example 6.2: Retry with Exponential Backoff
 *
 * Implementing retry logic for transient failures.
 */
export async function example_6_2_retryWithBackoff<T>(
  operation: () => Promise<T>,
  maxRetries: number = 3,
  baseDelayMs: number = 1000
): Promise<T> {
  logger.info("Example 6.2: Retry with Exponential Backoff");

  let lastError: Error | undefined;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error: any) {
      lastError = error;

      // Don't retry on certain errors
      if (
        error.message?.includes("invalid_api_key") ||
        error.message?.includes("context_length_exceeded")
      ) {
        throw error;
      }

      // Calculate delay with exponential backoff
      const delay = baseDelayMs * Math.pow(2, attempt);
      logger.warn(`Attempt ${attempt + 1} failed, retrying in ${delay}ms`, {
        error: error.message,
      });

      // Wait before retrying
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw lastError || new Error("Max retries exceeded");
}

// Usage example
export async function example_6_2_usage(): Promise<string> {
  const model = new ChatOpenAI({ modelName: "gpt-4-turbo-preview" });

  return example_6_2_retryWithBackoff(async () => {
    const response = await model.invoke([
      new HumanMessage("Hello!"),
    ]);
    return response.content as string;
  });
}

/**
 * Example 6.3: Fallback to Alternative Model
 *
 * If one model fails, automatically try another.
 */
export async function example_6_3_fallbackModel(): Promise<string> {
  logger.info("Example 6.3: Fallback Model");

  const models = [
    new ChatOpenAI({ modelName: "gpt-4-turbo-preview" }),
    new ChatOpenAI({ modelName: "gpt-3.5-turbo" }),
    // Could also add Anthropic as fallback:
    // new ChatAnthropic({ modelName: "claude-3-sonnet-20240229" }),
  ];

  const message = [new HumanMessage("What is the meaning of life?")];

  for (let i = 0; i < models.length; i++) {
    try {
      logger.info(`Trying model ${i + 1}/${models.length}`);
      const response = await models[i].invoke(message);
      return response.content as string;
    } catch (error: any) {
      logger.warn(`Model ${i + 1} failed`, { error: error.message });
      if (i === models.length - 1) {
        throw new Error("All models failed");
      }
    }
  }

  throw new Error("No models available");
}

/**
 * Example 6.4: Timeout Handling
 *
 * Implement timeouts to prevent hanging on slow responses.
 */
export async function example_6_4_withTimeout<T>(
  operation: () => Promise<T>,
  timeoutMs: number = 30000
): Promise<T> {
  logger.info("Example 6.4: Timeout Handling");

  return Promise.race([
    operation(),
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new Error("Operation timed out")), timeoutMs)
    ),
  ]);
}

// ============================================================================
// SECTION 7
