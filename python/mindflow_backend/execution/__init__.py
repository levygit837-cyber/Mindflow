"""
Execution module do MindFlow — Missões autônomas via MissionLauncher.

Este módulo conecta os Execution Graphs (Phase 2A) ao sistema de delegação,
permitindo que missões autônomas sejam lançadas quando um mission_type
está disponível na RuntimePolicy do agente.

Uso recomendado — imports diretos para evitar circular imports:
    from mindflow_backend.execution.missions.mission_context import MissionContext
    from mindflow_backend.execution.missions.mission_result import (
        MissionResult, MemoryAnnotationRef,
    )
    from mindflow_backend.execution.missions.mission_launcher import (
        MissionLauncher, get_mission_launcher,
    )
"""