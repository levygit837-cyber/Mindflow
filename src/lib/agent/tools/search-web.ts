/**
 * Standalone search_web tool for the Deep Agent.
 *
 * Uses SearXNG (local meta-search engine) to search the web.
 * Returns formatted results (title, url, snippet) limited to top 10.
 */

import { tool } from "@langchain/core/tools";
import { z } from "zod";

const SEARXNG_URL = process.env.SEARXNG_URL ?? "http://localhost:8080";

interface SearXNGResult {
  title?: string;
  url?: string;
  content?: string;
  engine?: string;
  score?: number;
}

interface SearXNGResponse {
  results?: SearXNGResult[];
  suggestions?: string[];
  query?: string;
}

function formatResults(data: SearXNGResponse): string {
  const results = data.results ?? [];
  if (results.length === 0) {
    const suggestions = data.suggestions ?? [];
    if (suggestions.length > 0) {
      return `No results found. Suggestions: ${suggestions.join(", ")}`;
    }
    return "No results found.";
  }

  const top = results.slice(0, 10);
  const formatted = top.map((r, i) => {
    const title = r.title || "Untitled";
    const url = r.url || "";
    const snippet = r.content
      ? r.content.length > 300
        ? r.content.slice(0, 297) + "..."
        : r.content
      : "";
    return `${i + 1}. **${title}**\n   URL: ${url}\n   ${snippet}`;
  });

  return formatted.join("\n\n");
}

export const searchWebTool = tool(
  async ({ query }) => {
    try {
      const res = await fetch(
        `${SEARXNG_URL}/search?q=${encodeURIComponent(query)}&format=json`,
        { signal: AbortSignal.timeout(15_000) }
      );
      if (!res.ok) {
        return `SearXNG returned status ${res.status}: ${await res.text()}`;
      }
      const data = (await res.json()) as SearXNGResponse;
      return formatResults(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      return `Web search unavailable: ${message}`;
    }
  },
  {
    name: "search_web",
    description:
      "Search the web for up-to-date information, documentation, news, and references using SearXNG. Returns top 10 results with titles, URLs, and snippets.",
    schema: z.object({
      query: z.string().describe("Search query"),
    }),
  }
);
