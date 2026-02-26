# Agent Structured Outputs — Reference Guide

## Architecture Overview

```
User Message
     │
     ▼
┌─────────────┐     ┌──────────────────┐
│  Classifier │────▶│  OutputCategory   │
│  (Haiku)    │     │  (19 categories)  │
└─────────────┘     └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  getOutputSchema  │
                    │  (dynamic lookup) │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ Specialized Agent │
                    │ (Sonnet + Schema) │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  AgentOutput      │
                    │  (validated Zod)  │
                    └──────────────────┘
```

## Output Categories Quick Reference

| # | Category | When to Use | Key Fields |
|---|----------|-------------|------------|
| 1 | `code` | Code generation, review, refactoring | `fragments`, `dependencies`, `breakingChanges` |
| 2 | `explanation` | Technical explanations, how-to | `summary`, `sections`, `analogies`, `targetAudience` |
| 3 | `project` | Project status, architecture | `techStack`, `architecture`, `milestones`, `risks` |
| 4 | `people` | Contacts, team, person info | `people[]`, `relationship`, `interactionSuggestions` |
| 5 | `task` | Todos, sprints, action items | `tasks[]`, `criticalPath`, `totalEstimatedHours` |
| 6 | `debug` | Errors, bugs, stack traces | `rootCause`, `fix`, `affectedFiles`, `severity` |
| 7 | `data_analysis` | Metrics, charts, insights | `keyFindings`, `dataPoints`, `charts`, `anomalies` |
| 8 | `decision` | Comparing options, choosing | `options[]` (pros/cons), `recommendation`, `decisionMatrix` |
| 9 | `learning` | Tutorials, educational content | `steps[]`, `exercises`, `prerequisites`, `learningObjectives` |
| 10 | `calendar` | Scheduling, events, availability | `events[]`, `conflicts`, `freeSlots` |
| 11 | `file_operation` | File create/edit/move/delete | `operations[]`, `affectedPaths`, `rollbackSteps` |
| 12 | `search_result` | Web/internal search | `results[]`, `synthesizedAnswer`, `suggestedQueries` |
| 13 | `conversation` | Casual chat, personal | `message`, `tone`, `sentiment`, `emotionalState` |
| 14 | `summary` | Summarizing any content | `tldr`, `keyPoints`, `actionItems`, `decisions` |
| 15 | `recommendation` | Suggesting tools/products | `recommendations[]` (scored), `topPick`, `criteria` |
| 16 | `notification` | Alerts, reminders, updates | `type`, `urgency`, `actionRequired`, `expiresAt` |
| 17 | `creative` | Writing, brainstorming, copy | `content`, `variants[]`, `tone`, `keywords` |
| 18 | `finance` | Budget, expenses, forecasts | `lineItems[]`, `totals`, `insights`, `alerts` |
| 19 | `health` | Fitness, nutrition, wellness | `recommendations[]`, `metrics`, `disclaimer` |

## Integration Strategies

### Strategy 1: Universal Agent (simplest)
```typescript
responseFormat: toolStrategy(AgentOutput)
```
- Model picks the right schema from the discriminated union
- Good for prototyping and general-purpose agents
- Tradeoff: more tokens in tool definitions

### Strategy 2: Specialized Agents (most accurate)
```typescript
responseFormat: toolStrategy(CodeOutput)  // coding agent
responseFormat: toolStrategy(TaskOutput)  // task agent
```
- Each agent has exactly one output type
- Best accuracy per category
- Requires orchestration layer

### Strategy 3: Router Pattern (best of both worlds)
```typescript
// Step 1: Classify with Haiku (fast, cheap)
// Step 2: Run specialized agent with correct schema
const schema = getOutputSchema(classification.category);
responseFormat: toolStrategy(schema)
```
- Best accuracy + flexibility
- Two LLM calls per request
- Recommended for production

### Strategy 4: Subset Union (balanced)
```typescript
responseFormat: toolStrategy([CodeOutput, DebugOutput, ExplanationOutput])
```
- Model picks from a smaller set
- Good for domain-specific agents (dev, personal, business)

## Example Query → Output Type Mapping

| User Query | Category | Why |
|-----------|----------|-----|
| "Create a REST API for users" | `code` | Code generation request |
| "What is event sourcing?" | `explanation` | Conceptual question |
| "How's the auth project going?" | `project` | Project status inquiry |
| "Who's on the frontend team?" | `people` | People/team lookup |
| "Break this into tasks" | `task` | Task creation request |
| "Why is this crashing?" | `debug` | Error/bug investigation |
| "Show me conversion rates" | `data_analysis` | Metrics/analytics |
| "Should I use Redis or Memcached?" | `decision` | Comparison/choice |
| "Teach me about Docker" | `learning` | Educational request |
| "Schedule a meeting Friday" | `calendar` | Scheduling |
| "Rename all .js files to .ts" | `file_operation` | File manipulation |
| "Find docs about authentication" | `search_result` | Search query |
| "Hey, how are you?" | `conversation` | Casual chat |
| "Summarize yesterday's meeting" | `summary` | Content summary |
| "Best CI/CD tool for us?" | `recommendation` | Tool suggestion |
| "Remind me at 3pm" | `notification` | Alert/reminder |
| "Write a blog post about AI" | `creative` | Content creation |
| "How much did we spend in January?" | `finance` | Financial query |
| "Create a workout plan" | `health` | Wellness request |

## Common Fields (BaseAgentOutput)

Every output includes:
- `category` — discriminator for type narrowing
- `title` — short descriptive title
- `confidence` — `high | medium | low | uncertain`
- `reasoning` — why the agent chose this approach
- `followUpSuggestions` — next actions the user might want
- `metadata` — extensible key-value store
