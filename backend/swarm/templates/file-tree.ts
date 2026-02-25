/**
 * File Tree ASCII template — default fallback that renders a tree view of changes.
 *
 * Used for general/frontend projects and as the fallback when no specific
 * project type template matches.
 */

import type { TemplateParams } from "./index";
import type { FileChangeEntry } from "@shared/types/swarm";
import {
  TOP_BORDER,
  BOTTOM_BORDER,
  SEPARATOR,
  padLine,
  renderStatusBar,
} from "./index";

export function renderFileTreeTemplate(params: TemplateParams): string {
  const { projectName, timestamp, fileChanges, progress, statusMessage } = params;

  const treeLines = buildTreeLines(fileChanges);

  const lines = [
    TOP_BORDER,
    padLine(`│  📁 SANDBOX — ${projectName} — ${timestamp}`),
    SEPARATOR,
    padLine("│"),
    padLine("│  FILE CHANGES:"),
    padLine("│"),
    ...treeLines,
    padLine("│"),
    SEPARATOR,
    renderStatusBar(progress, statusMessage),
    BOTTOM_BORDER,
  ];

  return lines.join("\n");
}

interface TreeNode {
  name: string;
  children: Map<string, TreeNode>;
  entry?: FileChangeEntry;
}

function buildTreeLines(fileChanges: FileChangeEntry[]): string[] {
  if (fileChanges.length === 0) {
    return [padLine("│  (no file changes yet)")];
  }

  // Build a tree structure from file paths
  const root: TreeNode = { name: ".", children: new Map() };

  for (const fc of fileChanges) {
    const parts = fc.filepath.split("/");
    let current = root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      if (!current.children.has(part)) {
        current.children.set(part, { name: part, children: new Map() });
      }
      current = current.children.get(part)!;

      // Mark the leaf with the file change entry
      if (i === parts.length - 1) {
        current.entry = fc;
      }
    }
  }

  // Render the tree
  const lines: string[] = [];
  renderNode(root, "", true, lines);
  return lines;
}

function renderNode(
  node: TreeNode,
  prefix: string,
  isRoot: boolean,
  lines: string[]
): void {
  if (isRoot) {
    // Render root children directly
    const children = [...node.children.entries()];
    for (let i = 0; i < children.length; i++) {
      const [, child] = children[i];
      const isLast = i === children.length - 1;
      renderNode(child, "│  ", isLast, lines);
    }
    return;
  }

  const connector = prefix.endsWith("│  ") ? "├── " : "├── ";
  const icon = getFileIcon(node);
  const annotation = getAnnotation(node);

  lines.push(padLine(`${prefix}${connector}${icon} ${node.name}${annotation}`));

  const children = [...node.children.entries()];
  for (let i = 0; i < children.length; i++) {
    const [, child] = children[i];
    const isLast = i === children.length - 1;
    const childPrefix = prefix + (isLast ? "    " : "│   ");
    renderNode(child, childPrefix, isLast, lines);
  }
}

function getFileIcon(node: TreeNode): string {
  if (node.children.size > 0) return "📂";
  if (!node.entry) return "📄";

  switch (node.entry.action) {
    case "create":
      return "✅";
    case "modify":
      return "🔄";
    case "delete":
      return "❌";
    default:
      return "📄";
  }
}

function getAnnotation(node: TreeNode): string {
  if (!node.entry) return "";
  const suffix =
    node.entry.action === "create"
      ? " (new)"
      : node.entry.action === "delete"
        ? " (deleted)"
        : "";
  const diff = node.entry.diff_summary ? `  ${node.entry.diff_summary}` : "";
  return `${diff}${suffix}`;
}
