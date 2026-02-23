# OmniMind — Project Overview

## Purpose
OmniMind is a personal AI agent platform with deep multi-step task resolution. Uses LangGraph + deepagents framework. Has a single Next.js 16 fullstack app (no separate backend process).

## Tech Stack
- **Framework:** Next.js 16 App Router + TypeScript 5.9
- **Agent:** LangGraph (`@langchain/langgraph`) + deepagents v1.7 + LangChain core
- **LLM Providers:** Anthropic, OpenAI, Google (VertexAI / GenAI), Ollama
- **State:** Zustand v5 (client-side agent chat store)
- **Streaming:** SSE (ReadableStream) via `/api/agent/chat` route
- **DB:** PostgreSQL (checkpointer for LangGraph memory)
- **UI:** React 19, TailwindCSS v4 (CSS-first, no tailwind.config.js), Radix UI, lucide-react
- **Package manager:** pnpm

## Key Architecture
- `src/lib/agent/` — agent core: index.ts (factory), deep-agent-config.ts (createDeepAgent), stream.ts (SSE helpers), chat-stream-normalizer.ts (LangGraph event → StreamEvent), safe-backend.ts (command blocklist), log-bus.ts (pub/sub singleton)
- `src/app/api/agent/chat/route.ts` — POST endpoint: streams agent responses via SSE, publishes to logBus
- `src/app/api/agent/logs/stream/route.ts` — GET SSE endpoint: streams all agent events to /logs page
- `src/lib/swarm/` — multi-agent swarm (orchestrator, coder, analyst, reviewer)
- `src/stores/agent-store.ts` — Zustand store with contentParts (ThinkingPart, TextPart, ToolCallPart, etc.)
- `src/hooks/use-agent-chat.ts` — SSE consumer hook
- `src/hooks/use-log-stream.ts` — LogBus SSE consumer hook for /logs page
- `src/components/agent/` — ThinkingBlock, ResponseBlock, ToolCallBlock, AgentStepsBlock, ChatInterface
- `src/components/logs/log-viewer.tsx` — real-time log viewer with filters

## Routing
- `/` — Dashboard
- `/agent` — Deep Agent chat
- `/swarm` — Multi-agent swarm
- `/logs` — Real-time agent event log viewer
- `/settings` — LLM provider settings
