/**
 * ASCII template system for the Sandbox Renderer.
 *
 * Selects and renders parameterized ASCII art visualizations based on
 * file changes and detected project type. Each template generates a
 * structured box-drawing display for the sandbox panel.
 */

import type { FileChangeEntry } from "@shared/types/swarm";
import type { ProjectType } from "../prompts/router";
import { detectProjectType } from "../prompts/router";
import { renderRestApiTemplate } from "./rest-api";
import { renderGraphqlTemplate } from "./graphql";
import { renderMicroservicesTemplate } from "./microservices";
import { renderCliToolTemplate } from "./cli-tool";
import { renderFileTreeTemplate } from "./file-tree";

// ============================================================================
// Template parameters
// ============================================================================

/**
 * Parameters passed to every ASCII template renderer.
 */
export interface TemplateParams {
  /** Name of the project or task */
  projectName: string;
  /** ISO 8601 timestamp of the render */
  timestamp: string;
  /** All file changes from the coder */
  fileChanges: FileChangeEntry[];
  /** Completion percentage (0-100) */
  progress: number;
  /** Short status message */
  statusMessage: string;
}

/**
 * Signature that every template renderer must implement.
 */
export type AsciiTemplateRenderer = (params: TemplateParams) => string;

// ============================================================================
// Template registry
// ============================================================================

const TEMPLATE_REGISTRY: Record<Exclude<ProjectType, "general">, AsciiTemplateRenderer> = {
  "rest-api": renderRestApiTemplate,
  graphql: renderGraphqlTemplate,
  microservices: renderMicroservicesTemplate,
  cli: renderCliToolTemplate,
  frontend: renderFileTreeTemplate, // frontend falls through to file-tree
};

/**
 * Select the best ASCII template based on file changes.
 *
 * Extracts file paths from the changes, runs project type detection,
 * and returns the matching template renderer. Falls back to the
 * file-tree template when no specific type is detected.
 */
export function selectTemplate(fileChanges: FileChangeEntry[]): AsciiTemplateRenderer {
  const paths = fileChanges.map((fc) => fc.filepath);
  const projectType = detectProjectType(paths);

  if (projectType === "general") {
    return renderFileTreeTemplate;
  }

  return TEMPLATE_REGISTRY[projectType] ?? renderFileTreeTemplate;
}

// ============================================================================
// Shared helpers used by multiple templates
// ============================================================================

/**
 * Render the file changes section common to all templates.
 */
export function renderFileChangesSection(fileChanges: FileChangeEntry[]): string {
  if (fileChanges.length === 0) {
    return "│  (no file changes yet)                                   │";
  }

  const lines: string[] = [];
  for (const fc of fileChanges) {
    const icon =
      fc.action === "create" ? "✅" : fc.action === "modify" ? "🔄" : "❌";
    const suffix =
      fc.action === "create" ? " (new)" : fc.action === "delete" ? " (deleted)" : "";
    const summary = fc.diff_summary ? `  ${fc.diff_summary}` : "";
    const raw = `│  ${icon} ${fc.filepath}${summary}${suffix}`;
    lines.push(padLine(raw));
  }
  return lines.join("\n");
}

/**
 * Render a progress bar.
 * @param progress 0-100
 * @param width    total character width of the bar (filled + empty)
 */
export function renderProgressBar(progress: number, width: number = 20): string {
  const clamped = Math.max(0, Math.min(100, progress));
  const filled = Math.round((clamped / 100) * width);
  const empty = width - filled;
  return "█".repeat(filled) + "░".repeat(empty);
}

/**
 * Pad a line to fit within a 59-char inner box (total 61 with borders).
 * Truncates if too long.
 */
export function padLine(line: string, width: number = 59): string {
  // Strip existing trailing border if present
  const clean = line.replace(/\s*│\s*$/, "");
  const visibleLength = stripAnsi(clean).length;
  if (visibleLength >= width + 2) {
    // Truncate — keep the leading border
    return clean.slice(0, width + 1) + "│";
  }
  return clean + " ".repeat(width + 2 - visibleLength) + "│";
}

/** Strip ANSI escape codes for length calculation. */
function stripAnsi(str: string): string {
  return str.replace(/\u001b\[[0-9;]*m/g, "");
}

/**
 * Render the common status bar at the bottom.
 */
export function renderStatusBar(progress: number, statusMessage: string): string {
  const bar = renderProgressBar(progress);
  const raw = `│  STATUS: ${bar} ${progress}% — ${statusMessage}`;
  return padLine(raw);
}

/**
 * Top border of the sandbox box.
 */
export const TOP_BORDER = "┌─────────────────────────────────────────────────────────────┐";

/**
 * Bottom border of the sandbox box.
 */
export const BOTTOM_BORDER = "└─────────────────────────────────────────────────────────────┘";

/**
 * Section separator line.
 */
export const SEPARATOR = "├─────────────────────────────────────────────────────────────┤";
