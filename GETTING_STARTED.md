# 🚀 Getting Started with OmniMind Backend Development

**Welcome! This guide will get you from zero to developing your first feature in 15 minutes.**

---

## 📚 Documentation Overview

Before diving in, here's what each guide covers:

| Guide | What It's For | When to Read |
|-------|---------------|--------------|
| **GETTING_STARTED.md** (this file) | First-time setup and quick start | **START HERE** |
| **WORKFLOW_GUIDE.md** | Step-by-step feature development | When building features |
| **FOLDER_GUIDE.md** | What each folder is for | When deciding where to put code |
| **DEVELOPMENT_GUIDE.md** | Best practices and patterns | When writing code |
| **COMMANDS.md** | All available commands | As reference |

---

## ⚡ Quick Start (15 minutes)

### Step 1: Initial Setup (5 minutes)

```bash
# 1. Navigate to backend directory
cd OmniMindv03/backend

# 2. Install dependencies
npm install

# 3. Copy environment file
cp env.example .env

# 4. Edit .env and add your OpenAI API key
# Windows: notepad .env
# Mac/Linux: nano .env
# Or use VS Code: code .env

# Add this line:
OPENAI_API_KEY=sk-your-actual-key-here
```

**Your `.env` file should look like:**

```
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
OPENAI_MODEL=gpt-4-turbo-preview
PORT=8000
NODE_ENV=development
```

---

### Step 2: Test Your Setup (5 minutes)

**Run the quick test file to verify everything works:**

```bash
# Make sure you're in the backend directory
cd backend

# Run the test
npx tsx src/test-agent.ts
```

**You should see:**

```
🧪 Testing OmniMind Agent...
============================================================
✅ Environment variables loaded
📦 Creating agent...
✅ Agent created successfully

📤 Sending message: "Hello, World! Tell me a fun fact about TypeScript."

📥 Response received:
------------------------------------------------------------
[AI response will appear here]
------------------------------------------------------------

✅ Test completed successfully!
============================================================
```

**✅ If you see this, your setup is complete!**

**❌ If you see an error:**
- Check your API key is correct in `.env`
- Make sure you ran `npm install`
- See [Troubleshooting](#troubleshooting) below

---

### Step 3: Start the Server (5 minutes)

```bash
# Start the development server
npm run dev
```

**You should see:**

```
🚀 Server is running on http://localhost:8000
📝 Environment: development
✅ Health check available at http://localhost:8000/health
```

**Test it in your browser:**
- Open: http://localhost:8000
- Open: http://localhost:8000/health

**Or with curl:**

```bash
curl http://localhost:8000/health
```

**Expected response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-30T12:00:00.000Z",
  "uptime": 1.234,
  "environment": "development"
}
```

**✅ Your server is running!**

---

## 🎯 Your First Feature (10 minutes)

Now let's create a simple feature to understand the workflow.

### Goal: Create a "Greeting Agent"

**What it does:** Takes a name and returns a personalized greeting.

---

### Step 1: Create the Function (3 minutes)

Create file: `backend/src/agents/nodes/greeter.ts`

```typescript
import { ChatOpenAI } from '@langchain/openai';
import { createLogger } from '../../utils/logger';

const logger = createLogger('Greeter');

/**
 * Generate a personalized greeting
 */
export async function greetUser(name: string, language: string = 'English'): Promise<string> {
  // Validate input
  if (!name || name.trim().length === 0) {
    throw new Error('Name cannot be empty');
  }
  
  logger.info('Generating greeting', { name, language });
  
  try {
    const model = new ChatOpenAI({
      model: 'gpt-4-turbo-preview',
      temperature: 0.8,
      openAIApiKey: process.env.OPENAI_API_KEY,
    });
    
    const prompt = `Generate a warm, friendly greeting for a person named ${name}. 
    Make it personalized and cheerful. Respond in ${language}.
    Just return the greeting, nothing else.`;
    
    const response = await model.invoke(prompt);
    const greeting = response.content as string;
    
    logger.info('Greeting generated successfully');
    return greeting;
    
  } catch (error: any) {
    logger.error('Failed to generate greeting', { error: error.message });
    throw error;
  }
}
```

---

### Step 2: Test It Quickly (2 minutes)

Create file: `backend/src/test-greeter.ts`

```typescript
import dotenv from 'dotenv';
import { greetUser } from './agents/nodes/greeter';

dotenv.config();

async function test() {
  console.log('🧪 Testing Greeter...\n');
  
  try {
    const greeting = await greetUser('Alice', 'English');
    console.log('Greeting:', greeting);
    
    console.log('\n✅ Test passed!');
  } catch (error: any) {
    console.error('❌ Test failed:', error.message);
  }
}

test();
```

**Run it:**

```bash
npx tsx src/test-greeter.ts
```

**You should see a personalized greeting! ✅**

---

### Step 3: Add API Endpoint (5 minutes)

Create file: `backend/src/api/routes/greeterRoutes.ts`

```typescript
import { Router } from 'express';
import { z } from 'zod';
import { greetUser } from '../../agents/nodes/greeter';
import { createLogger } from '../../utils/logger';

const router = Router();
const logger = createLogger('GreeterRoutes');

const greetSchema = z.object({
  name: z.string().min(1).max(100),
  language: z.string().optional().default('English'),
});

router.post('/greet', async (req, res, next) => {
  try {
    const { name, language } = greetSchema.parse(req.body);
    const greeting = await greetUser(name, language);
    
    res.json({
      success: true,
      greeting,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    next(error);
  }
});

export default router;
```

**Register the route in `backend/src/index.ts`:**

Find the section around line 55 and add:

```typescript
// API Routes
import agentRoutes from './api/routes/agentRoutes';
import greeterRoutes from './api/routes/greeterRoutes'; // ADD THIS

app.use('/api/agents', agentRoutes);
app.use('/api/greeter', greeterRoutes); // ADD THIS
```

---

### Step 4: Test via API

**Make sure server is running:**

```bash
npm run dev
```

**Test with curl:**

```bash
curl -X POST http://localhost:8000/api/greeter/greet \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice"}'
```

**Or PowerShell (Windows):**

```powershell
$body = @{ name = "Alice" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/greeter/greet" -Method POST -ContentType "application/json" -Body $body
```

**Or use Postman/Insomnia:**
- Method: POST
- URL: `http://localhost:8000/api/greeter/greet`
- Body: `{"name": "Alice"}`

**Expected response:**

```json
{
  "success": true,
  "greeting": "Hello Alice! Wonderful to meet you...",
  "timestamp": "2024-01-30T12:00:00.000Z"
}
```

**🎉 Congratulations! You just created your first feature!**

---

## 🧭 What's Next?

### Option 1: Learn the Workflow

Read **WORKFLOW_GUIDE.md** to understand:
- Daily development workflow
- Complete feature development process
- Testing methods
- Best practices

### Option 2: Understand the Architecture

Read **FOLDER_GUIDE.md** to learn:
- What each folder is for
- What types of files go where
- Naming conventions
- Decision trees for code placement

### Option 3: Deep Dive into Development

Read **DEVELOPMENT_GUIDE.md** for:
- Best practices
- Common patterns
- Code examples
- Professional tips

---

## 📋 Development Workflow Summary

### Daily Routine

```
1. PLAN
   ↓
2. CODE (write function)
   ↓
3. QUICK TEST (npx tsx src/test-feature.ts)
   ↓
4. ADD API (create route)
   ↓
5. FULL TEST (Postman/Insomnia)
   ↓
6. COMMIT (git add, commit, push)
```

### File Organization

```
Agent Logic       → src/agents/nodes/[feature].ts
API Endpoints     → src/api/routes/[feature]Routes.ts
Quick Tests       → src/test-[feature].ts
Data Models       → src/models/[entity].ts
Validation        → src/schemas/[entity]Schema.ts
Utilities         → src/utils/[purpose].ts
```

### Testing Methods

**Method 1: Quick Test File** (Use during development)
```bash
npx tsx src/test-feature.ts
```
- ⚡ Fastest
- 🐛 Easy to debug
- 🔄 Quick iterations

**Method 2: API Testing** (Use before deploying)
```bash
# Terminal 1
npm run dev

# Terminal 2 / Postman
curl http://localhost:8000/api/...
```
- ✅ Complete flow
- 🌐 Exactly how frontend uses it

**Method 3: Automated Tests** (Professional)
```bash
npm test
```
- 🤖 Automated
- ✅ Catch bugs early

---

## 🎓 Learning Path

### Day 1-2: Setup & First Feature
- ✅ Complete Quick Start above
- ✅ Create your own simple feature
- ✅ Test with quick test file

### Day 3-5: API Integration
- ✅ Add API routes to your features
- ✅ Test with Postman/Insomnia
- ✅ Read WORKFLOW_GUIDE.md

### Week 2: Best Practices
- ✅ Add validation to your routes
- ✅ Improve error handling
- ✅ Add logging
- ✅ Read DEVELOPMENT_GUIDE.md

### Week 3: Advanced Features
- ✅ Create complex workflows (graphs)
- ✅ Add agent tools
- ✅ Write automated tests
- ✅ Read FOLDER_GUIDE.md

---

## 🔍 Troubleshooting

### "Cannot find module" error

```bash
cd backend
rm -rf node_modules package-lock.json
npm install
```

### "OPENAI_API_KEY not found"

```bash
# Check your .env file
cat .env  # Mac/Linux
type .env  # Windows CMD
Get-Content .env  # Windows PowerShell

# Should show: OPENAI_API_KEY=sk-...
# If missing, add it to .env
```

### "Port 8000 already in use"

```bash
# Windows PowerShell
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Mac/Linux
lsof -i :8000
kill -9 <PID>

# Or change port in .env
PORT=8001
```

### "TypeScript errors"

```bash
# Check your tsconfig.json exists
# Reinstall TypeScript
npm install -D typescript
npm install -D tsx
```

### Test file not working

```bash
# Make sure you're in backend directory
cd backend
pwd  # Should show: .../OmniMindv03/backend

# Check .env is in backend directory
ls .env  # Should exist

# Run with full path
npx tsx src/test-agent.ts
```

### Server starts but routes don't work

```bash
# Check route is registered in index.ts
# Should have:
import myRoutes from './api/routes/myRoutes';
app.use('/api/my', myRoutes);

# Restart server
# Press Ctrl+C to stop
npm run dev
```

---

## 📞 Quick Reference

### Common Commands

```bash
# Start development
npm run dev

# Quick test
npx tsx src/test-[feature].ts

# Run tests
npm test

# Build
npm run build

# Lint
npm run lint

# Format
npm run format
```

### File Locations

```
Backend code:     backend/src/
Agent logic:      backend/src/agents/nodes/
API routes:       backend/src/api/routes/
Quick tests:      backend/src/test-*.ts
Main entry:       backend/src/index.ts
Environment:      backend/.env
```

### Useful URLs (when server running)

```
Health check:     http://localhost:8000/health
Root:             http://localhost:8000/
Your API:         http://localhost:8000/api/[your-route]
```

---

## 🎯 Key Takeaways

1. **Always start with quick test files** (fastest way to develop)
2. **Test often** (after every small change)
3. **Add logging everywhere** (helps debugging)
4. **Follow the folder structure** (keeps code organized)
5. **Read error messages carefully** (they tell you what's wrong)
6. **One feature at a time** (don't try to do everything at once)
7. **Use the guides** (they have everything you need)

---

## 📖 Documentation Map

```
START HERE
    ↓
GETTING_STARTED.md (this file)
    ↓
Did your setup work?
    ↓ YES
    ↓
Ready to build features?
    ↓ YES
    ↓
WORKFLOW_GUIDE.md
(Complete step-by-step for building features)
    ↓
Need to know where code goes?
    ↓ YES
    ↓
FOLDER_GUIDE.md
(Explains every folder and file type)
    ↓
Want best practices?
    ↓ YES
    ↓
DEVELOPMENT_GUIDE.md
(Patterns, examples, tips)
    ↓
Need a command reference?
    ↓ YES
    ↓
COMMANDS.md
(All available commands)
```

---

## 🚀 You're Ready!

You now have:
- ✅ A working development environment
- ✅ Understanding of the basic workflow
- ✅ Your first feature working
- ✅ Knowledge of where to find help

**Start building! And remember:**
- The guides are here to help you
- Test early and often
- Don't be afraid to experiment
- Read the error messages
- One step at a time

**Happy coding! 🎉**

---

## 📚 Additional Resources

- **WORKFLOW_GUIDE.md** - Detailed feature development workflow
- **FOLDER_GUIDE.md** - Complete folder structure explanation
- **DEVELOPMENT_GUIDE.md** - Best practices and patterns
- **COMMANDS.md** - Command reference
- **ARCHITECTURE.md** - System architecture overview
- **STRUCTURE.md** - Project structure details

Need help? Check the guides above - they cover everything! 💪