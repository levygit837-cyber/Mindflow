# MindFlow CLI

Modern terminal interface with streaming support, inspired by Claude Code but with MindFlow's own identity.

## Features

- **Streaming Protocol** - NDJSON-based structured I/O for real-time updates
- **Tool Execution Tracking** - Visual progress indicators for tool calls
- **Thinking Blocks** - Collapsible reasoning display
- **Virtualized Message List** - Performance for long conversations
- **Keyboard Navigation** - Efficient shortcuts for power users

## Installation

```bash
npm install
npm run build
```

## Usage

```bash
# Run in development mode
npm run dev

# Build and run
npm run build
npm start

# Or use globally
npm link
mindflow
```

## Architecture

```
src/cli/
├── core/
│   ├── StructuredIO.ts      # NDJSON streaming protocol
│   └── MessageStore.ts      # Zustand state management
├── components/
│   ├── ChatInterface.tsx    # Main container
│   ├── MessageList.tsx      # Virtualized message list
│   ├── InputBar.tsx         # Input with spinner
│   ├── messages/
│   │   ├── UserMessage.tsx
│   │   ├── AssistantMessage.tsx
│   │   ├── ThinkingMessage.tsx
│   │   ├── ToolUseMessage.tsx
│   │   ├── ToolResultMessage.tsx
│   │   └── SystemMessage.tsx
│   └── ui/
│       └── Spinner.tsx      # MindFlow identity spinner
├── types/
│   └── protocol.ts          # Message type definitions
└── entrypoints/
    └── cli.tsx             # Entry point
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Enter | Submit message |
| ↑/↓ | Navigate input history |
| Ctrl+C | Quit |
| Ctrl+L | Clear screen |
| Tab | Navigate UI elements |
| Enter (on message) | Expand/collapse |

## Design System

### Colors (Teal Professional)

- **Primary:** `#0D6E6E` (Teal Dark)
- **Secondary:** `#14B8A6` (Teal Medium)
- **Accent:** `#5EEAD4` (Teal Light)
- **Background:** `#0A0A0A` (Black)
- **Surface:** `#1A1A1A` (Dark Gray)
- **Success:** `#22C55E` (Green)
- **Error:** `#EF4444` (Red)

### Spinner

MindFlow uses rotating quadrants: `◐ ◓ ◑ ◒`

Different from Claude's dots - this is MindFlow's unique identity.

## Protocol

Messages are exchanged via NDJSON (newline-delimited JSON):

```json
{"type": "user", "content": "Hello", "timestamp": 1234567890, "uuid": "..."}
{"type": "assistant", "content": "Hi there!", "timestamp": 1234567891, "uuid": "..."}
{"type": "tool_use", "name": "FileReadTool", "tool_use_id": "...", "input": {...}}
{"type": "tool_result", "tool_use_id": "...", "output": "..."}
```

## Development

```bash
# Watch mode
npm run dev

# Type checking
npm run typecheck

# Linting
npm run lint
```

## License

MIT
