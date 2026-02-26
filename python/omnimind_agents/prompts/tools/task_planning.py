TASK_PLANNING_PROMPT = """## Task Planning Tool

### write_todos (Task Planning)
- Use ONLY for complex tasks that require 3 or more steps.
- Each call REPLACES the entire todo list — always include all items (pending, in_progress, completed).
- Mark items as "in_progress" when you start working on them, "completed" when done.
- NEVER call write_todos multiple times in the same turn — consolidate into one call.
- For simple tasks (1-2 steps), just do them directly without write_todos."""
