# Design System: MindFlow

## 1. Visual Theme & Atmosphere

MindFlow's interface is a collaborative AI workspace designed for multi-agent orchestration. The experience is built on a dark theme canvas that emphasizes agent identity through color-coded visual language. Each specialized agent (Orchestrator, Analyst, Coder, Researcher) has a distinct color signature that permeates the entire interface — from avatar badges to message borders, progress indicators, and action chips.

The design philosophy centers on **agent-first visibility**: users should instantly recognize which agent is speaking, delegating, or executing. This is achieved through a consistent color system where each agent's signature color appears in:
- Agent chips and avatars
- Message borders and accent lines
- Progress bars and status indicators
- Action pills and suggestion cards
- Tool call result blocks

The interface balances technical precision with approachable warmth. Dark surfaces (`#0a0a0a` to `#1a1a1a`) provide high-contrast canvas for code and text, while the agent color palette adds vibrancy without overwhelming. Typography uses a clean sans-serif system with monospace for code, ensuring readability during extended collaborative sessions.

The EventRail is the central metaphor — a vertical timeline of agent activities, tool calls, thinking blocks, and delegation events. Each event type has distinctive visual treatment: collapsible thinking blocks, expandable tool call cards with dark code blocks, delegation cards with strategy badges, and streaming indicators for real-time responses.

**Key Characteristics:**
- Agent color-coded identity system (4 distinct colors)
- Dark theme with high-contrast surfaces
- EventRail vertical timeline as central organizing metaphor
- Collapsible/expandable event cards for progressive disclosure
- Streaming indicators for real-time AI responses
- Empty state with suggestion cards colored by agent type
- Monospace for code, clean sans-serif for UI text
- 8px base spacing system

## 2. Color Palette & Roles

### Agent Signature Colors
- **Orchestrator Teal** (`#0D6E6E`): Primary orchestration agent. Used for session management, coordination events, and system-level messages. Deep, authoritative teal.
- **Analyst Indigo** (`#5B6ABF`): Analysis and insights agent. Used for data interpretation, pattern recognition, and analytical outputs. Rich, thoughtful indigo.
- **Coder Orange** (`#C75D2C`): Code generation and execution agent. Used for code blocks, file operations, and development tasks. Warm, energetic orange.
- **Researcher Green** (`#2D8F5E`): Research and information gathering agent. Used for documentation, web searches, and knowledge retrieval. Fresh, verdant green.

### Surface & Background
- **Surface Primary** (`#0a0a0a`): Deepest background, main page surface. Near-black for maximum contrast.
- **Surface Secondary** (`#1a1a1a`): Card backgrounds, elevated containers, sidebar. Slightly lighter dark surface.
- **Surface Tertiary** (`#2a2a2a`): Input areas, code blocks, deeper nested elements. Mid-dark surface.
- **Surface Highlight** (`#3a3a3a`): Hover states, active elements, emphasized surfaces. Lighter dark surface.

### Text Colors
- **Text Primary** (`#ffffff`): Primary text on dark surfaces. Pure white for maximum readability.
- **Text Secondary** (`#b0b0b0`): Secondary text, descriptions, metadata. Light gray for hierarchy.
- **Text Tertiary** (`#707070`): Tertiary text, timestamps, de-emphasized content. Medium gray.
- **Text Muted** (`#505050`): Placeholder text, disabled states. Darker gray.

### Semantic Colors
- **Success** (`#2D8F5E`): Reuses Researcher Green for success states
- **Error** (`#e74c3c`): Standard error red for failures and exceptions
- **Warning** (`#f39c12`): Warning yellow for caution states
- **Info** (`#3498db`): Info blue for informational messages

### Border Colors
- **Border Subtle** (`#2a2a2a`): Subtle borders, dividers. Matches surface tertiary
- **Border Standard** (`#3a3a3a`): Standard borders, card edges. Matches surface highlight
- **Border Emphasized** (`#4a4a4a`): Emphasized borders, active states. Slightly lighter
- **Border Agent**: Each agent's signature color at 30% opacity for agent-specific borders

### Accent & Interactive
- **Accent Primary** (`#0D6E6E`): Reuses Orchestrator Teal for primary CTAs and brand moments
- **Focus Ring** (`#0D6E6E`): Teal focus ring for accessibility
- **Link Color** (`#5B6ABF`): Reuses Analyst Indigo for links and interactive text

## 3. Typography Rules

### Font Family
- **UI/Body**: `Inter`, `system-ui`, `-apple-system`, `Segoe UI`, `Helvetica Neue`, `Arial`
- **Code**: `Fira Code`, `JetBrains Mono`, `ui-monospace`, `SFMono-Regular`, `Menlo`, `Monaco`, `Consolas`
- **Headings**: Same as UI/Body (Inter) with weight variations

### Hierarchy

| Role | Font | Size | Weight | Line Height | Letter Spacing | Notes |
|------|------|------|--------|-------------|----------------|-------|
| Display Hero | Inter | 48px (3rem) | 600 | 1.20 | -0.02px | Hero headings, empty state titles |
| Section Heading | Inter | 32px (2rem) | 600 | 1.25 | -0.01px | Section titles |
| Sub-heading | Inter | 24px (1.5rem) | 600 | 1.30 | normal | Card titles, feature names |
| Title | Inter | 20px (1.25rem) | 600 | 1.35 | normal | Smaller headings |
| Body Large | Inter | 16px (1rem) | 400 | 1.50 | normal | Primary body text |
| Body Standard | Inter | 14px (0.875rem) | 400 | 1.50 | normal | Standard body text |
| Body Small | Inter | 12px (0.75rem) | 400 | 1.40 | 0.01px | Compact body, captions |
| Caption | Inter | 11px (0.688rem) | 400 | 1.30 | 0.02px | Metadata, timestamps |
| Label | Inter | 10px (0.625rem) | 500 | 1.20 | 0.05px | Badges, small labels |
| Code Block | Fira Code | 14px (0.875rem) | 400 | 1.60 | normal | Code blocks, terminal |
| Code Inline | Fira Code | 13px (0.813rem) | 400 | 1.50 | normal | Inline code |

### Principles
- **Clean sans-serif hierarchy**: Inter provides modern, readable typography with weight-based hierarchy (400 for body, 600 for headings).
- **Monospace for code**: Fira Code ensures code readability with ligatures and clear character distinction.
- **Tight letter-spacing on headings**: Slight negative letter-spacing on larger headings for a compressed, modern feel.
- **Generous line-height for body**: 1.50 line-height on body text for comfortable reading during long sessions.
- **Micro letter-spacing on small text**: Positive letter-spacing on labels (10px) and captions (11px) for readability at small sizes.

## 4. Component Stylings

### Agent Chips & Avatars
- Background: Agent signature color (full opacity)
- Text: White (`#ffffff`)
- Radius: Full pill (9999px) for chips, 50% for circular avatars
- Padding: 4px 12px for chips
- Size: 24px diameter for small avatars, 32px for standard, 40px for large
- Border: None (color background provides definition)

### Buttons

**Primary**
- Background: Orchestrator Teal (`#0D6E6E`)
- Text: White (`#ffffff`)
- Padding: 10px 20px
- Radius: 8px
- Hover: Darken to `#0a5a5a`
- Focus: Teal focus ring (`#0D6E6E` 0px 0px 0px 2px)

**Secondary**
- Background: Surface Highlight (`#3a3a3a`)
- Text: White (`#ffffff`)
- Padding: 10px 20px
- Radius: 8px
- Hover: Lighten to `#4a4a4a`
- Border: 1px solid Border Standard (`#3a3a3a`)

**Ghost**
- Background: Transparent
- Text: Text Primary (`#ffffff`)
- Padding: 10px 20px
- Radius: 8px
- Hover: Background `rgba(255,255,255,0.1)`
- Border: 1px solid Border Subtle (`#2a2a2a`)

**Agent-Specific**
- Background: Agent signature color
- Text: White
- Use: Agent-specific actions, delegation buttons

### Cards & Containers
- Background: Surface Secondary (`#1a1a1a`)
- Border: 1px solid Border Subtle (`#2a2a2a`)
- Radius: 12px standard, 8px compact, 16px featured
- Padding: 16px standard, 12px compact
- Shadow: Subtle `rgba(0,0,0,0.3) 0px 4px 12px` for elevated cards
- Agent-colored accent: Top border 2px in agent signature color for agent-specific cards

### EventRail Components

**ThinkingBlock**
- Background: Surface Tertiary (`#2a2a2a`)
- Border: 1px solid Border Subtle
- Radius: 8px
- Header: Agent chip + "Thinking" label in Text Secondary
- Content: Reasoning text in Text Secondary
- Collapsed: Single line with expand chevron
- Expanded: Full reasoning text with preserved formatting

**DelegationCard**
- Background: Surface Tertiary (`#2a2a2a`)
- Border: 1px solid Border Subtle
- Radius: 8px
- Header: Agent chip + "Delegating to [Agent]" label
- Badges: Strategy, tools metadata pills in agent color
- Content: Delegation context and instructions
- Expandable with chevron

**ToolCallCard**
- Background: Surface Tertiary (`#2a2a2a`)
- Border: 1px solid Border Subtle, left border 3px in agent color
- Radius: 8px
- Header: Tool name + status indicator
- Content: Dark code block with syntax highlighting
- Expandable: Collapsed shows summary, expanded shows full result

**ContextPill**
- Background: Surface Highlight (`#3a3a3a`)
- Text: Text Secondary
- Radius: Full pill (9999px)
- Padding: 4px 10px
- Border: 1px solid Border Subtle
- Use: Context indicators, file references

**StreamingIndicator**
- Animation: Pulsing dots or progress bar
- Color: Agent signature color or Accent Primary
- Size: 16px height for inline, 2px height for progress bar
- Use: Real-time streaming status

### Input Area
- Background: Surface Tertiary (`#2a2a2a`)
- Border: 1px solid Border Standard (`#3a3a3a`)
- Radius: 12px
- Padding: 12px 16px
- Text: Text Primary (`#ffffff`)
- Placeholder: Text Muted (`#505050`)
- Focus: Border shifts to Accent Primary (`#0D6E6E`)
- Chips: Agent selection, folder selection, orchestrate mode pills

### Empty State
- Background: Surface Primary (`#0a0a0a`)
- Centered content with "M" logo
- Title: Display Hero in Text Primary
- Subtitle: Body Large in Text Secondary
- Suggestion Cards: 3 cards with agent-colored accents/borders
  - Coder suggestion with orange accent
  - Analyst suggestion with indigo accent
  - Researcher suggestion with green accent
- Full Input Area below suggestions

### Navigation
- Sidebar: Surface Secondary (`#1a1a1a`) background
- Width: 240px collapsed, 280px expanded
- Border: Right border 1px solid Border Subtle
- Logo: "M" monogram in Accent Primary
- Nav items: Text Secondary on hover, Text Primary on active
- Active indicator: Left border 2px in Accent Primary

### Code Blocks
- Background: Surface Tertiary (`#2a2a2a`) or darker (`#1e1e1e`)
- Border: 1px solid Border Subtle
- Radius: 8px
- Font: Fira Code at 14px
- Padding: 12px
- Syntax highlighting: Agent-colored accents for different token types

## 5. Layout Principles

### Spacing System
- Base unit: 8px
- Scale: 4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px, 96px
- Component padding: 12px compact, 16px standard, 24px generous
- Gap between elements: 8px tight, 12px comfortable, 16px generous
- Section spacing: 32px standard, 48px generous, 64px hero

### Grid & Container
- Max content width: 1200px for main content
- Sidebar: Fixed 240-280px width
- EventRail: Full height with scroll, max content width inherited from container
- Card grids: 2-3 columns for suggestion cards, single column for events
- Responsive: Single column on mobile, multi-column on desktop

### Whitespace Philosophy
- **Dark negative space**: The dark surfaces mean whitespace feels like breathing room rather than emptiness. Large dark areas feel premium and focused.
- **Progressive disclosure**: Collapsible event cards keep the interface clean while allowing detailed inspection when needed.
- **Agent color punctuations**: Agent signature colors provide visual breaks and identity markers within the dark canvas.

### Border Radius Scale
- Sharp (0px): Code blocks, inputs
- Small (4px): Compact cards, badges
- Standard (8px): Most cards, buttons, containers
- Comfortable (12px): Input areas, larger cards
- Generous (16px): Featured cards, modals
- Full Pill (9999px): Chips, pills, tags

## 6. Depth & Elevation

| Level | Treatment | Use |
|-------|-----------|-----|
| Flat (Level 0) | No shadow | Page background, inline text |
| Border Only (Level 1) | 1px solid Border Subtle | Standard cards, containers |
| Border Emphasized (Level 1b) | 1px solid Border Standard | Emphasized cards, active states |
| Agent Border (Level 1c) | 1px solid Agent Color (30%) | Agent-specific containers |
| Subtle Shadow (Level 2) | `rgba(0,0,0,0.3) 0px 4px 12px` | Elevated cards, modals |
| Focus Ring (Level 3) | `0px 0px 0px 2px` Accent Primary | Interactive focus states |

**Shadow Philosophy**: MindFlow uses subtle shadows primarily for elevation on modals and popovers. The dark theme means shadows don't need to be heavy — the surface color variations (`#0a0a0a` → `#1a1a1a` → `#2a2a2a`) provide most of the depth hierarchy. Agent signature colors provide visual pop without needing additional depth.

### Decorative Depth
- Surface color scale creates primary depth: darker = deeper, lighter = elevated
- Agent-colored borders and accents provide visual hierarchy without shadows
- Collapsible event cards use chevron rotation to indicate expanded state
- Streaming indicators use animation for temporal depth

## 7. Do's and Don'ts

### Do
- Use agent signature colors consistently for agent identity
- Maintain dark theme with high-contrast text for readability
- Use collapsible event cards for progressive disclosure
- Apply agent-colored borders/accents to agent-specific components
- Keep code blocks in dark surfaces with monospace fonts
- Use pill shapes (9999px radius) for agent chips and tags
- Maintain 8px base spacing system for consistency
- Use Surface Secondary (`#1a1a1a`) for card backgrounds
- Apply subtle shadows only for elevated elements (modals, popovers)

### Don't
- Don't use light backgrounds for main content — dark theme is core to the identity
- Don't mix agent colors indiscriminately — each agent should have consistent color usage
- Don't use sharp corners (< 4px radius) on cards and buttons — softness is preferred
- Don't apply heavy shadows — surface color variations provide sufficient depth
- Don't use serif fonts for UI — sans-serif (Inter) is the standard
- Don't reduce contrast below accessibility standards — white text on dark surfaces
- Don't ignore the collapsible/expandable pattern for event cards
- Don't use pure black (#000000) — use Surface Primary (#0a0a0a) for softer black

## 8. Responsive Behavior

### Breakpoints
| Name | Width | Key Changes |
|------|-------|-------------|
| Mobile | <640px | Single column, sidebar collapses to drawer, reduced padding |
| Tablet | 640-1024px | Sidebar becomes collapsible, 2-column card grids |
| Desktop | >1024px | Full sidebar, multi-column layouts, maximum content width |

### Touch Targets
- Buttons use comfortable padding (10px 20px minimum)
- Agent chips maintain tap-friendly sizing (4px 12px padding, 24px+ height)
- Navigation links adequately spaced for thumb navigation
- Minimum recommended: 44x44px for touch targets

### Collapsing Strategy
- **Sidebar**: Full width → collapsible drawer on mobile/tablet
- **EventRail**: Maintains full width, cards stack vertically
- **Hero text**: 48px → 32px → 24px progressive scaling
- **Suggestion cards**: 3-column → 2-column → single column stacked
- **Section padding**: Reduces proportionally but maintains breathing room
- **Input area**: Maintains full width, adjusts padding

### Image Behavior
- Agent avatars scale proportionally
- Code blocks maintain monospace font and syntax highlighting
- Suggestion cards maintain agent-colored accents at all sizes
- No art direction changes between breakpoints

## 9. Agent Prompt Guide

### Quick Color Reference
- Orchestrator: `#0D6E6E` (teal)
- Analyst: `#5B6ABF` (indigo)
- Coder: `#C75D2C` (orange)
- Researcher: `#2D8F5E` (green)
- Surface Primary: `#0a0a0a` (near-black)
- Surface Secondary: `#1a1a1a` (dark gray)
- Surface Tertiary: `#2a2a2a` (mid-dark)
- Text Primary: `#ffffff` (white)
- Text Secondary: `#b0b0b0` (light gray)
- Border Subtle: `#2a2a2a`

### Example Component Prompts
- "Create an Orchestrator agent chip: background `#0D6E6E`, white text, full-pill radius (9999px), 4px 12px padding, 14px Inter weight 500."
- "Design a ThinkingBlock: `#2a2a2a` background, 1px solid `#2a2a2a` border, 8px radius. Header with agent chip + 'Thinking' label in `#b0b0b0`. Content text in `#b0b0b0` at 14px Inter. Collapsed state shows single line with expand chevron."
- "Build a ToolCallCard for Coder: `#2a2a2a` background, 1px solid `#2a2a2a` border, left border 3px in `#C75D2C`, 8px radius. Header shows tool name + status. Content is dark code block with Fira Code 14px."
- "Create an empty state: `#0a0a0a` background, centered 'M' logo in `#0D6E6E`. Title at 48px Inter weight 600 in `#ffffff`. Subtitle at 16px in `#b0b0b0`. Three suggestion cards below with agent-colored borders (orange, indigo, green)."
- "Design the InputArea: `#2a2a2a` background, 1px solid `#3a3a3a` border, 12px radius, 12px 16px padding. Text in `#ffffff` at 14px Inter. Placeholder in `#505050`. Focus border shifts to `#0D6E6E`. Include agent/folder/orchestrate pills."

### Iteration Guide
1. Always use agent signature colors for agent identity — `#0D6E6E` for Orchestrator, `#5B6ABF` for Analyst, `#C75D2C` for Coder, `#2D8F5E` for Researcher
2. Maintain dark theme — use `#0a0a0a`, `#1a1a1a`, `#2a2a2a` for surfaces, never white backgrounds
3. Use Inter for UI text, Fira Code for code blocks
4. Apply collapsible/expandable pattern to event cards (ThinkingBlock, DelegationCard, ToolCallCard)
5. Use pill shapes (9999px radius) for agent chips and tags
6. Surface scale provides depth — darker = deeper, lighter = elevated
7. Agent-colored borders/accents provide visual hierarchy without heavy shadows
8. Maintain 8px base spacing system for consistency
