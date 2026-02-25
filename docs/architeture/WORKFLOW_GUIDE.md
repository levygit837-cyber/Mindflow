# 🚀 Workflow Guide - From Idea to Working Feature

**Step-by-step guide for beginners on how to develop and test features in OmniMind**

---

## 📋 Table of Contents

1. [Daily Development Workflow](#daily-development-workflow)
2. [Your First Feature: Step-by-Step](#your-first-feature-step-by-step)
3. [Testing Your Code](#testing-your-code)
4. [Common Workflows](#common-workflows)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)

---

## 🔄 Daily Development Workflow

### Morning Setup (Do this once per day)

```bash
# 1. Navigate to backend
cd OmniMindv03/backend

# 2. Pull latest changes (if working with team)
git pull

# 3. Install any new dependencies
npm install

# 4. Check your environment variables
cat .env  # Linux/Mac
type .env  # Windows CMD
Get-Content .env  # Windows PowerShell

# 5. Make sure it has:
# OPENAI_API_KEY=sk-your-key-here
# OPENAI_MODEL=gpt-4-turbo-preview
# PORT=8000
```

### Development Loop (Repeat for each feature)

```
┌─────────────────────────────────────────────┐
│  1. PLAN                                    │
│     What am I building?                     │
│     Where does the code go?                 │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│  2. CODE                                    │
│     Write the function                      │
│     Add logging                             │
│     Handle errors                           │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│  3. QUICK TEST                              │
│     Create test file                        │
│     Run: npx tsx src/test-[feature].ts      │
│     Fix bugs                                │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│  4. CONNECT TO API                          │
│     Create route                            │
│     Register in index.ts                    │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│  5. FULL TEST                               │
│     Start server: npm run dev               │
│     Test in Postman/Insomnia                │
│     Fix bugs                                │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│  6. COMMIT                                  │
│     git add .                               │
│     git commit -m "feat: your feature"      │
│     git push                                │
└─────────────────────────────────────────────┘
```

---

## 🎯 Your First Feature: Step-by-Step

### Example Feature: Text Summarizer

**Goal:** Create an AI that summarizes long text into bullet points.

---

### Step 1: Plan (5 minutes)

**Answer these questions:**

1. **What does it do?**
   - Takes long text as input
   - Returns bullet-point summary
   
2. **Where does the code go?**
   - Main logic: `src/agents/nodes/summarizer.ts` (simple AI operation)
   - API endpoint: `src/api/routes/summarizerRoutes.ts`
   
3. **What data does it need?**
   - Input: `{ text: string, maxBullets?: number }`
   - Output: `{ summary: string[], originalLength: number }`

4. **Test method:**
   - First: Quick test file
   - Then: Postman

---

### Step 2: Create the Core Function (10 minutes)

**Create file:** `backend/src/agents/nodes/summarizer.ts`

```typescript
import { ChatOpenAI } from '@langchain/openai';
import { createLogger } from '../../utils/logger';

const logger = createLogger('Summarizer');

/**
 * Summarize text into bullet points
 * 
 * @param text - The text to summarize
 * @param maxBullets - Maximum number of bullet points (default: 5)
 * @returns Array of bullet points
 */
export async function summarizeText(
  text: string, 
  maxBullets: number = 5
): Promise<string[]> {
  // Validate input
  if (!text || text.trim().length === 0) {
    throw new Error('Text cannot be empty');
  }
  
  if (text.length < 100) {
    throw new Error('Text too short to summarize (minimum 100 characters)');
  }
  
  if (maxBullets < 1 || maxBullets > 10) {
    throw new Error('maxBullets must be between 1 and 10');
  }
  
  logger.info('Summarizing text', { 
    textLength: text.length, 
    maxBullets 
  });
  
  try {
    // Create AI model
    const model = new ChatOpenAI({
      model: process.env.OPENAI_MODEL || 'gpt-4-turbo-preview',
      temperature: 0.3, // Lower temperature for more focused summaries
      openAIApiKey: process.env.OPENAI_API_KEY,
    });
    
    // Create prompt
    const prompt = `
Summarize the following text into exactly ${maxBullets} concise bullet points.
Each bullet point should capture a key idea or fact.
Return only the bullet points, one per line, starting with a dash (-).

Text:
${text}

Summary:
`.trim();
    
    // Get response
    const response = await model.invoke(prompt);
    const content = response.content as string;
    
    // Parse bullet points
    const bullets = content
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.startsWith('-') || line.startsWith('•'))
      .map(line => line.replace(/^[-•]\s*/, ''))
      .filter(line => line.length > 0);
    
    logger.info('Summarization complete', { 
      bulletsGenerated: bullets.length 
    });
    
    return bullets;
    
  } catch (error: any) {
    logger.error('Summarization failed', { 
      error: error.message,
      textLength: text.length 
    });
    throw new Error(`Summarization failed: ${error.message}`);
  }
}

/**
 * Get word count of text
 */
export function getWordCount(text: string): number {
  return text.trim().split(/\s+/).length;
}
```

**✅ Checkpoint:** File created with function that:
- Validates input
- Has logging
- Handles errors
- Has JSDoc comments

---

### Step 3: Create Quick Test File (5 minutes)

**Create file:** `backend/src/test-summarizer.ts`

```typescript
import dotenv from 'dotenv';
import { summarizeText, getWordCount } from './agents/nodes/summarizer';

dotenv.config();

async function test() {
  console.log('🧪 Testing Summarizer...\n');
  console.log('='.repeat(60));
  
  try {
    // Test text
    const longText = `
Artificial Intelligence (AI) has revolutionized numerous industries 
in recent years. From healthcare to finance, AI systems are being 
deployed to automate tasks, improve decision-making, and enhance 
productivity. Machine learning, a subset of AI, enables computers 
to learn from data without explicit programming. Deep learning, 
which uses neural networks, has achieved remarkable success in 
image recognition, natural language processing, and game playing. 
However, AI also raises important ethical concerns, including 
privacy, bias, and job displacement. As AI continues to advance, 
society must carefully consider how to harness its benefits while 
mitigating its risks. Regulation and responsible development 
practices are essential to ensure AI serves humanity's best interests.
    `.trim();
    
    console.log(`📄 Original text (${getWordCount(longText)} words):`);
    console.log(longText);
    console.log('\n' + '='.repeat(60) + '\n');
    
    // Test 1: Default (5 bullets)
    console.log('Test 1: Default summary (5 bullets)\n');
    const summary1 = await summarizeText(longText);
    console.log('📝 Summary:');
    summary1.forEach((bullet, i) => {
      console.log(`   ${i + 1}. ${bullet}`);
    });
    console.log();
    
    // Test 2: Custom bullets
    console.log('='.repeat(60) + '\n');
    console.log('Test 2: Custom summary (3 bullets)\n');
    const summary2 = await summarizeText(longText, 3);
    console.log('📝 Summary:');
    summary2.forEach((bullet, i) => {
      console.log(`   ${i + 1}. ${bullet}`);
    });
    console.log();
    
    // Test 3: Error handling (text too short)
    console.log('='.repeat(60) + '\n');
    console.log('Test 3: Error handling (short text)\n');
    try {
      await summarizeText('Too short');
    } catch (error: any) {
      console.log('✅ Error caught correctly:', error.message);
    }
    
    console.log('\n' + '='.repeat(60));
    console.log('\n✅ All tests completed!');
    
  } catch (error: any) {
    console.error('\n❌ Test failed!');
    console.error('Error:', error.message);
    console.error('\nStack trace:', error.stack);
    process.exit(1);
  }
}

test();
```

**Run the test:**

```bash
cd backend
npx tsx src/test-summarizer.ts
```

**Expected output:**

```
🧪 Testing Summarizer...

============================================================
📄 Original text (123 words):
Artificial Intelligence (AI) has revolutionized...

============================================================

Test 1: Default summary (5 bullets)

📝 Summary:
   1. AI has revolutionized numerous industries...
   2. Machine learning enables computers to learn...
   3. Deep learning has achieved success in...
   4. AI raises ethical concerns including...
   5. Regulation and responsible development are essential...

============================================================

Test 2: Custom summary (3 bullets)

📝 Summary:
   1. AI has transformed multiple industries...
   2. Machine learning and deep learning are key...
   3. Ethical concerns and regulation are important...

============================================================

✅ All tests completed!
```

**✅ Checkpoint:** Your function works! You tested it without starting the server.

---

### Step 4: Create API Route (10 minutes)

**Create file:** `backend/src/api/routes/summarizerRoutes.ts`

```typescript
import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { summarizeText, getWordCount } from '../../agents/nodes/summarizer';
import { createLogger } from '../../utils/logger';

const router = Router();
const logger = createLogger('SummarizerRoutes');

// Validation schema
const summarizeSchema = z.object({
  text: z.string()
    .min(100, 'Text must be at least 100 characters')
    .max(50000, 'Text too long (max 50,000 characters)'),
  maxBullets: z.number()
    .int()
    .min(1)
    .max(10)
    .optional()
    .default(5),
});

// POST /api/summarizer/summarize
router.post('/summarize', async (req: Request, res: Response, next: NextFunction) => {
  try {
    // Validate request
    const { text, maxBullets } = summarizeSchema.parse(req.body);
    
    logger.info('Summarization request', { 
      textLength: text.length,
      maxBullets 
    });
    
    // Summarize
    const summary = await summarizeText(text, maxBullets);
    
    // Response
    res.status(200).json({
      success: true,
      summary,
      metadata: {
        originalLength: text.length,
        originalWordCount: getWordCount(text),
        bulletCount: summary.length,
        timestamp: new Date().toISOString(),
      },
    });
    
  } catch (error) {
    if (error instanceof z.ZodError) {
      return res.status(400).json({
        success: false,
        error: 'Validation error',
        details: error.errors.map(err => ({
          field: err.path.join('.'),
          message: err.message,
        })),
      });
    }
    next(error);
  }
});

// GET /api/summarizer/status
router.get('/status', (req: Request, res: Response) => {
  res.status(200).json({
    status: 'operational',
    features: ['text-summarization'],
    limits: {
      minTextLength: 100,
      maxTextLength: 50000,
      maxBullets: 10,
    },
    timestamp: new Date().toISOString(),
  });
});

export default router;
```

**✅ Checkpoint:** API route created with validation and error handling.

---

### Step 5: Register Route (2 minutes)

**Edit file:** `backend/src/index.ts`

Find this section (around line 55):

```typescript
// API Routes
// Import and register routes here
// Example:
// import agentRoutes from './api/routes/agentRoutes';
// app.use('/api/agents', agentRoutes);
```

**Add your route:**

```typescript
// API Routes
import agentRoutes from './api/routes/agentRoutes';
import summarizerRoutes from './api/routes/summarizerRoutes'; // NEW

app.use('/api/agents', agentRoutes);
app.use('/api/summarizer', summarizerRoutes); // NEW
```

**✅ Checkpoint:** Your API is now accessible at `/api/summarizer/summarize`

---

### Step 6: Test with Server (10 minutes)

**Terminal 1: Start the server**

```bash
cd backend
npm run dev
```

**Look for:**

```
🚀 Server is running on http://localhost:8000
📝 Environment: development
✅ Health check available at http://localhost:8000/health
```

**Terminal 2: Test with curl**

```bash
# Test the status endpoint first
curl http://localhost:8000/api/summarizer/status

# Test summarization
curl -X POST http://localhost:8000/api/summarizer/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Artificial Intelligence has revolutionized numerous industries in recent years. From healthcare to finance, AI systems are being deployed to automate tasks, improve decision-making, and enhance productivity. Machine learning enables computers to learn from data without explicit programming.",
    "maxBullets": 3
  }'
```

**Or use Postman/Insomnia:**

1. **Create new request**
   - Method: `POST`
   - URL: `http://localhost:8000/api/summarizer/summarize`

2. **Set headers**
   - `Content-Type`: `application/json`

3. **Set body (JSON)**
   ```json
   {
     "text": "Your long text here (at least 100 characters)...",
     "maxBullets": 5
   }
   ```

4. **Click Send**

**Expected response:**

```json
{
  "success": true,
  "summary": [
    "AI has revolutionized multiple industries",
    "Machine learning enables automated learning",
    "AI deployment spans healthcare to finance"
  ],
  "metadata": {
    "originalLength": 287,
    "originalWordCount": 42,
    "bulletCount": 3,
    "timestamp": "2024-01-30T12:00:00.000Z"
  }
}
```

**✅ Checkpoint:** Your feature is fully working and accessible via HTTP!

---

### Step 7: Commit Your Code (3 minutes)

```bash
# Check what changed
git status

# Stage your changes
git add src/agents/nodes/summarizer.ts
git add src/api/routes/summarizerRoutes.ts
git add src/index.ts
git add src/test-summarizer.ts

# Commit with descriptive message
git commit -m "feat: add text summarization feature

- Add summarizeText function in agents/nodes/summarizer.ts
- Add /api/summarizer/summarize endpoint
- Add validation and error handling
- Add quick test file for development
- Supports 1-10 bullet points
- Minimum 100 characters input"

# Push to remote
git push origin main
```

**✅ Checkpoint:** Code saved and shared with team!

---

## 🧪 Testing Your Code

### Method 1: Quick Test File (Fastest - Use During Development)

**When to use:**
- ✅ Initial development
- ✅ Debugging
- ✅ Quick iterations
- ✅ Don't need HTTP layer

**Steps:**

1. Create `src/test-[feature].ts`
2. Import your function
3. Call it with test data
4. Run: `npx tsx src/test-[feature].ts`

**Example:**

```typescript
import dotenv from 'dotenv';
import { myFunction } from './path/to/function';

dotenv.config();

async function test() {
  console.log('Testing...');
  const result = await myFunction('test input');
  console.log('Result:', result);
}

test();
```

**Pros:**
- ⚡ Super fast (no server startup)
- 🐛 Easy to debug
- 🔄 Quick iterations

**Cons:**
- ❌ Doesn't test HTTP layer
- ❌ Not how users will access it

---

### Method 2: Postman/Insomnia (Use Before Deploying)

**When to use:**
- ✅ Testing complete flow
- ✅ Before deploying
- ✅ Integration with frontend
- ✅ Save requests for reuse

**Steps:**

1. Start server: `npm run dev`
2. Open Postman/Insomnia
3. Create request with method, URL, headers, body
4. Click Send
5. Verify response

**Example request:**

```
Method: POST
URL: http://localhost:8000/api/feature/action
Headers:
  Content-Type: application/json
Body:
{
  "input": "test data"
}
```

**Pros:**
- ✅ Tests complete flow
- ✅ Save and organize requests
- ✅ Exactly how frontend uses it

**Cons:**
- ⏱️ Slower (need server running)
- 🔄 More setup required

---

### Method 3: Automated Tests (Professional)

**When to use:**
- ✅ Before committing code
- ✅ CI/CD pipelines
- ✅ Prevent regressions
- ✅ Team projects

**Steps:**

1. Create `tests/[feature].test.ts`
2. Write test cases
3. Run: `npm test`

**Example:**

```typescript
import { describe, test, expect } from '@jest/globals';
import { myFunction } from '../src/path/to/function';

describe('My Feature', () => {
  test('should work with valid input', async () => {
    const result = await myFunction('valid input');
    expect(result).toBeDefined();
    expect(result.length).toBeGreaterThan(0);
  });
  
  test('should reject empty input', async () => {
    await expect(myFunction('')).rejects.toThrow('cannot be empty');
  });
});
```

**Pros:**
- ✅ Automated
- ✅ Catch bugs early
- ✅ Professional practice

**Cons:**
- ⏱️ Takes time to write
- 📚 Learning curve

---

## 📝 Common Workflows

### Workflow 1: Creating a Simple Agent Function

```bash
# 1. Create the function
touch backend/src/agents/nodes/myFeature.ts

# 2. Write code with exports (not top-level await)

# 3. Create test file
touch backend/src/test-myFeature.ts

# 4. Test it
npx tsx backend/src/test-myFeature.ts

# 5. Fix bugs and repeat step 4 until it works
```

---

### Workflow 2: Adding API Endpoint

```bash
# 1. Create route file
touch backend/src/api/routes/myFeatureRoutes.ts

# 2. Write route with validation

# 3. Register in index.ts
# Add: import myFeatureRoutes from './api/routes/myFeatureRoutes';
# Add: app.use('/api/myfeature', myFeatureRoutes);

# 4. Start server
npm run dev

# 5. Test in Postman/Insomnia
```

---

### Workflow 3: Debugging an Error

```bash
# 1. Check server logs
# Look in terminal where npm run dev is running

# 2. Add more logging
logger.info('Debug point', { variable: value });

# 3. Test with quick file
npx tsx src/test-feature.ts

# 4. Check environment variables
cat .env | grep OPENAI_API_KEY

# 5. Check network (for API endpoints)
curl http://localhost:8000/health
```

---

### Workflow 4: Refactoring Code

```bash
# 1. Make sure current code works
npm test  # or your test method

# 2. Make ONE small change

# 3. Test again immediately
npx tsx src/test-feature.ts

# 4. Repeat steps 2-3 for each change

# 5. Commit when stable
git add .
git commit -m "refactor: improve myFeature"
```

---

## ✅ Best Practices

### DO ✅

```typescript
// Export functions
export async function processData(input: string) { ... }

// Validate input
if (!input || input.trim().length === 0) {
  throw new Error('Input cannot be empty');
}

// Use logging
logger.info('Processing data', { inputLength: input.length });

// Handle errors
try {
  const result = await operation();
  return result;
} catch (error: any) {
  logger.error('Operation failed', { error: error.message });
  throw new Error(`Failed: ${error.message}`);
}

// Add JSDoc comments
/**
 * Process user input
 * @param input - User input string
 * @returns Processed result
 */

// Use descriptive names
function translateTextToSpanish(text: string) { ... }
```

### DON'T ❌

```typescript
// Don't use top-level await
const result = await operation();  // ❌ Runs immediately!

// Don't skip validation
function process(input: any) {  // ❌ No validation
  return operation(input);
}

// Don't ignore errors
try {
  await operation();
} catch (error) {
  console.log('error');  // ❌ Not helpful
  return null;  // ❌ Hides the error
}

// Don't use vague names
function doStuff(x: any) { ... }  // ❌ What does this do?

// Don't mix concerns
async function everythingInOne(data: any) {
  // validate, process, save DB, send email, log... ❌
}
```

---

## 🐛 Troubleshooting

### Problem: "Cannot find module"

```bash
# Solution 1: Reinstall dependencies
cd backend
rm -rf node_modules package-lock.json
npm install

# Solution 2: Check import path
# Make sure path is correct relative to file location
import { myFunc } from '../../utils/myFile';  # ../ goes up one directory
```

---

### Problem: "OPENAI_API_KEY not found"

```bash
# Solution: Check .env file
cd backend
cat .env  # Should show: OPENAI_API_KEY=sk-...

# If missing, copy from example
cp env.example .env
# Then edit .env and add your key
```

---

### Problem: "Port 8000 already in use"

```bash
# Windows PowerShell:
netstat -ano | findstr :8000
taskkill /PID <PID_NUMBER> /F

# Linux/Mac:
lsof -i :8000
kill -9 <PID_NUMBER>

# Or change port in .env:
PORT=8001
```

---

### Problem: "Function not working as expected"

```bash
# Step 1: Add logging everywhere
logger.info('Before operation', { input });
const result = await operation(input);
logger.info('After operation', { result });

# Step 2: Test with simple input
npx tsx src/test-feature.ts

# Step 3: Check the logs
# Terminal will show all logger.info() messages

# Step 4: Simplify the function
# Comment out complex parts, test with minimal code
```

---

### Problem: "Tests passing but API not working"

```bash
# Check if route is registered
# In index.ts, should have:
import myRoutes from './api/routes/myRoutes';
app.use('/api/my', myRoutes);

# Test the endpoint exists
curl http://localhost:8000/health  # Should work
curl http://localhost:8000/api/my/status  # Test your endpoint

# Check server logs
# Terminal running npm run dev shows all requests
```

---

## 🎯 Quick Reference

### Start Development Session

```bash
cd OmniMindv03/backend
npm install
npm run dev  # Keep this running in one terminal
```

### Create New Feature

```bash
# 1. Create function file
# backend/src/agents/nodes/[feature].ts

# 2. Create test file
# backend/src/test-[feature].ts

# 3. Test it
npx tsx src/test-[feature].ts

# 4. Create route (if needed)
# backend/src/api/routes/[feature]Routes.ts

# 5. Register route in index.ts

# 6. Test with Postman

# 7. Commit
git add .
git commit -m "feat: add [feature]"
git push
```

### Common Commands

```bash
# Development
npm run dev          # Start development server

# Testing
npx tsx src/test-[feature].ts  # Quick test
npm test             # Run automated tests

# Building
npm run build        # Compile TypeScript
npm start            # Run production build

# Linting/Formatting
npm run lint         # Check code style
npm run lint:fix     # Fix code style
npm run format       # Format code
```

---

## 🎓 Learning Path

### Week 1: Basics
- ✅ Run the test file example
- ✅ Modify test file with your own message
- ✅ Create one simple function
- ✅ Test it with quick test file

### Week 2: API Integration
- ✅ Create your first route
- ✅ Register it in index.ts
- ✅ Test with Postman
- ✅ Handle one error case

### Week 3: Complex Features
- ✅ Create feature with validation
- ✅ Add proper error handling
- ✅ Add logging
- ✅ Write documentation

### Week 4: Professional Practices
- ✅ Write automated tests
- ✅ Follow file organization
- ✅ Use proper naming conventions
- ✅ Review and refactor code

---

**Remember:**
- 🚀 Start with quick test files (fastest)
- 🔄 Iterate quickly
- 📝 Add logging everywhere
- ✅ Test often
- 💡 One feature at a time
- 🐛 Debug as you go
- 📚 Read error messages carefully
- 🎯 Follow the examples in this guide

Good luck! 🎉