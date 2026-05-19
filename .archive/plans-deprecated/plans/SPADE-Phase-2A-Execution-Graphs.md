# 📊 Fase 2A — Execution Graphs Especializados por Agente

**Fase:** 2A | **Semana:** 2–3 | **Prioridade:** P0  
**PRD Base:** `docs/PRD/PRD-Agent-Roles-Execution-Graphs.md`  
**Depende de:** `1C` (MissionGraphType enum deve existir)  
**Bloqueia:** `2B` (MissionLauncher precisa dos graphs registrados)  
**Paralelo a:** `1B` (AgentCommunicationMixin)

---

## 📋 Sumário

Criar os execution graphs especializados que cada agente usa para suas missões autônomas. Atualmente o sistema tem apenas `SimpleOrchestratorGraph` (Route→Execute→Respond). Esta fase adiciona grafos com fluxos, ferramentas e loops otimizados por tipo de tarefa: investigação, implementação de código e pesquisa.

Todos os graphs são registrados no `GraphFactory` via `MissionGraphType` enum.

---

## 🏗️ Arquitetura dos Graphs

```
graphs/implementations/
  orchestrator/           ← EXISTENTE (SimpleOrchestratorGraph)
  analysis/               ← CRIAR
    analysis_graph.py     (AnalysisGraph)
    deep_investigation_graph.py  (DeepInvestigationGraph)
    security_audit_graph.py      (SecurityAuditGraph)
    code_review_graph.py         (CodeReviewGraph)
  coding/                 ← CRIAR
    coding_graph.py       (CodingGraph)
    bug_fix_graph.py      (BugFixGraph)
    refactor_graph.py     (RefactorGraph)
  research/               ← CRIAR
    research_graph.py     (ResearchGraph)
    comparison_graph.py   (ComparisonGraph)
```

### Estrutura Base Herdada

Todos os novos graphs herdam de `BaseGraph` (já existe em `graphs/base/graph.py`).

---

## 🔧 Implementação por Graph

---

### Graph 1 — `AnalysisGraph`

**Arquivo:** `graphs/implementations/analysis/analysis_graph.py`

**Fluxo:** `initialize → read_context → investigate ⟲ → annotate ⟲ → synthesize → report`

```
[initialize_node]
    ↓ setup tools, memory scope, agent policy
[read_context_node]
    ↓ filesystem scan, structure mapping
[investigate_node] ←─────────────────────┐
    ↓                                     │  loop até confidence >= 0.85
[annotate_node] ──────────────────────────┘  ou max_iterations
    ↓ (quando loop completo)
[synthesize_node]
    ↓
[report_node]
```

**Tools habilitadas neste graph:**
- `CODE_ANALYSIS` (primary)
- `FILESYSTEM` (read-only)
- `SHELL` (somente read: find, grep, cat)
- `MEMORY` (write: annotations por iteração)
- `P2P_COMMUNICATION` (notify progress)

**Critério de parada do loop:**
```python
def should_continue_investigation(state) -> str:
    if state.get("confidence", 0) >= 0.85:
        return "synthesize"
    if state.get("iteration", 0) >= state.get("max_iterations", 500):
        return "synthesize"
    return "investigate"
```

---

### Graph 2 — `CodingGraph`

**Arquivo:** `graphs/implementations/coding/coding_graph.py`

**Fluxo:** `initialize → plan → read_context → implement ⟲ → verify ⟲ → [test] → report`

```
[initialize_node]
    ↓ setup sandbox, tools, memory read
[plan_node]
    ↓ decompose task into steps
[read_context_node]
    ↓ read existing files, understand patterns
[implement_node] ←───────────────────────────┐
    ↓                                         │  retry se verify falha
[verify_node] ────────────────────────────────┘  (max 3 retries)
    ↓ (se testes disponíveis)
[test_node]
    ↓
[report_node]
```

**Tools habilitadas:**
- `FILESYSTEM` (read + write)
- `SHELL` (full: run tests, linters)
- `SANDBOX` (execução isolada)
- `CODE_ANALYSIS` (read patterns)
- `MEMORY` (read: project context)
- `P2P_COMMUNICATION` (request ao Analyst se architectural doubt)

**Critério de parada do ciclo implement→verify:**
```python
MAX_VERIFY_RETRIES = 3

def should_retry_implementation(state) -> str:
    if state.get("verify_passed"):
        return "test"
    if state.get("verify_retries", 0) >= MAX_VERIFY_RETRIES:
        return "report"  # entrega com aviso de verify falhou
    return "implement"
```

---

### Graph 3 — `SecurityAuditGraph`

**Arquivo:** `graphs/implementations/analysis/security_audit_graph.py`

**Fluxo:** `initialize → scan_surface → identify_vectors → test_vulnerabilities ⟲ → document ⟲ → prioritize → report`

```
[initialize_node]
    ↓ sandbox READ_ONLY, security tools
[scan_surface_node]
    ↓ map attack surface (endpoints, auth, data access)
[identify_vectors_node]
    ↓ categorize: injection, auth, exposure, etc.
[test_vulnerabilities_node] ←───────────────┐
    ↓                                        │  por vulnerability
[document_node] ─────────────────────────────┘  (anota memória imediatamente)
    ↓
[prioritize_node]
    ↓ CVSS-like scoring
[report_node]
```

**Regra especial:** Sandbox sempre READ_ONLY. Nunca escreve arquivos.  
**Cada vulnerabilidade anotada imediatamente** na memória universal (não espera fim da missão).

---

### Graph 4 — `ResearchGraph`

**Arquivo:** `graphs/implementations/research/research_graph.py`

**Fluxo:** `initialize → search ⟲ → collect ⟲ → deduplicate → synthesize → cite → report`

```
[initialize_node]
    ↓ configure sources, search scope
[search_node] ←────────────────────────────┐
    ↓                                       │  multi-source loop
[collect_node] ─────────────────────────────┘  web + docs
    ↓
[deduplicate_node]
    ↓ remove redundant sources
[synthesize_node]
    ↓ merge findings
[cite_node]
    ↓ format with references
[report_node]
```

**Tools habilitadas:**
- `WEB_SEARCH` (primary)
- `PINCHTAB_FLEET` (multi-tab)
- `PINCHTAB_BROWSER` (content extraction)
- `MEMORY` (cache findings)
- `P2P_COMMUNICATION` (stream discoveries para Coder/Analyst)

---

### Graph 5 — `BugFixGraph`

**Arquivo:** `graphs/implementations/coding/bug_fix_graph.py`

**Fluxo:** `initialize → reproduce → diagnose → fix → verify → test → report`

```
[initialize_node]
[reproduce_node]    ← reproduce o bug em sandbox
[diagnose_node]     ← root cause analysis
[fix_node]   ←──────────────────────────────┐
    ↓                                        │  retry se verify falha
[verify_node] ───────────────────────────────┘
[test_node]
[report_node]
```

---

### Graph 6 — `DeepInvestigationGraph`

**Arquivo:** `graphs/implementations/analysis/deep_investigation_graph.py`

**Fluxo:** `initialize → scope → pass_N_read ⟲ → pass_N_annotate ⟲ → cross_reference → synthesize → report`

```
[initialize_node]
[scope_node]    ← define profundidade e escopo do investigation
[pass_read_node] ←──────────────────────────┐
    ↓                                        │  N passes independentes
[pass_annotate_node] ────────────────────────┘  cada pass = 1 aspecto diferente
[cross_reference_node]  ← conecta achados entre passes
[synthesize_node]
[report_node]
```

**Usado por:** `analyst:deep_iteration` com até 1000 iterações.

---

## 🔧 Implementação — Código Base dos Graphs

Todos os graphs seguem o mesmo padrão. Aqui o template para `AnalysisGraph`:

```python
# graphs/implementations/analysis/analysis_graph.py
"""
AnalysisGraph — Execution graph para missões de análise do Analyst.

Fluxo: initialize → read_context → (investigate → annotate)* → synthesize → report
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.graphs.base.graph import BaseGraph
from mindflow_backend.graphs.base.state import GraphState
from mindflow_backend.graphs.base.types import GraphConfig, GraphType
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

CONFIDENCE_THRESHOLD = 0.85
DEFAULT_MAX_ITERATIONS = 500


class AnalysisGraph(BaseGraph):
    """Grafo de análise iterativa para o agente Analyst."""

    graph_type = GraphType.ANALYSIS  # Novo valor no enum — ver Passo Extra

    def __init__(self, graph_id: str = "analysis", config: GraphConfig | None = None):
        super().__init__(graph_id, config or GraphConfig())
        self._setup_nodes()
        self._setup_connections()
        self.set_entry_point("initialize")

    def _setup_nodes(self) -> None:
        from mindflow_backend.nodes.implementations.analysis.initialize_node import AnalysisInitializeNode
        from mindflow_backend.nodes.implementations.analysis.read_context_node import ReadContextNode
        from mindflow_backend.nodes.implementations.analysis.investigate_node import InvestigateNode
        from mindflow_backend.nodes.implementations.analysis.annotate_node import AnnotateNode
        from mindflow_backend.nodes.implementations.analysis.synthesize_node import SynthesizeNode
        from mindflow_backend.nodes.implementations.analysis.report_node import AnalysisReportNode

        self.add_node("initialize", AnalysisInitializeNode("initialize"))
        self.add_node("read_context", ReadContextNode("read_context"))
        self.add_node("investigate", InvestigateNode("investigate"))
        self.add_node("annotate", AnnotateNode("annotate"))
        self.add_node("synthesize", SynthesizeNode("synthesize"))
        self.add_node("report", AnalysisReportNode("report"))

    def _setup_connections(self) -> None:
        from mindflow_backend.graphs.base.types import NodeConnection

        self.add_connection(NodeConnection("initialize", "read_context"))
        self.add_connection(NodeConnection("read_context", "investigate"))
        self.add_connection(NodeConnection("synthesize", "report"))
        
        # Loop condicional: investigate → annotate → investigate ou synthesize
        self.add_conditional_connection(
            source="annotate",
            condition_fn=self._should_continue,
            routes={"investigate": "investigate", "synthesize": "synthesize"},
        )
        self.add_connection(NodeConnection("investigate", "annotate"))

    @staticmethod
    def _should_continue(state: dict[str, Any]) -> str:
        confidence = state.get("confidence", 0.0)
        iteration = state.get("iteration", 0)
        max_iter = state.get("max_iterations", DEFAULT_MAX_ITERATIONS)

        if confidence >= CONFIDENCE_THRESHOLD or iteration >= max_iter:
            return "synthesize"
        return "investigate"

    async def execute(self, state: GraphState) -> GraphState:
        """Executa o fluxo de análise iterativa."""
        # Implementação usando BaseGraph.run_flow()
        return await self._run_flow(state)
```

---

## 🔧 Passo Extra — Estender `GraphType` Enum

**Arquivo:** `python/mindflow_backend/graphs/base/types.py`

```python
class GraphType(str, Enum):
    SIMPLE = "simple"              # EXISTENTE
    
    # NOVOS — Análise
    ANALYSIS = "analysis"
    DEEP_INVESTIGATION = "deep_investigation"
    SECURITY_AUDIT = "security_audit"
    CODE_REVIEW = "code_review"
    
    # NOVOS — Código
    CODING_TASK = "coding_task"
    BUG_FIX = "bug_fix"
    REFACTOR = "refactor"
    
    # NOVOS — Pesquisa
    WEB_RESEARCH = "web_research"
    COMPARISON = "comparison"
```

---

## 🔧 Passo Final — Registrar no `GraphFactory`

**Arquivo:** `python/mindflow_backend/graphs/factory.py`

```python
# Em _register_builtin_graphs():

def _register_builtin_graphs(self) -> None:
    # EXISTENTE
    self.register_graph_class(
        graph_type=GraphType.SIMPLE,
        graph_class=SimpleOrchestratorGraph,
        ...
    )
    
    # NOVOS — Análise
    from mindflow_backend.graphs.implementations.analysis.analysis_graph import AnalysisGraph
    self.register_graph_class(GraphType.ANALYSIS, AnalysisGraph)
    
    from mindflow_backend.graphs.implementations.analysis.deep_investigation_graph import DeepInvestigationGraph
    self.register_graph_class(GraphType.DEEP_INVESTIGATION, DeepInvestigationGraph)
    
    from mindflow_backend.graphs.implementations.analysis.security_audit_graph import SecurityAuditGraph
    self.register_graph_class(GraphType.SECURITY_AUDIT, SecurityAuditGraph)
    
    from mindflow_backend.graphs.implementations.analysis.code_review_graph import CodeReviewGraph
    self.register_graph_class(GraphType.CODE_REVIEW, CodeReviewGraph)
    
    # NOVOS — Código
    from mindflow_backend.graphs.implementations.coding.coding_graph import CodingGraph
    self.register_graph_class(GraphType.CODING_TASK, CodingGraph)
    
    from mindflow_backend.graphs.implementations.coding.bug_fix_graph import BugFixGraph
    self.register_graph_class(GraphType.BUG_FIX, BugFixGraph)
    
    from mindflow_backend.graphs.implementations.coding.refactor_graph import RefactorGraph
    self.register_graph_class(GraphType.REFACTOR, RefactorGraph)
    
    # NOVOS — Pesquisa
    from mindflow_backend.graphs.implementations.research.research_graph import ResearchGraph
    self.register_graph_class(GraphType.WEB_RESEARCH, ResearchGraph)
    
    from mindflow_backend.graphs.implementations.research.comparison_graph import ComparisonGraph
    self.register_graph_class(GraphType.COMPARISON, ComparisonGraph)
```

---

## ✅ Checklist de Conclusão

### Semana 2 (Dias 1–3) — Estrutura e Análise
- [ ] Criar `graphs/implementations/analysis/__init__.py`
- [ ] Criar `graphs/implementations/analysis/analysis_graph.py` (AnalysisGraph)
- [ ] Criar `graphs/implementations/analysis/deep_investigation_graph.py`
- [ ] Criar `graphs/implementations/analysis/security_audit_graph.py`
- [ ] Criar `graphs/implementations/analysis/code_review_graph.py`
- [ ] Criar nodes de análise em `nodes/implementations/analysis/`

### Semana 2 (Dias 4–5) — Código e Pesquisa
- [ ] Criar `graphs/implementations/coding/__init__.py`
- [ ] Criar `graphs/implementations/coding/coding_graph.py` (CodingGraph)
- [ ] Criar `graphs/implementations/coding/bug_fix_graph.py`
- [ ] Criar `graphs/implementations/coding/refactor_graph.py`
- [ ] Criar `graphs/implementations/research/__init__.py`
- [ ] Criar `graphs/implementations/research/research_graph.py`
- [ ] Criar `graphs/implementations/research/comparison_graph.py`

### Semana 3 — Registro e Testes
- [ ] Estender `GraphType` enum em `graphs/base/types.py`
- [ ] Registrar todos os novos graphs no `GraphFactory._register_builtin_graphs()`
- [ ] Criar mapping `MissionGraphType → GraphType` para o MissionLauncher
- [ ] Testes unitários por graph
  - [ ] `test_analysis_graph_initialize_and_run()`
  - [ ] `test_analysis_graph_loop_stops_at_confidence()`
  - [ ] `test_coding_graph_verify_retry()`
  - [ ] `test_security_audit_graph_readonly_sandbox()`
  - [ ] `test_research_graph_multi_source()`
- [ ] `GraphFactory.get_available_types()` retorna 9+ tipos

---

## 📊 Métricas de Sucesso

| Métrica | Target |
|---|---|
| Graph types registrados | ≥ 9 (1 existente + 8 novos) |
| AnalysisGraph loop stops at confidence | 100% dos testes |
| CodingGraph verify retries ≤ 3 | Hard stop implementado |
| SecurityAuditGraph sandbox = READ_ONLY | Verificado em teste |
| GraphFactory.create_graph(ANALYSIS) funciona | ✅ |

---

## ⚠️ Riscos

| Risco | Mitigação |
|---|---|
| Nodes de análise ainda não existem | Criar nodes mínimos (stub com log) e iterar |
| Loop infinito em AnalysisGraph | `max_iterations` hard stop em `_should_continue()` |
| Import circular entre graphs e nodes | Imports lazy dentro de `_setup_nodes()` |
| GraphFactory muito pesado no startup | Lazy registration: graphs só importados quando solicitados |
