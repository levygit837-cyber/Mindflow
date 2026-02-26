/**
 * CLI Tool ASCII template — renders a simulated terminal output.
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

export function renderCliToolTemplate(params: TemplateParams): string {
  const { projectName, timestamp, fileChanges, progress, statusMessage } = params;

  const cliName = extractCliName(fileChanges.map((f) => f.filepath)) ?? projectName;

  const lines = [
    TOP_BORDER,
    padLine(`│  ⌨️  SANDBOX — ${projectName} — ${timestamp}`),
    SEPARATOR,
    padLine("│"),
    padLine("│  ┌─────────────────────────────────────────────┐"),
    padLine("│  │  $ terminal                                 │"),
    padLine("│  ├─────────────────────────────────────────────┤"),
    padLine(`│  │  $ ${cliName} --help`),
    padLine("│  │"),
    padLine(`│  │  Usage: ${cliName} [options] <command>`),
    padLine("│  │"),
    padLine("│  │  Commands:"),
    ...renderCliCommands(fileChanges),
    padLine("│  │"),
    padLine(`│  │  $ ${cliName} run`),
    padLine("│  │  ✓ Running..."),
    padLine("│  │"),
    padLine("│  └─────────────────────────────────────────────┘"),
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

function extractCliName(filePaths: string[]): string | null {
  for (const fp of filePaths) {
    const match = fp.match(/(?:bin|cli)\/([a-z0-9_-]+)/i);
    if (match?.[1]) return match[1];
  }
  return null;
}

function renderCliCommands(fileChanges: import("@shared/types/swarm").FileChangeEntry[]): string[] {
  const commands: string[] = [];

  for (const fc of fileChanges) {
    // Try to extract command names from file paths like "commands/init.ts"
    const match = fc.filepath.match(/commands?\/([a-z0-9_-]+)/i);
    if (match?.[1]) {
      const cmd = match[1];
      if (!commands.includes(cmd)) commands.push(cmd);
    }
  }

  if (commands.length === 0) {
    return [
      padLine("│  │    init        Initialize project"),
      padLine("│  │    run         Run the application"),
    ];
  }

  return commands.slice(0, 5).map((cmd) =>
    padLine(`│  │    ${cmd.padEnd(12)}(detected)`)
  );
}
