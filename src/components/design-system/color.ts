/**
 * MindFlow CLI — Design System Colors
 *
 * Color palette for the terminal UI, mapped to semantic roles.
 */

export const MINDFLOW_COLORS = {
    // Brand
    primary: "#6366F1",     // MindFlow indigo
    secondary: "#8B5CF6",   // Purple
    accent: "#06B6D4",      // Cyan

    // Agent roles
    orchestrator: "#F59E0B",  // Amber
    analyst: "#3B82F6",       // Blue
    coder: "#10B981",         // Emerald
    reviewer: "#8B5CF6",      // Purple
    researcher: "#EC4899",    // Pink
    planner: "#F97316",       // Orange

    // Status
    success: "#22C55E",
    warning: "#EAB308",
    error: "#EF4444",
    info: "#3B82F6",

    // Text
    text: "#E5E7EB",
    textMuted: "#9CA3AF",
    textDim: "#6B7280",
    textBright: "#F9FAFB",

    // Background
    bg: "#111827",
    bgLight: "#1F2937",
    bgLighter: "#374151",
    border: "#4B5563",
} as const;

/**
 * Get ANSI-compatible color name for terminal output.
 * Terminal color names that map to chalk/ANSI colors.
 */
export const TERMINAL_COLORS = {
    primary: "cyan",
    secondary: "magenta",
    accent: "blue",
    orchestrator: "yellow",
    analyst: "blue",
    coder: "green",
    reviewer: "magenta",
    researcher: "red",
    planner: "yellow",
    success: "green",
    warning: "yellow",
    error: "red",
    info: "blue",
    text: "white",
    textMuted: "gray",
    textDim: "gray.dim",
    textBright: "whiteBright",
} as const;

export type ColorKey = keyof typeof TERMINAL_COLORS;