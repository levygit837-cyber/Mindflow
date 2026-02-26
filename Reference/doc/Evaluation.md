# Evaluation

> Camada: 4 — Operacional | Depende de: ToolsDoc, AgentsDoc, PromptGuide | Referenciado por: —
> Stack: deepagents · LangGraph · LangChain · TypeScript

---

## A) Visão Geral

- Agentes podem estar **confiantes e errados** — sem avaliação, você não sabe se o sistema funciona até chegar na produção.
- Avaliação em agentes cobre três níveis: **unitário** (cada tool isolada), **integração** (fluxo de agente completo) e **end-to-end** (task real do usuário).
- Métricas principais: **fidelidade** (resposta correta?), **grounding** (baseada em fatos reais?), **latência** (tempo aceitável?), **custo** (tokens gastos justificam o resultado?).
- **LLM-as-judge** é uma técnica onde um modelo avalia as respostas de outro — útil quando não há ground truth fixo.
- Avaliação não precisa de framework pesado — testes Vitest simples com `expect` cobrem a maioria dos casos.

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

```typescript
// src/server/agent/__tests__/tools.test.ts
import { describe, it, expect } from "vitest";
import { readFileTool } from "@/server/agent/prompts/tools/filesystem";
import { writeFile } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";

describe("readFileTool", () => {
  it("retorna conteúdo do arquivo", async () => {
    const tmpPath = join(tmpdir(), `test-${Date.now()}.txt`);
    await writeFile(tmpPath, "conteudo de teste", "utf-8");

    const result = await readFileTool.invoke({ path: tmpPath });
    expect(result).toContain("conteudo de teste");
  });

  it("retorna erro legível quando arquivo não existe", async () => {
    const result = await readFileTool.invoke({
      path: "/caminho/que/nao/existe.txt",
    });
    expect(result).toContain("[ERRO]");
    expect(result.toLowerCase()).toMatch(/nao encontrado|not found/);
  });

  it("lida com arquivo vazio sem travar", async () => {
    const tmpPath = join(tmpdir(), `empty-${Date.now()}.txt`);
    await writeFile(tmpPath, "", "utf-8");

    const result = await readFileTool.invoke({ path: tmpPath });
    expect(result).not.toBeNull();
  });
});
```

---

### Exemplo 2 — Avaliação de agente com LLM-as-judge

```typescript
import { ChatAnthropic } from "@langchain/anthropic";

const JUDGE_PROMPT = `Avalie se a resposta do agente está correta e completa.

Pergunta: {question}
Resposta do agente: {answer}
Contexto disponível: {context}

Critérios:
- CORRETO: a resposta é factualmente correta baseada no contexto?
- COMPLETO: a resposta endereça todos os aspectos da pergunta?
- GROUNDED: a resposta se baseia no contexto, não inventa?

Retorne JSON:
{"correto": true, "completo": true, "grounded": true, "score": 1, "justificativa": "frase"}

Onde score vai de 1 (péssimo) a 5 (excelente).`;

const judge = new ChatAnthropic({ model: "claude-haiku-4-5-20251001" });

interface JudgeVerdict {
  correto?: boolean;
  completo?: boolean;
  grounded?: boolean;
  score?: number;
  justificativa?: string;
  error?: string;
  raw?: string;
}

async function checkResponseQuality(
  question: string,
  answer: string,
  context: string
): Promise<JudgeVerdict> {
  const prompt = JUDGE_PROMPT.replace("{question}", question)
    .replace("{answer}", answer)
    .replace("{context}", context);

  const response = await judge.invoke([{ role: "user", content: prompt }]);
  let raw = (response.content as string).trim();

  // Remove markdown code fences se presentes
  if (raw.startsWith("```")) {
    const lines = raw.split("\n");
    raw = lines.slice(1, -1).join("\n");
  }

  try {
    return JSON.parse(raw) as JudgeVerdict;
  } catch {
    return { error: "Judge retornou formato invalido", raw: raw.slice(0, 200) };
  }
}

// Uso em suite de testes:
it("avalia qualidade da resposta do agente", async () => {
  const question = "Qual e a funcao da classe StateBackend?";
  const context = "StateBackend armazena estado em memoria acessivel via path /memories/.";
  const result = await agent.invoke(
    { messages: [{ role: "user", content: question }] },
    { recursionLimit: 10 }
  );
  const answer = result.messages[result.messages.length - 1].content as string;

  const verdict = await checkResponseQuality(question, answer, context);
  expect(verdict.score ?? 0).toBeGreaterThanOrEqual(3);
  expect(verdict.grounded).toBe(true);
});
```

---

### Exemplo 3 (RUIM → CORRIGIDO)

```typescript
// RUIM — "teste" que so verifica que nao explodiu, sem medir qualidade

it("agent works", async () => {
  const result = await agent.invoke({ messages: [{ role: "user", content: "Ola" }] });
  expect(result).not.toBeNull(); // sempre passa, nao mede nada
});
```

```typescript
// CORRIGIDO — testa comportamento real com casos parametrizados

import { describe, it, expect } from "vitest";

interface EvalCase {
  id: string;
  input: string;
  expectContains: string;
}

const EVAL_CASES: EvalCase[] = [
  {
    id: "resposta_esperada",
    input: "O que e StateBackend?",
    expectContains: "estado",
  },
  {
    id: "admite_desconhecimento",
    input: "Qual e o preco do Bitcoin agora?",
    expectContains: "nao tenho",
  },
];

describe("agent behavior", () => {
  it.each(EVAL_CASES)("$id", async ({ input, expectContains }) => {
    const result = await agent.invoke(
      { messages: [{ role: "user", content: input }] },
      { recursionLimit: 10 }
    );
    const answer = (
      result.messages[result.messages.length - 1].content as string
    ).toLowerCase();
    expect(answer).toContain(expectContains.toLowerCase());
  });
});
```

---

## F) Confiabilidade / Anti-Alucinação

- **Nunca confie em avaliacao manual em producao** — automatize o que puder
- **Use thresholds explícitos** — "score >= 3.5 = aprovado" é melhor que "parece bom"
- **Monitore degradacao** — um agente que funcionava pode piorar após mudança de modelo ou prompt

```typescript
// Monitoramento simples de tokens por request
function logRequestMetrics(
  response: { usage_metadata?: Record<string, unknown> },
  requestId: string
): void {
  const usage = response.usage_metadata ?? {};
  console.log(
    JSON.stringify({
      requestId,
      inputTokens: usage["input_tokens"] ?? null,
      outputTokens: usage["output_tokens"] ?? null,
    })
  );
}
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

```typescript
// ============================================================
// TEMPLATE: Eval suite minimo
// src/server/agent/__tests__/eval-suite.test.ts
// Rodar com: pnpm test  ou  vitest run
// ============================================================

import { describe, it, expect, beforeEach } from "vitest";
import { ChatAnthropic } from "@langchain/anthropic";

// --- Casos de teste ---
interface EvalCase {
  id: string;
  input: string;
  expectContains?: string;
  expectNoCrash?: boolean;
}

const EVAL_CASES: EvalCase[] = [
  {
    id: "happy_path",
    input: "Pergunta valida e clara",
    expectContains: "palavra_chave_esperada",
  },
  {
    id: "admite_desconhecimento",
    input: "Pergunta sobre algo fora do contexto",
    expectContains: "nao tenho",
  },
  {
    id: "edge_comprimento",
    input: "x".repeat(5000), // input muito longo
    expectNoCrash: true,
  },
];

describe("agent eval suite", () => {
  it.each(EVAL_CASES)("$id", async ({ input, expectContains, expectNoCrash }) => {
    let answer: string;

    try {
      const result = await agent.invoke(
        { messages: [{ role: "user", content: input }] },
        { recursionLimit: 10 }
      );
      answer = (
        result.messages[result.messages.length - 1].content as string
      ).toLowerCase();
    } catch (e) {
      if (expectNoCrash) {
        throw new Error(`Agente explodiu com input longo: ${e}`);
      }
      return;
    }

    if (expectContains !== undefined) {
      expect(answer).toContain(expectContains.toLowerCase());
    }
  });
});
```
