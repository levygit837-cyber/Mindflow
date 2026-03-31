import { renderUserMessage } from "../chat/UserMessage";

interface InputBarProps {
    onSubmit: (text: string) => void;
    disabled?: boolean;
    placeholder?: string;
}

/**
 * InputBar placeholder render function.
 * The actual input is handled by Ink's useInput hook in the REPL.
 * Returns a visual prompt indicator.
 */
export function renderInputBar(disabled?: boolean): string {
    const prompt = disabled ? "..." : ">";
    return `${prompt} `;
}

/**
 * Check if the input is a command (starts with /).
 */
export function isCommand(input: string): boolean {
    return input.startsWith("/");
}

/**
 * Parse command from input. Returns { command, args }.
 */
export function parseCommand(input: string): { command: string; args: string } {
    if (!input.startsWith("/")) {
        return { command: "", args: input };
    }
    const parts = input.slice(1).split(" ");
    return {
        command: parts[0]?.toLowerCase() || "",
        args: parts.slice(1).join(" "),
    };
}