/**
 * Coder Agent tool definitions.
 *
 * Provides the Coder Agent with file I/O, search, shell execution, and web
 * search capabilities. Follows the `tool()` + Zod pattern from note-tools.ts.
 */

import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { exec } from "node:child_process";
import { promisify } from "node:util";
import { glob } from "glob";

const execAsync = promisify(exec);

const SEARXNG_URL = process.env.SEARXNG_URL ?? "http://localhost:8080";

// ============================================================================
// NOTE: read_file, write_file, and edit_file are NOT defined here.
// They are provided automatically by the deepagents createDeepAgent()
// filesystem middleware. Defining them here would cause a
// "Duplicate function declaration" error from the Gemini API.
// ============================================================================

// ============================================================================
// Search tools
// ============================================================================

export const searchFilesTool = tool(
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
      "Search for files matching a glob pattern (e.g. '**/*.ts'). Returns matching file paths.",
    schema: z.object({
      pattern: z.string().describe("Glob pattern to match files"),
      searchPath: z
        .string()
        .optional()
        .describe("Directory to search in (defaults to cwd)"),
    }),
  },
);

export const searchContentTool = tool(
  async ({ pattern, searchPath, fileGlob }) => {
    try {
      const cwd = searchPath ?? process.cwd();
      // Build grep command — use ripgrep if available, fall back to grep
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
      "Search file contents using a regex pattern (grep-style). Returns matching lines with file paths and line numbers.",
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
// Shell execution
// ============================================================================

export const runCommandTool = tool(
  async ({ command }) => {
    try {
      const { stdout, stderr } = await execAsync(command, {
        timeout: 60_000,
        maxBuffer: 1024 * 1024,
      });
      const output = [
        stdout.trim() ? `STDOUT:\n${stdout.trim()}` : "",
        stderr.trim() ? `STDERR:\n${stderr.trim()}` : "",
      ]
        .filter(Boolean)
        .join("\n\n");
      return output || "(no output)";
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      return `Command failed: ${message}`;
    }
  },
  {
    name: "run_command",
    description:
      "Execute a shell command and return stdout/stderr. Times out after 60 seconds.",
    schema: z.object({
      command: z.string().describe("Shell command to execute"),
    }),
  },
);

// ============================================================================
// Web search (searchNXG)
// ============================================================================

export const searchWebTool = tool(
  async ({ query }) => {
    try {
      const res = await fetch(`${SEARXNG_URL}/search?q=${encodeURIComponent(query)}&format=json`, {
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
      "Search the web using searchNXG for documentation, best practices, CVEs, and other references.",
    schema: z.object({
      query: z.string().describe("Search query"),
    }),
  },
);

// ============================================================================
// Aggregated tool list
// ============================================================================

export const coderTools = [
  searchFilesTool,
  searchContentTool,
  runCommandTool,
  searchWebTool,
];
