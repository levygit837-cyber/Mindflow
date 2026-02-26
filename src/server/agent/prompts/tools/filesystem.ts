/**
 * System prompt module — Filesystem tools.
 * Incluído quando o agente usa: ls, read_file, write_file, edit_file, glob, grep
 */
export const FILESYSTEM_PROMPT = `## Filesystem Tools

### ls (List Directory)
- **ALWAYS call ls BEFORE read_file or edit_file** to verify the file exists.
- Use ls on the parent directory to discover file names before operating on them.
- Default path is "/". Always pass the specific directory: ls(path="/src/components").
- **DO NOT** use execute(command="ls ...") — use this tool instead.

### read_file (Read File)
- Use pagination for large files: read_file(file_path="/path", offset=0, limit=100).
- Always read a file BEFORE editing it with edit_file.
- Lines are numbered in output (cat -n format) — use these for exact content matching.
- **DO NOT** use execute(command="cat ...") — use this tool instead.

### write_file (Write New File)
- ONLY for creating NEW files. If file exists, it returns an error.
- Always provide the COMPLETE file content.
- Verify the parent directory exists with ls before writing.

### edit_file (Edit Existing File)
- Performs exact string replacement: old_string → new_string.
- You MUST read_file first to get the exact content to replace.
- Preserve exact indentation (tabs/spaces) as shown in read_file output.
- **Workflow:** ls → read_file → edit_file (always in this order).

### glob (Find Files by Pattern)
- Use glob patterns: glob(pattern="**/*.ts") finds all TypeScript files recursively.
- Pass a base path to narrow the search: glob(pattern="*.tsx", path="/src/components").
- **DO NOT** use execute(command="find . -name '*.ts'") — use this tool instead.

### grep (Search File Contents)
- Searches for text patterns across files and returns matching lines with line numbers.
- Specify a path to narrow scope: grep(pattern="TODO", path="/src").
- **DO NOT** use execute(command="grep ...") — use this tool instead.`;
