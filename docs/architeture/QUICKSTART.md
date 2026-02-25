# 🚀 Quick Start Guide - OmniMind v03

Get your TypeScript backend with LangGraph up and running in 5 minutes!

## Prerequisites

Before you begin, make sure you have:

- ✅ **Node.js** v18 or higher ([Download here](https://nodejs.org/))
- ✅ **npm**, **yarn**, or **pnpm** (comes with Node.js)
- ✅ An **OpenAI API key** or **Anthropic API key** ([Get one here](https://platform.openai.com/api-keys))
- ✅ A code editor (VS Code recommended)

## Step 1: Install Dependencies

Navigate to the backend directory and install all required packages:

```bash
cd backend
npm install
```

**Alternative package managers:**
```bash
# Using Yarn
yarn install

# Using pnpm
pnpm install
```

This will install:
- Express.js (API framework)
- LangChain & LangGraph (AI agent framework)
- TypeScript (type safety)
- Zod (validation)
- Winston (logging)
- And more...

## Step 2: Configure Environment Variables

1. **Copy the example environment file:**
   ```bash
   cp env.example .env
   ```

2. **Edit the `.env` file** with your settings:
   ```env
   # Minimum required configuration
   NODE_ENV=development
   PORT=8000
   
   # Add your API key (at least one required)
   OPENAI_API_KEY=sk-your-actual-openai-key-here
   # OR
   ANTHROPIC_API_KEY=sk-ant-your-actual-anthropic-key-here
   
   # Security (change this!)
   JWT_SECRET=your-super-secret-jwt-key-minimum-32-characters
   
   # Frontend URL (if different)
   CORS_ORIGIN=http://localhost:3000
   ```

   **⚠️ Important:** 
   - Never commit your `.env` file to Git
   - Use strong, unique secrets in production
   - Keep your API keys secure

## Step 3: Start the Development Server

Run the server in development mode with hot-reload:

```bash
npm run dev
```

You should see:
```
🚀 Server is running on http://localhost:8000
📝 Environment: development
✅ Health check available at http://localhost:8000/health
```

## Step 4: Test the API

### Using curl:
```bash
# Health check
curl http://localhost:8000/health

# Chat with the agent
curl -X POST http://localhost:8000/api/agents/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, AI agent!"}'
```

### Using your browser:

Open [http://localhost:8000](http://localhost:8000) to see the API welcome message.

### Using Postman or Insomnia:

1. **Create a POST request** to: `http://localhost:8000/api/agents/chat`
2. **Set Headers:** `Content-Type: application/json`
3. **Body (raw JSON):**
   ```json
   {
     "message": "What can you help me with?",
     "options": {
       "stream": false
     }
   }
   ```
4. **Send** and view the response!

## Step 5: Explore the Code

### Key Files to Understand:

1. **`src/index.ts`** - Main application entry point
   - Sets up Express server
   - Configures middleware
   - Health check endpoints

2. **`src/config/index.ts`** - Configuration management
   - Loads environment variables
   - Validates configuration
   - Type-safe config access

3. **`src/agents/graphs/exampleAgentGraph.ts`** - LangGraph agent example
   - Defines agent workflow
   - Shows how to use LangGraph nodes
   - Demonstrates streaming

4. **`src/api/routes/agentRoutes.ts`** - API routes
   - Chat endpoint
   - Streaming support
   - Request validation

5. **`src/types/index.ts`** - TypeScript types
   - Shared type definitions
   - Interface definitions
   - Type safety across the app

## Common Tasks

### Run in Production Mode

```bash
# Build the project
npm run build

# Start production server
npm start
```

### Run Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage
```

### Lint and Format Code

```bash
# Check for linting errors
npm run lint

# Fix linting errors automatically
npm run lint:fix

# Format code with Prettier
npm run format

# Type check without building
npm run type-check
```

## Next Steps

### 1. Customize Your Agent

Edit `src/agents/graphs/exampleAgentGraph.ts` to create your own agent logic:

```typescript
// Add your custom nodes
async function myCustomNode(state: AgentState) {
  // Your logic here
  return { ...state, customData: "something" };
}

// Add to your graph
workflow.addNode("my_custom_node", myCustomNode);
```

### 2. Add New API Routes

Create a new route file in `src/api/routes/`:

```typescript
// src/api/routes/myRoutes.ts
import { Router } from 'express';

const router = Router();

router.get('/my-endpoint', (req, res) => {
  res.json({ message: 'Hello from my endpoint!' });
});

export default router;
```

Then register it in `src/index.ts`:

```typescript
import myRoutes from './api/routes/myRoutes';
app.use('/api/my-routes', myRoutes);
```

### 3. Add Custom Tools

Create tools for your agents in `src/agents/tools/`:

```typescript
// src/agents/tools/myTool.ts
export async function myCustomTool(input: string) {
  // Tool logic here
  return { result: "processed data" };
}
```

### 4. Set Up a Database

Choose an ORM and add it to your project:

```bash
# For Prisma
npm install @prisma/client
npm install -D prisma

# For TypeORM
npm install typeorm reflect-metadata

# For Drizzle
npm install drizzle-orm
```

### 5. Add Authentication

Implement JWT authentication using the provided config and types.

### 6. Build Your Frontend

Use the AI to generate your frontend and connect it to these API endpoints!

## Troubleshooting

### Port Already in Use

If port 8000 is already in use, change it in your `.env`:
```env
PORT=8080
```

### TypeScript Errors

Make sure all dependencies are installed:
```bash
npm install
```

Clear the build cache:
```bash
rm -rf dist node_modules
npm install
```

### API Key Errors

Double-check your `.env` file:
- Ensure no extra spaces around the `=` sign
- Make sure the key starts with `sk-` for OpenAI
- Verify the key is valid on the provider's dashboard

### Module Not Found

Check your `tsconfig.json` path aliases match your imports.

## Useful Resources

- **LangGraph.js Docs:** https://langchain-ai.github.io/langgraphjs/
- **LangChain.js Docs:** https://js.langchain.com/
- **TypeScript Handbook:** https://www.typescriptlang.org/docs/
- **Express.js Guide:** https://expressjs.com/en/guide/routing.html
- **Zod Documentation:** https://zod.dev/

## Getting Help

- Check the main `README.md` for architecture details
- Review example code in `src/agents/` and `src/api/`
- Look at type definitions in `src/types/`

## Project Structure Recap

```
backend/
├── src/
│   ├── agents/          # AI agent logic
│   │   ├── nodes/       # Individual processing nodes
│   │   ├── graphs/      # Complete agent workflows
│   │   └── tools/       # Custom tools
│   ├── api/             # REST API
│   │   ├── routes/      # Endpoint definitions
│   │   └── middleware/  # Express middleware
│   ├── config/          # Configuration
│   ├── models/          # Data models
│   ├── services/        # Business logic
│   ├── types/           # TypeScript types
│   ├── utils/           # Utilities
│   └── index.ts         # Entry point
├── dist/                # Compiled output
├── tests/               # Tests
├── .env                 # Your environment variables
├── package.json         # Dependencies and scripts
└── tsconfig.json        # TypeScript configuration
```

---

**You're all set!** 🎉 Start building amazing AI agents with LangGraph and TypeScript!