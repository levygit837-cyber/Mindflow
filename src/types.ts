/**
 * MindFlow CLI — Type Definitions
 */

// ============================================================================
// Agent Types
// ============================================================================

export type AgentRole = "orchestrator" | "analyst" | "coder" | "reviewer" | "researcher" | "planner";

export type AgentStatus = "idle" | "thinking" | "working" | "waiting" | "complete" | "error";

export interface Agent {
    id: string;
    name: string;
    role: AgentRole;
    status: AgentStatus;
    color: string;
    currentTask?: string;
    summary?: string; // Summarized status from local model
}

// ============================================================================
// Message Types
// ============================================================================

export type MessageType = "user" | "agent" | "system" | "orchestrator" | "summary" | "error";

export interface Message {
    id: string;
    type: MessageType;
    content: string;
    timestamp: Date;
    // Agent-specific fields
    agentId?: string;
    agentName?: string;
    agentRole?: AgentRole;
    agentColor?: string;
    // Status fields
    isThinking?: boolean;
    isComplete?: boolean;
    // System fields
    systemType?: "team_created" | "mission_started" | "mission_complete" | "error";
}

// ============================================================================
// Team / Mission Types
// ============================================================================

export interface Team {
    id: string;
    name: string;
    leaderId: string;
    members: Agent[];
    createdAt: Date;
}

export type MissionStatus = "pending" | "running" | "complete" | "failed" | "cancelled";

export interface Mission {
    id: string;
    type: string;
    agentId: string;
    agentName: string;
    status: MissionStatus;
    progress?: number; // 0-100
    summary?: string; // Summarized from local model
    startedAt?: Date;
    completedAt?: Date;
}

// ============================================================================
// AppState Types
// ============================================================================

export interface AppState {
    // Connection
    connected: boolean;
    backendUrl: string;

    // Session
    sessionId: string | null;
    messages: Message[];

    // Team
    currentTeam: Team | null;
    activeAgents: Agent[];
    missions: Mission[];

    // UI State
    isProcessing: boolean;
    inputDisabled: boolean;
    verboseMode: boolean;

    // Summarizer
    summaries: Record<string, string>; // agentId -> summary text
    lastSummaryUpdate: number; // timestamp
}

// ============================================================================
// SSE Event Types
// ============================================================================

export type SseEventType =
    | "agent_status"
    | "agent_message"
    | "mission_update"
    | "team_update"
    | "summary"
    | "error"
    | "complete";

export interface SseEvent<T = unknown> {
    type: SseEventType;
    data: T;
    timestamp?: string;
}