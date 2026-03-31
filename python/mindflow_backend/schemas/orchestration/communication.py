"""
Schemas de comunicação e missão para agentes MindFlow.

CommRole: papel na sessão colaborativa (leader/specialist/observer)
MissionGraphType: tipo de execution graph disponível por agente
"""

from __future__ import annotations

from enum import Enum


class CommRole(str, Enum):
    """
    Papel de comunicação do agente em sessões colaborativas.

    LEADER     → Orquestra, cria teams, autoriza missões, sintetiza resultados
    SPECIALIST → Executa missões autônomas, reporta ao leader
    OBSERVER   → Monitora execuções alheias e anota memória, não bloqueia
    """

    LEADER = "leader"
    SPECIALIST = "specialist"
    OBSERVER = "observer"


class MissionGraphType(str, Enum):
    """
    Tipos de execution graphs disponíveis para missões autônomas.

    Cada tipo mapeia para uma implementação em graphs/implementations/.
    Agentes só podem executar os graphs listados em sua RuntimePolicy.
    """

    # ── Analyst graphs ───────────────────────────────────────────────
    ANALYSIS = "analysis"
    """Investigação geral: read_context → investigate (loop) → synthesize"""

    DEEP_INVESTIGATION = "deep_investigation"
    """Investigação multi-pass exaustiva: múltiplos passes com anotação"""

    SECURITY_AUDIT = "security_audit"
    """Auditoria de segurança: scan_surface → identify_vectors → document"""

    CODE_REVIEW = "code_review"
    """Review de código: lint → pattern_check → quality_score → report"""

    IDEATION = "ideation"
    """Brainstorm estruturado: explore → generate → score → report"""

    MULTI_PASS_ANALYSIS = "multi_pass_analysis"
    """Deep iteration: N passes de análise até confidence >= threshold"""

    VULNERABILITY_SCAN = "vulnerability_scan"
    """Scan focado em vulnerabilidades específicas de segurança"""

    EXPLORATION = "exploration"
    """Exploração livre: mapeamento de território desconhecido"""

    # ── Coder graphs ────────────────────────────────────────────────
    CODING_TASK = "coding_task"
    """Implementação completa: plan → read → implement → verify → test"""

    BUG_FIX = "bug_fix"
    """Correção de bugs: reproduce → diagnose → fix → verify"""

    REFACTOR = "refactor"
    """Refatoração: read → plan → refactor → verify → test"""

    IMPLEMENTATION = "implementation"
    """Implementação de feature: spec → implement → test → document"""

    ARCHITECTURE_DESIGN = "architecture_design"
    """Design arquitetural: research → design → document → prototype"""

    STRUCTURAL_REFACTOR = "structural_refactor"
    """Refatoração estrutural de larga escala"""

    # ── Researcher graphs ───────────────────────────────────────────
    WEB_RESEARCH = "web_research"
    """Pesquisa web: search (loop) → collect → deduplicate → cite"""

    DOCUMENTATION_LOOKUP = "documentation_lookup"
    """Consulta de documentação: query → extract → summarize"""

    COMPARISON_ANALYSIS = "comparison_analysis"
    """Análise comparativa: research_A → research_B → compare → recommend"""
