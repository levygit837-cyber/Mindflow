/**
 * ============================================================================
 * 03 - TOOLS AND AGENTS EXAMPLES
 * ============================================================================
 *
 * This file contains comprehensive examples of creating and using tools
 * with LangChain agents. Tools extend the capabilities of LLMs by allowing
 * them to interact with external systems, APIs, and data sources.
 *
 * Topics covered:
 * - Basic tool creation
 * - Structured tool inputs with Zod
 * - Dynamic tools
 * - Tool binding to models
 * - Agent executors
 * - ReAct agents
 * - Tool error handling
 * - Tool callbacks and logging
 * - Real-world tool patterns (search, APIs, databases)
 * - Custom tool classes
 * - Tool composition
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
  ToolMessage,
  BaseMessage,
} from "@langchain/core/messages";
import { tool, DynamicStructuredTool, DynamicTool } from "@langchain/core/tools";
import { StructuredTool } from "@langchain/core/tools";
import { z } from "zod";
import { AgentExecutor, createReactAgent, createToolCallingAgent } from "langchain/agents";
import { ChatPromptTemplate, MessagesPlaceholder } from "@langchain/core/prompts";
import { pull } from "langchain/hub";
import { StateGraph, END, START, Annotation } from "@langchain/langgraph";
import { ToolNode } from "@langchain/langgraph/prebuilt";
import { createLogger } from "../utils/logger";
import { CallbackManager } from "@langchain/core/callbacks/manager";

const logger = createLogger("ToolsAndAgentsExamples");

// ============================================================================
// SECTION 1: BASIC TOOL CREATION
// ============================================================================

/**
 * Example 1.1: Simple Tool with @tool Decorator Pattern
 *
 * The simplest way to create a tool - using the `tool` function.
 * This wraps a function and provides metadata for the LLM.
 */

// Define a simple calculator tool
export const calculatorTool = tool(
  async ({ expression }: { expression: string }): Promise<string> => {
    logger.info("Calculator tool called", { expression });
    try {
      // IMPORTANT: In production, use a proper math parser, not eval!
      // This is simplified for demonstration purposes
      const sanitized = expression.replace(/[^0-9+\-*/().%\s]/g, "");
      const result = Function(`"use strict"; return (${sanitized})`)();
      return `The result of ${expression} is: ${result}`;
    } catch (error: any) {
      return `Error calculating expression: ${error.message}`;
    }
  },
  {
    name: "calculator",
    description: "Performs mathematical calculations. Input should be a valid mathematical expression like '2 + 2' or '(5 * 3) / 2'.",
    schema: z.object({
      expression: z.string().describe("The mathematical expression to evaluate"),
    }),
  }
);

/**
 * Example 1.2: Tool with Multiple Parameters
 *
 * Tools can accept multiple parameters with different types.
 */
export const temperatureConverterTool = tool(
  async ({
    value,
    fromUnit,
    toUnit,
  }: {
    value: number;
    fromUnit: "celsius" | "fahrenheit" | "kelvin";
    toUnit: "celsius" | "fahrenheit" | "kelvin";
  }): Promise<string> => {
    logger.info("Temperature converter called", { value, fromUnit, toUnit });

    // Convert to Celsius first
    let celsius: number;
    switch (fromUnit) {
      case "fahrenheit":
        celsius = (value - 32) * (5 / 9);
        break;
      case "kelvin":
        celsius = value - 273.15;
        break;
      default:
        celsius = value;
    }

    // Convert from Celsius to target
    let result: number;
    switch (toUnit) {
      case "fahrenheit":
        result = celsius * (9 / 5) + 32;
        break;
      case "kelvin":
        result = celsius + 273.15;
        break;
      default:
        result = celsius;
    }

    return `${value}°${fromUnit.charAt(0).toUpperCase()} = ${result.toFixed(2)}°${toUnit.charAt(0).toUpperCase()}`;
  },
  {
    name: "temperature_converter",
    description: "Converts temperature between Celsius, Fahrenheit, and Kelvin",
    schema: z.object({
      value: z.number().describe("The temperature value to convert"),
      fromUnit: z.enum(["celsius", "fahrenheit", "kelvin"]).describe("The source unit"),
      toUnit: z.enum(["celsius", "fahrenheit", "kelvin"]).describe("The target unit"),
    }),
  }
);

/**
 * Example 1.3: Async Tool with External API Simulation
 *
 * Tools often need to call external APIs. Here's a pattern for that.
 */
export const weatherTool = tool(
  async ({ city, country }: { city: string; country?: string }): Promise<string> => {
    logger.info("Weather tool called", { city, country });

    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Simulated weather data (in real app, call actual API)
    const weatherData: Record<string, any> = {
      "new york": { temp: 72, condition: "Partly Cloudy", humidity: 65, wind: 12 },
      "london": { temp: 59, condition: "Rainy", humidity: 80, wind: 8 },
      "tokyo": { temp: 68, condition: "Sunny", humidity: 55, wind: 5 },
      "paris": { temp: 64, condition: "Cloudy", humidity: 70, wind: 10 },
      "sydney": { temp: 77, condition: "Clear", humidity: 45, wind: 15 },
    };

    const data = weatherData[city.toLowerCase()];

    if (!data) {
      return `Weather data not available for ${city}. Try: New York, London, Tokyo, Paris, or Sydney.`;
    }

    return `Weather in ${city}${country ? `, ${country}` : ""}:
- Temperature: ${data.temp}°F
- Condition: ${data.condition}
- Humidity: ${data.humidity}%
- Wind Speed: ${data.wind} mph`;
  },
  {
    name: "get_weather",
    description: "Gets current weather information for a city",
    schema: z.object({
      city: z.string().describe("The city name"),
      country: z.string().optional().describe("The country (optional)"),
    }),
  }
);

// ============================================================================
// SECTION 2: STRUCTURED TOOLS WITH CLASSES
// ============================================================================

/**
 * Example 2.1: Custom Tool Class
 *
 * For more complex tools, extend StructuredTool for better organization.
 */
export class SearchDatabaseTool extends StructuredTool {
  name = "search_database";
  description = "Searches the product database for items matching the query";

  schema = z.object({
    query: z.string().describe("Search query"),
    category: z.string().optional().describe("Product category filter"),
    maxResults: z.number().default(5).describe("Maximum number of results"),
    sortBy: z.enum(["relevance", "price_asc", "price_desc", "rating"]).default("relevance"),
  });

  // Simulated database
  private products = [
    { id: 1, name: "Laptop Pro 15", category: "electronics", price: 1299, rating: 4.5 },
    { id: 2, name: "Wireless Mouse", category: "electronics", price: 49, rating: 4.2 },
    { id: 3, name: "Standing Desk", category: "furniture", price: 599, rating: 4.8 },
    { id: 4, name: "Ergonomic Chair", category: "furniture", price: 449, rating: 4.6 },
    { id: 5, name: "USB-C Hub", category: "electronics", price: 79, rating: 4.3 },
    { id: 6, name: "Monitor 27 inch", category: "electronics", price: 399, rating: 4.7 },
    { id: 7, name: "Desk Lamp", category: "lighting", price: 89, rating: 4.1 },
    { id: 8, name: "Mechanical Keyboard", category: "electronics", price: 149, rating: 4.9 },
  ];

  async _call({
    query,
    category,
    maxResults,
    sortBy,
  }: z.infer<typeof this.schema>): Promise<string> {
    logger.info("Database search called", { query, category, maxResults, sortBy });

    // Filter by query and category
    let results = this.products.filter((p) => {
      const matchesQuery = p.name.toLowerCase().includes(query.toLowerCase());
      const matchesCategory = !category || p.category === category.toLowerCase();
      return matchesQuery && matchesCategory;
    });

    // Sort results
    switch (sortBy) {
      case "price_asc":
        results.sort((a, b) => a.price - b.price);
        break;
      case "price_desc":
        results.sort((a, b) => b.price - a.price);
        break;
      case "rating":
        results.sort((a, b) => b.rating - a.rating);
        break;
      // relevance = default order (no sorting needed)
    }

    // Limit results
    results = results.slice(0, maxResults);

    if (results.length === 0) {
      return `No products found matching "${query}"${category ? ` in category "${category}"` : ""}.`;
    }

    const formatted = results
      .map((p) => `- ${p.name} | $${p.price} | Rating: ${p.rating}/5 | Category: ${p.category}`)
      .join("\n");

    return `Found ${results.length} product(s):\n${formatted}`;
  }
}

/**
 * Example 2.2: Tool with State/Context
 *
 * Tools can maintain state or access shared context.
 */
export class ShoppingCartTool extends StructuredTool {
  name = "shopping_cart";
  description = "Manages a shopping cart - add items, remove items, or view cart";

  schema = z.object({
    action: z.enum(["add", "remove", "view", "clear"]).describe("Action to perform"),
    itemName: z.string().optional().describe("Name of item (for add/remove)"),
    quantity: z.number().default(1).describe("Quantity (for add)"),
  });

  // Shared cart state
  private cart: Map<string, { name: string; quantity: number; price: number }> = new Map();

  // Price lookup (simplified)
  private prices: Record<string, number> = {
    "laptop": 999,
    "mouse": 49,
    "keyboard": 129,
    "monitor": 399,
    "headphones": 199,
  };

  async _call({
    action,
    itemName,
    quantity,
  }: z.infer<typeof this.schema>): Promise<string> {
    logger.info("Shopping cart action", { action, itemName, quantity });

    switch (action) {
      case "add": {
        if (!itemName) return "Error: Item name required for 'add' action";
        const normalizedName = itemName.toLowerCase();
        const price = this.prices[normalizedName] || 50; // default price

        const existing = this.cart.get(normalizedName);
        if (existing) {
          existing.quantity += quantity;
        } else {
          this.cart.set(normalizedName, { name: itemName, quantity, price });
        }
        return `Added ${quantity}x ${itemName} to cart. Cart now has ${this.getCartTotal()} items.`;
      }

      case "remove": {
        if (!itemName) return "Error: Item name required for 'remove' action";
        const normalizedName = itemName.toLowerCase();

        if (this.cart.has(normalizedName)) {
          this.cart.delete(normalizedName);
          return `Removed ${itemName} from cart.`;
        }
        return `Item "${itemName}" not found in cart.`;
      }

      case "view": {
        if (this.cart.size === 0) {
          return "Your cart is empty.";
        }

        let total = 0;
        const items: string[] = [];
        this.cart.forEach((item) => {
          const subtotal = item.price * item.quantity;
          total += subtotal;
          items.push(`- ${item.name} x${item.quantity} @ $${item.price} = $${subtotal}`);
        });

        return `Shopping Cart:\n${items.join("\n")}\n\nTotal: $${total}`;
      }

      case "clear": {
        this.cart.clear();
        return "Cart has been cleared.";
      }

      default:
        return `Unknown action: ${action}`;
    }
  }

  private getCartTotal(): number {
    let total = 0;
    this.cart.forEach((item) => (total += item.quantity));
    return total;
  }
}

/**
 * Example 2.3: Tool with Validation and Error Handling
 *
 * Robust tools should validate inputs and handle errors gracefully.
 */
export class EmailSenderTool extends StructuredTool {
  name = "send_email";
  description = "Sends an email to the specified recipient";

  schema = z.object({
    to: z.string().email("Invalid email address").describe("Recipient email address"),
    subject: z.string().min(1).max(200).describe("Email subject"),
    body: z.string().min(1).max(10000).describe("Email body content"),
    priority: z.enum(["low", "normal", "high"]).default("normal").describe("Email priority"),
    attachments: z.array(z.string()).optional().describe("File paths of attachments"),
  });

  async _call({
    to,
    subject,
    body,
    priority,
    attachments,
  }: z.infer<typeof this.schema>): Promise<string> {
    logger.info("Email send requested", { to, subject, priority });

    try {
      // Validate email more thoroughly
      if (!this.isValidEmailDomain(to)) {
        return `Error: The email domain appears to be invalid or unreachable.`;
      }

      // Check for suspicious content (simplified)
      if (this.containsSuspiciousContent(body)) {
        return `Error: Email content flagged for review. Please revise.`;
      }

      // Simulate sending email
      await this.simulateSend(to, subject, body, priority, attachments);

      return `Email sent successfully!
- To: ${to}
- Subject: ${subject}
- Priority: ${priority}
- Attachments: ${attachments?.length || 0} file(s)`;
    } catch (error: any) {
      logger.error("Failed to send email", { error: error.message });
      return `Failed to send email: ${error.message}`;
    }
  }

  private isValidEmailDomain(email: string): boolean {
    const validDomains = ["gmail.com", "outlook.com", "yahoo.com", "company.com"];
    const domain = email.split("@")[1];
    return validDomains.some((d) => domain.endsWith(d));
  }

  private containsSuspiciousContent(body: string): boolean {
    const suspiciousPatterns = [/password.*reset.*link/i, /click.*here.*win/i];
    return suspiciousPatterns.some((pattern) => pattern.test(body));
  }

  private async simulateSend(
    to: string,
    subject: string,
    body: string,
    priority: string,
    attachments?: string[]
  ): Promise<void> {
    // Simulate network delay
    await new Promise((resolve) => setTimeout(resolve, 200));

    // Simulate random failures (10% chance)
    if (Math.random() < 0.1) {
      throw new Error("SMTP server temporarily unavailable");
    }
  }
}

// ============================================================================
// SECTION 3: DYNAMIC TOOLS
// ============================================================================

/**
 * Example 3.1: DynamicTool for Simple Use Cases
 *
 * When you need a quick tool without complex schemas.
 */
export const currentTimeTool = new DynamicTool({
  name: "get_current_time",
  description: "Gets the current date and time. No input required.",
  func: async (_input: string): Promise<string> => {
    const now = new Date();
    return `Current time: ${now.toLocaleString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      timeZoneName: "short",
    })}`;
  },
});

/**
 * Example 3.2: DynamicStructuredTool for Complex Schemas
 *
 * When you need a dynamic tool but with structured input.
 */
export const scheduleMeetingTool = new DynamicStructuredTool({
  name: "schedule_meeting",
  description: "Schedules a meeting with participants",
  schema: z.object({
    title: z.string().describe("Meeting title"),
    participants: z.array(z.string().email()).describe("List of participant emails"),
    datetime: z.string().describe("Meeting date and time in ISO format"),
    duration: z.number().min(15).max(480).describe("Duration in minutes"),
    location: z.string().optional().describe("Meeting location or video link"),
    notes: z.string().optional().describe("Additional notes"),
  }),
  func: async ({
    title,
    participants,
    datetime,
    duration,
    location,
    notes,
  }): Promise<string> => {
    logger.info("Scheduling meeting", { title, participants: participants.length });

    // Validate datetime
    const meetingDate = new Date(datetime);
    if (isNaN(meetingDate.getTime())) {
      return "Error: Invalid date format. Please use ISO format (e.g., 2024-01-15T10:00:00)";
    }

    if (meetingDate < new Date()) {
      return "Error: Cannot schedule meetings in the past.";
    }

    // Check for conflicts (simplified)
    const hasConflict = Math.random() < 0.2; // 20% chance of conflict
    if (hasConflict) {
      return `Scheduling conflict detected. Some participants are busy at ${datetime}. Please choose another time.`;
    }

    // Generate meeting ID
    const meetingId = `MTG-${Date.now().toString(36).toUpperCase()}`;

    return `Meeting scheduled successfully!
- Meeting ID: ${meetingId}
- Title: ${title}
- Date/Time: ${meetingDate.toLocaleString()}
- Duration: ${duration} minutes
- Participants: ${participants.join(", ")}
- Location: ${location || "To be determined"}
${notes ? `- Notes: ${notes}` : ""}

Calendar invites have been sent to all participants.`;
  },
});

/**
 * Example 3.3: Tool Factory - Creating Tools Dynamically
 *
 * Sometimes you need to create tools at runtime based on configuration.
 */
export function createApiTool(config: {
  name: string;
  description: string;
  endpoint: string;
  method: "GET" | "POST";
  headers?: Record<string, string>;
}): DynamicStructuredTool {
  return new DynamicStructuredTool({
    name: config.name,
    description: config.description,
    schema: z.object({
      params: z.record(z.any()).optional().describe("Query parameters or request body"),
    }),
    func: async ({ params }): Promise<string> => {
      logger.info(`API tool ${config.name} called`, { endpoint: config.endpoint, params });

      try {
        // Simulate API call
        await new Promise((resolve) => setTimeout(resolve, 100));

        // In real implementation:
        // const response = await fetch(config.endpoint, {
        //   method: config.method,
        //   headers: config.headers,
        //   body: config.method === 'POST' ? JSON.stringify(params) : undefined,
        // });
        // return await response.text();

        return `API ${config.name} called successfully with params: ${JSON.stringify(params)}`;
      } catch (error: any) {
        return `API call failed: ${error.message}`;
      }
    },
  });
}

// Example usage of tool factory
export const userApiTool = createApiTool({
  name: "get_user_info",
  description: "Fetches user information from the user service",
  endpoint: "https://api.example.com/users",
  method: "GET",
});

// ============================================================================
// SECTION 4: TOOL BINDING AND MODEL INTEGRATION
// ============================================================================

/**
 * Example 4.1: Binding Tools to a Model
 *
 * Tools must be bound to a model before the model can use them.
 */
export async function example_4_1_bindToolsToModel(): Promise<string> {
  logger.info("Example 4.1: Binding Tools to Model");

  // Create model
  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0,
  });

  // Define tools
  const tools = [calculatorTool, weatherTool, currentTimeTool];

  // Bind tools to model
  const modelWithTools = model.bindTools(tools);

  // Now the model can decide when to use tools
  const response = await modelWithTools.invoke([
    new HumanMessage("What's 25 * 4, and what's the weather in Tokyo?"),
  ]);

  logger.info("Model response with tools", {
    content: response.content,
    toolCalls: response.tool_calls,
  });

  return JSON.stringify({
    content: response.content,
    toolCalls: response.tool_calls,
  });
}

/**
 * Example 4.2: Handling Tool Calls
 *
 * When a model decides to use a tool, you need to execute it and return results.
 */
export async function example_4_2_handleToolCalls(): Promise<BaseMessage[]> {
  logger.info("Example 4.2: Handling Tool Calls");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0,
  });

  const tools = [calculatorTool, weatherTool];
  const toolMap = new Map(tools.map((t) => [t.name, t]));

  const modelWithTools = model.bindTools(tools);

  // Initial message
  const messages: BaseMessage[] = [
    new HumanMessage("Calculate 15% tip on $85 and tell me the weather in London"),
  ];

  // First invocation - model will return tool calls
  const response = await modelWithTools.invoke(messages);
  messages.push(response);

  // Execute tool calls
  if (response.tool_calls && response.tool_calls.length > 0) {
    for (const toolCall of response.tool_calls) {
      const tool = toolMap.get(toolCall.name);
      if (tool) {
        logger.info(`Executing tool: ${toolCall.name}`, { args: toolCall.args });
        const result = await tool.invoke(toolCall.args);
        messages.push(
          new ToolMessage({
            content: result,
            tool_call_id: toolCall.id,
          })
        );
      }
    }

    // Get final response with tool results
    const finalResponse = await modelWithTools.invoke(messages);
    messages.push(finalResponse);
  }

  return messages;
}

/**
 * Example 4.3: Tool Choice - Forcing Specific Tools
 *
 * You can force the model to use a specific tool or any tool.
 */
export async function example_4_3_toolChoice(): Promise<{
  auto: any;
  forced: any;
  none: any;
}> {
  logger.info("Example 4.3: Tool Choice");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0,
  });

  const tools = [calculatorTool, weatherTool];

  // Auto - model decides
  const autoResponse = await model.bindTools(tools).invoke([
    new HumanMessage("Hello, how are you?"),
  ]);

  // Force specific tool
  const forcedResponse = await model
    .bindTools(tools, { tool_choice: { type: "function", function: { name: "calculator" } } })
    .invoke([new HumanMessage("Tell me about Paris")]);

  // Disable tools
  const noneResponse = await model
    .bindTools(tools, { tool_choice: "none" })
    .invoke([new HumanMessage("What is 2+2?")]);

  return {
    auto: { content: autoResponse.content, toolCalls: autoResponse.tool_calls },
    forced: { content: forcedResponse.content, toolCalls: forcedResponse.tool_calls },
    none: { content: noneResponse.content, toolCalls: noneResponse.tool_calls },
  };
}

// ============================================================================
// SECTION 5: AGENT EXECUTORS
// ============================================================================

/**
 * Example 5.1: Tool Calling Agent
 *
 * The recommended way to create agents in LangChain - using tool calling.
 */
export async function example_5_1_toolCallingAgent(): Promise<string> {
  logger.info("Example 5.1: Tool Calling Agent");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0,
  });

  const tools = [calculatorTool, weatherTool, currentTimeTool];

  // Create prompt
  const prompt = ChatPromptTemplate.fromMessages([
    ["system", "You are a helpful assistant. Use tools when needed to answer questions accurately."],
    new MessagesPlaceholder("chat_history"),
    ["human", "{input}"],
    new MessagesPlaceholder("agent_scratchpad"),
  ]);

  // Create agent
  const agent = createToolCallingAgent({
    llm: model,
    tools,
    prompt,
  });

  // Create executor
  const executor = new AgentExecutor({
    agent,
    tools,
    verbose: true, // Set to true to see agent's reasoning
    maxIterations: 5,
  });

  // Run the agent
  const result = await executor.invoke({
    input: "What time is it, and can you calculate 20% of 150?",
    chat_history: [],
  });

  return result.output;
}

/**
 * Example 5.2: Agent with Memory/Chat History
 *
 * Agents can maintain conversation context across turns.
 */
export async function example_5_2_agentWithMemory(): Promise<string[]> {
  logger.info("Example 5.2: Agent with Memory");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0,
  });

  const tools = [calculatorTool, weatherTool];

  const prompt = ChatPromptTemplate.fromMessages([
    ["system", "You are a helpful assistant with memory of our conversation."],
    new MessagesPlaceholder("chat_history"),
    ["human", "{input}"],
    new MessagesPlaceholder("agent_scratchpad"),
  ]);

  const agent = createToolCallingAgent({ llm: model, tools, prompt });
  const executor = new AgentExecutor({ agent, tools });

  // Maintain chat history
  const chatHistory: BaseMessage[] = [];
  const responses: string[] = [];

  // Turn 1
  const result1 = await executor.invoke({
    input: "What's the weather in New York?",
    chat_history: chatHistory,
  });
  chatHistory.push(new HumanMessage("What's the weather in New York?"));
  chatHistory.push(new AIMessage(result1.output));
  responses.push(result1.output);

  // Turn 2 - references previous context
  const result2 = await executor.invoke({
    input: "How does that compare to London?",
    chat_history: chatHistory,
  });
  chatHistory.push(new HumanMessage("How does that compare to London?"));
  chatHistory.push(new AIMessage(result2.output));
  responses.push(result2.output);

  // Turn 3 - continues context
  const result3 = await executor.invoke({
    input: "If I need to pack for both, what should I bring?",
    chat_history: chatHistory,
  });
  responses.push(result3.output);

  return responses;
}

/**
 * Example 5.3: Agent with Custom Error Handling
 *
 * Proper error handling makes agents more robust.
 */
export async function example_5_3_agentWithErrorHandling(): Promise<{
  success: boolean;
  output?: string;
  error?: string;
}> {
  logger.info("Example 5.3: Agent with Error Handling");

  const model = new ChatOpenAI({
    modelName: "gpt-4-turbo-preview",
    temperature: 0,
  });

  // Tool that sometimes fails
  const unreliableTool = tool(
    async ({ query }: { query: string }): Promise<string> => {
      if (Math.random() < 0.5) {
        throw new Error("Service temporarily unavailable");
      }
      return `Results for: ${query}`;
    },
    {
      name: "unreliable_search",
      description: "A search tool that sometimes fails",
      schema: z.object({ query: z.string() }),
    }
  );

  const prompt = ChatPromptTemplate.fromMessages([
    ["system", "You are a helpful assistant. If a tool fails, explain the situation and try alternatives."],
    new MessagesPlaceholder("chat_history"),
    ["human", "{input}"],
    new MessagesPlaceholder("agent_scratchpad"),
  ]);

  const agent = createToolCallingAgent({
    llm: model,
    tools: [unreliableTool, calculatorTool],
    prompt,
  });

  const executor = new AgentExecutor({
    agent,
    tools: [unreliableTool, calculatorTool],
    maxIterations: 3,
    handleParsingErrors: (error) => {
      logger.error("Parsing error in agent", { error });
      return "I encountered an error processing that request. Let me try again.";
    },
  });

  try {
    const result = await executor.invoke({
      input: "Search for 'LangChain tutorials'",
      chat_history: [],
    });

    return { success: true, output: result.output };
  } catch (error: any) {
