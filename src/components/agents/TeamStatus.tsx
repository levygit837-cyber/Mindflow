/**
 * MindFlow CLI - Team Status Component
 * Shows compact team composition at the top of the screen.
 * Layer 1 (always visible) - compact view.
 */

import { Agent } from "../../types";
import { ROLE_EMOJIS } from "../design-system";
import { formatAgentBadge } from "./AgentBadge";

interface TeamStatusProps {
    agents: Agent[];
}

export function renderTeamStatus(props: TeamStatusProps): string {
    if (props.agents.length === 0) return "";

    const status = props.agents.map(a => {
        const emoji = ROLE_EMOJIS[a.role] || "?";
        const indicator =
            a.status === "working" || a.status === "thinking" ? "\u25CF" :
                a.status === "complete" ? "\u2713" :
                    "\u25CB";
        return `${indicator} ${emoji} ${a.name}`;
    }).join("   ");

    return `\U0001F465 Team: ${status}`;
}