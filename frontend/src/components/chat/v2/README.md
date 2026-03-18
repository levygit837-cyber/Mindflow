# Chat Visualization V2

This directory contains the second generation of chat visualization components for the OmniMind system. These components provide improved visual clarity, reduced clutter, and enhanced user experience compared to V1.

## Directory Structure

```
v2/
├── README.md              # This file
├── index.ts               # Main export point
├── types.ts               # TypeScript type definitions
├── utils.ts               # Utility functions
├── styles.css             # Shared styles and animations
└── components/            # React components (to be created)
    ├── ThinkingNotifier/
    ├── ThoughtBlock/
    ├── DelegationCard/
    ├── ToolEventCard/
    ├── StreamNotifier/
    ├── MemoryRecallCard/
    ├── AgentTodoList/
    ├── JourneyTimeline/
    └── AgentJourneyPanel/
```

## Core Concepts

### Agent Types

The system supports four agent types:
- **Orchestrator**: Main coordinator (teal #0D6E6E)
- **Analyst**: Analysis specialist (blue #5B6ABF)
- **Coder**: Code specialist (orange #C75D2C)
- **Researcher**: Research specialist (green #2D8F5E)

### Tone System

Visual feedback uses six tones:
- **accent**: Primary actions (routing, decisions)
- **info**: Informational states (memory, context)
- **success**: Successful completions
- **warning**: Warnings and slow operations
- **error**: Errors and failures
- **neutral**: Default state

### Theme Support

All components support both light and dark themes through CSS variables defined in `tokens.css`. Some components (MemoryRecallCard, AgentTodoList) are theme-dependent and only render in dark theme.

## Utility Functions

### `resolveMindflowV2AgentType(raw: string): MindflowV2AgentType`
Normalizes various agent name formats to canonical types.

### `getMindflowV2AgentTheme(raw: string): MindflowV2AgentTheme`
Returns theme configuration (colors, labels) for an agent.

### `resolveMindflowV2Tone(kind: string): MindflowV2Tone`
Maps status/kind strings to visual tones.

### `formatMindflowV2Duration(ms: number): string`
Formats milliseconds to human-readable duration (e.g., "1m 23s").

### `formatMindflowV2Value(value: unknown): string`
Formats any value to string representation.

### `summarizeMindflowV2Value(value: unknown, maxLength?: number): string`
Truncates formatted values with ellipsis.

## CSS Variables

Components use CSS variables from `tokens.css`:

### Agent Colors
- `--mindflow-v2-agent-orchestrator`
- `--mindflow-v2-agent-analyst`
- `--mindflow-v2-agent-coder`
- `--mindflow-v2-agent-researcher`

### State Colors
- `--state-success`
- `--state-error`
- `--state-warning`
- `--state-info`

### Typography
- `--font-brand`: Serif for headers
- `--font-mono`: Monospace for code/meta
- `--font-sans`: Sans-serif for body text

### Spacing & Layout
- `--spacing-1` through `--spacing-9`
- `--radius-sm` through `--radius-full`

## Animation System

Components use framer-motion for declarative animations:

### Entry Animation
```typescript
initial={{ opacity: 0, y: 8 }}
animate={{ opacity: 1, y: 0 }}
transition={{ duration: 0.18 }}
```

### Panel Slide
```typescript
initial={{ x: 380, opacity: 0 }}
animate={{ x: 0, opacity: 1 }}
exit={{ x: 380, opacity: 0 }}
transition={{ duration: 0.22, ease: 'easeOut' }}
```

### Pulse (CSS)
```css
.mindflow-v2-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
```

## Component Guidelines

### Naming Convention
- Components: PascalCase (e.g., `ThinkingNotifier`)
- Files: PascalCase for components, camelCase for utilities
- CSS classes: kebab-case with `mindflow-v2-` prefix

### Props Pattern
```typescript
interface ComponentProps {
  // Required props first
  agentType: MindflowV2AgentType;
  content: string;
  
  // Optional props with defaults
  status?: string;
  defaultExpanded?: boolean;
  
  // Callbacks
  onClick?: () => void;
  
  // Style overrides
  className?: string;
}
```

### State Management
- Use local state for UI concerns (expanded, selected)
- Derive data from props when possible
- Avoid prop drilling - use context for deep trees

### Accessibility
- Use semantic HTML elements
- Include ARIA labels for interactive elements
- Support keyboard navigation
- Maintain color contrast ratios (WCAG AA)

## Testing Strategy

### Unit Tests
- Test component rendering with various props
- Test user interactions (clicks, expansions)
- Test edge cases (empty data, null values)
- Test theme application

### Property-Based Tests
- Validate universal properties across inputs
- Test invariants (e.g., collapsed state for long content)
- Use fast-check for input generation

### Integration Tests
- Test complete flows (delegation → journey → completion)
- Test multiple agents simultaneously
- Test theme switching during streaming

## Performance Considerations

- Use `React.memo` for expensive components
- Implement `useMemo` for costly calculations
- Lazy load large components (AgentJourneyPanel)
- Limit re-renders during streaming
- Cap notifier arrays (NOTIFIER_CAP = 6)

## Related Documentation

- [Design Document](/.kiro/specs/chat-visualization-v2/design.md)
- [Requirements](/.kiro/specs/chat-visualization-v2/requirements.md)
- [Tasks](/.kiro/specs/chat-visualization-v2/tasks.md)
