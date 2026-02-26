/**
 * REST API ASCII template — renders a request → middleware → handler → DB flow.
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

export function renderRestApiTemplate(params: TemplateParams): string {
  const { projectName, timestamp, fileChanges, progress, statusMessage } = params;

  // Detect DB type from file paths
  const dbLabel = detectDbType(fileChanges.map((f) => f.filepath));

  const lines = [
    TOP_BORDER,
    padLine(`│  🔧 SANDBOX — ${projectName} — ${timestamp}`),
    SEPARATOR,
    padLine("│"),
    padLine("│  ┌──────────┐    ┌──────────┐    ┌──────────┐"),
    padLine("│  │  Client   │───▶│  API GW  │───▶│  Service │"),
    padLine("│  │  Request  │    │  /v1/... │    │  Layer   │"),
    padLine("│  └──────────┘    └──────────┘    └─────┬────┘"),
    padLine("│                                        │"),
    padLine("│                                   ┌────▼────┐"),
    padLine(`│                                   │   DB    │`),
    padLine(`│                                   │ (${dbLabel})`),
    padLine("│                                   └─────────┘"),
    padLine("│"),
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

function detectDbType(filePaths: string[]): string {
  const joined = filePaths.join(" ").toLowerCase();
  if (joined.includes("prisma") || joined.includes("postgres")) return "PostgreSQL";
  if (joined.includes("mongo")) return "MongoDB";
  if (joined.includes("sqlite")) return "SQLite";
  if (joined.includes("mysql")) return "MySQL";
  if (joined.includes("redis")) return "Redis";
  return "Database";
}
