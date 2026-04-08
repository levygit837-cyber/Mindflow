# Guia Prático: Implementando o MindFlow Design System no Figma

## 📋 Acesso ao Arquivo
**URL:** [MindFlow Design System](https://www.figma.com/design/kQ7Yudxh3DdFpbMt0C76Zz)

## 🎨 Passo 1: Configurar Design Tokens

### 1.1 Criar Página de Tokens
1. No Figma, crie uma nova página chamada "🎨 Design Tokens"
2. Organize em seções: Colors, Typography, Spacing, Effects

### 1.2 Cores - Criar Styles
Selecione cada elemento e crie Style (Cmd+Shift+C):

#### Background Colors
```figma
# Criar retângulos com estas cores e criar Styles:
--bg-primary: #0E0E12
--bg-surface: #16161C  
--bg-elevated: #1E1E26
--bg-sidebar: #0B0B0F
--bg-input: #1A1A22
--bg-hover: #262630
--bg-active-session: #14141C
```

#### Text Colors
```figma
--text-primary: #E8E8ED
--text-secondary: #9898A6
--text-meta: #5C5C6E
--text-ghost: #3A3A48
--text-inverse: #08080A
```

#### Agent Colors (Brand)
```figma
--agent-orchestrator: #1A8F8F
--agent-analyst: #6E7FE0
--agent-coder: #E8734A
--agent-researcher: #3BA876
```

### 1.3 Tipografia - Criar Text Styles
```figma
# Criar textos e criar Styles (Cmd+Opt+T):

Headings:
- Display 1: Inter/24px/600/Semibold
- Display 2: Inter/20px/600/Semibold  
- Heading 1: Inter/18px/600/Semibold
- Heading 2: Inter/16px/500/Medium

Body:
- Body Large: Inter/16px/400/Regular
- Body: Inter/14px/400/Regular
- Body Small: Inter/12px/400/Regular

Meta:
- Caption: Inter/11px/400/Regular
- Label: Inter/10px/600/Semibold

Monospace:
- Code Large: JetBrains Mono/14px/400/Regular
- Code: JetBrains Mono/12px/400/Regular
- Code Small: JetBrains Mono/10px/400/Regular
```

## 🧩 Passo 2: Criar Componentes Fundamentais

### 2.1 Criar Página "🧩 Foundation Components"

#### Buttons (ActionButton)
1. **Primary Button**
   - Retângulo: 36px height, 120px width
   - Background: --signal-synapse (#9B7FD4)
   - CornerRadius: 8px
   - Text: "Send" / Inter/13px/600/White
   - Icon: Lucide/send/14px/White
   - Criar componente com variants: State=Default,Hover,Pressed,Disabled

2. **Secondary Button**
   - Background: --bg-surface (#16161C)
   - Border: --line-primary (#2A2A36) 1px
   - Text: --text-primary (#E8E8ED)
   - Mesmas dimensões

3. **Ghost Button**
   - Background: Transparent
   - Text: --text-meta (#5C5C6E)
   - Sem borda

4. **Danger Button**
   - Background: --signal-error (#E06B54)
   - Text: White

#### Agent Chips
1. **Criar AgentChip/Orchestrator**
   - Auto Layout: Horizontal, 8px gap
   - Background: --agent-orchestrator (#1A8F8F)
   - CornerRadius: 999px
   - Padding: 0 14px
   - Height: 28px
   - Circle: 6px diameter, White
   - Text: "Orchestrator" / Inter/11px/600/White
   - LetterSpacing: 0.5px

2. **Variants para outros agentes**
   - Analyst: --agent-analyst (#6E7FE0)
   - Coder: --agent-coder (#E8734A)
   - Researcher: --agent-researcher (#3BA876)

#### Status Dots
- Círculos 8px diameter
- Cores: Success (#3BA876), Warning (#D4A23F), Error (#E06B54), Idle (#5C5C6E)

## 💬 Passo 3: Criar Componentes Chat UI

### 3.1 Criar Página "💬 Chat Components"

#### Sidebar Component
1. **Frame Principal**
   - Width: 260px, Height: 640px
   - Background: --bg-sidebar (#0B0B0F)
   - Border Right: --line-primary 1px

2. **Logo Section**
   - Auto Layout Vertical, 8px gap
   - Padding: 20px 20px 16px 20px
   - Border Bottom: --line-primary 1px
   - Logo Dot: 8px círculo --agent-orchestrator
   - Logo Text: "MindFlow" / JetBrains Mono/13px/600/--text-primary
   - Settings Icon: Lucide/settings/13px/--text-meta

3. **New Chat Button**
   - Background: --bg-active-session (#14141C)
   - Border Left: --agent-orchestrator 2px
   - Padding: 10px 16px
   - Icon + Text: --agent-orchestrator color

4. **Sessions List**
   - Active Session: --bg-active-session, --agent-orchestrator left border
   - Inactive Sessions: Transparent, transparent border
   - Time stamps: --text-ghost, JetBrains Mono/9px

5. **User Section**
   - Border Top: --line-primary 1px
   - Avatar: 32px círculo --agent-orchestrator com inicial
   - User info: Name (--text-primary), Role (--text-meta)

#### Input Area Component
1. **Container Principal**
   - Background: --bg-primary
   - Border Top: --line-primary 1px
   - Padding: 16px 32px
   - Gap: 8px

2. **Toolbar**
   - Folder Picker: --bg-surface, --text-meta, Lucide/paperclip
   - Model Selector: --bg-surface, dropdown, Lucide/chevron-down

3. **Input Shell**
   - Background: --bg-surface
   - Border: --line-primary 1px, CornerRadius: 12px
   - Padding: 12px 16px
   - Gap: 12px
   - Textarea: Placeholder --text-ghost, Inter/14px
   - Send Button: 32px circle, --signal-synapse, Lucide/arrow-up-right

4. **Hint Text**
   - Center aligned, --text-ghost, Inter/11px

#### Message Bubbles
1. **UserMessage**
   - Background: --bg-elevated
   - CornerRadius: 12px
   - Padding: 12px 16px
   - Max Width: 80%

2. **AgentMessage**
   - Background: --bg-surface
   - Mesmas dimensões

## 📱 Passo 4: Criar Layout Templates

### 4.1 Criar Página "📱 Layout Templates"

#### Chat View Template
1. **Desktop Layout**
   - Sidebar: 260px fixed left
   - Main Content: Remaining width
   - Input Area: Fixed bottom, full width

2. **Mobile Layout**
   - Full-width content
   - Collapsible sidebar (hamburger menu)
   - Input area always visible

#### Empty State Template
- Centered content
- Logo + Title + Subtitle
- Suggestion cards (3 cards horizontal)

## 🔧 Passo 5: Configurar Component Properties

### 5.1 Boolean Properties
```figma
# Para cada componente, adicionar:
- hasIcon: true/false
- isLoading: true/false  
- isActive: true/false
- isDisabled: true/false
```

### 5.2 Variant Properties
```figma
# Buttons:
- State: Default/Hover/Pressed/Disabled
- Size: sm/md/lg
- Variant: Primary/Secondary/Ghost/Danger

# Agent Chips:
- Agent: Orchestrator/Analyst/Coder/Researcher
- Size: sm/md
```

### 5.3 Text Properties
```figma
# Textos dinâmicos:
- buttonText: string
- labelText: string
- placeholderText: string
```

## 🎯 Passo 6: Criar Interactions

### 6.1 Hover States
- Buttons: Opacity 80% ou background mais claro
- Chips: Scale 1.05
- Interactive elements: Cursor pointer

### 6.2 Focus States
- Outline: 2px --signal-synapse
- Offset: 2px

### 6.3 Transitions
- Duration: 150ms
- Easing: Easy Out

## 📚 Passo 7: Documentação

### 7.1 Criar Página "📚 Documentation"
1. **Usage Guidelines**
   - When to use each component
   - Do's and Don'ts
   - Accessibility notes

2. **Component Catalog**
   - Screenshots of each component
   - Props table
   - Code examples

3. **Design Principles**
   - Dark theme guidelines
   - Agent color usage
   - Typography hierarchy

## 🔗 Passo 8: Code Connect Setup

### 8.1 Instalar Code Connect Plugin
1. Vá para Plugins > Search "Code Connect"
2. Instale o plugin oficial do Figma

### 8.2 Mapear Componentes React
```figma
# Para cada componente:
1. Selecione o componente
2. Plugin > Code Connect > Create mapping
3. Configure:
   - Component name: Button, AgentChip, etc.
   - Props: variant, size, children, etc.
   - Framework: React
   - Language: TypeScript
```

### 8.3 Exportar Tokens
1. Plugin > Code Connect > Export tokens
2. Formato: CSS Variables
3. Salvar como design-tokens.css

## ✅ Checklist de Implementação

### Design Tokens ☐
- [ ] All color styles created
- [ ] All text styles created  
- [ ] All effect styles created
- [ ] All spacing styles created

### Foundation Components ☐
- [ ] Button variants (4 states × 3 sizes)
- [ ] Agent chips (4 agents × 2 sizes)
- [ ] Status indicators (4 states)
- [ ] Icon library (Lucide icons)

### Chat Components ☐
- [ ] Sidebar (all states)
- [ ] Input area (all states)
- [ ] Message bubbles (user/agent)
- [ ] Tool cards (collapsed/expanded)
- [ ] Tool pills

### Layout Templates ☐
- [ ] Desktop chat view
- [ ] Mobile chat view
- [ ] Empty state
- [ ] Loading states

### Documentation ☐
- [ ] Usage guidelines
- [ ] Component catalog
- [ ] Design principles
- [ ] Accessibility guide

### Code Connect ☐
- [ ] All components mapped
- [ ] Tokens exported
- [ ] Code generation working
- [ ] Integration tested

## 🚀 Próximos Passos

1. **Implementação Imediata:** Começar com Design Tokens
2. **Semana 1:** Foundation Components
3. **Semana 2:** Chat UI Components  
4. **Semana 3:** Layout Templates e Documentação
5. **Semana 4:** Code Connect e Testes

## 📞 Suporte

- **Arquivo Figma:** https://www.figma.com/design/kQ7Yudxh3DdFpbMt0C76Zz
- **Plano Detalhado:** `/home/levybonito/Projetos/MindFlow/FIGMA-DESIGN-SYSTEM-PLAN.md`
- **Referência Pencil:** `/home/levybonito/Projetos/MindFlow/design/mindflow/Frontend/pencil-new.pen`

---

**Status:** Pronto para implementação manual no Figma
**Ação Imediata:** Criar página de Design Tokens e começar a configurar os styles de cores
