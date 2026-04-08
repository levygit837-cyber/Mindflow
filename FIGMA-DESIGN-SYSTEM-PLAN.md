# MindFlow Design System - Implementation Plan

## Overview
Este documento detalha a implementação completa do Design System do MindFlow no Figma, baseado nos componentes existentes no arquivo Pencil e nos requisitos da Chat UI.

## File Structure
**Figma File:** [MindFlow Design System](https://www.figma.com/design/kQ7Yudxh3DdFpbMt0C76Zz)

## 1. Design Tokens (Foundation)

### Colors
Baseado nos tokens existentes no arquivo Pencil:

#### Primary Colors
- **--bg-primary**: #0E0E12 (Main background)
- **--bg-surface**: #16161C (Cards, panels)
- **--bg-elevated**: #1E1E26 (Hover states)
- **--bg-sidebar**: #0B0B0F (Sidebar background)
- **--bg-input**: #1A1A22 (Input backgrounds)
- **--bg-hover**: #262630 (Interactive hover)
- **--bg-active-session**: #14141C (Active chat session)

#### Text Colors
- **--text-primary**: #E8E8ED (Main text)
- **--text-secondary**: #9898A6 (Secondary text)
- **--text-meta**: #5C5C6E (Meta information)
- **--text-ghost**: #3A3A48 (Placeholder/disabled)
- **--text-inverse**: #08080A (On colored backgrounds)

#### Line Colors
- **--line-primary**: #2A2A36 (Main borders)
- **--line-soft**: #1E1E28 (Subtle borders)
- **--line-strong**: #3A3A48 (Strong borders)

#### Agent Colors (Brand)
- **--agent-orchestrator**: #1A8F8F (Primary brand)
- **--agent-orchestrator-muted**: #112828 (Dark variant)
- **--agent-orchestrator-soft**: #0F2E2E (Soft variant)
- **--agent-analyst**: #6E7FE0 (Analyst brand)
- **--agent-analyst-muted**: #1A1E3A (Dark variant)
- **--agent-analyst-soft**: #161A36 (Soft variant)
- **--agent-coder**: #E8734A (Coder brand)
- **--agent-coder-muted**: #3A1E14 (Dark variant)
- **--agent-coder-soft**: #2E1810 (Soft variant)
- **--agent-researcher**: #3BA876 (Researcher brand)
- **--agent-researcher-muted**: #142E22 (Dark variant)
- **--agent-researcher-soft**: #0F2E1E (Soft variant)

#### Signal Colors
- **--signal-success**: #3BA876 (Success states)
- **--signal-error**: #E06B54 (Error states)
- **--signal-warning**: #D4A23F (Warning states)
- **--signal-info**: #5B8FD9 (Information)
- **--signal-synapse**: #9B7FD4 (AI/Synapse actions)
- **--signal-synapse-soft**: #1A1528 (Soft synapse)

### Typography
#### Font Families
- **Primary:** Inter (UI text)
- **Monospace:** JetBrains Mono (Code, technical labels)

#### Font Sizes
- **Display:** 24px, 28px
- **Headings:** 18px, 20px
- **Body:** 14px, 16px
- **Small:** 11px, 12px, 13px
- **Micro:** 9px, 10px

#### Font Weights
- **Regular:** 400
- **Medium:** 500
- **Semibold:** 600
- **Bold:** 700

#### Line Heights
- **Tight:** 1.4
- **Normal:** 1.6
- **Relaxed:** 1.8

### Spacing Scale
- **xs:** 4px
- **sm:** 8px
- **md:** 12px
- **lg:** 16px
- **xl:** 20px
- **2xl:** 24px
- **3xl:** 32px
- **4xl:** 40px
- **5xl:** 48px

### Border Radius
- **sm:** 4px (Small elements)
- **md:** 6px (Buttons, inputs)
- **lg:** 8px (Cards, panels)
- **xl:** 12px (Large containers)
- **full:** 999px (Pills, avatars)

### Shadows
- **sm:** 0px 1px 2px rgba(0, 0, 0, 0.1)
- **md:** 0px 4px 6px rgba(0, 0, 0, 0.15)
- **lg:** 0px 10px 15px rgba(0, 0, 0, 0.2)
- **xl:** 0px 20px 25px rgba(0, 0, 0, 0.25)

## 2. Foundation Components

### Buttons
#### ActionButton/Primary
- Background: --signal-synapse
- Text: --white
- Height: 36px
- Padding: 0 20px
- Border radius: 8px
- Font: Inter 13px 600

#### ActionButton/Secondary
- Background: --bg-surface
- Text: --text-primary
- Border: --line-primary 1px
- Height: 36px
- Padding: 0 20px
- Border radius: 8px

#### ActionButton/Ghost
- Background: transparent
- Text: --text-meta
- Height: 36px
- Padding: 0 16px
- Border radius: 8px

#### ActionButton/Danger
- Background: --signal-error
- Text: --white
- Height: 36px
- Padding: 0 20px
- Border radius: 8px

### Agent Chips
#### AgentChip/Orchestrator
- Background: --agent-orchestrator
- Text: --white
- Height: 28px
- Padding: 0 14px
- Border radius: 999px
- Font: Inter 11px 600
- Letter spacing: 0.5px

#### AgentChip/Analyst
- Background: --agent-analyst
- Text: --white
- Same dimensions as Orchestrator

#### AgentChip/Coder
- Background: --agent-coder
- Text: --white
- Same dimensions as Orchestrator

#### AgentChip/Researcher
- Background: --agent-researcher
- Text: --white
- Same dimensions as Orchestrator

### Status Dots
- **Active:** --signal-success
- **Thinking:** --signal-warning
- **Error:** --signal-error
- **Idle:** --text-meta
- Size: 8px diameter

### Icons
- Icon font: Lucide
- Sizes: 13px, 14px, 15px, 16px
- Colors: Inherit from text color

## 3. Chat UI Components

### Sidebar
#### Structure
```
Sidebar (260px width, 640px height)
├── sbLogo
│   ├── sbLogoDot (--agent-orchestrator, 8px)
│   ├── sbLogoText ("MindFlow", JetBrains Mono 13px 600)
│   └── sbSettingsBtn (Lucide settings, --text-meta)
├── sbActions
│   └── sbNewChat (--agent-orchestrator background)
├── sbRecent
│   └── sbRecentLabel ("RECENT", --text-meta)
├── Sessions
│   ├── sbSess1 (Active session with --agent-orchestrator border)
│   ├── sbSess2 (Inactive session)
│   └── sbSess3 (Inactive session)
└── sbUser
    ├── newAvatar (--agent-orchestrator, 32px)
    └── sbUserInfo
        ├── sbUserName (--text-primary)
        └── sbUserRole (--text-meta)
```

#### Specifications
- Width: 260px
- Background: --bg-sidebar
- Border: --line-primary 1px (right side)
- Padding: Top sections 20px, 8px
- New Chat button: --agent-orchestrator background with white text
- Sessions: --bg-active-session for active, transparent for inactive
- Active session indicator: --agent-orchestrator 2px left border

### Input Area
#### Structure
```
InputArea
├── iaToolbar
│   ├── iaTool1 (Folder picker)
│   └── iaTool2 (Model selector with dropdown)
├── iaShell
│   ├── iaTextarea (Multiline input)
│   └── iaSendBtn (--signal-synapse background)
└── iaHint (Disclaimer text)
```

#### Specifications
- Background: --bg-primary
- Border: --line-primary 1px (top)
- Padding: 16px 32px
- Gap: 8px between elements

#### Input Toolbar
- Folder picker: --bg-surface, --text-meta
- Model selector: --bg-surface, --text-meta with dropdown

#### Input Shell
- Background: --bg-surface
- Border: --line-primary 1px
- Border radius: 12px
- Padding: 12px 16px
- Gap: 12px

#### Send Button
- Background: --signal-synapse
- Size: 32px x 32px
- Border radius: 8px
- Icon: Lucide arrow-up-right in white

### Message Bubbles
#### UserMessage
- Background: --bg-elevated
- Text: --text-primary
- Border radius: 12px
- Padding: 12px 16px
- Max width: 80% of container

#### AgentMessage
- Background: --bg-surface
- Text: --text-primary
- Border radius: 12px
- Padding: 12px 16px
- Max width: 80% of container

### Tool Cards
#### ToolCallCard/Collapsed
- Background: --bg-elevated
- Border: --line-primary 1px
- Border radius: 8px
- Padding: 12px
- Tool icon + name + status

#### ToolCallCard/Expanded
- Same as collapsed but with:
- Tool description
- Parameters
- Results/code block
- Dark background for code

### Tool Pills
- Background: --bg-hover
- Text: --text-secondary
- Border radius: 16px
- Padding: 4px 8px
- Font size: 11px

## 4. Implementation Steps

### Step 1: Create Design Tokens Page
1. Create color styles for all color tokens
2. Create text styles for typography
3. Create effect styles for shadows
4. Create grid layout styles for spacing

### Step 2: Create Foundation Components
1. Build button variants (Primary, Secondary, Ghost, Danger)
2. Create agent chips with proper colors
3. Design status indicators
4. Create icon library with Lucide icons

### Step 3: Build Chat UI Components
1. Design sidebar with all states
2. Create input area with toolbar
3. Build message bubble components
4. Design tool cards and pills

### Step 4: Create Layout Templates
1. Chat view template (sidebar + main content)
2. Empty state template
3. Mobile responsive layouts

### Step 5: Documentation
1. Create usage guidelines
2. Document component states
3. Create interaction patterns
4. Setup Code Connect for React integration

## 5. Component Variants

### Button States
- Default, Hover, Active, Disabled, Loading

### Input States
- Default, Focus, Error, Disabled

### Message States
- Sending, Sent, Failed, Streaming

### Tool States
- Pending, Running, Success, Error

## 6. Responsive Design

### Breakpoints
- Mobile: 320px - 768px
- Tablet: 768px - 1024px
- Desktop: 1024px+

### Adaptations
- Sidebar collapses to hamburger on mobile
- Input area becomes full-width on mobile
- Tool cards stack vertically on small screens

## 7. Accessibility

### Contrast Ratios
- All text meets WCAG AA standards
- Interactive elements have 4.5:1 minimum contrast

### Focus States
- All interactive elements have visible focus indicators
- Focus follows logical tab order

### Screen Reader Support
- All icons have appropriate labels
- Component states are announced properly

## 8. Code Connect Setup

### React Components
- Map Figma components to React components
- Define props for each variant
- Setup automatic code generation

### CSS Variables
- Export design tokens as CSS custom properties
- Use in React components for theming

## Next Steps

1. **Immediate:** Create design tokens page in Figma
2. **Week 1:** Build foundation components
3. **Week 2:** Create Chat UI components
4. **Week 3:** Documentation and Code Connect setup
5. **Week 4:** Testing and refinement

## Files to Reference

- Pencil Design: `/home/levybonito/Projetos/MindFlow/design/mindflow/Frontend/pencil-new.pen`
- Component Library: Existing 51 reusable components
- Design Tokens: 38 color variables defined

---

**Status:** Ready for implementation in Figma
**Next Action:** Create design tokens page and start building foundation components
