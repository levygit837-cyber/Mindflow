# Agent Runtime Policy

`mindflow_backend.agents.specialists.runtime_policy.AGENT_RUNTIME_POLICY` is the canonical runtime contract for agent identity, tools, sandbox, thinking level, and prompt selection.

Current matrix:

- `orchestrator`: tools `MEMORY`, `PLANNING`; sandbox `NONE`
- `analyst`: tools `CODE_ANALYSIS`, `FILESYSTEM`, `SHELL`; sandbox `READ_ONLY`
- `analyst:security_guard`: tools `CODE_ANALYSIS`, `FILESYSTEM`, `SHELL`; sandbox `READ_ONLY`
- `analyst:critic`: tools `CODE_ANALYSIS`, `FILESYSTEM`, `SHELL`; sandbox `READ_ONLY`
- `analyst:brainstorm`: tools `CODE_ANALYSIS`, `FILESYSTEM`; sandbox `READ_ONLY`
- `analyst:deep_iteration`: tools `CODE_ANALYSIS`, `FILESYSTEM`, `SHELL`; sandbox `READ_ONLY`
- `coder`: tools `FILESYSTEM`, `SHELL`; sandbox `FULL`
- `coder:arch_tech`: tools `CODE_ANALYSIS`, `FILESYSTEM`, `SHELL`; sandbox `FULL`
- `researcher`: tools `WEB_SEARCH`, `PINCHTAB_FLEET`, `PINCHTAB_BROWSER`; sandbox `READ_ONLY`

Notes:

- `creative` is removed as a runtime identity. Ideation and alternatives exploration route to `analyst:brainstorm`.
- `DATABASE` and `BROWSER_SEARCH` remain reserved tool scopes with no owner in this refactor.
- Chains and graphs should resolve execution by `agent_id`, not by prompt overrides on a base role.
