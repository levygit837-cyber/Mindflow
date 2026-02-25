/**
 * Live Analyst Agent tool definitions.
 *
 * The analyst operates in stealth/read-only mode. It only has:
 *  - search_web: to verify findings against real documentation and CVE databases
 *  - write_report: pseudo-tool that returns report content for the node to
 *    persist in the graph state (the analyst never writes to the filesystem)
 */

import { tool } from "@langchain/core/tools";
import { z } from "zod";

const SEARXNG_URL = process.env.SEARXNG_URL ?? "http://localhost:8080";

// ============================================================================
// Web search (searchNXG)
// ============================================================================

export const analystSearchWebTool = tool(
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
      "Search the web using searchNXG to verify best practices, check CVEs, and validate findings with real documentation.",
    schema: z.object({
      query: z.string().describe("Search query for verification"),
    }),
  },
);

// ============================================================================
// Report pseudo-tool
// ============================================================================

export const analystWriteReportTool = tool(
  async ({ reportContent }) => {
    // This is a pseudo-tool: the node function will read the content from the
    // tool output and write it to `analyst_report_md` in the graph state.
    // The tool itself just returns the content unchanged as confirmation.
    return reportContent;
  },
  {
    name: "write_report",
    description:
      "Submit the analysis report content. The report will be stored in the shared graph state as analyst_report_md. Use markdown format.",
    schema: z.object({
      reportContent: z
        .string()
        .describe("Full markdown content of the analysis report"),
    }),
  },
);

// ============================================================================
// Aggregated tool list
// ============================================================================

export const analystTools = [analystSearchWebTool, analystWriteReportTool];
