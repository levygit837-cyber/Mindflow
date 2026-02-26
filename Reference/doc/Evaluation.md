# Evaluation

> Camada: 4 — Operacional | Depende de: ToolsDoc, AgentsDoc, PromptGuide | Referenciado por: —
> Stack: deepagents · LangGraph · LangChain · Python

---

## A) Visão Geral

- Agentes podem estar **confiantes e errados** — sem avaliação, você não sabe se o sistema funciona até chegar na produção.
- Avaliação em agentes cobre três níveis: **unitário** (cada tool isolada), **integração** (fluxo de agente completo) e **end-to-end** (task real do usuário).
- Métricas principais: **fidelidade** (resposta correta?), **grounding** (baseada em fatos reais?), **latência** (tempo aceitável?), **custo** (tokens gastos justificam o resultado?).
- **LLM-as-judge** é uma técnica onde um modelo avalia as respostas de outro — útil quando não há ground truth fixo.
- Avaliação não precisa de framework pesado — testes Python simples com `assert` cobrem a maioria dos casos.

---

## B) Conceitos Essenciais

| Termo | Definição |
|---|---|
| **Ground truth** | Resposta correta conhecida, usada para comparar com o output do agente |
| **Fidelidade** | O output está correto e completo em relação ao esperado? |
| **Grounding** | O output está ancorado em fatos do contexto, não inventado? |
| **LLM-as-judge** | Usar um LLM para avaliar a qualidade de respostas quando não há ground truth fixo |
| **Eval suite** | Conjunto de casos de teste para avaliar o agente — inputs, contextos e outputs esperados |
| **Regression** | Teste que verifica que mudanças não quebraram comportamento que funcionava |
| **Latência P95** | O tempo que 95% das requests levam — métrica de performance real |
| **Token efficiency** | Relação entre tokens gastos e qualidade do resultado |

---

## C) Boas Práticas

### DO ✅

- **Comece com testes unitários por tool** — antes de testar o agente completo, certifique que cada tool funciona
- **Crie um eval suite mínimo** — 5–10 casos representativos por funcionalidade
- **Teste casos de borda** — input vazio, muito longo, ambíguo, adversarial
- **Monitore latência e custo por request** — métricas de negócio além de qualidade
- **Use LLM-as-judge para avaliações qualitativas** — quando o output correto não é binário
- **Versione seus evals junto com os prompts** — prompt muda = evals precisam ser revalidados

### DON'T ❌

- **Não avalie apenas o happy path** — casos de erro são onde agentes falham mais
- **Não confie só em LLM-as-judge** — adicione testes determinísticos para o que puder
- **Não ignore latência** — uma resposta correta em 30 segundos pode ser inutilizável

---

## D) Receitas Reutilizáveis

### Checklist de avaliação

- [ ] Testes unitários para cada tool (input → output esperado)
- [ ] Eval suite com casos representativos (happy path + edge cases)
- [ ] Teste de regressão após mudança de prompt ou tool
- [ ] Monitoramento de latência e tokens em produção
- [ ] LLM-as-judge para outputs qualitativos sem ground truth

---

## E) Exemplos Práticos

### Exemplo 1 — Teste unitário de tool

```python
# python/tests/test_tools.py
import pytest
from omnimind_agents.prompts.tools.filesystem import read_file_tool  # ajuste o import real

def test_read_file_success(tmp_path):
    """Tool retorna conteúdo do arquivo."""
    f = tmp_path / "test.txt"
    f.write_text("conteudo de teste")
    result = read_file_tool.invoke({"path": str(f)})
    assert "conteudo de teste" in result

def test_read_file_not_found():
    """Tool retorna erro legível quando arquivo não existe."""
    result = read_file_tool.invoke({"path": "/caminho/que/nao/existe.txt"})
    assert "[ERRO]" in result
    assert "nao encontrado" in result.lower() or "not found" in result.lower()

def test_read_file_empty(tmp_path):
    """Tool lida com arquivo vazio sem travar."""
    f = tmp_path / "empty.txt"
    f.write_text("")
    result = read_file_tool.invoke({"path": str(f)})
    assert result is not None
```

---

### Exemplo 2 — Avaliação de agente com LLM-as-judge

```python
import json
from langchain_anthropic import ChatAnthropic

JUDGE_PROMPT = """Avalie se a resposta do agente está correta e completa.

Pergunta: {question}
Resposta do agente: {answer}
Contexto disponível: {context}

Critérios:
- CORRETO: a resposta é factualmente correta baseada no contexto?
- COMPLETO: a resposta endereça todos os aspectos da pergunta?
- GROUNDED: a resposta se baseia no contexto, não inventa?

Retorne JSON:
{{"correto": true, "completo": true, "grounded": true, "score": 1, "justificativa": "frase"}}

Onde score vai de 1 (péssimo) a 5 (excelente)."""

judge = ChatAnthropic(model="claude-haiku-4-5-20251001")

def check_response_quality(question: str, answer: str, context: str) -> dict:
    response = judge.invoke([{
        "role": "user",
        "content": JUDGE_PROMPT.format(
            question=question,
            answer=answer,
            context=context,
        )
    }])
    raw = response.content.strip()
    # Remove markdown code fences se presentes
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1])
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "Judge retornou formato invalido", "raw": raw[:200]}

# Uso em suite de testes:
def test_agent_response_quality(agent):
    question = "Qual e a funcao da classe StateBackend?"
    context = "StateBackend armazena estado em memoria acessivel via path /memories/."
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"recursion_limit": 10},
    )
    answer = result["messages"][-1].content

    verdict = check_response_quality(question, answer, context)
    assert verdict.get("score", 0) >= 3, f"Score baixo: {verdict}"
    assert verdict.get("grounded", False), "Resposta nao ancorada no contexto"
```

---

### Exemplo 3 (RUIM → CORRIGIDO)

```python
# RUIM — "teste" que so verifica que nao explodiu, sem medir qualidade

def test_agent_works():
    result = agent.invoke({"messages": [{"role": "user", "content": "Ola"}]})
    assert result is not None  # sempre passa, nao mede nada
```

```python
# CORRIGIDO — testa comportamento real com casos parametrizados

import pytest

EVAL_CASES = [
    {
        "id": "resposta_esperada",
        "input": "O que e StateBackend?",
        "expect_contains": "estado",
    },
    {
        "id": "admite_desconhecimento",
        "input": "Qual e o preco do Bitcoin agora?",
        "expect_contains": "nao tenho",
    },
]

@pytest.mark.parametrize("case", EVAL_CASES, ids=[c["id"] for c in EVAL_CASES])
def test_agent_behavior(case, agent):
    result = agent.invoke(
        {"messages": [{"role": "user", "content": case["input"]}]},
        config={"recursion_limit": 10},
    )
    answer = result["messages"][-1].content.lower()
    assert case["expect_contains"].lower() in answer, (
        f"Esperava '{case['expect_contains']}' em: {answer[:200]}"
    )
```

---

## F) Confiabilidade / Anti-Alucinação

- **Nunca confie em avaliacao manual em producao** — automatize o que puder
- **Use thresholds explícitos** — "score >= 3.5 = aprovado" é melhor que "parece bom"
- **Monitore degradacao** — um agente que funcionava pode piorar após mudança de modelo ou prompt

```python
# Monitoramento simples de tokens por request
def log_request_metrics(response, request_id: str) -> None:
    usage = getattr(response, "usage", None) or getattr(response, "response_metadata", {})
    print(json.dumps({
        "request_id": request_id,
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
    }))
```

---

## G) Analogia

Avaliar um agente é como fazer **controle de qualidade em linha de producao**. Voce nao inspeciona cada produto — define amostras representativas, metricas claras e um threshold de aceitacao. Quando um produto sai fora do padrao, rastreia a causa raiz e corrige o processo.

---

## H) Erros Comuns e Como Evitar

| Erro | Causa | Como evitar |
|---|---|---|
| So testa happy path | Otimismo excessivo | Adicione pelo menos 3 edge cases no eval suite |
| LLM-as-judge sem criterios | Prompt vago para o juiz | Defina criterios explícitos e scoring numerico |
| Eval suite desatualizado | Prompt mudou, testes nao | Versione prompts e evals juntos |
| Sem monitoramento em producao | "Funciona no dev" | Adicione logging de tokens e latencia por request |

---

## I) Mini-Template Pronto

```python
# ============================================================
# TEMPLATE: Eval suite minimo
# ============================================================

import pytest
import json
from langchain_anthropic import ChatAnthropic

# --- Casos de teste ---
EVAL_CASES = [
    {
        "id": "happy_path",
        "input": "Pergunta valida e clara",
        "expect_contains": "palavra_chave_esperada",
    },
    {
        "id": "admite_desconhecimento",
        "input": "Pergunta sobre algo fora do contexto",
        "expect_contains": "nao tenho",
    },
    {
        "id": "edge_comprimento",
        "input": "x" * 5000,  # input muito longo
        "expect_no_crash": True,
    },
]

@pytest.mark.parametrize("case", EVAL_CASES, ids=[c["id"] for c in EVAL_CASES])
def test_agent_suite(case, agent):
    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": case["input"]}]},
            config={"recursion_limit": 10},
        )
        answer = result["messages"][-1].content.lower()
    except Exception as e:
        if case.get("expect_no_crash"):
            pytest.fail(f"Agente explodiu com input longo: {e}")
        return

    if "expect_contains" in case:
        assert case["expect_contains"].lower() in answer, (
            f"[{case['id']}] Esperava '{case['expect_contains']}', recebeu: {answer[:200]}"
        )
```
