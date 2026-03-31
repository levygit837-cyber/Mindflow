# 🎭 Fase 1C — CommRoles e Extensão de AgentRuntimePolicy

**Fase:** 1C | **Semana:** 1–2 | **Prioridade:** P0  
**PRD Base:** `docs/PRD/PRD-Agent-Roles-Execution-Graphs.md`  
**Depende de:** Nada — paralelo à Fase 1A  
**Bloqueia:** `2A` (Execution Graphs usam MissionGraphType), `2B` (MissionLauncher lê policies)  
**Paralelo a:** `1A` (CommunicationBus)

---

## 📋 Sumário

Definir formalmente os papéis de comunicação (`CommRole`) e os tipos de grafos de missão (`MissionGraphType`) como schemas canônicos. Depois estender o `AgentRuntimePolicy` com os novos campos: `comm_role`, `available_mission_graphs`, `can_observe` e `mission_types`. Cada política de agente receberá a sua configuração completa.

Esta fase é de **pura definição de schema** — não altera comportamento, apenas estabelece contratos formais que as fases seguintes usam.

---

## 🏗️ Arquitetura

```
schemas/orchestration/
  orchestrator.py       ← AgentType, ExecutionStrategy (EXISTENTE)
  specialists.py        ← SpecialistType (EXISTENTE)
  communication.py      ← NOVO: CommRole, MissionGraphType
                                                  │
                                                  ↓
agents/specialists/
  runtime_policy.py     ← MODIFICAR: adicionar 4 campos à AgentRuntimePolicy
                          comm_role: CommRole
                          available_mission_graphs: tuple[MissionGraphType, ...]
                          can_observe: bool
                          mission_types: tuple[str, ...]
                                                  │
                                                  ↓
AGENT_RUNTIME_POLICY dict ← ATUALIZAR todas as 10 policies com novos campos
```

---

## 🎯 O Que Fazer

### Estado Atual
```
schemas/orchestration/
  ✅ orchestrator.py    → AgentType, ExecutionStrategy, ToolScope, etc.
  ✅ specialists.py     → SpecialistType
  ❌ communication.py   → NÃO EXISTE — criar agora

agents/specialists/
  ✅ runtime_policy.py  → AgentRuntimePolicy com 8 campos existentes
  ❌ runtime_policy.py  → FALTAM: comm_role, available_mission_graphs, can_observe, mission_types
```

---

## 🔧 Implementação Passo a Passo

### Passo 1 — Criar `schemas/orchestration/communication.py`

```python
# schemas/orchestration/communication.py
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
```

**Arquivo:** `python/mindflow_backend/schemas/orchestration/communication.py`

---

### Passo 2 — Atualizar `schemas/orchestration/__init__.py`

```python
# Adicionar exports ao __init__.py dos schemas de orchestration
from .communication import CommRole, MissionGraphType

# No __all__ adicionar:
# "CommRole",
# "MissionGraphType",
```

---

### Passo 3 — Estender `AgentRuntimePolicy`

**Arquivo:** `python/mindflow_backend/agents/specialists/runtime_policy.py`

```python
# Adicionar import no topo:
from mindflow_backend.schemas.orchestration.communication import (
    CommRole,
    MissionGraphType,
)

# Estender o dataclass (manter slots=True e frozen=True):
@dataclass(frozen=True, slots=True)
class AgentRuntimePolicy:
    """Immutable runtime contract for a role or specialist identity."""
    
    # ── Campos existentes (NÃO ALTERAR) ──────────────────────────────
    agent_role: AgentType
    system_prompt: str
    specialist: SpecialistType | None = None
    tools: tuple[ToolScope, ...] = ()
    sandbox: SandboxMode = SandboxMode.NONE
    thinking_level: ThinkingLevel = ThinkingLevel.MEDIUM
    keep_context: bool = True
    max_iterations: int = 1
    summary: str = ""
    use_when: str = ""

    # ── Campos NOVOS (com defaults para backward compat) ─────────────
    comm_role: CommRole = CommRole.SPECIALIST
    """Papel na sessão colaborativa: leader | specialist | observer"""

    available_mission_graphs: tuple[MissionGraphType, ...] = ()
    """Tipos de execution graphs que este agente pode executar"""

    can_observe: bool = False
    """Se True, o agente pode entrar em modo observer após missão"""

    mission_types: tuple[str, ...] = ()
    """Tipos de missão que este agente pode liderar (strings descritivas)"""
```

> **Importante:** Os campos novos têm defaults, garantindo que código existente que instancia `AgentRuntimePolicy` sem esses campos continue funcionando.

---

### Passo 4 — Atualizar Todas as Runtime Policies

**Arquivo:** `python/mindflow_backend/agents/specialists/runtime_policy.py`

Atualizar o dict `AGENT_RUNTIME_POLICY` com os novos campos em cada entry:

```python
AGENT_RUNTIME_POLICY: dict[str, AgentRuntimePolicy] = {

    "orchestrator": AgentRuntimePolicy(
        agent_role=AgentType.ORCHESTRATOR,
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        tools=(ToolScope.MEMORY, ToolScope.PLANNING, ToolScope.DELEGATION),
        sandbox=SandboxMode.NONE,
        thinking_level=ThinkingLevel.HIGH,
        max_iterations=1000,
        summary="Central conversational agent que delega a especialistas.",
        use_when="Todos os requests do usuário — entry point único.",
        # ── NOVOS CAMPOS ──────────────────────────────────────────────
        comm_role=CommRole.LEADER,
        available_mission_graphs=(),      # Não executa missões; lança missões de outros
        can_observe=True,                 # Monitora todas as missões em andamento
        mission_types=("coordination", "synthesis", "team_session"),
    ),

    "analyst": AgentRuntimePolicy(
        agent_role=AgentType.ANALYST,
        system_prompt=ANALYST_SYSTEM_PROMPT,
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.SHELL, ToolScope.MEMORY),
        sandbox=SandboxMode.READ_ONLY,
        thinking_level=ThinkingLevel.MEDIUM,
        max_iterations=500,
        summary="Investigação de código, análise, auditoria.",
        use_when="Entender código, rastrear bugs, explicar implementações.",
        # ── NOVOS CAMPOS ──────────────────────────────────────────────
        comm_role=CommRole.SPECIALIST,
        available_mission_graphs=(
            MissionGraphType.ANALYSIS,
            MissionGraphType.DEEP_INVESTIGATION,
            MissionGraphType.SECURITY_AUDIT,
            MissionGraphType.CODE_REVIEW,
        ),
        can_observe=True,
        mission_types=("analysis", "code_investigation", "review"),
    ),

    "analyst:security_guard": AgentRuntimePolicy(
        agent_role=AgentType.ANALYST,
        specialist=SpecialistType.SECURITY_GUARD,
        system_prompt=compose_analyst_prompt("core", "security_guard"),
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.SHELL),
        sandbox=SandboxMode.READ_ONLY,
        thinking_level=ThinkingLevel.HIGH,
        max_iterations=500,
        summary="Auditorias de segurança e análise de vulnerabilidades.",
        use_when="Security reviews, auth analysis, vulnerability checks.",
        # ── NOVOS CAMPOS ──────────────────────────────────────────────
        comm_role=CommRole.SPECIALIST,
        available_mission_graphs=(
            MissionGraphType.SECURITY_AUDIT,
            MissionGraphType.VULNERABILITY_SCAN,
        ),
        can_observe=True,
        mission_types=("security_audit", "vulnerability_scan"),
    ),

    "analyst:critic": AgentRuntimePolicy(
        agent_role=AgentType.ANALYST,
        specialist=SpecialistType.CRITIC,
        system_prompt=compose_analyst_prompt("core", "critic"),
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.SHELL),
        sandbox=SandboxMode.READ_ONLY,
        thinking_level=ThinkingLevel.MEDIUM,
        max_iterations=500,
        summary="Code review, critique e avaliação de qualidade.",
        use_when="Review focado de qualidade e riscos de implementação.",
        # ── NOVOS CAMPOS ──────────────────────────────────────────────
        comm_role=CommRole.SPECIALIST,
        available_mission_graphs=(
            MissionGraphType.CODE_REVIEW,
            MissionGraphType.ANALYSIS,
        ),
        can_observe=False,
        mission_types=("code_review", "quality_assessment"),
    ),

    "analyst:brainstorm": AgentRuntimePolicy(
        agent_role=AgentType.ANALYST,
        specialist=SpecialistType.BRAINSTORM,
        system_prompt=compose_analyst_prompt("core", "brainstorm"),
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM),
        sandbox=SandboxMode.READ_ONLY,
        thinking_level=ThinkingLevel.MEDIUM,
        max_iterations=500,
        summary="Geração de ideias e exploração de alternativas.",
        use_when="Ideação, exploração e brainstorming.",
        # ── NOVOS CAMPOS ──────────────────────────────────────────────
        comm_role=CommRole.SPECIALIST,
        available_mission_graphs=(
            MissionGraphType.IDEATION,
            MissionGraphType.EXPLORATION,
        ),
        can_observe=False,
        mission_types=("ideation", "exploration"),
    ),

    "analyst:deep_iteration": AgentRuntimePolicy(
        agent_role=AgentType.ANALYST,
        specialist=SpecialistType.DEEP_ITERATION,
        system_prompt=DEEP_ANALYSIS_PROMPT,
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.SHELL),
        sandbox=SandboxMode.READ_ONLY,
        thinking_level=ThinkingLevel.HIGH,
        max_iterations=1000,
        summary="Investigação multi-arquivo com análise iterativa exaustiva.",
        use_when="Análise de alta complexidade com múltiplos passes.",
        # ── NOVOS CAMPOS ──────────────────────────────────────────────
        comm_role=CommRole.SPECIALIST,
        available_mission_graphs=(
            MissionGraphType.DEEP_INVESTIGATION,
            MissionGraphType.MULTI_PASS_ANALYSIS,
        ),
        can_observe=True,
        mission_types=("deep_analysis", "multi_pass_investigation"),
    ),

    "analyst:planner": AgentRuntimePolicy(
        agent_role=AgentType.ANALYST,
        specialist=SpecialistType.DEEP_ITERATION,
        system_prompt=PLANNING_PROMPT,
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.PLANNING),
        sandbox=SandboxMode.READ_ONLY,
        thinking_level=ThinkingLevel.HIGH,
        max_iterations=500,
        summary="Planejamento estruturado com análise de impacto.",
        use_when="Tarefas complexas que requerem planejamento antes da implementação.",
        # ── NOVOS CAMPOS ──────────────────────────────────────────────
        comm_role=CommRole.SPECIALIST,
        available_mission_graphs=(
            MissionGraphType.ANALYSIS,
            MissionGraphType.DEEP_INVESTIGATION,
        ),
        can_observe=False,
        mission_types=("planning", "impact_analysis"),
    ),

    "coder": AgentRuntimePolicy(
        agent_role=AgentType.CODER,
        system_prompt=CODER_SYSTEM_PROMPT,
        tools=(ToolScope.FILESYSTEM, ToolScope.SHELL, ToolScope.MEMORY),
        sandbox=SandboxMode.FULL,
        thinking_level=ThinkingLevel.HIGH,
        max_iterations=1000,
        summary="Escrita de código, implementação, refatoração.",
        use_when="Implementar features, corrigir bugs, editar codebase.",
        # ── NOVOS CAMPOS ──────────────────────────────────────────────
        comm_role=CommRole.SPECIALIST,
        available_mission_graphs=(
            MissionGraphType.CODING_TASK,
            MissionGraphType.REFACTOR,
            MissionGraphType.BUG_FIX,
            MissionGraphType.IMPLEMENTATION,
        ),
        can_observe=False,
        mission_types=("coding", "bug_fix", "refactor", "implementation"),
    ),

    "coder:arch_tech": AgentRuntimePolicy(
        agent_role=AgentType.CODER,
        specialist=SpecialistType.ARCH_TECH,
        system_prompt=compose_coder_prompt("core", "arch_tech"),
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.SHELL),
        sandbox=SandboxMode.FULL,
        thinking_level=ThinkingLevel.HIGH,
        max_iterations=1000,
        summary="Design arquitetural, decisões estruturais e refatoração.",
        use_when="Coding de arquitetura ou refatoração estrutural.",
        # ── NOVOS CAMPOS ──────────────────────────────────────────────
        comm_role=CommRole.SPECIALIST,
        available_mission_graphs=(
            MissionGraphType.ARCHITECTURE_DESIGN,
            MissionGraphType.STRUCTURAL_REFACTOR,
            MissionGraphType.CODING_TASK,
        ),
        can_observe=False,
        mission_types=("architecture_design", "structural_refactor"),
    ),

    "researcher": AgentRuntimePolicy(
        agent_role=AgentType.RESEARCHER,
        system_prompt=RESEARCHER_SYSTEM_PROMPT,
        tools=(ToolScope.WEB_SEARCH, ToolScope.PINCHTAB_FLEET, ToolScope.PINCHTAB_BROWSER, ToolScope.MEMORY),
        sandbox=SandboxMode.READ_ONLY,
        thinking_level=ThinkingLevel.HIGH,
        max_iterations=500,
        summary="Pesquisa web, documentação e comparações externas.",
        use_when="Pesquisa externa, documentação e comparações de tecnologias.",
        # ── NOVOS CAMPOS ──────────────────────────────────────────────
        comm_role=CommRole.SPECIALIST,
        available_mission_graphs=(
            MissionGraphType.WEB_RESEARCH,
            MissionGraphType.DOCUMENTATION_LOOKUP,
            MissionGraphType.COMPARISON_ANALYSIS,
        ),
        can_observe=False,
        mission_types=("web_research", "documentation", "comparison"),
    ),
}
```

---

### Passo 5 — Atualizar `schemas/orchestration/orchestrator.py` (ExecutionStrategy)

Adicionar `TEAM_SESSION` ao enum:

```python
class ExecutionStrategy(str, Enum):
    DIRECT_RESPONSE = "direct_response"
    DELEGATE = "delegate"
    CHAIN = "chain"
    GRAPH = "graph"
    TEAM_SESSION = "team_session"    # NOVO — usado pela Fase 3A
```

---

## ✅ Checklist de Conclusão

### Semana 1 (Dias 1–3)
- [ ] Criar `schemas/orchestration/communication.py`
  - [ ] `CommRole` enum (LEADER, SPECIALIST, OBSERVER)
  - [ ] `MissionGraphType` enum (todos os 17 tipos)
  - [ ] Docstrings descritivos por tipo
- [ ] Atualizar `schemas/orchestration/__init__.py` com exports

### Semana 1–2 (Dias 4–7)
- [ ] Adicionar imports de `CommRole` e `MissionGraphType` em `runtime_policy.py`
- [ ] Adicionar 4 novos campos ao `AgentRuntimePolicy` dataclass
  - [ ] `comm_role: CommRole = CommRole.SPECIALIST`
  - [ ] `available_mission_graphs: tuple[MissionGraphType, ...] = ()`
  - [ ] `can_observe: bool = False`
  - [ ] `mission_types: tuple[str, ...] = ()`
- [ ] Atualizar TODAS as 10 entries em `AGENT_RUNTIME_POLICY`
- [ ] Adicionar `ExecutionStrategy.TEAM_SESSION` ao orchestrator schema

### Validação
- [ ] `list_agent_runtime_policies()` retorna policies com novos campos
- [ ] `get_agent_runtime_policy("orchestrator").comm_role == CommRole.LEADER`
- [ ] `get_agent_runtime_policy("analyst").available_mission_graphs` tem 4 items
- [ ] `get_agent_runtime_policy("coder").can_observe == False`
- [ ] Código existente que usa `AgentRuntimePolicy` não quebra (todos os campos têm defaults)
- [ ] Testes unitários `test_runtime_policy_comm_fields.py`

---

## 🧪 Teste de Validação Rápida

```python
from mindflow_backend.agents.specialists.runtime_policy import (
    get_agent_runtime_policy,
    list_agent_runtime_policies,
)
from mindflow_backend.schemas.orchestration.communication import CommRole

# Verificar todos os agents têm comm_role
for policy in list_agent_runtime_policies():
    assert policy.comm_role in CommRole, f"Faltando comm_role em {policy.agent_id}"
    print(f"✅ {policy.agent_id}: {policy.comm_role.value}, graphs={len(policy.available_mission_graphs)}")

# Verificar Orchestrator é LEADER
orch = get_agent_runtime_policy("orchestrator")
assert orch.comm_role == CommRole.LEADER
assert orch.can_observe is True
print("✅ Orchestrator é LEADER e can_observe=True")

# Verificar Analyst tem graphs
analyst = get_agent_runtime_policy("analyst")
assert len(analyst.available_mission_graphs) >= 3
print(f"✅ Analyst tem {len(analyst.available_mission_graphs)} mission graphs")
```

---

## 📊 Métricas de Sucesso

| Métrica | Target |
|---|---|
| 100% das policies com `comm_role` definido | ✅ |
| Código existente não quebra após extensão | 0 erros de importação/runtime |
| `MissionGraphType` cobre todos os graphs planejados | 17 tipos definidos |
| Testes unitários passando | 100% |
