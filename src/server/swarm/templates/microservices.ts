/**
 * Microservices ASCII template — renders a topology of services with connections.
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

export function renderMicroservicesTemplate(params: TemplateParams): string {
  const { projectName, timestamp, fileChanges, progress, statusMessage } = params;

  const services = extractServiceNames(fileChanges.map((f) => f.filepath));
  const serviceBoxes = renderServiceTopology(services);

  const lines = [
    TOP_BORDER,
    padLine(`│  🌐 SANDBOX — ${projectName} — ${timestamp}`),
    SEPARATOR,
    padLine("│"),
    padLine("│  ┌──────────┐"),
    padLine("│  │  Gateway  │"),
    padLine("│  │  (API GW) │"),
    padLine("│  └─────┬────┘"),
    padLine("│        │"),
    ...serviceBoxes,
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

function extractServiceNames(filePaths: string[]): string[] {
  const names = new Set<string>();
  for (const fp of filePaths) {
    // Match patterns like "services/user/..." or "src/user-service/..."
    const match = fp.match(/(?:services?|src)\/([a-z0-9_-]+?)(?:-service)?\//i);
    if (match?.[1]) {
      names.add(match[1]);
    }
  }
  const result = [...names].slice(0, 4);
  return result.length > 0 ? result : ["service-a", "service-b"];
}

function renderServiceTopology(services: string[]): string[] {
  const lines: string[] = [];

  if (services.length <= 2) {
    // Side-by-side layout
    const [a, b] = services;
    const labelA = truncateLabel(a ?? "svc-a", 8);
    const labelB = b ? truncateLabel(b, 8) : null;

    if (labelB) {
      lines.push(padLine("│   ┌────▼────┐   ┌─────────┐"));
      lines.push(padLine(`│   │ ${labelA.padEnd(8)}│   │ ${labelB.padEnd(8)}│`));
      lines.push(padLine("│   └─────────┘   └─────────┘"));
    } else {
      lines.push(padLine("│        ┌────▼────┐"));
      lines.push(padLine(`│        │ ${labelA.padEnd(8)}│`));
      lines.push(padLine("│        └─────────┘"));
    }
  } else {
    // Tree layout for 3-4 services
    lines.push(padLine("│   ┌────┴────┬─────────┐"));
    for (let i = 0; i < services.length; i += 2) {
      const a = truncateLabel(services[i], 8);
      const b = services[i + 1] ? truncateLabel(services[i + 1], 8) : null;
      if (b) {
        lines.push(padLine(`│   ┌─────────┐   ┌─────────┐`));
        lines.push(padLine(`│   │ ${a.padEnd(8)}│   │ ${b.padEnd(8)}│`));
        lines.push(padLine(`│   └─────────┘   └─────────┘`));
      } else {
        lines.push(padLine(`│   ┌─────────┐`));
        lines.push(padLine(`│   │ ${a.padEnd(8)}│`));
        lines.push(padLine(`│   └─────────┘`));
      }
    }
  }

  return lines;
}

function truncateLabel(label: string, maxLen: number): string {
  return label.length > maxLen ? label.slice(0, maxLen - 1) + "…" : label;
}
