/**
 * GraphQL ASCII template — renders a schema tree + resolver flow.
 */

import type { TemplateParams } from "./index";
import {
  TOP_BORDER,
  BOTTOM_BORDER,
  SEPARATOR,
  padLine,
  renderFileChangesSection,
  renderStatusBar,
} from "./index";

export function renderGraphqlTemplate(params: TemplateParams): string {
  const { projectName, timestamp, fileChanges, progress, statusMessage } = params;

  // Extract type names from file paths for the schema tree
  const typeNames = extractTypeNames(fileChanges.map((f) => f.filepath));

  const lines = [
    TOP_BORDER,
    padLine(`│  📊 SANDBOX — ${projectName} — ${timestamp}`),
    SEPARATOR,
    padLine("│"),
    padLine("│  ┌─────────────┐    ┌──────────────┐"),
    padLine("│  │   Client    │───▶│  GraphQL GW  │"),
    padLine("│  │  (Query)    │    │  /graphql    │"),
    padLine("│  └─────────────┘    └──────┬───────┘"),
    padLine("│                            │"),
    padLine("│                    ┌───────▼───────┐"),
    padLine("│                    │   Resolvers   │"),
    padLine("│                    └──┬─────────┬──┘"),
    padLine("│                       │         │"),
    padLine("│               ┌───────▼──┐ ┌────▼──────┐"),
    padLine("│               │  Schema  │ │  DataSrc  │"),
    padLine("│               │  Types   │ │  (DB/API) │"),
    padLine("│               └──────────┘ └───────────┘"),
    padLine("│"),
    ...(typeNames.length > 0
      ? [
          padLine("│  SCHEMA TYPES DETECTED:"),
          ...typeNames.map((t) => padLine(`│    ▸ ${t}`)),
          padLine("│"),
        ]
      : []),
    SEPARATOR,
    padLine("│  MODIFIED FILES:"),
    renderFileChangesSection(fileChanges),
    padLine("│"),
    SEPARATOR,
    renderStatusBar(progress, statusMessage),
    BOTTOM_BORDER,
  ];

  return lines.join("\n");
}

function extractTypeNames(filePaths: string[]): string[] {
  const names: string[] = [];
  for (const fp of filePaths) {
    // Match filenames like "user.graphql", "resolvers/post.ts"
    const match = fp.match(/(?:resolvers?|types?|schema)\/?([^/]+?)(?:\.\w+)?$/i);
    if (match?.[1]) {
      const name = match[1].charAt(0).toUpperCase() + match[1].slice(1);
      if (!names.includes(name)) names.push(name);
    }
  }
  return names.slice(0, 6); // limit to keep ASCII compact
}
