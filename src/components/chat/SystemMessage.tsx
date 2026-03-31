import { AgentStatus } from "../../types";

interface SystemMessageProps {
    content: string;
    systemType?: "team_created" | "mission_started" | "mission_complete" | "error";
}

const TYPE_ICONS: Record<string, string> = {
    team_created: "\U0001F465",
    mission_started: "\U0001F680",
    mission_complete: "\u2705",
    error: "\u274C",
};

export function renderSystemMessage(props: SystemMessageProps): string {
    const icon = props.systemType ? TYPE_ICONS[props.systemType] || "\u2139" : "\u2139";
    return `${icon} ${props.content}`;
}