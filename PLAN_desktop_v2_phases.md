# Plano de Fases: MindFlow Desktop v2

**Estratégia central:** O launcher PySide6 (`launcher.py`) já resolve tudo do backend — Docker, Postgres, migrations, FastAPI, graceful shutdown. O plano substitui apenas a UI: QML/OmniMind → React frontend renderizado via `QWebEngineView`. Sem Electron. Sem Tauri. Zero reescrita do launcher.

```
launcher.py (mantido)          main.py (substituído)
┌─────────────────────┐        ┌──────────────────────────────┐
│ docker compose up   │        │ QApplication                 │
│ wait postgres       │   →    │ QWebEngineView               │
│ alembic upgrade     │        │   └─ http://localhost:5173   │ (dev)
│ uvicorn start       │        │   └─ http://localhost:8000   │ (prod)
│ wait API health     │        │ view.show()                  │
│ run_ui() ──────────────────► │ app.exec()                   │
│ shutdown on exit    │        └──────────────────────────────┘
└─────────────────────┘
```

---

## Fase 0 — Desktop Shell: QML → WebEngineView [AGORA]

**Objetivo:** O comando `mindflow` abre o React frontend em uma janela nativa.

### 0.1 — Substituir `main.py`

```python
# python/mindflow_desktop/main.py
import os, sys
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile

def run_ui() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("MindFlow")

    profile = QWebEngineProfile.defaultProfile()
    profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)  # dev

    view = QWebEngineView()
    view.setWindowTitle("MindFlow")
    view.resize(1440, 900)

    frontend_url = os.getenv("MINDFLOW_FRONTEND_URL", "http://127.0.0.1:5173")
    view.setUrl(QUrl(frontend_url))
    view.show()

    raise SystemExit(app.exec())
```

### 0.2 — Launcher inicia Vite em dev mode (opcional)

Adicionar ao `launcher.py` antes de `run_ui()`:
```python
if _truthy(os.getenv("MINDFLOW_START_FRONTEND", "1")):
    frontend_root = python_root.parent / "frontend"
    frontend_process = _start_background_process(
        ["npm", "run", "dev"],
        cwd=frontend_root,
        log_path=logs_dir / "frontend.log",
    )
    processes.append(frontend_process)
    time.sleep(3)  # Vite sobe em ~1s
```

### 0.3 — Alias no sistema

```bash
# ~/.bash_aliases
alias mindflow="/home/levybonito/Projetos/MindFlow/python/.venv/bin/mindflow-desktop"
```

**Resultado da Fase 0:** `mindflow` → launcher inicia infra → abre janela nativa com React frontend

---

## Fase 1 — Design Foundation [Semana 1, Dia 1–2]

**Objetivo:** Sistema de tokens e tipografia corretos antes de tocar em qualquer componente.

### 1.1 — `tokens-v2.css`

Criar `frontend/src/styles/tokens-v2.css` com todas as variáveis CSS do sistema v2:

```css
/* Base do sistema v2 extraído do mindflow.pen */
:root {
  /* Backgrounds */
  --bg-main: #FAFAFA;
  --bg-sidebar: #FFFFFF;
  --bg-card: #FFFFFF;
  --bg-input: #FFFFFF;

  /* Borders */
  --border-default: #E5E5E5;
  --border-active: #0D6E6E;

  /* Text */
  --text-primary: #1A1A1A;
  --text-meta: #999999;
  --text-placeholder: #BBBBBB;

  /* Accent */
  --accent: #0D6E6E;
  --accent-bg: #E8F4F4;
  --accent-bg-dark: #0D2E2E;

  /* Agents */
  --agent-orchestrator: #8B5CF6;
  --agent-analyst: #F59E0B;
  --agent-coder: #3B82F6;
  --agent-research: #22D3EE;

  /* Delegation */
  --delegation-bg: #FEFDFF;
  --delegation-border: #DDD6E8;
  --delegation-meta: #8D84A0;
  --delegation-title: #251D2E;
  --delegation-purple: #8B5CF6;

  /* Typography families */
  --font-ui: 'JetBrains Mono', monospace;         /* chrome, labels, meta */
  --font-serif: 'Newsreader', serif;               /* títulos de sessão */
  --font-agent: 'Cormorant Garamond', serif;       /* nomes de agentes */
  --font-body: 'Familjen Grotesk', sans-serif;     /* corpo de texto */
  --font-mono-alt: 'Azeret Mono', monospace;       /* timestamps, meta */
  --font-badge: 'Space Grotesk', sans-serif;       /* badges de status */
}

[data-theme="dark"] {
  --bg-main: #0D0D0D;
  --bg-sidebar: #161616;
  --bg-card: #1E1E1E;
  --bg-input: #161616;
  --border-default: #2A2A2A;
  --text-primary: #E8E8E8;
  --text-meta: #555555;
  --text-placeholder: #444444;
  --delegation-bg: #161616;
  --delegation-border: #2A2A2A;
}
```

### 1.2 — Bundle das 6 fontes

```
frontend/src/assets/fonts/
├── JetBrainsMono-Regular.woff2
├── JetBrainsMono-SemiBold.woff2
├── Newsreader-Medium.woff2
├── CormorantGaramond-Medium.woff2
├── FamiljenGrotesk-Regular.woff2
├── AzeretMono-Regular.woff2
├── AzeretMono-Medium.woff2
└── SpaceGrotesk-Medium.woff2
```

Adicionar `@font-face` declarations em `index.css`.
**Validar no WebEngineView antes de avançar** — fontes locais carregam diferente de CDN.

---

## Fase 2 — Componentes Leaf (visual puro) [Semana 1, Dia 3–5]

**Regra:** Só CSS/tokens. Nenhuma lógica de componente é movida nessa fase. PRs pequenos por componente.

### Ordem de refatoração (menor risco → maior)

| Ordem | Componente | Mudança v2 | Arquivo |
|---|---|---|---|
| 1 | `Sidebar.tsx` | Padding v2, sem Section Header, teal left-border no ativo | Cosmético |
| 2 | `TopBar.tsx` | Título Newsreader 20px, subtítulo folderPath JetBrains Mono 11px cinza | Baixo |
| 3 | `ThinkingNotifier.tsx` | Pills por agente: `cornerRadius: 8`, cor por tipo | Baixo |
| 4 | `StreamNotifier.tsx` | 5 variantes de pill: routing/tool/done/error/warn com ícone Lucide + texto | Médio |
| 5 | `AgentBubble.tsx` | `cornerRadius: 12`, `fill: #1E1E1E` dark / `#FFFFFF` light, nome em Cormorant Garamond | Médio |
| 6 | `ThoughtBubble.tsx` | Substituir por pills de thinking state por agente | Médio |
| 7 | `Button.tsx` | Ajustar para sistema de tokens v2 | Baixo |

**Checkpoint:** Rodar o app após cada componente. Nenhuma feature quebrada.

---

## Fase 3 — Layout Trifásico [Semana 2, Dia 1–2]

**Objetivo:** `Sidebar | Chat | Inspector` com slot opcional para o painel direito.

### 3.1 — `MainLayout.tsx`

```tsx
// Antes: <Sidebar /> <Outlet />
// Depois:
interface MainLayoutProps {
  rightPanel?: React.ReactNode   // undefined = sem painel direito
}

// Layout: grid com 3 colunas
// grid-template-columns: 240px 1fr [rightPanelWidth]
// rightPanelWidth: 0px quando undefined, 420px quando presente
// transition: width 300ms ease para abertura suave
```

### 3.2 — `ChatPage.tsx`

```tsx
// ChatPage controla quando o inspector aparece
const [inspectorOpen, setInspectorOpen] = useState(false)
const [activeDelegation, setActiveDelegation] = useState(null)

<MainLayout rightPanel={inspectorOpen ? <DelegationInspector delegation={activeDelegation} /> : undefined}>
  <ChatInterface onDelegationClick={(d) => { setActiveDelegation(d); setInspectorOpen(true) }} />
</MainLayout>
```

---

## Fase 4 — DelegationCard + Inspector [Semana 2, Dia 3–5]

### 4.1 — Extração de hooks de `ChatInterface.tsx`

Antes de tocar no inspector, extrair lógica de delegação:

```
hooks/
├── useDelegationStack.ts   ← fila de agentes delegados sincronizada com SSE
└── useMessageRenderer.ts   ← lógica de renderização por tipo de evento
```

`useDelegationStack` mantém `delegatedAgents: Agent[]` onde `[0]` é o agente ativo.
Alimentado pelos eventos SSE `delegation_started` e `specialist_active`.

### 4.2 — `DelegationCard.tsx` (v2 — NZTyZ)

```
┌─────────────────────────────────────┐
│ ⬡ Delegation Pipeline  ● ativo      │  ← header: CPU icon + badge
├─────────────────────────────────────┤
│ ○ Research Agent        [running]   │
│ ○ Analyst Agent         [waiting]   │  ← body: agentes com status
│ ○ Coder Agent           [waiting]   │
├─────────────────────────────────────┤
│ ⏱ 3 agentes · ~2min    Pipeline #47 │  ← footer: timer + pipeline tag
└─────────────────────────────────────┘
         ↑ clicável → abre Inspector
```

### 4.3 — `DelegationInspector.tsx` (v2 — HWv2m)

Estado interno do stacked cards:

```tsx
// useDelegationStack retorna:
// [ResearchAgent, AnalystAgent, CoderAgent]  ← [0] é o front da pilha

// CSS: 3 cards sobrepostos com position:absolute
// front (index 0): translateY(0)   scale(1)   opacity(1)
// back1 (index 1): translateY(-8px) scale(0.97) opacity(0.86)
// back2 (index 2): translateY(-16px) scale(0.94) opacity(0.55)
// transition: all 300ms ease
```

Layout visual:
```
┌── rail (220px) ─┐  ┌── shell (fill) ──────────────────┐
│ delegated agents│  │   ┌── back2 (faded) ───────────┐  │
│                 │  │  ┌── back1 (semi) ────────────┐│  │
│ [●] Research   ←selected  ┌── front ─────────────┐ ││  │
│ [ ] Analyst     │  │  │  │ Research Agent        │ ││  │
│ [ ] Coder       │  │  │  │ status + tool calls   │ ││  │
│                 │  │  │  │ output preview        │ ││  │
└─────────────────┘  │  │  └──────────────────────-┘ ││  │
                     │  └──────────────────────────────┘│  │
                     └────────────────────────────────────┘
```

---

## Fase 5 — Novos Componentes [Semana 3, Dia 1–3]

### 5.1 — `AgentTodoList.tsx`

```tsx
// Consume eventos SSE: { type: "todo_update", data: { items: TodoItem[] } }
// Renderiza como card collapsível no chat
// Design: todoListCompLight / todoListCompDark do mindflow.pen
interface TodoItem {
  id: string
  label: string
  status: 'pending' | 'in_progress' | 'done'
}
```

### 5.2 — `MemoryRecallNotifier.tsx`

```tsx
// Dois tipos: Vector Memory Recall | Database Memory Recall
// Dois estados: loading (pulsar) | done (checkmark teal)
// Design: 1kYkh, 2FiNW, qYfEd, wfu69 do mindflow.pen
// Pill horizontal com ícone + label + estado
```

### 5.3 — Audit de `displayPolicy.ts` + `notifierMapping.ts`

Mapear todos os novos `EventType` para os novos componentes antes de testar.

---

## Fase 6 — Polish Desktop [Semana 3, Dia 4–5]

### 6.1 — Janela customizada

- Remover titlebar nativo (`QWebEngineView` com `setWindowFlags(Qt.FramelessWindowHint)`)
- Implementar drag region no React: `app-region: drag` via CSS + IPC PySide6
- Botões de controle (fechar/minimizar/maximizar) no TopBar v2

### 6.2 — App icon

- Criar `mindflow.icns` (Mac), `mindflow.ico` (Win), `mindflow.png` (Linux)
- Aplicar via `app.setWindowIcon(QIcon(...))`

### 6.3 — Build script

```makefile
# python/Makefile — adicionar targets:
desktop-build:   # vite build → FastAPI serve static → mindflow-desktop
desktop-dev:     # vite dev + mindflow-desktop com MINDFLOW_FRONTEND_URL=http://localhost:5173
```

---

## Cronograma

```
Semana 1:
  Dia 1: Fase 0 (WebEngineView + alias) ← HOJE
  Dia 2: Fase 1 (tokens-v2.css + fontes)
  Dia 3: Fase 2 início (Sidebar, TopBar, ThinkingNotifier)
  Dia 4: Fase 2 cont. (StreamNotifier, AgentBubble)
  Dia 5: Fase 2 fim (ThoughtBubble, Button) + checkpoint visual

Semana 2:
  Dia 1–2: Fase 3 (MainLayout 3 colunas)
  Dia 3–4: Fase 4 parte 1 (extração hooks + DelegationCard v2)
  Dia 5: Fase 4 parte 2 (DelegationInspector stacked cards)

Semana 3:
  Dia 1–3: Fase 5 (TodoList + MemoryRecall + audit displayPolicy)
  Dia 4–5: Fase 6 (polish desktop + build script)
```

---

## Arquivos que NÃO mudam nessa refatoração

- `launcher.py` — backend lifecycle perfeito, não tocar
- `useOmniStream.ts` — SSE hookl estável
- `useChatSessions.ts` — CRUD de sessões funcionando
- `appStore.ts` — state management ok
- Toda a camada de backend (`/python/mindflow_backend/`)
