import { AppState, Message, Agent, Mission } from "../types";

/**
 * MindFlow CLI - In-memory state management (simple Redux-like pattern).
 * No external state library needed - pure functional updates.
 */

let state: AppState = createInitialState();
let listeners: Set<() => void> = new Set();

function createInitialState(): AppState {
    return {
        connected: false,
        backendUrl: process.env.MINDFLOW_BACKEND_URL || "http://localhost:8000",
        sessionId: null,
        messages: [],
        currentTeam: null,
        activeAgents: [],
        missions: [],
        isProcessing: false,
        inputDisabled: false,
        verboseMode: false,
        summaries: {},
        lastSummaryUpdate: 0,
    };
}

export function getState(): AppState {
    return { ...state };
}

export function setState(updater: (prev: AppState) => AppState): void {
    const nextState = updater(state);
    state = nextState;
    notifyListeners();
}

export function subscribe(listener: () => void): () => void {
    listeners.add(listener);
    return () => {
        listeners.delete(listener);
    };
}

function notifyListeners(): void {
    for (const listener of listeners) {
        listener();
    }
}

// ============================================================================
// Action Creators
// ============================================================================

export function setUserMessage(content: string): void {
    const msg: Message = {
        id: generateId(),
        type: "user",
        content,
        timestamp: new Date(),
    };
    setState((prev) => ({
        ...prev,
        messages: [...prev.messages, msg],
    }));
}

export function setAgentMessage(
    agentId: string,
    agentName: string,
    content: string,
    agentColor?: string
): void {
    const msg: Message = {
        id: generateId(),
        type: "agent",
        content,
        timestamp: new Date(),
        agentId,
        agentName,
        agentColor,
    };
    setState((prev) => ({
        ...prev,
        messages: [...prev.messages, msg],
    }));
}

export function updateAgentStatus(
    agentId: string,
    status: Agent["status"],
    summary?: string
): void {
    setState((prev) => {
        const agents = prev.activeAgents.map((a) =>
            a.id === agentId
                ? { ...a, status, summary: summary ?? a.summary }
                : a
        );
        const summaries = { ...prev.summaries };
        if (summary) summaries[agentId] = summary;
        return {
            ...prev,
            activeAgents: agents,
            summaries,
            lastSummaryUpdate: Date.now(),
        };
    });
}

export function addAgent(agent: Agent): void {
    setState((prev) => ({
        ...prev,
        activeAgents: [...prev.activeAgents, agent],
    }));
}

export function setProcessing(isProcessing: boolean): void {
    setState((prev) => ({
        ...prev,
        isProcessing,
        inputDisabled: isProcessing,
    }));
}

export function setConnected(connected: boolean): void {
    setState((prev) => ({ ...prev, connected }));
}

export function setSessionId(sessionId: string | null): void {
    setState((prev) => ({ ...prev, sessionId }));
}

function generateId(): string {
    return Math.random().toString(36).substring(2, 10);
}