# OmniMind — Suggested Commands

## Development
```bash
pnpm dev                  # Next.js dev server (http://localhost:3000) via turbopack
node omni.js              # Same as pnpm dev, via CLI
node omni.js --logs       # Dev server + real-time agent logs in terminal
pnpm build                # Production build
pnpm start                # Production server
```

## Testing
```bash
pnpm test                 # Vitest (run once)
pnpm test:watch           # Vitest in watch mode
```

## Type checking
```bash
pnpm exec tsc --noEmit    # TypeScript type check (no emit)
```

## Database
```bash
# PostgreSQL required for LangGraph checkpointer
# Connection string in .env.local: DATABASE_URL=...
```

## Git
```bash
git checkout -b feat/nome-da-feature
git add <specific-files>
git commit -m "feat: description"
git push origin feat/nome
```

## Notes
- No separate backend process — everything is Next.js 16 App Router
- SSE logs available at http://localhost:3000/api/agent/logs/stream
- LogBus singleton lives in src/lib/agent/log-bus.ts (max 500 history entries)
