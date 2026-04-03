"""Feature Flags V2 - Enhanced Feature Flag System.

Expands the existing feature_flags.py with:
- Rollout percentage with consistent hashing
- User targeting
- Session consistency
- A/B testing support
- Feature dependencies
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class FeatureFlagStatus(str, Enum):
    """Status de uma feature flag."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    PARTIAL = "partial"  # Rollout parcial


@dataclass
class ABVariant:
    """Variante de um experimento A/B.

    Attributes:
        name: Nome da variante (ex: "control", "treatment")
        weight: Peso da variante (0-100)
        config: Configuração específica da variante
    """
    name: str
    weight: int = 50
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class ABExperiment:
    """Experimento A/B.

    Attributes:
        name: Nome do experimento
        variants: Lista de variantes
        enabled: Se o experimento está ativo
    """
    name: str
    variants: list[ABVariant] = field(default_factory=list)
    enabled: bool = True


@dataclass
class FeatureFlagV2:
    """Feature flag com suporte avançado.

    Attributes:
        name: Nome da flag
        enabled: Se a flag está globalmente habilitada
        rollout_percentage: Percentual de rollout (0-100)
        target_users: Lista de usuários específicos habilitados
        dependencies: Flags que devem estar ativas primeiro
        description: Descrição da flag
        experiment: Experimento A/B associado
    """
    name: str
    enabled: bool = False
    rollout_percentage: float = 100.0
    target_users: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    description: str = ""
    experiment: ABExperiment | None = None

    def get_status(self) -> FeatureFlagStatus:
        """Retorna status da flag."""
        if not self.enabled:
            return FeatureFlagStatus.DISABLED
        if self.rollout_percentage >= 100:
            return FeatureFlagStatus.ENABLED
        return FeatureFlagStatus.PARTIAL


def _hash_to_bucket(flag_name: str, session_id: str) -> int:
    """Calcula bucket consistente para uma flag e sessão.

    Usa MD5 para garantir que mesmo usuário sempre
    veja mesma versão da feature.

    Returns:
        Bucket de 1 a 100
    """
    hash_input = f"{flag_name}:{session_id}"
    hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
    return (hash_value % 100) + 1


class FeatureFlagsV2:
    """Gerenciador de feature flags V2.

    Suporta rollout percentage, targeting, dependências e A/B testing.

    Usage:
        ff = FeatureFlagsV2()

        # Registrar flag com rollout de 50%
        ff.register(FeatureFlagV2(
            name="NEW_UI",
            enabled=True,
            rollout_percentage=50.0,
            description="New user interface"
        ))

        # Verificar se flag está ativa para um usuário
        if ff.is_enabled("NEW_UI", session_id="user-123"):
            # Usar nova UI
            pass

        # A/B Testing
        experiment = ABExperiment(
            name="search_algorithm",
            variants=[
                ABVariant("control", weight=50, config={"algo": "old"}),
                ABVariant("treatment", weight=50, config={"algo": "new"})
            ]
        )
        ff.register(FeatureFlagV2(
            name="SEARCH_ALGO_V2",
            enabled=True,
            rollout_percentage=100,
            experiment=experiment
        ))

        variant = ff.get_variant("SEARCH_ALGO_V2", session_id="user-123")
    """

    def __init__(self) -> None:
        self._flags: dict[str, FeatureFlagV2] = {}
        self._overrides: dict[str, bool] = {}  # Override local

    def register(self, flag: FeatureFlagV2) -> None:
        """Registra uma feature flag."""
        self._flags[flag.name] = flag
        _logger.info(
            "feature_flag_registered",
            name=flag.name,
            enabled=flag.enabled,
            rollout=flag.rollout_percentage,
        )

    def unregister(self, flag_name: str) -> None:
        """Remove uma feature flag."""
        self._flags.pop(flag_name, None)
        self._overrides.pop(flag_name, None)

    def get_flag(self, flag_name: str) -> FeatureFlagV2 | None:
        """Retorna uma feature flag por nome."""
        return self._flags.get(flag_name)

    def is_enabled(
        self,
        flag_name: str,
        session_id: str = "",
        user_id: str = "",
    ) -> bool:
        """Verifica se uma feature flag está ativa.

        Ordem de verificação:
        1. Override local
        2. Flag desabilitada globalmente
        3. Dependências
        4. Target users
        5. Rollout percentage

        Args:
            flag_name: Nome da flag
            session_id: ID da sessão (para consistência)
            user_id: ID do usuário (para targeting)

        Returns:
            True se a flag está ativa
        """
        # Verificar override
        if flag_name in self._overrides:
            return self._overrides[flag_name]

        flag = self._flags.get(flag_name)
        if not flag:
            return False

        # Flag desabilitada
        if not flag.enabled:
            return False

        # Verificar dependências
        for dep in flag.dependencies:
            if not self.is_enabled(dep, session_id=session_id, user_id=user_id):
                _logger.debug(
                    "feature_flag_dependency_not_met",
                    flag=flag_name,
                    dependency=dep,
                )
                return False

        # Verificar target users
        if flag.target_users and user_id in flag.target_users:
            return True

        # Verificar rollout percentage
        if flag.rollout_percentage >= 100:
            return True

        if flag.rollout_percentage <= 0:
            return False

        # Hash consistente para rollout
        identifier = session_id or user_id or "default"
        bucket = _hash_to_bucket(flag_name, identifier)
        return bucket <= flag.rollout_percentage

    def get_variant(
        self,
        flag_name: str,
        session_id: str = "",
        user_id: str = "",
    ) -> ABVariant | None:
        """Retorna variante de A/B testing para uma flag.

        Usa hash consistente para garantir que mesmo
        usuário sempre veja mesma variante.

        Args:
            flag_name: Nome da flag com experimento
            session_id: ID da sessão
            user_id: ID do usuário

        Returns:
            ABVariant ou None se não há experimento
        """
        flag = self._flags.get(flag_name)
        if not flag or not flag.experiment or not flag.experiment.enabled:
            return None

        # Verificar se flag está habilitada
        if not self.is_enabled(flag_name, session_id=session_id, user_id=user_id):
            return None

        experiment = flag.experiment
        if not experiment.variants:
            return None

        # Hash consistente para seleção de variante
        identifier = session_id or user_id or "default"
        hash_input = f"{flag_name}:variant:{identifier}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)

        # Selecionar variante baseada em peso
        total_weight = sum(v.weight for v in experiment.variants)
        if total_weight == 0:
            return experiment.variants[0]

        bucket = (hash_value % total_weight) + 1
        cumulative = 0

        for variant in experiment.variants:
            cumulative += variant.weight
            if bucket <= cumulative:
                return variant

        return experiment.variants[-1]

    def override(self, flag_name: str, enabled: bool) -> None:
        """Override local de uma feature flag."""
        self._overrides[flag_name] = enabled
        _logger.info(
            "feature_flag_overridden",
            flag=flag_name,
            enabled=enabled,
        )

    def clear_override(self, flag_name: str) -> None:
        """Remove override de uma feature flag."""
        self._overrides.pop(flag_name, None)

    def get_all_flags(self) -> dict[str, dict[str, Any]]:
        """Retorna todas as feature flags com seus status."""
        result = {}
        for name, flag in self._flags.items():
            result[name] = {
                "name": name,
                "enabled": flag.enabled,
                "status": flag.get_status().value,
                "rollout_percentage": flag.rollout_percentage,
                "dependencies": flag.dependencies,
                "description": flag.description,
                "has_experiment": flag.experiment is not None,
                "overridden": name in self._overrides,
            }
        return result

    def reset_all(self) -> None:
        """Reseta todas as flags e overrides."""
        self._flags.clear()
        self._overrides.clear()
        _logger.info("all_feature_flags_reset")


# Instância global singleton
_feature_flags_v2: FeatureFlagsV2 | None = None


def get_feature_flags_v2() -> FeatureFlagsV2:
    """Retorna instância global do FeatureFlagsV2."""
    global _feature_flags_v2
    if _feature_flags_v2 is None:
        _feature_flags_v2 = FeatureFlagsV2()
    return _feature_flags_v2