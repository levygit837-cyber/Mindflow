# 📁 Folder Architecture Guide

**Complete guide to the OmniMind backend folder structure**

This guide explains what each folder is for, what files go inside, and examples of when to use them.

---

## 🎯 Quick Reference

| Folder | Purpose | What Goes Here | Example Files |
|--------|---------|----------------|---------------|
| `agents/nodes/` | Individual AI operations | Simple agent functions | `translator.ts`, `summarizer.ts` |
| `agents/graphs/` | Complex workflows | Multi-step AI workflows | `researchGraph.ts`, `customerSupportGraph.ts` |
| `agents/tools/` | Agent tools | Functions agents can call | `searchTool.ts`, `calculatorTool.ts` |
| `api/routes/` | HTTP endpoints | Express route handlers | `agentRoutes.ts`, `userRoutes.ts` |
| `api/middleware/` | Request processing | Auth, validation, logging | `authMiddleware.ts`, `validationMiddleware.ts` |
| `config/` | Configuration | App settings, env vars | `index.ts`, `database.ts` |
| `core/` | Business logic | Domain-specific logic | `userManager.ts`, `conversationManager.ts` |
| `models/` | Data structures | TypeScript types/classes | `user.ts`, `message.ts` |
| `schemas/` | Validation | Zod schemas | `userSchema.ts`, `messageSchema.ts` |
| `services/` | Business services | Complex operations | `chatService.ts`, `emailService.ts` |
| `types/` | Type definitions | Shared TypeScript types | `index.ts`, `api.ts` |
| `utils/` | Helper functions | Pure utility functions | `logger.ts`, `validators.ts` |
| `examples/` | Learning code | Experimental code | `01-basics.examples.ts` |

---

## 📂 Detailed Folder Breakdown

---

### 1. `src/agents/nodes/` - Individual Agent Functions

**Purpose:** Single-purpose AI operations that can be reused

**When to use:**
- ✅ Simple AI tasks (translate, summarize, answer questions)
- ✅ Single-step operations
- ✅ Functions that other parts of the app will call
- ❌ Complex multi-step workflows (use `graphs/` instead)

**File naming:**
- `[functionality].ts` - e.g., `translator.ts`, `summarizer.ts`
- `[feature]Agent.ts` - e.g., `weatherAgent.ts`, `newsAgent.ts`

**Example structure:**

```typescript
// src/agents/nodes/translator.ts

import { ChatOpenAI } from '@langchain/openai';
import { createLogger } from '../../utils/logger';

const logger = createLogger('Translator');

/**
 * Translate text to target language
 */
export async function translateText(text: string, language: string): Promise<string> {
  logger.info('Translating text', { language, length: text.length });
  
  const model = new ChatOpenAI({
    model: 'gpt-4-turbo-preview',
    openAIApiKey: process.env.OPENAI_API_KEY,
  });
  
  const prompt = `Translate this text to ${language}: ${text}`;
  const response = await model.invoke(prompt);
  
  return response.content as string;
}

/**
 * Detect language of text
 */
export async function detectLanguage(text: string): Promise<string> {
  // Implementation
}
```

**Real-world examples:**
- `translator.ts` - Translation operations
- `summarizer.ts` - Text summarization
- `classifier.ts` - Text classification
- `sentiment.ts` - Sentiment analysis
- `extractor.ts` - Information extraction
- `generator.ts` - Content generation

---

### 2. `src/agents/graphs/` - Complex Workflows

**Purpose:** Multi-step AI workflows with state management

**When to use:**
- ✅ Multiple steps that depend on each other
- ✅ Conditional logic (if this, then that)
- ✅ Loops and iterations
- ✅ State that needs to persist across steps
- ❌ Simple one-shot operations (use `nodes/` instead)

**File naming:**
- `[workflow]Graph.ts` - e.g., `researchGraph.ts`, `customerSupportGraph.ts`
- `[feature]Workflow.ts` - e.g., `contentCreationWorkflow.ts`

**Example structure:**

```typescript
// src/agents/graphs/researchGraph.ts

import { StateGraph } from '@langchain/langgraph';
import { ChatOpenAI } from '@langchain/openai';

// Define state
interface ResearchState {
  query: string;
  searchResults: string[];
  analysis: string;
  summary: string;
  currentStep: string;
}

// Create graph
export function createResearchGraph() {
  const graph = new StateGraph<ResearchState>({
    channels: {
      query: { value: '' },
      searchResults: { value: [] },
      analysis: { value: '' },
      summary: { value: '' },
      currentStep: { value: 'search' },
    }
  });

  // Add nodes
  graph.addNode('search', searchNode);
  graph.addNode('analyze', analyzeNode);
  graph.addNode('summarize', summarizeNode);

  // Add edges
  graph.addEdge('search', 'analyze');
  graph.addEdge('analyze', 'summarize');
  graph.setEntryPoint('search');

  return graph.compile();
}

// Node implementations
async function searchNode(state: ResearchState): Promise<Partial<ResearchState>> {
  // Search implementation
  return { searchResults: ['result1', 'result2'] };
}

async function analyzeNode(state: ResearchState): Promise<Partial<ResearchState>> {
  // Analysis implementation
  return { analysis: 'analysis result' };
}

async function summarizeNode(state: ResearchState): Promise<Partial<ResearchState>> {
  // Summary implementation
  return { summary: 'final summary' };
}
```

**Real-world examples:**
- `researchGraph.ts` - Search → Analyze → Summarize
- `customerSupportGraph.ts` - Classify → Route → Respond → Followup
- `contentCreationGraph.ts` - Plan → Research → Write → Edit → Review
- `dataAnalysisGraph.ts` - Load → Clean → Analyze → Visualize

---

### 3. `src/agents/tools/` - Agent Tools

**Purpose:** Tools that agents can use during execution

**When to use:**
- ✅ External API calls (weather, news, search)
- ✅ Calculations and computations
- ✅ Database queries
- ✅ File operations
- ❌ Core agent logic (use `nodes/` instead)

**File naming:**
- `[functionality]Tool.ts` - e.g., `searchTool.ts`, `calculatorTool.ts`

**Example structure:**

```typescript
// src/agents/tools/searchTool.ts

import { DynamicStructuredTool } from '@langchain/core/tools';
import { z } from 'zod';

/**
 * Tool for searching the web
 */
export const searchTool = new DynamicStructuredTool({
  name: 'web_search',
  description: 'Search the web for information. Use this when you need current information.',
  schema: z.object({
    query: z.string().describe('The search query'),
  }),
  func: async ({ query }) => {
    // Implementation
    const results = await performWebSearch(query);
    return JSON.stringify(results);
  },
});

async function performWebSearch(query: string): Promise<any> {
  // Actual search implementation
}
```

**Real-world examples:**
- `searchTool.ts` - Web search
- `calculatorTool.ts` - Math operations
- `weatherTool.ts` - Weather data
- `databaseTool.ts` - Database queries
- `apiTool.ts` - External API calls

---

### 4. `src/api/routes/` - HTTP Endpoints

**Purpose:** Define URLs that users/frontend can call

**When to use:**
- ✅ Every feature that needs HTTP access
- ✅ All public APIs
- ✅ Frontend integration points

**File naming:**
- `[resource]Routes.ts` - e.g., `agentRoutes.ts`, `userRoutes.ts`
- Always plural: `usersRoutes.ts` not `userRoute.ts`

**Example structure:**

```typescript
// src/api/routes/agentRoutes.ts

import { Router } from 'express';
import { z } from 'zod';
import { invokeAgent } from '../../agents/nodes/agent';
import { createLogger } from '../../utils/logger';

const router = Router();
const logger = createLogger('AgentRoutes');

// Validation schema
const chatSchema = z.object({
  message: z.string().min(1).max(5000),
  options: z.object({
    model: z.string().optional(),
    temperature: z.number().optional(),
  }).optional(),
});

// POST /api/agents/chat
router.post('/chat', async (req, res, next) => {
  try {
    // Validate
    const { message, options } = chatSchema.parse(req.body);
    
    logger.info('Chat request', { messageLength: message.length });
    
    // Process
    const response = await invokeAgent(message, options);
    
    // Respond
    res.json({
      success: true,
      response,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/agents/status
router.get('/status', (req, res) => {
  res.json({
    status: 'operational',
    timestamp: new Date().toISOString(),
  });
});

export default router;
```

**Real-world examples:**
- `agentRoutes.ts` - `/api/agents/*` - Agent interactions
- `userRoutes.ts` - `/api/users/*` - User management
- `chatRoutes.ts` - `/api/chat/*` - Chat operations
- `analyticsRoutes.ts` - `/api/analytics/*` - Analytics

---

### 5. `src/api/middleware/` - Request Processing

**Purpose:** Code that runs before/after route handlers

**When to use:**
- ✅ Authentication/authorization
- ✅ Request validation
- ✅ Logging
- ✅ Error handling
- ✅ Rate limiting

**File naming:**
- `[purpose]Middleware.ts` - e.g., `authMiddleware.ts`, `validationMiddleware.ts`

**Example structure:**

```typescript
// src/api/middleware/authMiddleware.ts

import { Request, Response, NextFunction } from 'express';
import { createLogger } from '../../utils/logger';

const logger = createLogger('AuthMiddleware');

/**
 * Verify API key in request header
 */
export function requireApiKey(req: Request, res: Response, next: NextFunction) {
  const apiKey = req.headers['x-api-key'];
  
  if (!apiKey) {
    logger.warn('Missing API key', { ip: req.ip });
    return res.status(401).json({ error: 'API key required' });
  }
  
  if (apiKey !== process.env.API_KEY) {
    logger.warn('Invalid API key', { ip: req.ip });
    return res.status(401).json({ error: 'Invalid API key' });
  }
  
  logger.info('API key validated', { ip: req.ip });
  next();
}

/**
 * Rate limiting middleware
 */
export function rateLimit(maxRequests: number, windowMs: number) {
  const requests = new Map<string, number[]>();
  
  return (req: Request, res: Response, next: NextFunction) => {
    const ip = req.ip || 'unknown';
    const now = Date.now();
    
    // Get request timestamps for this IP
    const timestamps = requests.get(ip) || [];
    
    // Remove old timestamps
    const recentTimestamps = timestamps.filter(t => now - t < windowMs);
    
    // Check limit
    if (recentTimestamps.length >= maxRequests) {
      return res.status(429).json({ error: 'Too many requests' });
    }
    
    // Add current request
    recentTimestamps.push(now);
    requests.set(ip, recentTimestamps);
    
    next();
  };
}
```

**Real-world examples:**
- `authMiddleware.ts` - Authentication
- `validationMiddleware.ts` - Request validation
- `loggingMiddleware.ts` - Request/response logging
- `rateLimitMiddleware.ts` - Rate limiting
- `errorMiddleware.ts` - Error handling

---

### 6. `src/config/` - Configuration

**Purpose:** Application settings and environment variables

**When to use:**
- ✅ Environment-specific settings
- ✅ Constants used across the app
- ✅ API configurations
- ❌ Business logic (use `core/` or `services/`)

**File naming:**
- `index.ts` - Main config
- `[domain].ts` - Specific configs: `database.ts`, `auth.ts`

**Example structure:**

```typescript
// src/config/index.ts

import dotenv from 'dotenv';

dotenv.config();

export const config = {
  server: {
    port: parseInt(process.env.PORT || '8000', 10),
    host: process.env.HOST || 'localhost',
    env: process.env.NODE_ENV || 'development',
  },
  
  openai: {
    apiKey: process.env.OPENAI_API_KEY || '',
    model: process.env.OPENAI_MODEL || 'gpt-4-turbo-preview',
    temperature: parseFloat(process.env.TEMPERATURE || '0.7'),
    maxTokens: parseInt(process.env.MAX_TOKENS || '2000', 10),
  },
  
  cors: {
    origin: process.env.CORS_ORIGIN || 'http://localhost:3000',
    credentials: true,
  },
  
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    file: process.env.LOG_FILE || 'combined.log',
  },
};

// Validate required config
export function validateConfig() {
  if (!config.openai.apiKey) {
    throw new Error('OPENAI_API_KEY is required');
  }
  
  if (config.server.port < 1 || config.server.port > 65535) {
    throw new Error('Invalid PORT number');
  }
}
```

**Real-world examples:**
- `index.ts` - Main configuration
- `database.ts` - Database settings
- `auth.ts` - Authentication settings
- `ai.ts` - AI model settings

---

### 7. `src/core/` - Core Business Logic

**Purpose:** Domain-specific business logic that doesn't fit elsewhere

**When to use:**
- ✅ Domain-specific operations
- ✅ Business rules
- ✅ Data management
- ❌ HTTP handling (use `api/routes/`)
- ❌ AI operations (use `agents/`)

**File naming:**
- `[domain]Manager.ts` - e.g., `userManager.ts`, `conversationManager.ts`

**Example structure:**

```typescript
// src/core/conversationManager.ts

import { createLogger } from '../utils/logger';

const logger = createLogger('ConversationManager');

interface Conversation {
  id: string;
  userId: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

/**
 * Manage user conversations
 */
export class ConversationManager {
  private conversations = new Map<string, Conversation>();
  
  createConversation(userId: string): Conversation {
    const conversation: Conversation = {
      id: generateId(),
      userId,
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    
    this.conversations.set(conversation.id, conversation);
    logger.info('Conversation created', { id: conversation.id, userId });
    
    return conversation;
  }
  
  addMessage(conversationId: string, message: Message): void {
    const conversation = this.conversations.get(conversationId);
    
    if (!conversation) {
      throw new Error('Conversation not found');
    }
    
    conversation.messages.push(message);
    conversation.updatedAt = new Date();
    
    logger.info('Message added', { conversationId, role: message.role });
  }
  
  getConversation(conversationId: string): Conversation | undefined {
    return this.conversations.get(conversationId);
  }
}

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
}
```

**Real-world examples:**
- `conversationManager.ts` - Manage conversations
- `userManager.ts` - User operations
- `sessionManager.ts` - Session handling
- `cacheManager.ts` - Caching logic

---

### 8. `src/models/` - Data Structures

**Purpose:** Define the shape of your data

**When to use:**
- ✅ TypeScript interfaces/types
- ✅ Data models
- ✅ Class definitions
- ❌ Validation logic (use `schemas/`)

**File naming:**
- `[entity].ts` - e.g., `user.ts`, `message.ts`, `conversation.ts`

**Example structure:**

```typescript
// src/models/message.ts

/**
 * Chat message interface
 */
export interface ChatMessage {
  id: string;
  conversationId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  metadata?: MessageMetadata;
}

/**
 * Message metadata
 */
export interface MessageMetadata {
  model?: string;
  tokens?: number;
  duration?: number;
  error?: string;
}

/**
 * Conversation interface
 */
export interface Conversation {
  id: string;
  userId: string;
  title?: string;
  messages: ChatMessage[];
  createdAt: Date;
  updatedAt: Date;
  status: 'active' | 'archived' | 'deleted';
}

/**
 * User interface
 */
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'user' | 'admin';
  createdAt: Date;
  preferences?: UserPreferences;
}

export interface UserPreferences {
  theme?: 'light' | 'dark';
  language?: string;
  notifications?: boolean;
}
```

**Real-world examples:**
- `user.ts` - User data structure
- `message.ts` - Message data structure
- `conversation.ts` - Conversation data structure
- `agent.ts` - Agent configuration structure

---

### 9. `src/schemas/` - Validation Schemas

**Purpose:** Validate data using Zod

**When to use:**
- ✅ API request validation
- ✅ Environment variable validation
- ✅ User input validation
- ❌ Type definitions (use `models/`)

**File naming:**
- `[entity]Schema.ts` - e.g., `userSchema.ts`, `messageSchema.ts`

**Example structure:**

```typescript
// src/schemas/messageSchema.ts

import { z } from 'zod';

/**
 * Chat message validation schema
 */
export const chatMessageSchema = z.object({
  message: z.string()
    .min(1, 'Message cannot be empty')
    .max(5000, 'Message too long'),
  
  options: z.object({
    model: z.enum(['gpt-4-turbo-preview', 'gpt-3.5-turbo']).optional(),
    temperature: z.number().min(0).max(2).optional(),
    maxTokens: z.number().int().positive().optional(),
    stream: z.boolean().optional(),
  }).optional(),
});

/**
 * User registration schema
 */
export const userRegistrationSchema = z.object({
  email: z.string().email('Invalid email format'),
  password: z.string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain uppercase letter')
    .regex(/[a-z]/, 'Password must contain lowercase letter')
    .regex(/[0-9]/, 'Password must contain number'),
  name: z.string().min(2).max(100),
});

/**
 * Translation request schema
 */
export const translationSchema = z.object({
  text: z.string().min(1).max(10000),
  targetLanguage: z.string().length(2), // ISO 639-1 code
  sourceLanguage: z.string().length(2).optional(),
});

// Export types derived from schemas
export type ChatMessageInput = z.infer<typeof chatMessageSchema>;
export type UserRegistrationInput = z.infer<typeof userRegistrationSchema>;
export type TranslationInput = z.infer<typeof translationSchema>;
```

**Real-world examples:**
- `userSchema.ts` - User validation
- `messageSchema.ts` - Message validation
- `configSchema.ts` - Configuration validation
- `apiSchema.ts` - API request validation

---

### 10. `src/services/` - Business Services

**Purpose:** Complex operations that combine multiple things

**When to use:**
- ✅ Operations involving multiple modules
- ✅ Orchestration logic
- ✅ Complex business workflows
- ❌ Simple utilities (use `utils/`)
- ❌ HTTP handling (use `api/routes/`)

**File naming:**
- `[domain]Service.ts` - e.g., `chatService.ts`, `emailService.ts`

**Example structure:**

```typescript
// src/services/chatService.ts

import { invokeAgent } from '../agents/nodes/agent';
import { ConversationManager } from '../core/conversationManager';
import { createLogger } from '../utils/logger';

const logger = createLogger('ChatService');
const conversationManager = new ConversationManager();

/**
 * Chat service that combines agent, conversation management, and persistence
 */
export class ChatService {
  /**
   * Process a chat message
   */
  async processMessage(userId: string, conversationId: string, message: string) {
    logger.info('Processing message', { userId, conversationId });
    
    try {
      // 1. Get or create conversation
      let conversation = conversationManager.getConversation(conversationId);
      if (!conversation) {
        conversation = conversationManager.createConversation(userId);
      }
      
      // 2. Add user message
      conversationManager.addMessage(conversationId, {
        role: 'user',
        content: message,
        timestamp: new Date(),
      });
      
      // 3. Get agent response
      const agentResponse = await invokeAgent(message);
      
      // 4. Add assistant message
      conversationManager.addMessage(conversationId, {
        role: 'assistant',
        content: agentResponse,
        timestamp: new Date(),
      });
      
      // 5. (Optional) Save to database
      // await database.saveConversation(conversation);
      
      logger.info('Message processed successfully', { conversationId });
      
      return {
        response: agentResponse,
        conversationId: conversation.id,
        messageCount: conversation.messages.length,
      };
      
    } catch (error: any) {
      logger.error('Failed to process message', { error: error.message });
      throw error;
    }
  }
  
  /**
   * Get conversation history
   */
  async getHistory(conversationId: string) {
    const conversation = conversationManager.getConversation(conversationId);
    
    if (!conversation) {
      throw new Error('Conversation not found');
    }
    
    return conversation.messages;
  }
}
```

**Real-world examples:**
- `chatService.ts` - Chat operations
- `emailService.ts` - Email sending
- `analyticsService.ts` - Analytics tracking
- `notificationService.ts` - Notifications

---

### 11. `src/types/` - TypeScript Type Definitions

**Purpose:** Shared types used across the application

**When to use:**
- ✅ Types used in multiple files
- ✅ External library type extensions
- ✅ Global type definitions
- ❌ Feature-specific types (put in the feature file)

**File naming:**
- `index.ts` - Main types
- `[domain].ts` - Domain-specific types: `api.ts`, `database.ts`

**Example structure:**

```typescript
// src/types/index.ts

import { Request } from 'express';

/**
 * Extended Express Request with user
 */
export interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    email: string;
    role: string;
  };
}

/**
 * API Response wrapper
 */
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  metadata?: {
    timestamp: string;
    requestId: string;
  };
}

/**
 * Pagination
 */
export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    limit: number;
    total: number;
    hasMore: boolean;
  };
}

/**
 * Agent configuration
 */
export interface AgentConfig {
  model: string;
  temperature: number;
  maxTokens?: number;
  topP?: number;
}
```

**Real-world examples:**
- `index.ts` - Common types
- `api.ts` - API-related types
- `database.ts` - Database types
- `express.d.ts` - Express type extensions

---

### 12. `src/utils/` - Utility Functions

**Purpose:** Pure helper functions

**When to use:**
- ✅ Formatting functions
- ✅ Validation helpers
- ✅ Common operations
- ❌ Business logic (use `core/` or `services/`)
- ❌ Feature-specific code (put in feature folder)

**File naming:**
- `[purpose].ts` - e.g., `logger.ts`, `validators.ts`, `formatters.ts`

**Example structure:**

```typescript
// src/utils/formatters.ts

/**
 * Format date to ISO string
 */
export function formatDate(date: Date): string {
  return date.toISOString().split('T')[0];
}

/**
 * Truncate text to max length
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}

/**
 * Format file size
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

/**
 * Sleep/delay function
 */
export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Retry function with exponential backoff
 */
export async function retry<T>(
  fn: () => Promise<T>,
  maxAttempts: number = 3,
  delayMs: number = 1000
): Promise<T> {
  let lastError: Error;
  
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error: any) {
      lastError = error;
      if (attempt < maxAttempts) {
        await sleep(delayMs * attempt);
      }
    }
  }
  
  throw lastError!;
}
```

**Real-world examples:**
- `logger.ts` - Logging utilities
- `validators.ts` - Validation helpers
- `formatters.ts` - Formatting functions
- `crypto.ts` - Encryption/hashing
- `date.ts` - Date utilities

---

### 13. `src/examples/` - Learning and Experimentation

**Purpose:** Safe place to learn and test code

**When to use:**
- ✅ Learning new libraries
- ✅ Testing ideas
- ✅ Code examples
- ✅ Prototyping
- ❌ Production code (move to proper folders)

**File naming:**
- `##-[description].examples.ts`
- Numbered for ordering: `01-basics.examples.ts`, `02-advanced.examples.ts`

**Example structure:**

```typescript
// src/examples/01-agent-basics.examples.ts

import dotenv from 'dotenv';
import { ChatOpenAI } from '@langchain/openai';

dotenv.config();

/**
 * Example 1: Simple agent call
 */
async function example1_SimpleCall() {
  console.log('\n📝 Example 1: Simple agent call\n');
  
  const model = new ChatOpenAI({
    model: 'gpt-4-turbo-preview',
    openAIApiKey: process.env.OPENAI_API_KEY,
  });
  
  const response = await model.invoke('Say hello!');
  console.log('Response:', response.content);
}

/**
 * Example 2: With system message
 */
async function example2_SystemMessage() {
  console.log('\n📝 Example 2: With system message\n');
  
  // Implementation
}

// Run examples
async function main() {
  await example1_SimpleCall();
  await example2_SystemMessage();
}

if (require.main === module) {
  main();
}
```

---

## 🎯 Decision Tree: Where Should My Code Go?

```
START: I want to create...

├─ HTTP Endpoint (URL users can call)
│  └─ api/routes/[feature]Routes.ts
│
├─ AI Operation
│  ├─ Simple (one step)
│  │  └─ agents/nodes/[feature].ts
│  │
│  └─ Complex (multiple steps)
│     └─ agents/graphs/[feature]Graph.ts
│
├─ Tool for agent to use
│  └─ agents/tools/[tool]Tool.ts
│
├─ Business logic
│  ├─ Simple helper function
│  │  └─ utils/[purpose].ts
│  │
│  └─ Complex operation
│     └─ services/[feature]Service.ts
│
├─ Data structure
│  ├─ Type definition
│  │  └─ models/[entity].ts
│  │
│  └─ Validation schema
│     └─ schemas/[entity]Schema.ts
│
├─ Configuration
│  └─ config/[domain].ts
│
├─ Middleware (auth, logging, etc.)
│  └─ api/middleware/[purpose]Middleware.ts
│
└─ Learning/Testing
   └─ examples/##-[name].examples.ts
```

---

## 📋 Checklist: Creating a New Feature

### Planning Phase
- [ ] What does this feature do? (write 1-2 sentences)
- [ ] What data does it need? (input)
- [ ] What data does it return? (output)
- [ ] Does it need an HTTP endpoint? (yes/no)
- [ ] Does it use AI? (yes/no)
- [ ] Is it simple or complex? (simple/complex)

### Implementation Phase