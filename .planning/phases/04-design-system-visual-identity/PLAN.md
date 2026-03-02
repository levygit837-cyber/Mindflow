# Plan: Phase 4 — Design System & Visual Identity

**Goal:** Define and implement the OmniMind Design System across CLI and a new modern web frontend, focusing on "Deep Reasoning" visualization and agent personalities.

---

## 4.1 — Brand & Design Tokens
**Objective:** Establish the foundational visual tokens for OmniMind (Neural Dark, Glass Box).

- [ ] **Task 4.1.1:** Define `tokens.json` with brand colors, spacing, and typography (Neural Dark).
- [ ] **Task 4.1.2:** Design distinct icons/avatars for each of the 5 Agent Personalities.
- [ ] **Task 4.1.3:** Create a unified palette for "Reasoning" vs. "Action" states.
- [ ] **Validation:** Visual review of tokens and agent assets.

## 4.2 — Terminal UX Overhaul (CLI DS)
**Objective:** Transform the `omnimind_cli` into a rich, terminal-first design experience.

- [ ] **Task 4.2.1:** Implement `render/theme.py` in `omnimind_cli` using `Rich` theme system.
- [ ] **Task 4.2.2:** Redesign `ChatStreamRenderer` with panels, pulses, and structured headers for each agent.
- [ ] **Task 4.2.3:** Add live progress bars/spinners for background agent tasks (System 2 pulse).
- [ ] **Task 4.2.4:** Implement hierarchical rendering for "Thought" vs. "Output" (Reasoning Tree equivalent).
- [ ] **Validation:** Run `omnimind chat` and verify the new visual flow.

## 4.3 — Modern Web Frontend Scaffold
**Objective:** Scaffold a modern, concise, and original web frontend (React/Vite).

- [ ] **Task 4.3.1:** Initialize `frontend/` with Vite + React + TypeScript + Vanilla CSS.
- [ ] **Task 4.3.2:** Implement a "Glassmorphic" layout with sidebar and main agent viewport.
- [ ] **Task 4.3.3:** Build a custom SSE client hook `useOmniStream` to consume backend events.
- [ ] **Task 4.3.4:** Create the base `AgentDashboard` component with the "Neural Dark" theme.
- [ ] **Validation:** Run the frontend and connect to backend stream (successful login/connect).

## 4.4 — Reasoning & DT Visualization (The "Glass Box")
**Objective:** Implement the "Glass Box" philosophy through advanced UI components.

- [ ] **Task 4.4.1:** Build the `ReasoningTree` component (collapsible hierarchy of thoughts).
- [ ] **Task 4.4.2:** Implement "Agent State" cards showing which personality is active and its current tool scope.
- [ ] **Task 4.4.3:** Add "Confidence Heatmaps" or "Stochastic Shimmer" for low-confidence model outputs.
- [ ] **Task 4.4.4:** Integrate human-in-the-loop (HITL) intervention points in the UI.
- [ ] **Validation:** End-to-end flow showing a complex task (DT) visually updating on the web frontend.

---

## Success Criteria
1. **Consistency:** CLI and Web Frontend use the same design tokens and language.
2. **Transparency:** "Thinking" process is clearly separated from "Output."
3. **Identity:** Each of the 5 agents has a unique, recognizable visual signature.
4. **Performance:** SSE streaming is fluid with no layout jumps.
5. **Modernity:** The web UI feels original and distinct from standard LLM chat interfaces.

## Verification Strategy
- **CLI:** Manual verification of `omnimind_cli` rendering.
- **Web:** Unit tests for components + E2E stream verification.
- **Design:** Final "Visual Polish" review against `RESEARCH.md` goals.
