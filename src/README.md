# MindFlow CLI

Terminal interface for MindFlow multi-agent AI system.

## Stack

- **Ink** — React para terminal (fork customizado do Claude Code)
- **React 19** — UI declarativa
- **TypeScript** — Type safety
- **Yoga** — Layout engine (flexbox para terminal)
- **SSE** — Server-sent events para streaming do backend

## Arquitetura Visual

```
┌─────────────────────────────────────────────────┐
│ MindFlow CLI                                     │
│                                                   │
│  You: "Analise o sistema de autenticação"         │
│                                                   │
│  🧠 Orchestrator → Montando equipe...            │
│  👥 analyst, coder, reviewer                      │
│                                                   │
│  📊 analyst   → Examinando estrutura auth...      │
│  🔧 coder     → Aguardando análise...            │
│  🔍 reviewer  → Aguardando implementação...      │
│                                                   │
│  📊 analyst   → Auth usa JWT + RBAC, sem 2FA     │
│  🔧 coder     → Adicionando 2FA e rate limit     │
│                                                   │
│  ✓ Pronto: Sistema auth melhorado com 2FA        │
└─────────────────────────────────────────────────┘
```

### Princípios de UI

1. **Transparência** — Nunca poluir a UI com comunicação raw inter-agente
2. **Summarização** — Modelo local gera frases concisas de status
3. **Minimalismo** — Mostrar apenas o necessário para o usuário entender
4. **Progressividade** — Informação adicional sob demanda (teclas/expansão)

## Estrutura de Diretórios

```
src/
├── entrypoints/          ← CLI entry point
├── components/           ← React components
│   ├── design-system/    ← Box, Text, cores
│   ├── chat/             ← Mensagens e histórico
│   ├── input/            ← Input bar e comandos
│   ├── agents/           ← Badges e status de agentes
│   └── feedback/         ← Spinner, loading, progresso
├── ink/                  ← Ink framework
├── services/             ← API SSE connection
├── state/                ← AppState store
├── hooks/                ← Custom hooks
├── summarizer/           ← Modelo local de summarização
└── screens/              ← REPL principal
```

## Design Decisions

| Decisão | Razão |
|---------|-------|
| Ink do Claude Code | Qualidade de produção comprovada |
| SSE para backend | Simple, streaming, nativo em browsers |
| Summarizer local | UI limpa sem ruído de comunicação |
| Comunicação NUNCA raw | Poluiria a UI com mensagens internas |
| Mobile planned | API agnóstica (SSE funciona em qualquer platform) |

## Setup

```bash
cd src/
bun install
bun run dev
```
