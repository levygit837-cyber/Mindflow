"""Squad Registry — Templates pré-configurados de times de agentes.

Evita a necessidade de um leilão completo para padrões conhecidos de colaboração.
O HybridRouter consulta o registry quando o IntelligentRouter identifica
is_multi_agent=True com alta confiança.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SquadTemplate:
    """Template imutável de um squad pré-configurado.

    Attributes:
        name: Identificador único do squad.
        description: Descrição curta do propósito do squad.
        agent_ids: Tupla com IDs dos agentes participantes.
        leader: Agente que lidera e sintetiza os resultados.
        skip_discussion: Se True pula a fase de Discussion (fast path p/ sub-teams).
        intent_keywords: Palavras-chave que ativam este squad.
            Usadas para matching por regex (case-insensitive, qualquer idioma).
    """

    name: str
    description: str
    agent_ids: tuple[str, ...]
    leader: str
    skip_discussion: bool = False
    intent_keywords: tuple[str, ...] = field(default_factory=tuple)

    def matches(self, intent_text: str) -> bool:
        """Retorna True se alguma keyword bate com o texto de intenção."""
        if not self.intent_keywords:
            return False
        pattern = "|".join(re.escape(kw) for kw in self.intent_keywords)
        return bool(re.search(pattern, intent_text, re.IGNORECASE))


# ---------------------------------------------------------------------------
# Squads pré-definidos
# ---------------------------------------------------------------------------

REFACTORING_SQUAD = SquadTemplate(
    name="refactoring",
    description="Refatoração de código: análise de code smell → implementação → revisão",
    agent_ids=("analyst", "coder"),
    leader="coder",
    skip_discussion=False,
    intent_keywords=(
        "refactor",
        "refatorar",
        "refactoring",
        "reorganize",
        "clean code",
        "code smell",
        "limpeza",
        "reestruturar",
        "restructure",
    ),
)

FEATURE_SQUAD = SquadTemplate(
    name="feature_development",
    description="Desenvolvimento de feature completa: análise de requisitos → implementação",
    agent_ids=("analyst", "coder"),
    leader="coder",
    skip_discussion=False,
    intent_keywords=(
        "implement",
        "implementar",
        "criar feature",
        "create feature",
        "build",
        "construir",
        "desenvolver",
        "develop",
        "nova funcionalidade",
        "new feature",
    ),
)

ANALYSIS_SQUAD = SquadTemplate(
    name="deep_analysis",
    description="Análise profunda: pesquisa + análise multi-perspectiva",
    agent_ids=("researcher", "analyst"),
    leader="analyst",
    skip_discussion=False,
    intent_keywords=(
        "analyze",
        "analisar",
        "análise",
        "analysis",
        "investigate",
        "investigar",
        "audit",
        "auditoria",
        "diagnose",
        "diagnosticar",
        "deep dive",
    ),
)

RESEARCH_SQUAD = SquadTemplate(
    name="research",
    description="Pesquisa multi-fonte com síntese: coleta + análise + documento",
    agent_ids=("researcher", "analyst"),
    leader="researcher",
    skip_discussion=True,
    intent_keywords=(
        "research",
        "pesquisar",
        "pesquise",
        "compare",
        "comparar",
        "survey",
        "levantamento",
        "documentação",
        "documentation",
        "best practices",
        "melhores práticas",
    ),
)

SECURITY_SQUAD = SquadTemplate(
    name="security_review",
    description="Revisão de segurança: análise de vulnerabilidades + remediação",
    agent_ids=("analyst", "coder"),
    leader="analyst",
    skip_discussion=False,
    intent_keywords=(
        "security",
        "segurança",
        "vulnerability",
        "vulnerabilidade",
        "exploit",
        "sanitize",
        "sanitização",
        "injection",
        "xss",
        "csrf",
        "authentication",
        "autenticação",
        "pentest",
    ),
)


# Registry ordenado: o primeiro match ganha
# Coloque squads mais específicos antes de genéricos
_ALL_SQUADS: tuple[SquadTemplate, ...] = (
    SECURITY_SQUAD,
    REFACTORING_SQUAD,
    RESEARCH_SQUAD,
    ANALYSIS_SQUAD,
    FEATURE_SQUAD,
)


class SquadRegistry:
    """Registry de templates de squads.

    Ponto central para configurar e consultar squads pré-definidos.
    """

    def __init__(self, squads: tuple[SquadTemplate, ...] = _ALL_SQUADS) -> None:
        self._squads = squads

    def find_squad(self, intent_text: str) -> SquadTemplate | None:
        """Encontra o primeiro squad que bate com o texto de intenção.

        Args:
            intent_text: Texto livre (normalmente formulated_objective do IntentAnalysis).

        Returns:
            SquadTemplate se houver match, None caso contrário.
        """
        for squad in self._squads:
            if squad.matches(intent_text):
                return squad
        return None

    def get_squad_by_name(self, name: str) -> SquadTemplate | None:
        """Recupera um squad pelo nome exato."""
        for squad in self._squads:
            if squad.name == name:
                return squad
        return None

    @property
    def all_squads(self) -> tuple[SquadTemplate, ...]:
        """Retorna todos os squads registrados (somente leitura)."""
        return self._squads


# Singleton global
_registry: SquadRegistry | None = None


def get_squad_registry() -> SquadRegistry:
    """Retorna a instância global do SquadRegistry."""
    global _registry
    if _registry is None:
        _registry = SquadRegistry()
    return _registry
