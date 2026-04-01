"""
Execution module do MindFlow — Unified Execution Engine + Missões autônomas.

Este módulo fornece:
- UnifiedExecutionEngine: Engine centralizada para todas as execuções
- AgentTeamManager: Gerenciamento de times colaborativos
- MissionLauncher: Lançamento de missões autônomas
- ToolExecutionLoop: Loop unificado de ferramentas (ReAct)

Uso recomendado — imports diretos para evitar circular imports:
    # Unified Engine
    from mindflow_backend.execution.unified_engine import UnifiedExecutionEngine
    from mindflow_backend.execution.agent_team_manager import AgentTeamManager
    from mindflow_backend.execution.types import (
        ExecutionContext, ExecutionState, ExecutionResult,
    )

    # Missions (legacy)
    from mindflow_backend.execution.missions.mission_context import MissionContext
    from mindflow_backend.execution.missions.mission_result import (
        MissionResult, MemoryAnnotationRef,
    )
    from mindflow_backend.execution.missions.mission_launcher import (
        MissionLauncher, get_mission_launcher,
    )

    # Loops
    from mindflow_backend.execution.loops.tool_loop import ToolExecutionLoop
"""