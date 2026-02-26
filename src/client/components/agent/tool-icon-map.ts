import type { LucideIcon } from "lucide-react";
import {
  Globe,
  Terminal,
  FileText,
  FilePen,
  FolderTree,
  Code,
  Search,
  FileSearch,
  FolderOpen,
  BookOpen,
  StickyNote,
  Link2,
  ListChecks,
  ClipboardList,
  Network,
  FileEdit,
  Settings,
  Loader2,
  AlertCircle,
} from "lucide-react";

export interface ToolVisualConfig {
  icon: LucideIcon;
  label: string;
}

const MAP: Record<string, ToolVisualConfig> = {
  // Web / search
  web_search: { icon: Globe, label: "Web Search" },
  search_web: { icon: Globe, label: "Web Search" },

  // Terminal / shell
  bash: { icon: Terminal, label: "Terminal" },
  run_command: { icon: Terminal, label: "Run Command" },
  execute: { icon: Code, label: "Execute Code" },

  // File operations
  read_file: { icon: FileText, label: "Read File" },
  write_file: { icon: FilePen, label: "Write File" },
  edit_file: { icon: FileEdit, label: "Edit File" },
  list_files: { icon: FolderTree, label: "List Files" },

  // Search / grep
  search_files: { icon: FileSearch, label: "Search Files" },
  search_content: { icon: Search, label: "Search Content" },
  glob: { icon: FileSearch, label: "Glob Search" },
  grep: { icon: Search, label: "Grep" },
  ls: { icon: FolderOpen, label: "List Directory" },

  // Note operations
  read_note: { icon: BookOpen, label: "Read Note" },
  search_notes: { icon: Search, label: "Search Notes" },
  get_notes_context: { icon: StickyNote, label: "Notes Context" },
  list_notes: { icon: ListChecks, label: "List Notes" },
  link_notes: { icon: Link2, label: "Link Notes" },

  // Task / report
  write_todos: { icon: ClipboardList, label: "Write Todos" },
  write_report: { icon: FilePen, label: "Write Report" },
  task: { icon: Network, label: "Task" },
};

const DEFAULT_CONFIG: ToolVisualConfig = {
  icon: Settings,
  label: "Tool",
};

function prettifyToolName(toolName: string): string {
  const raw = String(toolName || "").trim();
  if (!raw || raw.toLowerCase() === "unknown") return "Tool";

  return raw
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function getToolConfig(toolName: string): ToolVisualConfig {
  const config = MAP[toolName];
  if (config) return config;
  return { ...DEFAULT_CONFIG, label: prettifyToolName(toolName) };
}

/** Status-related icons re-exported for convenience */
export { Loader2 as SpinnerIcon, AlertCircle as ErrorIcon };
