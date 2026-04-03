"""Common prompt utilities and preamble for agent personalities."""

from __future__ import annotations

MINDFLOW_PREAMBLE = (
    "You are MindFlow, an advanced AI assistant with specialized capabilities. "
    "You are precise, reliable, and action-oriented. "
    "Always ground your answers in facts and evidence."
)

PERSISTENCE_DIRECTIVE = """\
## Deep Work Protocol

When facing a complex problem:
1. **Never give up on the first attempt.** If a tool call fails or returns unexpected \
results, analyze WHY and try a different approach.
2. **Decompose before answering.** Break the problem into concrete steps. Execute each \
step with tools before forming your final answer.
3. **Verify your own work.** After producing a solution, use tools to check if it is \
correct (read the file you wrote, run the test, etc.).
4. **Use ALL available tools.** Do not answer from memory when tools can provide facts \
— read files, search the codebase, execute commands. The tools exist for a reason.
5. **Ask for clarification over guessing.** If the user's intent is ambiguous, ask — \
do not produce a generic answer.
6. **Think step-by-step.** Plan your approach before executing. Use reasoning to \
decompose the problem, then act."""


def build_system_prompt(personality_prompt: str) -> str:
    """Combine the MindFlow preamble with a personality-specific prompt."""
    return f"{MINDFLOW_PREAMBLE}\n\n{personality_prompt}\n\n{PERSISTENCE_DIRECTIVE}"


async def build_assembled_prompt(
    personality_prompt: str = "",
    agent: "BaseAgent | None" = None,
    working_directory: str | None = None,
    include_tools: bool = True,
    include_environment: bool = True,
    include_git: bool = False,
    include_memory: bool = True,
    tool_injector: "ToolPromptInjector | None" = None,
) -> str:
    """NOVO: Monta prompt usando PromptAssembler multi-camada."""
    from mindflow_backend.agents.prompts.assembler import (
        AssemblyContext,
        PromptAssembler,
    )
    from mindflow_backend.agents.prompts.layers.base import BasePromptLayer
    from mindflow_backend.agents.prompts.layers.environment import EnvironmentLayer
    from mindflow_backend.agents.prompts.layers.git import GitContextLayer
    from mindflow_backend.agents.prompts.layers.memdir_layer import MemdirLayer
    from mindflow_backend.agents.prompts.layers.memory import MemoryFileLayer
    from mindflow_backend.agents.prompts.layers.tools import ToolDescriptionLayer

    assembler = PromptAssembler()
    assembler.add_layer(BasePromptLayer(personality_prompt))

    if include_tools:
        assembler.add_layer(ToolDescriptionLayer(tool_injector))

    if include_environment:
        assembler.add_layer(EnvironmentLayer())

    if include_git:
        assembler.add_layer(GitContextLayer())

    if include_memory:
        assembler.add_layer(MemoryFileLayer())
        assembler.add_layer(MemdirLayer())

    context = AssemblyContext(
        agent=agent,
        working_directory=working_directory,
    )
    return await assembler.assemble(context)
