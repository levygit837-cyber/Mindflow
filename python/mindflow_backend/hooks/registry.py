"""HookRegistry — Registration of hooks by source.

Equivalente de getRegisteredHooks(), registerFunctionHook(), etc. em src/utils/hooks.ts.
Gerencia hooks de diferentes fontes: config, plugins, agents, skills.
"""

from __future__ import annotations

from typing import Any, Callable, Awaitable

from mindflow_backend.hooks.types import HookEvent
from mindflow_backend.hooks.result import HookCommand, HookMatcher
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class HookRegistry:
    """Registro central de hooks.

    Gerencia hooks de múltiplas fontes:
    - Config hooks (from settings.yaml)
    - Plugin hooks (from plugin metadata)
    - Agent hooks (from agent frontmatter)
    - Function hooks (programmatic registration)
    """

    def __init__(self) -> None:
        # Fonte -> Evento -> lista de HookMatcher
        self._config_hooks: dict[HookEvent, list[HookMatcher]] = {}
        self._plugin_hooks: dict[str, dict[HookEvent, list[HookMatcher]]] = {}
        self._agent_hooks: dict[str, dict[HookEvent, list[HookMatcher]]] = {}
        # Function hooks — callbacks registrados programaticamente
        self._function_hooks: dict[HookEvent, list[tuple[str | None, Callable[..., Any]]]] = {}

    def register_config_hook(
        self,
        event: HookEvent,
        matcher: str | None,
        command: HookCommand,
    ) -> None:
        """Registra hook de configuração (settings.yaml)."""
        if event not in self._config_hooks:
            self._config_hooks[event] = []
        # Encontrar matcher existente ou criar novo
        for m in self._config_hooks[event]:
            if m.matcher == matcher:
                m.hooks.append(command)
                return
        self._config_hooks[event].append(HookMatcher(matcher=matcher, hooks=[command]))

    def register_plugin_hook(
        self,
        plugin_name: str,
        event: HookEvent,
        matcher: str | None,
        command: HookCommand,
    ) -> None:
        """Registra hook de plugin."""
        if plugin_name not in self._plugin_hooks:
            self._plugin_hooks[plugin_name] = {}
        if event not in self._plugin_hooks[plugin_name]:
            self._plugin_hooks[plugin_name][event] = []
        for m in self._plugin_hooks[plugin_name][event]:
            if m.matcher == matcher:
                m.hooks.append(command)
                return
        self._plugin_hooks[plugin_name][event].append(
            HookMatcher(matcher=matcher, hooks=[command])
        )

    def register_agent_hook(
        self,
        agent_id: str,
        event: HookEvent,
        matcher: str | None,
        command: HookCommand,
    ) -> None:
        """Registra hook de agent (frontmatter hooks)."""
        if agent_id not in self._agent_hooks:
            self._agent_hooks[agent_id] = {}
        if event not in self._agent_hooks[agent_id]:
            self._agent_hooks[agent_id][event] = []
        for m in self._agent_hooks[agent_id][event]:
            if m.matcher == matcher:
                m.hooks.append(command)
                return
        self._agent_hooks[agent_id][event].append(
            HookMatcher(matcher=matcher, hooks=[command])
        )

    def register_function_hook(
        self,
        event: HookEvent,
        matcher: str | None,
        callback: Callable[..., Any],
    ) -> None:
        """Registra hook programático (callback Python).

        Equivalente de addFunctionHook() em src/utils/hooks.ts.
        Chamado internamente por handlers, builtin hooks, etc.
        """
        if event not in self._function_hooks:
            self._function_hooks[event] = []
        self._function_hooks[event].append((matcher, callback))

    def get_hooks_for_event(
        self,
        event: HookEvent,
        *,
        session_id: str | None = None,
        agent_id: str | None = None,
        skip_plugins: bool = False,
    ) -> list[HookMatcher]:
        """Busca todos os hooks para um evento.

        Equivalente de getHooksConfig() em src/utils/hooks.ts.
        Combina hooks de todas as fontes na ordem correta.
        """
        result: list[HookMatcher] = []

        # 1. Config hooks
        result.extend(self._config_hooks.get(event, []))

        # 2. Plugin hooks (pode ser pulado se managed_only)
        if not skip_plugins:
            for plugin_name, events in self._plugin_hooks.items():
                result.extend(events.get(event, []))

        # 3. Agent hooks
        if agent_id and agent_id in self._agent_hooks:
            result.extend(self._agent_hooks[agent_id].get(event, []))

        # 4. Function hooks — converter para HookMatcher para consistência
        for matcher, callback in self._function_hooks.get(event, []):
            # Function hooks são executados diretamente pelo HookManager
            # Não são convertidos para HookMatcher — são tratados separadamente
            pass

        return result

    def get_function_hooks(
        self,
        event: HookEvent,
    ) -> list[tuple[str | None, Callable[..., Any]]]:
        """Busca function hooks para um evento."""
        return self._function_hooks.get(event, [])

    def unregister_agent_hooks(self, agent_id: str) -> None:
        """Remove todos os hooks de um agent."""
        if agent_id in self._agent_hooks:
            del self._agent_hooks[agent_id]
            _logger.debug("agent_hooks_unregistered", agent_id=agent_id)

    def unregister_plugin_hooks(self, plugin_name: str) -> None:
        """Remove todos os hooks de um plugin."""
        if plugin_name in self._plugin_hooks:
            del self._plugin_hooks[plugin_name]
            _logger.debug("plugin_hooks_unregistered", plugin_name=plugin_name)

    def clear_all(self) -> None:
        """Remove todos os hooks (para testes ou reset)."""
        self._config_hooks.clear()
        self._plugin_hooks.clear()
        self._agent_hooks.clear()
        self._function_hooks.clear()