"""
Execution module do MindFlow — Unified Execution Engine + Missões autônomas.

Este módulo fornece:
- UnifiedExecutionEngine: Engine centralizada para todas as execuções
- AgentTeamManager: Gerenciamento de times colaborativos
- MissionLauncher: Lançamento de missões autônomas
- StreamingToolExecutor: Execução de ferramentas com controle de concorrência
- Task management: Sistema de gerenciamento de tarefas

Uso recomendado — imports diretos para evitar circular imports:
    # Unified Engine
    from mindflow_backend.execution.unified_engine import UnifiedExecutionEngine
    from mindflow_backend.execution.agent_team_manager import AgentTeamManager
    from mindflow_backend.execution.types import (
        ExecutionContext, ExecutionState, ExecutionResult,
    )

    # Missions
    from mindflow_backend.execution.missions.mission_context import MissionContext
    from mindflow_backend.execution.missions.mission_result import (
        MissionResult, MemoryAnnotationRef,
    )
    from mindflow_backend.execution.missions.mission_launcher import (
        MissionLauncher, get_mission_launcher,
    )

    # Loops
    from mindflow_backend.execution.loops import (
        StreamingToolExecutor,
        partition_tool_calls,
    )

    # Task
    from mindflow_backend.execution.task import (
        TaskType,
        TaskStatus,
        generate_task_id,
        is_terminal_task_status,
    )
"""