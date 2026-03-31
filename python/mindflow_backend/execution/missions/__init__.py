"""
Execution Missions — Módulos para missões autônomas via MissionLauncher.

Fornece MissionContext, MissionResult, MemoryAnnotationRef e
MissionLauncher para conectar Execution Graphs ao DelegationEngine.

Uso recomendado — imports diretos:
    from mindflow_backend.execution.missions.mission_context import MissionContext
    from mindflow_backend.execution.missions.mission_result import (
        MissionResult, MemoryAnnotationRef,
    )
    from mindflow_backend.execution.missions.mission_launcher import (
        MissionLauncher, get_mission_launcher,
    )
"""


def __getattr__(name: str):
    """Lazy imports to avoid circular imports."""
    if name in ("MissionLauncher", "get_mission_launcher"):
        from mindflow_backend.execution.missions.mission_launcher import (
            MissionLauncher,
            get_mission_launcher,
        )
        if name == "MissionLauncher":
            return MissionLauncher
        return get_mission_launcher
    if name in ("MissionContext",):
        from mindflow_backend.execution.missions.mission_context import MissionContext
        return MissionContext
    if name in ("MissionResult", "MemoryAnnotationRef"):
        from mindflow_backend.execution.missions.mission_result import (
            MissionResult,
            MemoryAnnotationRef,
        )
        if name == "MissionResult":
            return MissionResult
        return MemoryAnnotationRef
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "MissionLauncher",
    "get_mission_launcher",
    "MissionContext",
    "MissionResult",
    "MemoryAnnotationRef",
]