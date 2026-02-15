/**
 * Code Reviewer Agent tool definitions.
 *
 * The reviewer operates in strict read-only mode. It can read files and search
 * the codebase but never write to project files. The only writable output is
 * the review report, which is stored in graph state via a pseudo-tool.
 */

import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { exec } from "node:child_process";
import { promisify } from "node:util";
import { glob } from "glob";

const execAsync = promisify(exec);

const SEARCHNXG_URL = process.env.SEARCHNXG_URL ?? "http://localhost:8080";

// ============================================================================
// NOTE: read_file is NOT defined here. It is provided automatically by the
// deepagents createDeepAgent() filesystem middleware. Defining it here would
// cause a "Duplicate function declaration" error from the Gemini API.
// ============================================================================

// ============================================================================
// Read-only search tools
// ============================================================================

export const reviewerSearchFilesTool = tool(
  async ({ pattern, searchPath }) => {
    try {
      const cwd = searchPath ?? process.cwd();
      const matches = await glob(pattern, {
        cwd,
        nodir: true,
        ignore: ["**/node_modules/**", "**/.git/**", "**/dist/**"],
      });
      if (matches.length === 0) return "No files matched the pattern.";
      return matches.join("\n");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      return `Error searching files: ${message}`;
    }
  },
  {
    name: "search_files",
    description:
      "Search for files matching a glob pattern (read-only). Returns matching file paths.",
    schema: z.object({
      pattern: z.string().describe("Glob pattern to match files"),
      searchPath: z
        .string()
        .optional()
        .describe("Directory to search in (defaults to cwd)"),
    }),
  },
);

export const reviewerSearchContentTool = tool(
  async ({ pattern, searchPath, fileGlob }) => {
    try {
      const cwd = searchPath ?? process.cwd();
      const globArg = fileGlob ? `--glob '${fileGlob}'` : "";
      const cmd = `rg --no-heading --line-number --max-count 50 ${globArg} -- '${pattern.replace(/'/g, "'\\''")}' '${cwd}' 2>/dev/null || grep -rn --include='${fileGlob ?? "*"}' -m 50 '${pattern.replace(/'/g, "'\\''")}' '${cwd}' 2>/dev/null`;
      const { stdout } = await execAsync(cmd, { timeout: 15_000 });
      if (!stdout.trim()) return "No matches found.";
      return stdout.trim();
    } catch {
      return "No matches found.";
    }
  },
  {
    name: "search_content",
    description:
      "Search file contents using a regex pattern (read-only grep-style). Returns matching lines with file paths and line numbers.",
    schema: z.object({
      pattern: z.string().describe("Regex pattern to search for"),
      searchPath: z
        .string()
        .optional()
        .describe("Directory to search in (defaults to cwd)"),
      fileGlob: z
        .string()
        .optional()
        .describe("Glob to filter files (e.g. '*.ts')"),
    }),
  },
);

// ============================================================================
// Web search (searchNXG)
// ============================================================================

export const reviewerSearchWebTool = tool(
  async ({ query }) => {
    try {
      const res = await fetch(`${SEARCHNXG_URL}/search?q=${encodeURIComponent(query)}&format=json`, {
        signal: AbortSignal.timeout(10_000),
      });
      if (!res.ok) {
        return `searchNXG returned status ${res.status}: ${await res.text()}`;
      }
      const data = await res.json();
      return JSON.stringify(data, null, 2);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      return `searchNXG unavailable: ${message}`;
    }
  },
  {
    name: "search_web",
    description:
      "Search the web using searchNXG for best practices, documentation, and industry standards to validate review findings.",
    schema: z.object({
      query: z.string().describe("Search query"),
    }),
  },
);

// ============================================================================
// Report pseudo-tool
// ============================================================================

export const reviewerWriteReportTool = tool(
  async ({ reportContent }) => {
    // Pseudo-tool: the node function reads the tool output and writes it to
    // `reviewer_report_md` in the graph state. No filesystem writes.
    return reportContent;
  },
  {
    name: "write_report",
    description:
      "Submit the code review report. The report will be stored in the shared graph state as reviewer_report_md. Use the structured markdown format with severity categories.",
    schema: z.object({
      reportContent: z
        .string()
        .describe("Full markdown content of the review report"),
    }),
  },
);

// ============================================================================
// Aggregated tool list
// ============================================================================

export const reviewerTools = [
  reviewerSearchFilesTool,
  reviewerSearchContentTool,
  reviewerSearchWebTool,
  reviewerWriteReportTool,
];
