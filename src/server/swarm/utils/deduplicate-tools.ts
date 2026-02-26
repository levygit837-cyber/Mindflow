/**
 * Safety-net utility that deduplicates tools by name.
 *
 * The `deepagents` package's `createDeepAgent()` injects built-in filesystem
 * middleware tools (read_file, write_file, edit_file, glob, grep, ls, execute).
 * If custom tools with the same names are also passed via the `tools` array the
 * Gemini API returns a 400 "Duplicate function declaration" error.
 *
 * This function ensures that, for any list of custom tools, only the **last**
 * occurrence of each tool name is kept. It also filters out names that are known
 * to be provided by the deepagents built-in middleware so they are never sent
 * twice.
 */

import type { StructuredToolInterface } from "@langchain/core/tools";

/** Tool names that deepagents createDeepAgent() registers automatically. */
const DEEPAGENT_BUILTIN_TOOL_NAMES = new Set([
  "read_file",
  "write_file",
  "edit_file",
  "glob",
  "grep",
  "ls",
  "execute",
  "TodoWrite",
]);

/**
 * Remove tools whose names collide with deepagents built-ins, then deduplicate
 * any remaining duplicates by keeping the last definition for each name.
 *
 * @param tools - Array of LangChain StructuredTool-like objects with a `name` property.
 * @returns A new array with duplicates removed.
 */
export function deduplicateTools<T extends StructuredToolInterface>(
  tools: readonly T[],
): T[] {
  const filtered = tools.filter(
    (t) => !DEEPAGENT_BUILTIN_TOOL_NAMES.has(t.name),
  );

  // Deduplicate by name — last definition wins
  const seen = new Map<string, T>();
  for (const t of filtered) {
    seen.set(t.name, t);
  }
  return Array.from(seen.values());
}
