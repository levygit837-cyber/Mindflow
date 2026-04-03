"""Graceful Degradation System for MindFlow.

Provides automatic feature degradation when dependencies fail,
with configurable policies and fallback values.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

T = TypeVar("T")


class DegradationLevel(str, Enum):
    """Níveis de degradação de features.

    FULL: Todas features disponíveis
    REDUCED: Algumas features desabilitadas
    MINIMAL: Apenas features core
    OFFLINE: Modo cache/offline
    """
    FULL = "full"
    REDUCED = "reduced"
    MINIMAL = "minimal"
    OFFLINE = "offline"


@dataclass
class DegradationPolicy:
    """Política de degradação para uma feature.

    Attributes:
        feature_name: Nome da feature
        degradation_level: Nível de degradação
        fallback_value: Valor retornado quando degradada
        cache_ttl: TTL do cache em segundos
        notify_user: Se deve notificar o usuário
        auto_recover: Se deve tentar recuperar automaticamente
        recovery_check_interval: Intervalo para verificação de recuperação
    """
    feature_name: str
    degradation_level: DegradationLevel = DegradationLevel.REDUCED
    fallback_value: Any = None
    cache_ttl: float = 300.0  # 5 minutos
    notify_user: bool = False
    auto_recover: bool = True
    recovery_check_interval: float = 60.0  # 1 minuto


@dataclass
class FeatureState:
    """Estado atual de uma feature.

    Attributes:
        feature_name: Nome da feature
        is_degraded: Se está degradada
        degradation_level: Nível de degradação atual
        degraded_since: Timestamp de quando foi degradada
        last_success: Timestamp do último sucesso
        last_recovery_attempt: Timestamp da última tentativa de recuperação
        failure_count: Contador de falhas
    """
    feature_name: str
    is_degraded: bool = False
    degradation_level: DegradationLevel = DegradationLevel.FULL
    degraded_since: float = 0.0
    last_success: float = 0.0
    last_recovery_attempt: float = 0.0
    failure_count: int = 0


class GracefulDegradationManager:
    """Gerencia degradação graciosa de features.

    Executa funções com fallback automático quando falham,
    cache de resultados bem-sucedidos, e recuperação automática.

    Usage:
        manager = GracefulDegradationManager()

        # Registrar política de degradação
        policy = DegradationPolicy(
            feature_name="semantic_search",
            degradation_level=DegradationLevel.REDUCED,
            fallback_value=[],
            cache_ttl=300.0,
            notify_user=False,
            auto_recover=True
        )
        manager.register_policy(policy)

        # Executar com degradação graciosa
        result = await manager.execute_with_degradation(
            feature_name="semantic_search",
            primary_func=search_function,
            query="authentication"
        )
    """

    def __init__(self) -> None:
        self._policies: dict[str, DegradationPolicy] = {}
        self._states: dict[str, FeatureState] = {}
        self._cache: dict[str, tuple[Any, float]] = {}  # (value, timestamp)

    def register_policy(self, policy: DegradationPolicy) -> None:
        """Registra uma política de degradação."""
        self._policies[policy.feature_name] = policy
        self._states[policy.feature_name] = FeatureState(
            feature_name=policy.feature_name
        )
        _logger.info(
            "degradation_policy_registered",
            feature=policy.feature_name,
            level=policy.degradation_level.value,
        )

    def get_policy(self, feature_name: str) -> DegradationPolicy | None:
        """Retorna política de uma feature."""
        return self._policies.get(feature_name)

    def get_state(self, feature_name: str) -> FeatureState | None:
        """Retorna estado atual de uma feature."""
        return self._states.get(feature_name)

    def is_degraded(self, feature_name: str) -> bool:
        """Verifica se uma feature está degradada."""
        state = self._states.get(feature_name)
        return state.is_degraded if state else False

    def get_degradation_level(self, feature_name: str) -> DegradationLevel:
        """Retorna nível de degradação de uma feature."""
        state = self._states.get(feature_name)
        return state.degradation_level if state else DegradationLevel.FULL

    def get_all_states(self) -> dict[str, dict[str, Any]]:
        """Retorna estado de todas as features."""
        return {
            name: {
                "is_degraded": state.is_degraded,
                "degradation_level": state.degradation_level.value,
                "degraded_since": state.degraded_since,
                "last_success": state.last_success,
                "failure_count": state.failure_count,
            }
            for name, state in self._states.items()
        }

    def _get_cached_value(self, feature_name: str) -> tuple[bool, Any]:
        """Retorna valor do cache se válido."""
        policy = self._policies.get(feature_name)
        if not policy:
            return False, None

        cached = self._cache.get(feature_name)
        if not cached:
            return False, None

        value, timestamp = cached
        elapsed = time.time() - timestamp

        if elapsed <= policy.cache_ttl:
            return True, value

        # Cache expirado
        del self._cache[feature_name]
        return False, None

    def _set_cached_value(self, feature_name: str, value: Any) -> None:
        """Armazena valor no cache."""
        self._cache[feature_name] = (value, time.time())

    def _mark_degraded(self, feature_name: str) -> None:
        """Marca feature como degradada."""
        state = self._states.get(feature_name)
        policy = self._policies.get(feature_name)

        if not state or not policy:
            return

        state.is_degraded = True
        state.degradation_level = policy.degradation_level
        state.failure_count += 1

        if state.degraded_since == 0:
            state.degraded_since = time.time()

        _logger.warning(
            "feature_degraded",
            feature=feature_name,
            level=policy.degradation_level.value,
            failure_count=state.failure_count,
        )

    def _mark_recovered(self, feature_name: str) -> None:
        """Marca feature como recuperada."""
        state = self._states.get(feature_name)
        if not state:
            return

        was_degraded = state.is_degraded

        state.is_degraded = False
        state.degradation_level = DegradationLevel.FULL
        state.degraded_since = 0.0
        state.last_success = time.time()
        state.failure_count = 0

        if was_degraded:
            _logger.info("feature_recovered", feature=feature_name)

    def _should_attempt_recovery(self, feature_name: str) -> bool:
        """Verifica se deve tentar recuperar feature."""
        state = self._states.get(feature_name)
        policy = self._policies.get(feature_name)

        if not state or not policy:
            return False

        if not state.is_degraded:
            return False

        if not policy.auto_recover:
            return False

        elapsed = time.time() - state.last_recovery_attempt
        return elapsed >= policy.recovery_check_interval

    async def execute_with_degradation(
        self,
        feature_name: str,
        primary_func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Executa função com degradação graciosa.

        Fluxo de execução:
        1. Verifica se feature está degradada
        2. Se degradada, tenta recuperar (se auto_recover=True)
        3. Se recuperação falha ou não habilitada, retorna fallback
        4. Se não degradada, tenta executar função primária
        5. Em falha, marca como degradada e retorna fallback
        6. Em sucesso, cacheia resultado

        Args:
            feature_name: Nome da feature
            primary_func: Função primária a executar
            *args: Argumentos posicionais para primary_func
            **kwargs: Argumentos nomeados para primary_func

        Returns:
            Resultado da função primária ou valor de fallback
        """
        policy = self._policies.get(feature_name)
        if not policy:
            # Sem política, executar diretamente
            return await self._execute_primary(primary_func, *args, **kwargs)

        state = self._states[feature_name]

        # Se feature está degradada
        if state.is_degraded:
            # Tentar recuperação
            if self._should_attempt_recovery(feature_name):
                state.last_recovery_attempt = time.time()
                try:
                    result = await self._execute_primary(
                        primary_func, *args, **kwargs
                    )
                    self._mark_recovered(feature_name)
                    self._set_cached_value(feature_name, result)
                    return result
                except Exception:
                    _logger.debug(
                        "recovery_failed",
                        feature=feature_name,
                    )
                    # Continuar com fallback

            # Retornar valor de fallback
            return await self._get_fallback(feature_name, policy)

        # Feature não está degradada - tentar executar
        try:
            result = await self._execute_primary(primary_func, *args, **kwargs)

            # Sucesso - cachear resultado
            self._set_cached_value(feature_name, result)
            state.last_success = time.time()

            return result

        except Exception as e:
            _logger.warning(
                "feature_execution_failed",
                feature=feature_name,
                error=str(e),
            )

            # Marcar como degradada
            self._mark_degraded(feature_name)

            # Retornar fallback
            return await self._get_fallback(feature_name, policy)

    async def _execute_primary(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Executa função primária, suportando sync e async."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)

    async def _get_fallback(
        self,
        feature_name: str,
        policy: DegradationPolicy,
    ) -> Any:
        """Retorna valor de fallback para uma feature degradada."""
        # Primeiro, tentar cache
        is_cached, cached_value = self._get_cached_value(feature_name)
        if is_cached:
            _logger.debug(
                "using_cached_fallback",
                feature=feature_name,
            )
            return cached_value

        # Retornar fallback estático
        _logger.debug(
            "using_static_fallback",
            feature=feature_name,
            level=policy.degradation_level.value,
        )
        return policy.fallback_value

    def recover_feature(self, feature_name: str) -> bool:
        """Força recuperação de uma feature manualmente."""
        state = self._states.get(feature_name)
        if not state:
            return False

        self._mark_recovered(feature_name)
        return True

    def reset_all(self) -> None:
        """Reseta todos os estados de degradação."""
        for feature_name in self._states:
            self._mark_recovered(feature_name)
        self._cache.clear()
        _logger.info("all_degradation_reset")


# Instância global singleton
_degradation_manager: GracefulDegradationManager | None = None


def get_degradation_manager() -> GracefulDegradationManager:
    """Retorna instância global do degradation manager."""
    global _degradation_manager
    if _degradation_manager is None:
        _degradation_manager = GracefulDegradationManager()
    return _degradation_manager