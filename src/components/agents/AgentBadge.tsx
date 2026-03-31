/**
 * MindFlow CLI — Agent Badge Component
 * Renders an agent identifier with emoji, name, and role color.
 */

import { ROLE_EMOJIS, ROLE_COLORS } from "../design-system";
import { AgentRole } from "../../types";

interface AgentBadgeProps {
    name: string;
    role: AgentRole;
    status?: "idle" | "thinking" | "working" | "waiting" | "complete" | "error";
}

const STATUS_ICONS: Record<string, string> = {
    idle: "\u25CB",       // ○
    thinking: "\u27E8",     // ⟐
    working: "\u25CF",      // ●
    waiting: "\u25CB",      // ○
    complete: "\u2713",     // ✓
    error: "\u2717",       // ✗
};

export function AgentBadge({ name, role, status = "idle" }: AgentBadgeProps) {
    const emoji = ROLE_EMOJIS[role] || "?";
    const colorKey = ROLE_COLORS[role] || "white";
    const statusIcon = STATUS_ICONS[status] || "?";

    // Format name with status indicator using raw unicode characters
    return {
        emoji,
        name,
        colorKey,
        statusIcon,
        displayText: `${emoji} ${name.padEnd(12)}${statusIcon}`
    };
}

/**
 * Get the agent's current display representation as a string.
 * This is used for non-JSX terminal output.
 */
export function formatAgentBadge(name: string, role: AgentRole, status: string): string {
    const emoji = ROLE_EMOJIS[role] || "?";
    const statusIcon = STATUS_ICONS[status] || "?";
    return `${emoji} ${name.padEnd(12)}${statusIcon}`;
}