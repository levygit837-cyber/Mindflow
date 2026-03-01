# OmniMind Project Context

**Status:** Phase 3 — Tool Registry & Decomposition Thinking (DT)
**Date:** 2026-03-01

## 1. Goal
Implement the final major architectural layers of the OmniMind backend: a centralized Tool Registry leveraging the `deepagents` framework and a multi-step Decomposition Thinking (DT) pipeline for complex tasks.

## 2. Completed Phases
- **Phase 1: Structure** (100% done) — Clean folder separation (runtime, agents, schemas, infra, api, grpc, storage, workers).
- **Phase 1.5: Security Foundation** (100% done) — Middleware for auth, rate limiting, request context, security headers, structured logging, resilience (retry/circuit breaker), and input sanitization.
- **Phase 2: Agent System** (100% done) — 5 personality definitions (Coder, Analyst, Researcher, ArchTech, Critic), AgentRegistry, and basic Orchestrator routing (router.py, graph.py).

## 3. Current Phase: Phase 3 (Tool Registry & DT)
- **Tool Registry:** Formalizing tool scopes. Utilizing `deepagents` for core tools (read/write/etc.).
- **Sandbox Strategy:** Mandatory background sandbox for shell commands.
- **Decomposition Thinking:** Complexity-gated (threshold default 0.65) multi-step reasoning.

## 4. Key Constraints
- **Python Backend Only:** No TS migration.
- **DeepAgents Integration:** Use existing framework capabilities.
- **Security First:** Maintain Phase 1.5 standards.
- **No Circular Imports:** Strict dependency graph enforcement.

## 5. Ideal Architecture Progress
- **Structural Alignment:** 100% (Folders match `ARCHITECTURE_PLAN.md`, shims in place).
- **Functional Alignment:** 75% (Security and Basic Agents done; DT and full Tool Registry pending).
