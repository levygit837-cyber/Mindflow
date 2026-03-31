import { AgentRole } from "../../types";

interface UserMessageProps {
    content: string;
    timestamp?: Date;
}

export function renderUserMessage(props: UserMessageProps): string {
    const timeStr = props.timestamp
        ? formatTime(props.timestamp)
        : "";
    return `You:${timeStr ? ` ${timeStr}` : ""}\n  ${props.content}`;
}

function formatTime(date: Date): string {
    return date.toLocaleTimeString("pt-BR", {
        hour: "2-digit",
        minute: "2-digit",
    });
}