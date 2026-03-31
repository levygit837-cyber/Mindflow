import { Message } from "../../types";
import { renderUserMessage } from "./UserMessage";
import { renderAgentMessage } from "./AgentMessage";
import { renderSystemMessage } from "./SystemMessage";

interface ChatHistoryProps {
    messages: Message[];
}

/**
 * Render all messages in the chat history.
 * Returns an array of strings, one per message.
 */
export function renderChatHistory(props: ChatHistoryProps): string[] {
    return props.messages.map(msg => {
        switch (msg.type) {
            case "user":
                return renderUserMessage({
                    content: msg.content,
                    timestamp: msg.timestamp,
                });

            case "agent":
                return renderAgentMessage({
                    agentName: msg.agentName || "Unknown",
                    agentRole: msg.agentRole || "analyst",
                    content: msg.content,
                    status: msg.isComplete ? "complete" : msg.isThinking ? "thinking" : undefined,
                    timestamp: msg.timestamp,
                    isThinking: msg.isThinking,
                });

            case "system":
                return renderSystemMessage({
                    content: msg.content,
                    systemType: msg.systemType,
                });

            case "orchestrator":
                return `\U0001F9E0 ${msg.content}`;

            case "summary":
                return `\u2728 ${msg.content}`;

            case "error":
                return `\u274C Error: ${msg.content}`;

            default:
                return msg.content;
        }
    });
}