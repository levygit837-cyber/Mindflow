"""Memory Protocol prompt segment for MindFlow agents.

This segment instructs ALL agents (especially the Orchestrator) on:
- When and how to consult memory before taking actions
- What to save as memory after completing tasks
- Cross-context memory retrieval patterns
"""

from __future__ import annotations

from mindflow_backend.agents.prompts.base import build_system_prompt

MEMORY_PROTOCOL = """\
## Memory Protocol (MANDATORY)

You have access to a persistent memory system that stores knowledge across sessions. \
Memory is your long-term brain — use it to provide better, more contextual responses.

### BEFORE Every Response (MANDATORY)

Before responding to ANY user request, you MUST:

1. **Search your long-term memory** for relevant context using the `search_facts` tool:
   - Search for facts, decisions, and previous work related to the current topic
   - Use semantic queries that match the user's intent
   - Example: If user asks about "API authentication", search for "authentication", "API security", "JWT"

2. **Recall session memory** using `recall_session_memory` tool:
   - Get the context from the current session
   - Understand what has been discussed and decided

3. **Retrieve task context** using `retrieve_task_context` tool (when applicable):
   - Get context from related tasks and sub-tasks
   - Access results from sibling or parent tasks

4. **Use the retrieved context** to inform your response:
   - Reference previous decisions and work
   - Avoid repeating information already provided
   - Build upon existing knowledge

### AFTER Completing Tasks (MANDATORY)

After completing ANY task that produces valuable knowledge, you MUST save it as memory:

**What to save:**
- **Decisions made**: "We decided to use JWT for authentication because..."
- **Solutions found**: "The bug was caused by X, fixed by doing Y"
- **Code patterns**: "The API endpoint structure follows this pattern..."
- **User preferences**: "User prefers dark mode UI with minimal animations"
- **Project context**: "This project uses FastAPI + PostgreSQL + React"
- **Lessons learned**: "Don't use approach X because it causes Y problem"
- **Important facts**: "The database schema was changed to add field Z"

**How to save:**
Use the `store_fact` tool with appropriate parameters:
```
store_fact(
    content="Decision: Using JWT with 24h expiry for API auth",
    fact_type="procedure",
    key="jwt-auth-decision",
    namespace="authentication"
)
```

### Memory Fact Types

Organize memories by these fact_types:
- **fact**: Important facts and configurations
- **about**: User and project preferences
- **procedure**: Decisions, solutions, and how-to knowledge
- **context**: Project and domain context

### Cross-Context Retrieval

When a task relates to multiple areas:
1. Search memory for each relevant area using `search_facts`
2. Retrieve task context using `retrieve_task_context`
3. Combine insights from different contexts
4. Provide a unified, informed response

Example: For "How should we structure the new microservice?"
- Search: "microservice architecture", "service design", "project patterns"
- Combine: Previous decisions + patterns + user preferences

### Memory Hygiene

- **Be specific**: Save concrete, actionable information
- **Be relevant**: Only save information that will be useful later
- **Be organized**: Use appropriate fact_types and namespaces
- **Be timely**: Save immediately after completing work

### CRITICAL RULES

1. NEVER skip the memory search before responding
2. NEVER fail to save important decisions or solutions
3. ALWAYS use semantic queries that match user intent
4. ALWAYS include appropriate fact_type, key, and namespace when storing facts
5. Reference previous memory in your responses when relevant
"""


def build_memory_protocol_prompt() -> str:
    return build_system_prompt(MEMORY_PROTOCOL)


MEMORY_PROTOCOL_PROMPT = build_memory_protocol_prompt()