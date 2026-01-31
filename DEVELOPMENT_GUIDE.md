# 🎓 Development Guide for Beginners

**Welcome to OmniMind!** This guide will teach you everything you need to know to develop features in this project, even if you're new to backend development.

---

## 📚 Table of Contents

1. [The Big Picture](#the-big-picture)
2. [Folder Structure Explained](#folder-structure-explained)
3. [Types of Files](#types-of-files)
4. [Development Workflow](#development-workflow)
5. [Creating Your First Feature](#creating-your-first-feature)
6. [Testing Methods](#testing-methods)
7. [Best Practices](#best-practices)
8. [Common Patterns](#common-patterns)
9. [Naming Conventions](#naming-conventions)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 The Big Picture

### How the Backend Works

```
User/Frontend → HTTP Request → Express Server → Routes → Business Logic → Agent → Response
                                    ↓
                              (index.ts)
                                    ↓
                         (api/routes/*.ts)
                                    ↓
                         (agents/nodes/*.ts)
```

**Simple explanation:**
1. User sends a message (via browser, Postman, or frontend)
2. Express server receives it at `index.ts`
3. Routes file handles the request (`agentRoutes.ts`)
4. Your agent code processes it (`agent.ts`)
5. Response goes back to the user

---

## 📁 Folder Structure Explained

### Complete Backend Structure

```
backend/
├── src/                          # All your source code goes here
│   ├── agents/                   # AI Agent logic
│   │   ├── graphs/              # LangGraph workflows (complex multi-step agents)
│   │   ├── nodes/               # Individual agent functions (simple agents)
│   │   └── tools/               # Tools that agents can use (search, calculator, etc.)
│   │
│   ├── api/                     # HTTP API layer
│   │   ├── middleware/          # Request processing (auth, validation, logging)
│   │   └── routes/              # API endpoints (URLs like /api/agents/chat)
│   │
│   ├── config/                  # Configuration files
│   │   └── index.ts            # App settings, environment variables
│   │
│   ├── core/                    # Core business logic (non-agent specific)
│   │   └── (your core logic)   # Database operations, business rules
│   │
│   ├── models/                  # Data models and types
│   │   └── omnimind.ts         # TypeScript interfaces/types
│   │
│   ├── schemas/                 # Validation schemas (Zod)
│   │   └── (validation files)  # Define what valid requests look like
│   │
│   ├── services/                # Business services
│   │   └── (service files)     # Complex operations that combine multiple things
│   │
│   ├── types/                   # TypeScript type definitions
│   │   └── index.ts            # Shared types used across the app
│   │
│   ├── utils/                   # Utility functions
│   │   └── logger.ts           # Helper functions (logging, formatting, etc.)
│   │
│   ├── examples/                # Learning examples (safe to experiment)
│   │   └── *.examples.ts       # Example code showing how to use features
│   │
│   ├── index.ts                 # 🚀 Main entry point (server starts here)
│   └── test-agent.ts            # Quick test file (run without server)
│
├── tests/                       # Test files
├── dist/                        # Compiled JavaScript (don't edit)
├── node_modules/                # Dependencies (don't edit)
├── package.json                 # Project configuration
├── tsconfig.json                # TypeScript configuration
├── .env                         # Environment variables (API keys, secrets)
└── env.example                  # Example .env file
```

---

## 📄 Types of Files

### 1. **Node Files** (`src/agents/nodes/*.ts`)

**Purpose:** Individual agent functions or simple AI operations

**When to use:**
- Single-purpose AI operations
- Simple question-answer agents
- Reusable agent components

**Example:** `agent.ts`, `summarizer.ts`, `translator.ts`

**What goes inside:**
```typescript
// ✅ GOOD - Export functions
export async function translateText(text: string, language: string) {
  const agent = createAgent();
  return await agent.invoke(`Translate to ${language}: ${text}`);
}

// ❌ BAD - Don't run code at top level
const response = await agent.invoke("Hello");  // This runs immediately!
```

**Naming convention:**
- `agent.ts` - Main agent
- `summarizer.ts` - Specific functionality
- `[feature]Agent.ts` - Feature-specific agent

---

### 2. **Graph Files** (`src/agents/graphs/*.ts`)

**Purpose:** Complex multi-step workflows using LangGraph

**When to use:**
- Multi-step processes (research → analyze → summarize)
- Conditional logic (if this, then that)
- State management (remember conversation history)
- Loops and iterations

**Example:** `researchGraph.ts`, `customerSupportGraph.ts`

**What goes inside:**
```typescript
import { StateGraph } from "@langchain/langgraph";

// Define your workflow
const graph = new StateGraph({
  channels: {
    messages: { value: [] },
    step: { value: "start" }
  }
});

// Add nodes (steps)
graph.addNode("research", researchNode);
graph.addNode("analyze", analyzeNode);
graph.addNode("summarize", summarizeNode);

// Add edges (flow)
graph.addEdge("research", "analyze");
graph.addEdge("analyze", "summarize");
```

**Naming convention:**
- `[workflow]Graph.ts` - e.g., `researchGraph.ts`
- `[feature]Workflow.ts` - e.g., `customerSupportWorkflow.ts`

---

### 3. **Route Files** (`src/api/routes/*.ts`)

**Purpose:** Define HTTP endpoints (URLs) that users can call

**When to use:**
- Always! Every feature needs a route to be accessible via HTTP

**Example:** `agentRoutes.ts`, `userRoutes.ts`, `analyticsRoutes.ts`

**What goes inside:**
```typescript
import { Router } from 'express';
import { invokeAgent } from '../../agents/nodes/agent';

const router = Router();

// POST /api/agents/chat
router.post('/chat', async (req, res) => {
  try {
    const { message } = req.body;
    const response = await invokeAgent(message);
    res.json({ success: true, response });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

export default router;
```

**Naming convention:**
- `[resource]Routes.ts` - e.g., `agentRoutes.ts`, `userRoutes.ts`
- Always plural: `usersRoutes.ts` not `userRoute.ts`

---

### 4. **Model Files** (`src/models/*.ts`)

**Purpose:** Define data structures and types

**When to use:**
- Defining what your data looks like
- Type safety throughout the app
- Documentation of data structures

**Example:** `omnimind.ts`, `user.ts`, `conversation.ts`

**What goes inside:**
```typescript
// Define interfaces/types
export interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp: Date;
}

export interface AgentState {
  messages: ChatMessage[];
  context: string;
  currentStep: string;
}

export class OmniMindAgent {
  // ... class definition
}
```

**Naming convention:**
- `[entity].ts` - e.g., `user.ts`, `message.ts`
- PascalCase for classes/interfaces: `ChatMessage`, `AgentState`

---

### 5. **Service Files** (`src/services/*.ts`)

**Purpose:** Business logic that combines multiple operations

**When to use:**
- Complex operations involving multiple steps
- Database + API + Agent operations together
- Reusable business logic

**Example:** `chatService.ts`, `authService.ts`

**What goes inside:**
```typescript
import { invokeAgent } from '../agents/nodes/agent';
import { saveToDatabase } from '../core/database';

export class ChatService {
  async processMessage(userId: string, message: string) {
    // 1. Get agent response
    const agentResponse = await invokeAgent(message);
    
    // 2. Save to database
    await saveToDatabase({
      userId,
      message,
      response: agentResponse
    });
    
    // 3. Return result
    return {
      response: agentResponse,
      saved: true
    };
  }
}
```

**Naming convention:**
- `[domain]Service.ts` - e.g., `chatService.ts`, `emailService.ts`
- Class names: `ChatService`, `AuthService`

---

### 6. **Utility Files** (`src/utils/*.ts`)

**Purpose:** Helper functions used throughout the app

**When to use:**
- Formatting functions
- Validation helpers
- Common operations (date formatting, string manipulation)

**Example:** `logger.ts`, `validators.ts`, `formatters.ts`

**What goes inside:**
```typescript
// Simple, pure functions
export function formatDate(date: Date): string {
  return date.toISOString().split('T')[0];
}

export function truncateText(text: string, maxLength: number): string {
  return text.length > maxLength 
    ? text.substring(0, maxLength) + '...'
    : text;
}
```

**Naming convention:**
- `[purpose].ts` - e.g., `logger.ts`, `validators.ts`
- Function names: verbs - `formatDate`, `validateEmail`, `parseJson`

---

### 7. **Config Files** (`src/config/*.ts`)

**Purpose:** Application configuration and settings

**When to use:**
- Environment-specific settings
- Constants used across the app
- API configurations

**Example:** `index.ts`, `database.ts`, `ai.ts`

**What goes inside:**
```typescript
export const config = {
  port: process.env.PORT || 8000,
  openai: {
    apiKey: process.env.OPENAI_API_KEY,
    model: process.env.OPENAI_MODEL || 'gpt-4-turbo-preview',
    temperature: 0.7,
  },
  database: {
    url: process.env.DATABASE_URL,
  }
};
```

**Naming convention:**
- `index.ts` - Main config
- `[domain].ts` - Specific configs: `database.ts`, `auth.ts`

---

### 8. **Test Files** (`tests/*.test.ts` or `*.spec.ts`)

**Purpose:** Automated tests for your code

**When to use:**
- Testing functions work correctly
- Preventing bugs when making changes
- Documentation of expected behavior

**Example:** `agent.test.ts`, `routes.test.ts`

**What goes inside:**
```typescript
import { invokeAgent } from '../src/agents/nodes/agent';

describe('Agent Tests', () => {
  test('should respond to simple message', async () => {
    const response = await invokeAgent("Hello");
    expect(response).toBeDefined();
    expect(typeof response).toBe('string');
  });
});
```

**Naming convention:**
- `[file].test.ts` or `[file].spec.ts`
- Match the file you're testing: `agent.test.ts` tests `agent.ts`

---

### 9. **Example Files** (`src/examples/*.examples.ts`)

**Purpose:** Learning and experimentation

**When to use:**
- Testing new ideas
- Learning how libraries work
- Prototyping features

**Example:** `01-basic.examples.ts`, `02-advanced.examples.ts`

**What goes inside:**
```typescript
// Safe to experiment here!
async function example1() {
  console.log('Testing something...');
  // Your experimental code
}

example1();
```

**Naming convention:**
- `##-[description].examples.ts`
- Numbered for ordering: `01-basics.examples.ts`, `02-advanced.examples.ts`

---

## 🔄 Development Workflow

### The Complete Process: Idea → Working Feature

#### **Phase 1: Planning** 📋

**Before writing code, answer these questions:**

1. **What does this feature do?**
   - Example: "Translate user messages to different languages"

2. **Where does the logic go?**
   - Simple agent operation? → `agents/nodes/`
   - Complex multi-step? → `agents/graphs/`
   - Business logic? → `services/`

3. **Does it need an API endpoint?**
   - Yes, if you want to test it via HTTP (Postman/Insomnia)
   - No, if it's just internal helper function

4. **What data does it need?**
   - Input: User message, language code
   - Output: Translated text

---

#### **Phase 2: Implementation** 💻

**Step-by-step implementation:**

**1. Create the Core Logic**

```typescript
// File: src/agents/nodes/translator.ts

import { ChatOpenAI } from '@langchain/openai';
import { createLogger } from '../../utils/logger';

const logger = createLogger('Translator');

export async function translateText(text: string, targetLanguage: string) {
  logger.info('Translating text', { targetLanguage, textLength: text.length });
  
  const model = new ChatOpenAI({
    model: 'gpt-4-turbo-preview',
    openAIApiKey: process.env.OPENAI_API_KEY,
  });
  
  const prompt = `Translate the following text to ${targetLanguage}:\n\n${text}`;
  const response = await model.invoke(prompt);
  
  logger.info('Translation completed');
  return response;
}
```

**2. Create a Quick Test File (Optional but Recommended)**

```typescript
// File: src/test-translator.ts

import dotenv from 'dotenv';
import { translateText } from './agents/nodes/translator';

dotenv.config();

async function test() {
  const result = await translateText("Hello, world!", "Spanish");
  console.log('Result:', result);
}

test();
```

**Run it:**
```bash
cd backend
npx tsx src/test-translator.ts
```

**3. Create API Route (if needed)**

```typescript
// File: src/api/routes/translatorRoutes.ts

import { Router } from 'express';
import { translateText } from '../../agents/nodes/translator';

const router = Router();

router.post('/translate', async (req, res) => {
  try {
    const { text, language } = req.body;
    
    // Validate input
    if (!text || !language) {
      return res.status(400).json({ 
        error: 'Missing required fields: text and language' 
      });
    }
    
    // Call your function
    const result = await translateText(text, language);
    
    // Return response
    res.json({ 
      success: true, 
      translation: result 
    });
  } catch (error: any) {
    res.status(500).json({ 
      error: error.message 
    });
  }
});

export default router;
```

**4. Register Route in index.ts**

```typescript
// File: src/index.ts

// Add this import near the top
import translatorRoutes from './api/routes/translatorRoutes';

// Add this after other routes (around line 60)
app.use('/api/translator', translatorRoutes);
```

---

#### **Phase 3: Testing** 🧪

You have **3 ways** to test your feature:

**Method 1: Quick Test File (Fastest)** ⚡

```bash
cd backend
npx tsx src/test-translator.ts
```

**Pros:**
- Super fast
- No server needed
- Easy to debug
- Great for development

**Cons:**
- Not testing the HTTP layer
- Not how users will actually use it

---

**Method 2: API Testing (Postman/Insomnia)** 🌐

**Step 1: Start the server**
```bash
cd backend
npm run dev
```

**Step 2: Open Postman/Insomnia**

**Step 3: Create a new request**
- Method: `POST`
- URL: `http://localhost:8000/api/translator/translate`
- Headers: `Content-Type: application/json`
- Body (JSON):
```json
{
  "text": "Hello, world!",
  "language": "Spanish"
}
```

**Step 4: Click Send**

**Expected Response:**
```json
{
  "success": true,
  "translation": "¡Hola, mundo!"
}
```

**Pros:**
- Tests the complete flow
- Exactly how users/frontend will use it
- Can save requests for later

**Cons:**
- Slower (need to start server)
- More steps involved

---

**Method 3: Automated Tests (Professional)** ✅

```typescript
// File: tests/translator.test.ts

import { translateText } from '../src/agents/nodes/translator';

describe('Translator', () => {
  test('translates to Spanish', async () => {
    const result = await translateText("Hello", "Spanish");
    expect(result).toContain("Hola");
  });
  
  test('handles empty text', async () => {
    await expect(translateText("", "Spanish"))
      .rejects
      .toThrow();
  });
});
```

**Run tests:**
```bash
cd backend
npm test
```

**Pros:**
- Automated (runs with `npm test`)
- Catches bugs early
- Professional practice

**Cons:**
- Takes time to write
- Need to learn testing framework

---

#### **Phase 4: Refinement** ✨

**Improve your code:**

1. **Add error handling**
```typescript
if (!text || text.trim().length === 0) {
  throw new Error('Text cannot be empty');
}

if (!SUPPORTED_LANGUAGES.includes(language)) {
  throw new Error(`Unsupported language: ${language}`);
}
```

2. **Add logging**
```typescript
logger.info('Translation request', { 
  language, 
  textLength: text.length 
});
```

3. **Add validation**
```typescript
import { z } from 'zod';

const translationSchema = z.object({
  text: z.string().min(1).max(5000),
  language: z.string().min(2).max(20),
});
```

4. **Add documentation**
```typescript
/**
 * Translate text to a target language
 * 
 * @param text - The text to translate
 * @param targetLanguage - Target language code (e.g., 'es', 'fr', 'de')
 * @returns Translated text
 * 
 * @example
 * const result = await translateText("Hello", "Spanish");
 * console.log(result); // "Hola"
 */
```

---

## 🧪 Testing Methods (Detailed)

### When to Use Each Method

| Method | Speed | Completeness | When to Use |
|--------|-------|--------------|-------------|
| **Quick Test File** | ⚡⚡⚡ | 50% | During development, debugging |
| **Postman/Insomnia** | ⚡⚡ | 100% | Before deploying, integration testing |
| **Automated Tests** | ⚡ | 100% | Before committing code, CI/CD |

---

### Method 1: Quick Test File (Detailed)

**Create:** `src/test-[feature].ts`

```typescript
import dotenv from 'dotenv';
import { yourFunction } from './path/to/function';

// Load environment variables
dotenv.config();

async function test() {
  console.log('🧪 Testing [Feature]...\n');
  
  try {
    // Test case 1
    console.log('Test 1: Basic functionality');
    const result1 = await yourFunction("input");
    console.log('✅ Result:', result1);
    
    // Test case 2
    console.log('\nTest 2: Edge case');
    const result2 = await yourFunction("edge case");
    console.log('✅ Result:', result2);
    
    console.log('\n✅ All tests passed!');
  } catch (error: any) {
    console.error('❌ Test failed:', error.message);
    process.exit(1);
  }
}

test();
```

**Run:**
```bash
cd backend
npx tsx src/test-[feature].ts
```

**Tips:**
- Start with this method always
- Test multiple scenarios
- Add console.log everywhere to see what's happening
- Don't commit these files (or put them in `examples/`)

---

### Method 2: Postman/Insomnia (Detailed)

**Step-by-Step:**

**1. Start Your Server**
```bash
cd backend
npm run dev
```

Look for:
```
🚀 Server is running on http://localhost:8000
```

**2. Open Postman/Insomnia**

**3. Create a Collection** (organize your requests)
- Name it "OmniMind API"
- Add folders for different features

**4. Create Request**

**GET Request Example:**
```
Method: GET
URL: http://localhost:8000/api/agents/status
```

**POST Request Example:**
```
Method: POST
URL: http://localhost:8000/api/agents/chat
Headers:
  Content-Type: application/json
Body (raw JSON):
{
  "message": "Hello, world!"
}
```

**5. Save Requests**
- Save each working request
- Add descriptions
- Organize in folders

**6. Test Different Scenarios**

```json
// Valid request
{ "message": "Hello!" }

// Empty message (should fail)
{ "message": "" }

// Missing field (should fail)
{ "wrong_field": "Hello!" }

// Very long message
{ "message": "a".repeat(10000) }
```

**7. Check Response**

**Success Response (200):**
```json
{
  "success": true,
  "response": "Hello! How can I help you?"
}
```

**Error Response (400/500):**
```json
{
  "error": "Message cannot be empty"
}
```

---

### Method 3: Automated Tests (Detailed)

**Create:** `tests/[feature].test.ts`

```typescript
import { describe, test, expect, beforeAll } from '@jest/globals';
import { yourFunction } from '../src/path/to/function';

describe('Feature Name', () => {
  beforeAll(() => {
    // Setup (runs before all tests)
    process.env.OPENAI_API_KEY = 'test-key';
  });

  test('should handle basic input', async () => {
    const result = await yourFunction('test input');
    
    // Assertions
    expect(result).toBeDefined();
    expect(typeof result).toBe('string');
    expect(result.length).toBeGreaterThan(0);
  });

  test('should reject empty input', async () => {
    await expect(yourFunction(''))
      .rejects
      .toThrow('cannot be empty');
  });

  test('should handle special characters', async () => {
    const result = await yourFunction('Hello! @#$%');
    expect(result).toBeDefined();
  });
});
```

**Run:**
```bash
cd backend
npm test                    # Run all tests
npm test translator         # Run specific test file
npm test -- --watch        # Watch mode (reruns on changes)
```

---

## ✅ Best Practices

### Code Organization

#### ✅ DO:

```typescript
// Export functions, not instances
export function createAgent() { ... }
export async function invokeAgent(message: string) { ... }

// Use descriptive names
export async function translateTextToSpanish(text: string) { ... }

// One responsibility per function
export function validateMessage(message: string): boolean { ... }
export async function sendMessage(message: string): Promise<Response> { ... }

// Use TypeScript types
export async function processMessage(message: string): Promise<AgentResponse> { ... }
```

#### ❌ DON'T:

```typescript
// Don't run code at top level
const agent = createAgent();
const response = await agent.invoke("Hello");  // ❌ Runs immediately!

// Don't use vague names
export function doStuff() { ... }  // ❌ What does this do?
export function process(x: any) { ... }  // ❌ Process what?

// Don't mix concerns
export async function everythingInOneFunction(data: any) {
  // validate, process, save to DB, send email, log... ❌ Too much!
}

// Don't use 'any' type
export function process(data: any): any { ... }  // ❌ No type safety
```

---

### File Organization

#### ✅ DO:

```typescript
// src/agents/nodes/translator.ts
// One purpose: translation
export function translateText() { ... }
export function detectLanguage() { ... }
export function getSupportedLanguages() { ... }

// src/agents/nodes/summarizer.ts
// One purpose: summarization
export function summarizeText() { ... }
export function summarizeBulletPoints() { ... }
```

#### ❌ DON'T:

```typescript
// src/utils.ts  ❌ Too generic
export function translate() { ... }
export function summarize() { ... }
export function validateEmail() { ... }
export function formatDate() { ... }
// Everything in one file!
```

---

### Error Handling

#### ✅ DO:

```typescript
export async function processMessage(message: string) {
  try {
    // Validate input
    if (!message || message.trim().length === 0) {
      throw new Error('Message cannot be empty');
    }
    
    if (message.length > 5000) {
      throw new Error('Message too long (max 5000 characters)');
    }
    
    // Process
    const result = await agent.invoke(message);
    
    // Validate output
    if (!result) {
      throw new Error('Agent returned empty response');
    }
    
    return result;
    
  } catch (error: any) {
    logger.error('Failed to process message', { 
      error: error.message,
      message: message.substring(0, 100) 
    });
    throw new Error(`Processing failed: ${error.message}`);
  }
}
```

#### ❌ DON'T:

```typescript
export async function processMessage(message: string) {
  const result = await agent.invoke(message);  // ❌ No error handling!
  return result;
}

// Or worse:
export async function processMessage(message: string) {
  try {
    return await agent.invoke(message);
  } catch (error) {
    console.log('Error');  // ❌ Not helpful!
    return null;  // ❌ Hides the error!
  }
}
```

---

### Logging

#### ✅ DO:

```typescript
import { createLogger } from '../../utils/logger';

const logger = createLogger('TranslatorAgent');

export async function translateText(text: string, language: string) {
  logger.info('Translation started', { 
    language, 
    textLength: text.length 
  });
  
  try {
    const result = await translate(text, language);
    
    logger.info('Translation completed', { 
      resultLength: result.length 
    });
    
    return result;
  } catch (error: any) {
    logger.error('Translation failed', { 
      error: error.message,
      language,
      textLength: text.length 
    });
    throw error;
  }
}
```

#### ❌ DON'T:

```typescript
export async function translateText(text: string, language: string) {
  console.log('translating');  // ❌ Not descriptive
  const result = await translate(text, language);
  console.log(result);  // ❌ Don't log sensitive data
  return result;
}
```

---

### Environment Variables

#### ✅ DO:

```typescript
// src/config/index.ts
export const config = {
  openai: {
    apiKey: process.env.OPENAI_API_KEY,
    model: process.env.OPENAI_MODEL || 'gpt-4-turbo-preview',
  },
  server: {
    port: parseInt(process.env.PORT || '8000'),
    host: process.env.HOST || 'localhost',
  }
};

// Validate on startup
if (!config.openai.apiKey) {
  throw new Error('OPENAI_API_KEY is required');
}
```

#### ❌ DON'T:

```typescript
// ❌ Hardcoded API keys
const apiKey = 'sk-1234567890';

// ❌ Accessing process.env everywhere
const response = await model.invoke(text, {
  apiKey: process.env.OPENAI_API_KEY  // Do this in one place only
});
```

---

## 📐 Common Patterns

### Pattern 1: Simple Function (Pure Logic)

**Use for:** Utilities, formatters, validators

```typescript
// src/utils/validators.ts

/**
 * Validate email format
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Truncate text to max length
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}
```

---

### Pattern 2: Agent Function

**Use for:** AI operations, LLM calls

```typescript
// src/agents/nodes/translator.ts

import { ChatOpenAI } from '@langchain/openai';
import { createLogger } from '../../utils/logger';

const logger = createLogger('Translator');

export async function translateText(
  text: string, 
  targetLanguage: string
): Promise<string> {
  logger.info('Translating', { targetLanguage, textLength: text.length });
  
  const model = new ChatOpenAI({
    model: 'gpt-4-turbo-preview',
    temperature: 0.3,
    openAIApiKey: process.env.OPENAI_API_KEY,
  });
  
  const prompt = `Translate to ${targetLanguage}:\n\n${text}`;
  const response = await model.invoke(prompt);
  
  return response.content as string;
}
```

---

### Pattern 3: API Route

**Use for:** HTTP endpoints

```typescript
// src/api/routes/translatorRoutes.ts

import { Router } from 'express';
import { z } from 'zod';
import { translateText } from '../../agents/nodes/translator';
import { createLogger } from '../../utils/logger';

const router = Router();
const logger = createLogger('TranslatorRoutes');

// Validation schema
const translateSchema = z.object({
  text: z.string().min(1).max(5000),
  language: z.string().min(2),
});

// POST /api/translator/translate
router.post('/translate', async (req, res, next) => {
  try {
    // Validate
    const { text, language } = translateSchema.parse(req.body);
    
    logger.info('Translation request', { language });
    
    // Process
    const result = await translateText(text, language);
    
    // Respond
    res.json({
      success: true,
      translation: result,
      metadata: {
        originalLength: text.length,
        translatedLength: result.length,
        language,
      }
    });
  } catch (error) {
    next(error