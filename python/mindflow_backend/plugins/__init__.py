"""Plugin platform entry points."""

from .manager import PluginManager, get_plugin_manager
from .models import (
    DeclarativeAgentDefinition,
    DeclarativeCommandDefinition,
    DeclarativeSkillDefinition,
    PluginDescriptor,
    PluginManifest,
    PluginScope,
    PluginSessionSnapshot,
    SkillActivation,
)
from .state_store import PluginState, PluginStateStore

__all__ = [
    "DeclarativeAgentDefinition",
    "DeclarativeCommandDefinition",
    "DeclarativeSkillDefinition",
    "PluginDescriptor",
    "PluginManifest",
    "PluginManager",
    "PluginScope",
    "PluginSessionSnapshot",
    "PluginState",
    "PluginStateStore",
    "SkillActivation",
    "get_plugin_manager",
]
