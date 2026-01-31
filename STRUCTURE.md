# 📂 OmniMind v03 - Complete Project Structure

This document provides a detailed overview of the entire project structure with explanations for each directory and file.

## 🌳 Complete Directory Tree

```
OmniMindv03/
│
├── backend/                          # TypeScript/Node.js Backend
│   ├── src/                         # Source code
│   │   │
│   │   ├── agents/                  # 🤖 LangGraph AI Agents
│   │   │   ├── nodes/               # Individual agent nodes
│   │   │   │   ├── researcherNode.ts
│   │   │   │   ├── analyzerNode.ts
│   │   │   │   └── responderNode.ts
│   │   │   │
│   │   │   ├── graphs/              # Complete agent workflows
│   │   │   │   ├── exampleAgentGraph.ts   ✓ Created
│   │   │   │   ├── conversationGraph.ts
│   │   │   │   └── taskAgentGraph.ts
│   │   │   │
│   │   │   └── tools/               # Custom tools for agents
│   │   │       ├── webSearchTool.ts
│   │   │       ├── databaseTool.ts
│   │   │       └── calculatorTool.ts
│   │   │
│   │   ├── api/                     # 🌐 REST API Layer
│   │   │   ├── routes/              # API endpoints
│   │   │   │   ├── agentRoutes.ts   ✓ Created
│   │   │   │   ├── chatRoutes.ts
│   │   │   │   ├── userRoutes.ts
│   │   │   │   └── healthRoutes.ts
│   │   │   │
│   │   │   └── middleware/          # Express middleware
│   │   │       ├── authMiddleware.ts
│   │   │       ├── validationMiddleware.ts
│   │   │       ├── errorHandler.ts
│   │   │       └── rateLimiter.ts
│   │   │
│   │   ├── config/                  # ⚙️ Configuration
│   │   │   ├── index.ts             ✓ Created
│   │   │   ├── database.ts
│   │   │   └── constants.ts
│   │   │
│   │   ├── models/                  # 📊 Data Models
│   │   │   ├── User.ts
│   │   │   ├── Conversation.ts
│   │   │   ├── Message.ts
│   │   │   └── Session.ts
│   │   │
│   │   ├── services/                # 💼 Business Logic
│   │   │   ├── agentService.ts
│   │   │   ├── chatService.ts
│   │   │   ├── userService.ts
│   │   │   └── authService.ts
│   │   │
│   │   ├── types/                   # 📝 TypeScript Types
│   │   │   ├── index.ts             ✓ Created
│   │   │   ├── agent.types.ts
│   │   │   ├── api.types.ts
│   │   │   └── database.types.ts
│   │   │
│   │   ├── utils/                   # 🛠️ Utilities
│   │   │   ├── logger.ts            ✓ Created
│   │   │   ├── encryption.ts
│   │   │   ├── validation.ts
│   │   │   └── helpers.ts
│   │   │
│   │   └── index.ts                 # 🚀 Entry Point   ✓ Created
│   │
│   ├── tests/                       # 🧪 Tests
│   │   ├── unit/
│   │   │   ├── agents/
│   │   │   ├── services/
│   │   │   └── utils/
│   │   │
│   │   ├── integration/
│   │   │   ├── api/
│   │   │   └── agents/
│   │   │
│   │   └── e2e/
│   │       └── workflows/
│   │
│   ├── dist/                        # 📦 Compiled JavaScript (generated)
│   │
│   ├── node_modules/                # 📚 Dependencies (generated)
│   │
│   ├── logs/                        # 📋 Application logs (generated)
│   │
│   ├── .env                         # 🔐 Environment variables (create from .env.example)
│   ├── env.example                  # 📄 Environment template   ✓ Created
│   ├── .gitignore                   # 🚫 Git ignore rules   ✓ Created
│   ├── .eslintrc.json              # 🔍 ESLint config   ✓ Created
│   ├── .prettierrc.json            # 💅 Prettier config   ✓ Created
│   ├── package.json                 # 📦 NPM configuration   ✓ Created
│   ├── tsconfig.json               # ⚡ TypeScript config   ✓ Created
│   └── README.md                    # 📖 Backend documentation
│
├── frontend/                        # 🎨 Frontend (To be generated)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   └── utils/
│   │
│   ├── public/
│   ├── package.json
│   └── README.md
│
├── README.md                        # 📘 Main project documentation   ✓ Created
├── QUICKSTART.md                    # 🚀 Quick start guide   ✓ Created
└── STRUCTURE.md                     # 📂 This file   ✓ Created
```

## 📋 Directory Descriptions

### `/backend` - Backend Root
The TypeScript/Node.js backend containing the AI agent system and REST API.

#### `/backend/src` - Source Code
All TypeScript source files before compilation.

#### `/backend/src/agents` - AI Agent System
**Purpose:** Contains all LangGraph agent implementations, workflows, and tools.

**When to use:**
- Creating new agent behaviors
- Defining agent workflows
- Adding custom tools for agents

**Key Files:**
- `graphs/exampleAgentGraph.ts` - Example of a complete agent workflow
- `nodes/` - Individual processing steps in agent workflows
- `tools/` - Reusable tools that agents can invoke

#### `/backend/src/api` - API Layer
**Purpose:** REST API endpoints and middleware for frontend communication.

**When to use:**
- Adding new API endpoints
- Implementing authentication
- Creating custom middleware

**Key Files:**
- `routes/agentRoutes.ts` - Agent interaction endpoints
- `middleware/` - Express middleware functions

#### `/backend/src/config` - Configuration
**Purpose:** Centralized configuration management with validation.

**When to use:**
- Adding new environment variables
- Configuring external services
- Managing application settings

**Key Files:**
- `index.ts` - Main configuration file with Zod validation

#### `/backend/src/models` - Data Models
**Purpose:** Database models and schemas.

**When to use:**
- Defining database entities
- Creating data structures
- Setting up ORM models

**Common patterns:**
- User models
- Chat/Message models
- Session management

#### `/backend/src/services` - Business Logic
**Purpose:** Application business logic separated from routes.

**When to use:**
- Complex business operations
- Reusable functionality
- Keeping routes clean and simple

**Best practices:**
- One service per domain (UserService, AgentService, etc.)
- Services should be testable independently
- Services orchestrate models and external APIs

#### `/backend/src/types` - TypeScript Types
**Purpose:** Shared type definitions and interfaces.

**When to use:**
- Creating shared types
- Defining API contracts
- Type safety across modules

**Key Files:**
- `index.ts` - Central type definitions

#### `/backend/src/utils` - Utilities
**Purpose:** Helper functions and utilities.

**When to use:**
- Common functionality
- Helper functions
- Shared utilities

**Key Files:**
- `logger.ts` - Winston-based logging

#### `/backend/tests` - Test Suite
**Purpose:** Unit, integration, and end-to-end tests.

**Structure:**
- `unit/` - Test individual functions/classes
- `integration/` - Test module interactions
- `e2e/` - Test complete workflows

### `/frontend` - Frontend Application
To be generated using AI tools. Will contain the user interface for interacting with the backend.

## 🎯 Where to Add Your Code

### Adding a New Agent Node
**Location:** `backend/src/agents/nodes/yourNode.ts`

```typescript
export async function yourNode(state: AgentState) {
  // Your logic here
  return { ...state, updates };
}
```

### Adding a New Agent Graph
**Location:** `backend/src/agents/graphs/yourGraph.ts`

Follow the pattern in `exampleAgentGraph.ts`

### Adding a New API Endpoint
**Location:** `backend/src/api/routes/yourRoutes.ts`

```typescript
import { Router } from 'express';
const router = Router();

router.post('/your-endpoint', async (req, res) => {
  // Your logic
});

export default router;
```

Don't forget to register in `index.ts`:
```typescript
import yourRoutes from './api/routes/yourRoutes';
app.use('/api/your-path', yourRoutes);
```

### Adding a New Service
**Location:** `backend/src/services/yourService.ts`

```typescript
export class YourService {
  async yourMethod() {
    // Business logic
  }
}
```

### Adding Custom Tools
**Location:** `backend/src/agents/tools/yourTool.ts`

```typescript
export async function yourTool(input: any) {
  // Tool implementation
  return result;
}
```

### Adding Middleware
**Location:** `backend/src/api/middleware/yourMiddleware.ts`

```typescript
import { Request, Response, NextFunction } from 'express';

export function yourMiddleware(req: Request, res: Response, next: NextFunction) {
  // Middleware logic
  next();
}
```

## 🔄 Data Flow

```
Frontend Request
    ↓
Express Server (index.ts)
    ↓
Middleware (validation, auth, etc.)
    ↓
Route Handler (api/routes/)
    ↓
Service Layer (services/)
    ↓
Agent/Tool (agents/)  ←→  LLM API
    ↓
Database (models/)
    ↓
Response back to Frontend
```

## 📝 File Naming Conventions

- **Files:** camelCase (e.g., `agentRoutes.ts`)
- **Directories:** lowercase (e.g., `agents/`)
- **Classes:** PascalCase (e.g., `class UserService`)
- **Interfaces:** PascalCase (e.g., `interface AgentState`)
- **Functions:** camelCase (e.g., `function processInput`)
- **Constants:** UPPER_SNAKE_CASE (e.g., `const MAX_RETRIES`)

## 🎨 Code Organization Principles

### 1. Separation of Concerns
Each directory has a single responsibility:
- Routes handle HTTP
- Services handle business logic
- Models handle data
- Utils handle helpers

### 2. Dependency Direction
```
Routes → Services → Models
       → Agents → Tools
       → Utils
```

Higher-level modules depend on lower-level modules, never the reverse.

### 3. Type Safety
All files use TypeScript with strict mode enabled. Share types through `types/` directory.

### 4. Modularity
Each feature should be self-contained and reusable.

## 🚀 Development Workflow

1. **Start with types** - Define interfaces in `types/`
2. **Create models** - If database entities needed
3. **Write services** - Implement business logic
4. **Add routes** - Expose via REST API
5. **Create agents** - Build AI workflows
6. **Add tests** - Ensure reliability
7. **Update docs** - Keep documentation current

## 📊 Current Status

✅ **Completed:**
- Project structure
- TypeScript configuration
- Core utilities (logger, config)
- Example agent implementation
- API routes foundation
- Type definitions
- Development tooling (ESLint, Prettier)

⬜ **To Do:**
- Implement authentication
- Add database integration
- Create additional agent nodes
- Write comprehensive tests
- Set up CI/CD
- Generate frontend

## 🔗 Related Documentation

- See `README.md` for project overview
- See `QUICKSTART.md` for setup instructions
- See `backend/src/types/index.ts` for type documentation
- See individual files for inline documentation

---

**Last Updated:** Initial creation
**Maintainer:** Keep this updated as project evolves