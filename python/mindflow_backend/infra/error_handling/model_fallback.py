"""Model Fallback System for automatic model switching on failures.

Provides a fallback chain that automatically switches to alternative models
when the primary model fails, with health tracking and recovery detection.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

from mindflow_backend.infra.error_handling.classifier import (
    ErrorCategory,
    classify_error,
    is_retryable,
)
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

T = TypeVar("T")


class ModelStatus(str, Enum):
    """Status de saúde de um modelo."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class ModelHealth:
    """Rastreia a saúde de um modelo individual.

    Attributes:
        model_name: Nome do modelo
        status: Status atual do modelo
        failure_count: Contador total de falhas
        consecutive_failures: Falhas consecutivas (reseta após sucesso)
        last_failure: Timestamp da última falha
        last_success: Timestamp do último sucesso
        recovery_check_interval: Intervalo para tentar recuperação (segundos)
        failure_threshold: Falhas consecutivas para marcar como UNAVAILABLE
    """
    model_name: str
    status: ModelStatus = ModelStatus.HEALTHY
    failure_count: int = 0
    consecutive_failures: int = 0
    last_failure: float = 0.0
    last_success: float = 0.0
    recovery_check_interval: float = 300.0  # 5 minutos
    failure_threshold: int = 3  # Após 3 falhas → UNAVAILABLE

    def record_failure(self) -> None:
        """Registra uma falha no modelo."""
        self.failure_count += 1
        self.consecutive_failures += 1
        self.last_failure = time.time()

        # Atualizar status baseado em falhas consecutivas
        if self.consecutive_failures >= self.failure_threshold:
            self.status = ModelStatus.UNAVAILABLE
            _logger.warning(
                "model_unavailable",
                model=self.model_name,
                consecutive_failures=self.consecutive_failures,
            )
        elif self.consecutive_failures >= 1:
            self.status = ModelStatus.DEGRADED

    def record_success(self) -> None:
        """Registra um sucesso no modelo."""
        self.consecutive_failures = 0
        self.last_success = time.time()

        if self.status != ModelStatus.HEALTHY:
            self.status = ModelStatus.HEALTHY
            _logger.info("model_recovered", model=self.model_name)

    def should_try_recovery(self) -> bool:
        """Verifica se deve tentar recuperar o modelo."""
        if self.status != ModelStatus.UNAVAILABLE:
            return False

        elapsed = time.time() - self.last_failure
        return elapsed >= self.recovery_check_interval

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""
        return {
            "model_name": self.model_name,
            "status": self.status.value,
            "failure_count": self.failure_count,
            "consecutive_failures": self.consecutive_failures,
            "last_failure": self.last_failure,
            "last_success": self.last_success,
        }


@dataclass
class FallbackChain:
    """Define a cadeia de fallback para um modelo primário.

    Attributes:
        primary: Modelo primário
        fallbacks: Lista ordenada de modelos de fallback
        health: Mapeamento de modelo → saúde
    """
    primary: str
    fallbacks: list[str] = field(default_factory=list)
    health: dict[str, ModelHealth] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Inicializa health tracking para todos os modelos."""
        all_models = [self.primary] + self.fallbacks
        for model in all_models:
            if model not in self.health:
                self.health[model] = ModelHealth(model_name=model)

    def get_available_models(self) -> list[str]:
        """Retorna modelos disponíveis em ordem de preferção."""
        available = []
        for model in [self.primary] + self.fallbacks:
            h = self.health.get(model)
            if h and h.status != ModelStatus.UNAVAILABLE:
                available.append(model)
        return available

    def get_next_fallback(self, failed_model: str) -> str | None:
        """Retorna próximo modelo de fallback após falha."""
        available = self.get_available_models()
        try:
            current_idx = available.index(failed_model)
            if current_idx + 1 < len(available):
                return available[current_idx + 1]
        except ValueError:
            pass
        return None


def calculate_backoff_delay(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
) -> float:
    """Calcula delay de backoff exponencial com jitter.

    Args:
        attempt: Número da tentativa (0-indexed)
        base_delay: Delay base em segundos
        max_delay: Delay máximo em segundos
        exponential_base: Base para exponencial
        jitter: Se deve adicionar jitter aleatório

    Returns:
        Delay em segundos para aguardar antes do próximo retry

    Example:
        attempt=0: delay = 1.0 * 2^0 = 1.0s (±25% jitter)
        attempt=1: delay = 1.0 * 2^1 = 2.0s (±25% jitter)
        attempt=2: delay = 1.0 * 2^2 = 4.0s (±25% jitter)
        attempt=3: delay = 1.0 * 2^3 = 8.0s (±25% jitter)
        Max: 60s
    """
    delay = base_delay * (exponential_base ** attempt)
    delay = min(delay, max_delay)

    if jitter:
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)

    return max(0, delay)


class ModelFallbackManager:
    """Gerencia fallback entre modelos com health tracking.

    Orquestra a cadeia de fallback, tracking de saúde,
    e detecção de recuperação automática.

    Usage:
        manager = ModelFallbackManager()

        # Configurar cadeia de fallback
        chain = FallbackChain(
            primary="gpt-4",
            fallbacks=["gpt-3.5-turbo", "claude-3-sonnet", "claude-3-haiku"]
        )
        manager.register_chain("default", chain)

        # Executar com fallback automático
        result = await manager.execute_with_fallback(
            chain_name="default",
            executor=my_api_call,
            *args,
            **kwargs
        )
    """

    def __init__(self) -> None:
        self._chains: dict[str, FallbackChain] = {}
        self._global_health: dict[str, ModelHealth] = {}

    def register_chain(self, name: str, chain: FallbackChain) -> None:
        """Registra uma cadeia de fallback."""
        self._chains[name] = chain

        # Sincronizar health global
        for model, health in chain.health.items():
            if model not in self._global_health:
                self._global_health[model] = health

        _logger.info(
            "fallback_chain_registered",
            name=name,
            primary=chain.primary,
            fallbacks=chain.fallbacks,
        )

    def get_chain(self, name: str) -> FallbackChain | None:
        """Retorna uma cadeia de fallback por nome."""
        return self._chains.get(name)

    def get_model_health(self, model_name: str) -> ModelHealth | None:
        """Retorna saúde de um modelo."""
        return self._global_health.get(model_name)

    def get_all_health(self) -> dict[str, dict[str, Any]]:
        """Retorna saúde de todos os modelos."""
        return {
            name: health.to_dict()
            for name, health in self._global_health.items()
        }

    def should_attempt_fallback(self, error: Exception) -> bool:
        """Verifica se o erro justifica fallback."""
        classification = classify_error(error)
        return classification in {
            ErrorCategory.SERVER_OVERLOAD,
            ErrorCategory.CAPACITY,
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.TIMEOUT,
            ErrorCategory.NETWORK_ERROR,
            ErrorCategory.AUTH_TRANSIENT,
        }

    async def execute_with_fallback(
        self,
        chain_name: str,
        executor: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Executa função com fallback automático entre modelos.

        Args:
            chain_name: Nome da cadeia de fallback registrada
            executor: Função async que recebe model_name como primeiro arg
            *args: Argumentos posicionais para executor
            **kwargs: Argumentos nomeados para executor

        Returns:
            Resultado da execução bem-sucedida

        Raises:
            ModelFallbackExhaustedError: Se todos os modelos falharem
        """
        chain = self._chains.get(chain_name)
        if not chain:
            raise ValueError(f"Fallback chain '{chain_name}' not registered")

        available_models = chain.get_available_models()
        if not available_models:
            raise ModelFallbackExhaustedError(
                f"No available models in chain '{chain_name}'"
            )

        last_error: Exception | None = None

        for model_name in available_models:
            health = chain.health[model_name]

            # Verificar se modelo está disponível
            if health.status == ModelStatus.UNAVAILABLE:
                # Verificar se é hora de tentar recuperação
                if health.should_try_recovery():
                    _logger.info(
                        "attempting_model_recovery",
                        model=model_name,
                    )
                else:
                    continue

            try:
                _logger.debug(
                    "attempting_model",
                    model=model_name,
                    chain=chain_name,
                )

                result = await executor(model_name, *args, **kwargs)

                # Sucesso - atualizar health
                health.record_success()

                _logger.info(
                    "model_execution_success",
                    model=model_name,
                    chain=chain_name,
                )

                return result

            except Exception as e:
                last_error = e
                health.record_failure()

                _logger.warning(
                    "model_execution_failed",
                    model=model_name,
                    error=str(e),
                    category=classify_error(e).value,
                )

                # Verificar se deve tentar fallback
                if not self.should_attempt_fallback(e):
                    _logger.info(
                        "non_retryable_error_no_fallback",
                        model=model_name,
                        error=str(e),
                    )
                    raise

                # Tentar próximo modelo
                next_model = chain.get_next_fallback(model_name)
                if next_model:
                    # Calcular backoff antes do próximo modelo
                    delay = calculate_backoff_delay(
                        attempt=health.consecutive_failures - 1,
                        base_delay=0.5,
                        max_delay=5.0,
                    )
                    if delay > 0:
                        await asyncio.sleep(delay)

        # Todos os modelos falharam
        raise ModelFallbackExhaustedError(
            f"All models exhausted in chain '{chain_name}'",
            last_error=last_error,
        )

    def reset_health(self, model_name: str | None = None) -> None:
        """Reseta health de um modelo ou todos."""
        if model_name:
            if model_name in self._global_health:
                self._global_health[model_name] = ModelHealth(
                    model_name=model_name
                )
        else:
            for name in self._global_health:
                self._global_health[name] = ModelHealth(model_name=name)
        _logger.info("health_reset", model=model_name or "all")


class ModelFallbackExhaustedError(Exception):
    """Erro quando todos os modelos de fallback foram esgotados."""

    def __init__(
        self,
        message: str,
        *,
        last_error: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.last_error = last_error


# Instância global singleton
_fallback_manager: ModelFallbackManager | None = None


def get_fallback_manager() -> ModelFallbackManager:
    """Retorna instância global do fallback manager."""
    global _fallback_manager
    if _fallback_manager is None:
        _fallback_manager = ModelFallbackManager()
    return _fallback_manager