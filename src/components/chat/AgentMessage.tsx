/**
 * MindFlow CLI — Agent Message Renderer
 * Renders agent messages with badge and status indicator.
 */

import { ROLE_COLORS, ROLE_EMOJIS } from "../design-system";
import { AgentRole, AgentStatus } from "../../types";

interface AgentMessageProps {
    agentName: string;
    agentRole: AgentRole;
    content: string;
    status?: AgentStatus;
    timestamp?: Date;
    isThinking?: boolean;
}

const STATUS_TEXT: Record<AgentStatus, string> = {
    idle: "",
    thinking: "Thinking...",
    working: "Working...",
    waiting: "Waiting...",
    complete: "",
    error: "Error",
};

export function renderAgentMessage(props: AgentMessageProps): string {
    const emoji = ROLE_EMOJIS[props.agentRole] || "?";
    const colorKey = ROLE_COLORS[props.agentRole] || "white";
    const statusText = props.isThinking
        ? STATUS_TEXT.thinking
        : props.status
            ? STATUS_TEXT[props.status]
            : "";

    let lines: string[] = [];

    // Agent header line
    let headerLine = `${emoji} ${props.agentName}`;
    if (statusText) {
        headerLine = `${headerLine} → ${statusText}`;
    }
    lines.push(headerLine);

    // Content line
    if (!props.isThinking && props.content) {
        lines.push(`  ${props.content}`);
    }

    return lines.join("\n");
}