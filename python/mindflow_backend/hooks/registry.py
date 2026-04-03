"""HookRegistry — Registration of hooks by source.

Equivalente de getRegisteredHooks(), registerFunctionHook(), etc. em src/utils/hooks.ts.
Gerencia hooks de diferentes fontes: config, plugins, agents, skills.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from mindflow_backend.hooks.result import HookCommand, HookMatcher as HookMatcherData
from mindflow_backend.hooks.matcher import HookMatcher
from mindflow_backend.hooks.types import HookEvent
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
        # Fonte -> Evento -> lista de HookMatcherData (dataclass com matcher + hooks)
        self._config_hooks: dict[HookEvent, list[HookMatcherData]] = {}
        self._plugin_hooks: dict[str, dict[HookEvent, list[HookMatcherData]]] = {}
        self._session_plugin_hooks: dict[str, dict[str, dict[HookEvent, list[HookMatcherData]]]] = defaultdict(dict)
        self._skill_hooks: dict[str, dict[HookEvent, list[HookMatcherData]]] = {}
        self._session_skill_hooks: dict[str, dict[str, dict[HookEvent, list[HookMatcherData]]]] = defaultdict(dict)
        self._agent_hooks: dict[str, dict[HookEvent, list[HookMatcherData]]] = {}
        # Function hooks — callbacks registrados programaticamente
        self._function_hooks: dict[HookEvent, list[tuple[str | None, Callable[..., Any]]]] = {}

    def _register_hook(
        self,
        storage: dict[str, dict[HookEvent, list[HookMatcherData]]],
        owner_id: str,
        event: HookEvent,
        matcher: str | None,
        command: HookCommand,
    ) -> None:
        if owner_id not in storage:
            storage[owner_id] = {}
        if event not in storage[owner_id]:
            storage[owner_id][event] = []
        for hook_matcher in storage[owner_id][event]:
            if hook_matcher.matcher == matcher:
                hook_matcher.hooks.append(command)
                return
        storage[owner_id][event].append(
            HookMatcherData(matcher=matcher, hooks=[command])
        )

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
        self._config_hooks[event].append(HookMatcherData(matcher=matcher, hooks=[command]))

    def register_plugin_hook(
        self,
        plugin_name: str,
        event: HookEvent,
        matcher: str | None,
        command: HookCommand,
        *,
        session_id: str | None = None,
    ) -> None:
        """Registra hook de plugin."""
        if session_id is None:
            self._register_hook(
                self._plugin_hooks,
                plugin_name,
                event,
                matcher,
                command,
            )
            return

        self._register_hook(
            self._session_plugin_hooks[session_id],
            plugin_name,
            event,
            matcher,
            command,
        )

    def register_skill_hook(
        self,
        skill_id: str,
        event: HookEvent,
        matcher: str | None,
        command: HookCommand,
        *,
        session_id: str | None = None,
    ) -> None:
        """Registra hook de skill."""
        if session_id is None:
            self._register_hook(
                self._skill_hooks,
                skill_id,
                event,
                matcher,
                command,
            )
            return

        self._register_hook(
            self._session_skill_hooks[session_id],
            skill_id,
            event,
            matcher,
            command,
        )

    def register_agent_hook(
        self,
        agent_id: str,
        event: HookEvent,
        matcher: str | None,
        command: HookCommand,
    ) -> None:
        """Registra hook de agent (frontmatter hooks)."""
        self._register_hook(
            self._agent_hooks,
            agent_id,
            event,
            matcher,
            command,
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
        match_query: str | None = None,
    ) -> list[HookMatcherData]:
        """Busca todos os hooks para um evento, opcionalmente filtrando por match_query.

        Equivalente de getHooksConfig() em src/utils/hooks.ts.
        Combina hooks de todas as fontes na ordem correta.

        Args:
            event: Evento de hook (PreToolUse, PostToolUse, etc.)
            session_id: ID da sessão (não usado atualmente)
            agent_id: ID do agente para incluir agent-specific hooks
            skip_plugins: Se True, pula hooks de plugins
            match_query: Query para filtrar hooks (ex: "Write", "Bash")

        Returns:
            Lista de HookMatcherData que correspondem ao evento e query
        """
        result: list[HookMatcherData] = []

        # 1. Config hooks
        result.extend(self._config_hooks.get(event, []))

        # 2. Plugin hooks (pode ser pulado se managed_only)
        if not skip_plugins:
            for plugin_name, events in self._plugin_hooks.items():
                result.extend(events.get(event, []))
            if session_id and session_id in self._session_plugin_hooks:
                for plugin_name, events in self._session_plugin_hooks[session_id].items():
                    result.extend(events.get(event, []))

        # 3. Skill hooks
        for skill_id, events in self._skill_hooks.items():
            result.extend(events.get(event, []))
        if session_id and session_id in self._session_skill_hooks:
            for skill_id, events in self._session_skill_hooks[session_id].items():
                result.extend(events.get(event, []))

        # 4. Agent hooks
        if agent_id and agent_id in self._agent_hooks:
            result.extend(self._agent_hooks[agent_id].get(event, []))

        # 5. Filtrar por match_query se fornecido
        if match_query:
            result = [
                hook_matcher
                for hook_matcher in result
                if HookMatcher.matches(match_query, hook_matcher.matcher)
            ]

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

    def unregister_plugin_hooks(
        self,
        plugin_name: str,
        *,
        session_id: str | None = None,
    ) -> None:
        """Remove todos os hooks de um plugin."""
        if session_id is None:
            if plugin_name in self._plugin_hooks:
                del self._plugin_hooks[plugin_name]
                _logger.debug("plugin_hooks_unregistered", plugin_name=plugin_name)
            return

        session_plugins = self._session_plugin_hooks.get(session_id)
        if session_plugins and plugin_name in session_plugins:
            del session_plugins[plugin_name]
            if not session_plugins:
                del self._session_plugin_hooks[session_id]
            _logger.debug(
                "session_plugin_hooks_unregistered",
                plugin_name=plugin_name,
                session_id=session_id,
            )

    def unregister_skill_hooks(
        self,
        skill_id: str,
        *,
        session_id: str | None = None,
    ) -> None:
        """Remove hooks de uma skill."""
        if session_id is None:
            if skill_id in self._skill_hooks:
                del self._skill_hooks[skill_id]
                _logger.debug("skill_hooks_unregistered", skill_id=skill_id)
            return

        session_skills = self._session_skill_hooks.get(session_id)
        if session_skills and skill_id in session_skills:
            del session_skills[skill_id]
            if not session_skills:
                del self._session_skill_hooks[session_id]
            _logger.debug(
                "session_skill_hooks_unregistered",
                skill_id=skill_id,
                session_id=session_id,
            )

    def clear_all(self) -> None:
        """Remove todos os hooks (para testes ou reset)."""
        self._config_hooks.clear()
        self._plugin_hooks.clear()
        self._session_plugin_hooks.clear()
        self._skill_hooks.clear()
        self._session_skill_hooks.clear()
        self._agent_hooks.clear()
        self._function_hooks.clear()
