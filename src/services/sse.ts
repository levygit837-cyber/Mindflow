import { SseEvent, SseEventType, Agent, Message } from "../types";
import { getState, setState, setConnected, addAgent, updateAgentStatus, setAgentMessage, setProcessing } from "../state/store";

/**
 * MindFlow CLI - SSE (Server-Sent Events) Service
 *
 * Connects to the MindFlow backend SSE endpoint for real-time streaming.
 * Uses EventSource for browser-native SSE support.
 */

let eventSource: EventSource | null = null;

/**
 * Connect to the MindFlow backend SSE stream.
 */
export function connectSSE(sessionId: string): void {
    const { backendUrl } = getState();
    const url = `${backendUrl}/api/sse/${sessionId}`;

    if (eventSource) {
        eventSource.close();
    }

    eventSource = new EventSource(url);

    eventSource.onopen = () => {
        setConnected(true);
    };

    eventSource.onerror = () => {
        setConnected(false);
        eventSource = null;
    };

    // Handle typed events
    eventSource.addEventListener("event", (event: any) => {
        try {
            const sseEvent: SseEvent = JSON.parse(event.data);
            handleSseEvent(sseEvent);
        } catch (e) {
            console.error("Failed to parse SSE event:", e);
        }
    });
}

/**
 * Disconnect from SSE stream.
 */
export function disconnectSSE(): void {
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
    setConnected(false);
}

/**
 * Handle a single SSE event based on its type.
 */
function handleSseEvent(event: SseEvent): void {
    switch (event.type) {
        case "agent_status":
            handleAgentStatus(event.data);
            break;
        case "agent_message":
            handleAgentMessage(event.data);
            break;
        case "mission_update":
            handleMissionUpdate(event.data);
            break;
        case "team_update":
            handleTeamUpdate(event.data);
            break;
        case "summary":
            handleSummary(event.data);
            break;
        case "error":
            handleError(event.data);
            break;
        case "complete":
            handleComplete(event.data);
            break;
    }
}

function handleAgentStatus(data: unknown): void {
    const status = data as { agentId: string; status: string; summary?: string };
    updateAgentStatus(status.agentId, status.status as Agent["status"], status.summary);
}

function handleAgentMessage(data: unknown): void {
    const msg = data as { agentId: string; agentName: string; content: string; color?: string };
    setAgentMessage(msg.agentId, msg.agentName, msg.content, msg.color);
}

function handleMissionUpdate(data: unknown): void {
    const mission = data as { missionId: string; agentId: string; status: string; progress?: number; summary?: string };
    if (mission.summary) {
        updateAgentStatus(mission.agentId, mission.status as Agent["status"], mission.summary);
    }
}

function handleTeamUpdate(data: unknown): void {
    const team = data as { agents: Agent[] };
    setState((prev) => ({
        ...prev,
        activeAgents: team.agents,
    }));
}

function handleSummary(data: unknown): void {
    const summary = data as { agentId: string; summary: string };
    updateAgentStatus(summary.agentId, "complete", summary.summary);
    setAgentMessage(summary.agentId, "summarizer", summary.summary);
    setProcessing(false);
}

function handleError(data: unknown): void {
    const error = data as { message: string; agentId?: string };
    if (error.agentId) {
        setAgentMessage(error.agentId, "system", `Error: ${error.message}`);
        setProcessing(false);
    }
}

function handleComplete(_data: unknown): void {
    setProcessing(false);
}

/**
 * Send a prompt to the backend (HTTP POST, not SSE).
 */
export async function sendPrompt(sessionId: string, prompt: string): Promise<void> {
    const { backendUrl } = getState();
    setProcessing(true);

    try {
        const response = await fetch(`${backendUrl}/api/session/${sessionId}/prompt`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content: prompt }),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
    } catch (error) {
        console.error("Failed to send prompt:", error);
        setProcessing(false);
        throw error;
    }
}