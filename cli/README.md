# MindFlow CLI

Terminal-based CLI interface for MindFlow with multi-agent orchestration visualization.

## Features

- 🎨 Real-time agent status visualization with animated spinners
- 📊 Tool execution timeline with status indicators
- 🌐 WebSocket-based live updates
- ⌨️ Keyboard shortcuts for quick navigation
- 🎯 Agent network tree visualization
- 📝 Message history with color-coded types

## Prerequisites

- Node.js 20+
- npm 10+
- MindFlow backend running on `localhost:8000`

## Installation

```bash
cd cli
npm install
```

## Configuration

Create a `.env` file in the `cli/` directory:

```env
MINDFLOW_API_URL=http://localhost:8000
MINDFLOW_WS_URL=ws://localhost:8000/ws
MINDFLOW_API_KEY=your_api_key_here
```

## Usage

### Development Mode

```bash
npm run dev
```

### Build

```bash
npm run build
```

### Production

```bash
npm start
```

## Keyboard Shortcuts

- `Ctrl+C` - Exit CLI
- `Ctrl+L` - Clear messages
- `Ctrl+A` - Toggle agent panel
- `Ctrl+T` - Toggle tools panel

## Architecture

### Tech Stack

- **React 19** - UI framework
- **Ink 5** - Terminal rendering
- **Zustand** - State management
- **WebSocket** - Real-time updates
- **Axios** - HTTP client

### Component Structure

```
src/
├── components/
│   ├── agents/          # Agent visualization
│   ├── messages/        # Message display
│   ├── tools/           # Tool execution views
│   ├── ui/              # Reusable UI components
│   └── layouts/         # Layout components
├── hooks/               # Custom React hooks
├── services/            # API and WebSocket services
├── state/               # Zustand store
├── types/               # TypeScript definitions
└── utils/               # Utility functions
```

### State Management

The CLI uses Zustand for state management with the following structure:

- **messages**: Chat message history
- **agents**: Active agent states with status
- **toolCalls**: Tool execution tracking
- **connectionStatus**: WebSocket connection state
- **expandedView**: UI panel visibility

### WebSocket Events

The CLI listens for these WebSocket events from the backend:

- `agent_status` - Agent state updates
- `agent_message` - Messages from agents
- `tool_call_start` - Tool execution started
- `tool_call_complete` - Tool execution finished
- `assistant_message` - Assistant responses
- `system_message` - System notifications

## Development

### Type Checking

```bash
npm run typecheck
```

### Linting

```bash
npm run lint
```

## Troubleshooting

### WebSocket Connection Issues

If the CLI shows "Disconnected":

1. Verify backend is running on `localhost:8000`
2. Check WebSocket endpoint is accessible
3. Verify `MINDFLOW_WS_URL` in `.env`

### Agent Panel Not Showing

Press `Ctrl+A` to toggle the agent panel visibility.

### Messages Not Appearing

1. Check backend logs for errors
2. Verify API endpoint in `.env`
3. Check browser console for WebSocket errors

## Contributing

1. Follow TypeScript strict mode
2. Use functional components with hooks
3. Keep components small and focused
4. Add types for all props and state

## License

MIT
