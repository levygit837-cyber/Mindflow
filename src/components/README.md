# MindFlow CLI - json-render Component Catalog

## Overview

Este catálogo define os componentes da CLI do MindFlow usando o framework [json-render](https://github.com/vercel-labs/json-render). AI gera especificações JSON que são renderizadas como componentes Ink (React para terminal).

## Architecture

```
AI generates JSON spec → json-render validates against catalog → Ink renderers display in terminal
```

## Components

### Layout Components

#### InputBar
Barra de input para prompts do usuário com cursor piscante.

**Props:**
- `placeholder: string` - Texto placeholder (default: "Type your request...")
- `value: string` - Valor atual do input (default: "")
- `focused: boolean` - Se o input está focado (default: true)

### Message Components

#### UserMessage
Mensagem do usuário com timestamp.

**Props:**
- `content: string` - Conteúdo da mensagem
- `timestamp?: string` - Timestamp ISO 8601 opcional

**Visual:** Cyan "You:" prefix

#### AgentMessage
Mensagem de agente com nome, role e timestamp.

**Props:**
- `agentName: string` - Nome do agente
- `agentRole?: string` - Role do agente (ex: "orchestrator", "coder")
- `content: string` - Conteúdo da mensagem
- `timestamp?: string` - Timestamp ISO 8601 opcional
- `color?: string` - Cor do agente (default: "blue")

**Visual:** Colored "{agentName}:" prefix, gray role in parentheses

#### OutputRender
Renderização de output (código, markdown, etc.) com suporte a streaming.

**Props:**
- `content: string` - Conteúdo a renderizar
- `language?: string` - Linguagem do código (ex: "javascript", "python")
- `streaming: boolean` - Se está em streaming (default: false)

**Visual:** Language tag em amarelo, cursor "▌" quando streaming

### EventRail Components

#### ThinkingIndicator
Indicador de pensamento com pontos animados.

**Props:**
- `active: boolean` - Se está ativo (default: true)
- `message: string` - Mensagem (default: "Thinking...")

**Visual:** Gray "{message}..." com pontos animados

#### SpinnerLoader
Spinner para operações assíncronas.

**Props:**
- `active: boolean` - Se está ativo (default: true)
- `message?: string` - Mensagem opcional

**Visual:** Yellow spinner Unicode + mensagem

#### ReadTool
Indicador de operação de leitura de arquivo.

**Props:**
- `path: string` - Caminho do arquivo
- `status: "pending"|"running"|"completed"|"error"` - Status da operação (default: "pending")
- `preview?: string` - Preview do conteúdo (primeiras linhas)

**Visual:** Status icon (○/◐/●/✕) + " READ: " + cyan path

#### WriteTool
Indicador de operação de escrita de arquivo.

**Props:**
- `path: string` - Caminho do arquivo
- `status: "pending"|"running"|"completed"|"error"` - Status da operação (default: "pending")
- `preview?: string` - Preview do conteúdo

**Visual:** Status icon (○/◐/●/✕) + " WRITE: " + magenta path

## Actions

Ações disponíveis para interatividade:

- `submit_prompt` - Submete prompt do usuário para agentes
- `cancel_operation` - Cancela operação atual
- `toggle_expansion` - Toggle expansão de componente

## Example JSON Spec

```json
{
  "root": "Box",
  "elements": {
    "Box": {
      "type": "Box",
      "props": {
        "flexDirection": "column",
        "flexGrow": 1
      },
      "children": ["UserMessage", "ThinkingIndicator", "AgentMessage", "InputBar"]
    },
    "UserMessage": {
      "type": "UserMessage",
      "props": {
        "content": "Create a REST API",
        "timestamp": "2026-04-05T16:30:00Z"
      }
    },
    "ThinkingIndicator": {
      "type": "ThinkingIndicator",
      "props": {
        "active": true,
        "message": "Analyzing requirements"
      }
    },
    "AgentMessage": {
      "type": "AgentMessage",
      "props": {
        "agentName": "Orchestrator",
        "agentRole": "orchestrator",
        "content": "I'll create a REST API with authentication",
        "color": "blue"
      }
    },
    "InputBar": {
      "type": "InputBar",
      "props": {
        "placeholder": "Type your request...",
        "value": "",
        "focused": true
      }
    }
  }
}
```

## Usage

```typescript
import { Renderer } from "@json-render/ink";
import { registry } from "./components/renderers";

// Render JSON spec
<Renderer spec={jsonSpec} registry={registry} />
```

## Design Tokens

Baseado no design do Pencil:

- **Agent Colors:**
  - Orchestrator: `#0D6E6E` (teal)
  - Analyst: `#5B6ABF` (purple)
  - Coder: `#C75D2C` (orange)
  - Researcher: `#2D8F5E` (green)

- **Status Colors:**
  - Pending: gray
  - Running: yellow
  - Completed: green
  - Error: red

## Next Steps

1. Conectar ao backend MindFlow para streaming de specs JSON
2. Adicionar componentes de Team Protocol (AgentChip, TeamSessionBlock)
3. Adicionar componentes de EventRail completos (DelegationCard, ToolCallCard)
4. Implementar actions para interatividade
5. Adicionar suporte a streaming progressivo de specs
