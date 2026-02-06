# OmniMind v03

A modern AI agent application built with **TypeScript**, **LangGraph**, and **DeepAgents** on the backend, with an AI-powered frontend.

## 🏗️ Architecture Overview

This project follows a clean, modular TypeScript architecture designed for scalability, type safety, and maintainability.

```
OmniMindv03/
├── backend/                    # TypeScript/Node.js backend
│   ├── src/
│   │   ├── agents/            # LangGraph agent implementations
│   │   │   ├── nodes/         # Individual agent nodes
│   │   │   ├── graphs/        # Agent workflow graphs
│   │   │   └── tools/         # Custom tools for agents
│   │   ├── api/               # API layer
│   │   │   ├── routes/        # API endpoint definitions
│   │   │   └── middleware/    # Express middleware
│   │   ├── config/            # Configuration management
│   │   ├── models/            # Data models & schemas
│   │   ├── services/          # Business logic layer
│   │   ├── types/             # TypeScript type definitions
│   │   ├── utils/             # Helper functions
│   │   └── index.ts           # Application entry point
│   ├── dist/                  # Compiled JavaScript output
│   ├── tests/                 # Unit and integration tests
│   ├── package.json
│   ├── tsconfig.json
│   └── .env.example
└── frontend/                  # AI-generated frontend
    └── (to be generated)
```

## 📁 Backend Folder Structure Explained

### `/backend/src/agents/`
The heart of your AI system where LangGraph agents live.

- **`nodes/`** - Individual processing units (nodes) that make up your agent workflows
  - Example: `researcherNode.ts`, `analyzerNode.ts`, `responderNode.ts`
  - Each node is a pure function that processes state and returns updates
  
- **`graphs/`** - Complete agent workflows built by connecting nodes
  - Example: `mainAgentGraph.ts`, `conversationGraph.ts`
  - Define the flow and logic of your AI agents
  
- **`tools/`** - Custom tools that agents can use
  - Example: `webSearchTool.ts`, `databaseTool.ts`, `calculatorTool.ts`
  - Integrations with external APIs and services

### `/backend/src/api/`
REST API layer for frontend communication.

- **`routes/`** - API endpoints organized by domain
  - Example: `agentRoutes.ts`, `conversationRoutes.ts`, `healthRoutes.ts`
  - Clean separation of concerns
  
- **`middleware/`** - Express middleware functions
  - Authentication, validation, logging, error handling

### `/backend/src/config/`
Centralized configuration management.
- Environment variables handling
- API keys and secrets
- Application settings
- Constants and enums

### `/backend/src/models/`
Data models and schemas.
- TypeScript interfaces and types
- Database models (if using ORM like Prisma, TypeORM)
- Validation schemas (Zod, Joi, etc.)

### `/backend/src/services/`
Business logic layer - keeps your routes clean and testable.
- Agent orchestration services
- Data processing services
- External API integrations
- Core business operations

### `/backend/src/types/`
TypeScript type definitions and interfaces.
- Custom type definitions
- Shared interfaces across the application
- Type guards and utilities
- API response types

### `/backend/src/utils/`
Helper functions and utilities.
- Logging utilities
- Data transformation helpers
- Common utilities
- Error handling helpers

## 🚀 Getting Started

### Prerequisites

- **Node.js** (v18+ recommended)
- **npm** or **yarn** or **pnpm**
- **TypeScript** (installed via dependencies)

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   # or
   yarn install
   # or
   pnpm install
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Run in development mode:**
   ```bash
   npm run dev
   # or
   yarn dev
   ```

5. **Build for production:**
   ```bash
   npm run build
   npm start
   ```

### Frontend Setup

*To be added after frontend generation*

## 🛠️ Technology Stack

### Backend
- **Runtime:** Node.js
- **Language:** TypeScript
- **Framework:** Express.js (or NestJS for enterprise)
- **Agent Framework:** LangGraph.js + LangChain.js
- **LLM Integration:** OpenAI, Anthropic, or other providers
- **Database:** PostgreSQL, MongoDB, or SQLite
- **Validation:** Zod or Joi
- **Testing:** Jest or Vitest
- **ORM (optional):** Prisma, TypeORM, or Drizzle

### Frontend
- *To be determined based on AI generation*
- Likely: React, Next.js, Vue, Svelte, or similar

## 📝 Development Guidelines

### Adding a New Agent Node

1. Create a new file in `src/agents/nodes/`
   ```typescript
   // src/agents/nodes/myNode.ts
   import { StateGraph } from "@langchain/langgraph";
   
   export async function myNode(state: MyStateType) {
     // Your node logic here
     return { ...state, updates };
   }
   ```

2. Register the node in your graph workflow in `src/agents/graphs/`

### Adding a New API Endpoint

1. Create or update a route file in `src/api/routes/`
   ```typescript
   // src/api/routes/myRoutes.ts
   import { Router } from 'express';
   import { myService } from '../services/myService';
   
   const router = Router();
   
   router.post('/endpoint', async (req, res) => {
     // Route handler
   });
   
   export default router;
   ```

2. Implement business logic in `src/services/`
3. Define types in `src/types/`
4. Register the route in your main app

### Project Principles

- **Type Safety First:** Leverage TypeScript's type system fully
- **Separation of Concerns:** Each module has a single responsibility
- **DRY (Don't Repeat Yourself):** Reuse code through services and utilities
- **Async/Await:** Use modern async patterns consistently
- **Error Handling:** Comprehensive error handling with custom error classes
- **Testing:** Write tests for critical functionality
- **Documentation:** Comment complex logic, use JSDoc for functions

## 🔐 Environment Variables

Create a `.env` file in the backend directory:

```env
# Server Configuration
NODE_ENV=development
PORT=8000
HOST=localhost

# API Keys
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/omnimind
# or
# DATABASE_URL=sqlite:./omnimind.db

# Security
JWT_SECRET=your_jwt_secret_here
CORS_ORIGIN=http://localhost:3000

# Logging
LOG_LEVEL=info
```

## 📦 Key NPM Scripts

```json
{
  "dev": "Start development server with hot reload",
  "build": "Compile TypeScript to JavaScript",
  "start": "Run compiled production server",
  "test": "Run test suite",
  "test:watch": "Run tests in watch mode",
  "lint": "Run ESLint",
  "format": "Format code with Prettier",
  "type-check": "Check TypeScript types without building"
}
```

## 🧪 Testing

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage
```

## 📚 Resources

- [LangGraph.js Documentation](https://langchain-ai.github.io/langgraphjs/)
- [LangChain.js Documentation](https://js.langchain.com/)
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)
- [Express.js Documentation](https://expressjs.com/)
- [Node.js Best Practices](https://github.com/goldbergyoni/nodebestpractices)

## 🎯 Next Steps

1. ✅ Set up backend folder structure
2. ⬜ Initialize npm project and install dependencies
3. ⬜ Configure TypeScript
4. ⬜ Set up Express server
5. ⬜ Create first LangGraph agent
6. ⬜ Build API endpoints
7. ⬜ Generate frontend with AI
8. ⬜ Connect frontend to backend
9. ⬜ Add authentication
10. ⬜ Deploy to production

## 🤝 Contributing

*Add contribution guidelines as needed*

## 📄 License

*Add license information*

---

**Note:** This is a living document. Update it as your project evolves!