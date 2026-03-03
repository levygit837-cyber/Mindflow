# ADR 0005 - Padronização do MaxTokens para Context Summary

- Status: Proposed
- Data: 2026-03-03
- Decisores: @omnimind-ia (autoria IA — Duo Workflow)
- Tags: arquitetura, backend, contexto, governança, tokens

> **Nota:** Este ADR foi redigido por IA (Duo Workflow) com base na sessão de agente
> 3032321 e na diretriz do mantenedor do projeto. A pasta `ADR-IA` é destinada a
> documentação gerada por IA, enquanto a pasta `ADR` (em `docs/adr/`) é reservada
> para revisão humana.

## Contexto

O projeto OmniMind utiliza um subsistema de **Context Governance** para controlar
o tamanho dos payloads que agentes exploradores (Analyst, Researcher) enviam ao
orquestrador. O objetivo é garantir que nenhum conteúdo bruto (raw context) chegue
à janela de contexto do LLM — apenas resumos estruturados (`ExplorerSummary`).

O mantenedor do projeto definiu que o **MaxTokens para Context Summary é 10.000
tokens (10k)** como padrão do projeto. Esse valor representa o limite máximo que
um resumo de agente explorador pode ter antes de ser rejeitado pelo guard.

### Problema identificado

Havia uma **inconsistência** entre dois pontos do código que definem esse limite:

| Arquivo | Campo/Parâmetro | Valor encontrado | Status |
|---------|----------------|------------------|--------|
| `orchestrator/context_guard.py` | `validate_payload_size(max_tokens=)` | `10000` | ✅ Correto |
| `schemas/context_governance.py` | `ContextBudgetConfig.max_payload_tokens` | `1000` | ❌ Incorreto (10x menor) |

O `ContextBudgetConfig.max_payload_tokens` estava com `1000` (1k) em vez de `10_000`
(10k), criando uma divergência entre o schema de configuração e a validação em runtime.

### Distinção importante

O campo `memory_summary_window_tokens` em `infra/config.py` (valor: `300_000`) é um
**conceito diferente**. Ele controla quando o `AgentMemoryService` dispara a
sumarização de janelas de memória (`_summarize_pending_window()`), e **não** está
relacionado ao limite de tamanho de payloads de Context Summary. Este valor permanece
inalterado.

## Decisão

Padronizar todos os valores padrão de MaxTokens para Context Summary em **10.000
tokens** (`10_000`) em todo o codebase, garantindo consistência entre:

1. O schema de configuração (`ContextBudgetConfig.max_payload_tokens`)
2. A validação em runtime (`validate_payload_size` default)
3. Os testes correspondentes

## Alternativas Consideradas

### 1. Manter o valor em 1.000 tokens

- **Prós:** Mais restritivo, força resumos mais concisos
- **Contras:** Inconsistente com o `validate_payload_size` que já usava 10k;
  muito restritivo para resumos de agentes exploradores que precisam incluir
  `context_files_read`, `key_symbols`, `missing_info` e outros campos estruturados
- **Decisão:** Rejeitada

### 2. Usar um valor maior (ex: 50.000 tokens)

- **Prós:** Mais flexível para resumos complexos
- **Contras:** Desnecessário para o caso de uso atual; aumenta risco de payloads
  grandes chegarem ao orquestrador; vai contra a diretriz do mantenedor (10k)
- **Decisão:** Rejeitada

### 3. Padronizar em 10.000 tokens (escolhida)

- **Prós:** Consistente com a diretriz do mantenedor; alinhado com o valor já
  usado em `context_guard.py`; suficiente para resumos estruturados de exploradores
- **Contras:** Nenhum significativo
- **Decisão:** Aceita

## Consequências

### Positivas

- Consistência entre o schema de configuração e a validação em runtime
- Agentes exploradores podem enviar resumos de até 10k tokens sem rejeição
- Eliminação de comportamento ambíguo: o `ContextBudgetConfig` agora reflete
  o mesmo limite que o `validate_payload_size`
- Teste `test_budget_config_defaults` atualizado e passando

### Negativas

- Impacto mínimo: apenas aumenta um valor padrão de schema de 1k para 10k
- Componentes que já usavam `ContextBudgetConfig.max_payload_tokens` diretamente
  (se houver) agora terão um limite 10x maior — mas isso é o comportamento desejado

## Plano de Implementação

1. **`python/omnimind_backend/schemas/context_governance.py`**
   - Alterado `max_payload_tokens: int = 1000` → `max_payload_tokens: int = 10_000`
   - Formatação com underscore (`10_000`) para consistência com `hard_limit_tokens: int = 1_000_000`

2. **`python/tests/test_context_governance_schemas.py`**
   - Alterada asserção `assert cfg.max_payload_tokens == 1000` → `assert cfg.max_payload_tokens == 10_000`

3. **Arquivos não alterados (já corretos):**
   - `python/omnimind_backend/orchestrator/context_guard.py` — já usava `max_tokens=10000`
   - `python/omnimind_backend/infra/config.py` — `memory_summary_window_tokens=300000` é conceito diferente
   - `python/tests/test_context_guard.py` — testes usam parâmetros explícitos, não o default

## Verificação

- `pytest tests/test_context_governance_schemas.py` — 4/4 passed ✅
- `pytest tests/test_context_guard.py` — 8/8 passed ✅
- `pytest` (suite completa) — 193 passed, 1 failed (pré-existente em `test_orchestrator_memory_rag.py`, não relacionado), 10 skipped ✅

## Plano de Migração (se aplicável)

Não há migração necessária. A alteração é apenas no valor padrão de um campo de
configuração Pydantic. Qualquer instância de `ContextBudgetConfig` que já passava
`max_payload_tokens` explicitamente não é afetada. Instâncias que usavam o default
agora terão o valor correto de 10k.

## Referências

- Sessão de agente: 3032321
- Arquivo alterado: `python/omnimind_backend/schemas/context_governance.py`
- Arquivo alterado: `python/tests/test_context_governance_schemas.py`
- Arquivo de referência: `python/omnimind_backend/orchestrator/context_guard.py`
- ADR relacionado: `docs/adr/0004-vault-derived-agent-contracts-and-context-governance.md`
- Documento de governança: `docs/architecture/orchestrator-context-governance.md`
