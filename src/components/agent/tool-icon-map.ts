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
  Check,
  AlertCircle,
} from "lucide-react";

export interface ToolVisualConfig {
  icon: LucideIcon;
  label: string;
  accentColor: string; // Tailwind color stem, e.g. "blue" -> used as text-blue-500 etc.
}

const MAP: Record<string, ToolVisualConfig> = {
  // Web / search
  web_search: { icon: Globe, label: "Web Search", accentColor: "sky" },
  search_web: { icon: Globe, label: "Web Search", accentColor: "sky" },

  // Terminal / shell
  bash: { icon: Terminal, label: "Terminal", accentColor: "green" },
  run_command: { icon: Terminal, label: "Run Command", accentColor: "green" },
  execute: { icon: Code, label: "Execute Code", accentColor: "violet" },

  // File operations
  read_file: { icon: FileText, label: "Read File", accentColor: "blue" },
  write_file: { icon: FilePen, label: "Write File", accentColor: "amber" },
  edit_file: { icon: FileEdit, label: "Edit File", accentColor: "orange" },
  list_files: { icon: FolderTree, label: "List Files", accentColor: "teal" },

  // Search / grep
  search_files: { icon: FileSearch, label: "Search Files", accentColor: "indigo" },
  search_content: { icon: Search, label: "Search Content", accentColor: "indigo" },
  glob: { icon: FileSearch, label: "Glob Search", accentColor: "indigo" },
  grep: { icon: Search, label: "Grep", accentColor: "indigo" },
  ls: { icon: FolderOpen, label: "List Directory", accentColor: "teal" },

  // Note operations
  read_note: { icon: BookOpen, label: "Read Note", accentColor: "purple" },
  search_notes: { icon: Search, label: "Search Notes", accentColor: "purple" },
  get_notes_context: { icon: StickyNote, label: "Notes Context", accentColor: "purple" },
  list_notes: { icon: ListChecks, label: "List Notes", accentColor: "purple" },
  link_notes: { icon: Link2, label: "Link Notes", accentColor: "purple" },

  // Task / report
  write_todos: { icon: ClipboardList, label: "Write Todos", accentColor: "emerald" },
  write_report: { icon: FilePen, label: "Write Report", accentColor: "amber" },
  task: { icon: Network, label: "Task", accentColor: "cyan" },
};

const DEFAULT_CONFIG: ToolVisualConfig = {
  icon: Settings,
  label: "Tool",
  accentColor: "gray",
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
export { Loader2 as SpinnerIcon, Check as CheckIcon, AlertCircle as ErrorIcon };
