/**
 * MindFlow CLI — Design System
 * Re-exports all design system components and tokens.
 */

export { MINDFLOW_COLORS, TERMINAL_COLORS } from "./color";
export type { ColorKey } from "./color";

/** Map agent role to its emoji identifier */
export const ROLE_EMOJIS: Record<string, string> = {
    orchestrator: "\U0001F9E0",
    analyst: "\U0001F4CA",
    coder: "\U0001F527",
    reviewer: "\U0001F50D",
    researcher: "\U0001F9EA",
    planner: "\U0001F4CB",
};

/** Map agent role to its terminal color key */
export const ROLE_COLORS: Record<string, string> = {
    orchestrator: "yellow",
    analyst: "blue",
    coder: "green",
    reviewer: "magenta",
    researcher: "red",
    planner: "yellow",
};