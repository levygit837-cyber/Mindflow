# PromptGuide

> Camada: 3 — Qualidade | Depende de: ContextoDoc, MemoryDoc | Referenciado por: SystemPromptDoc
> Stack: deepagents · LangGraph · LangChain · TypeScript

---

## A) Visão Geral

- Um prompt é a instrução que você dá ao LLM — a qualidade do prompt determina diretamente a qualidade da resposta.
- Prompts mal escritos causam respostas vagas, alucinações, formatos errados e uso incorreto de tools.
- A anatomia de um prompt eficaz tem cinco partes: **role**, **contexto**, **instrução**, **formato**, **exemplo**.
- Técnicas como **chain-of-thought**, **few-shot** e **structured output** são ferramentas — use a certa para cada cenário.
- O prompt é código: deve ser versionado, testado e revisado como qualquer outra parte do sistema.
- Para agentes, o prompt não é só para o LLM responder — é para o LLM **decidir** (qual tool usar, quando parar, como estruturar o output).

---

## B) Conceitos Essenciais

| Termo | Definição |
|---|---|
| **Zero-shot** | Prompt sem exemplos — só instrução; depende do modelo entender sozinho |
| **Few-shot** | Prompt com 2–5 exemplos de input/output esperado — guia o modelo com padrões concretos |
| **Chain-of-thought (CoT)** | Instrui o modelo a "pensar passo a passo" antes de responder — melhora raciocínio complexo |
| **Structured output** | Instrui o modelo a retornar JSON ou outro formato específico — essencial para pipelines |
| **System prompt** | Instrução persistente que define comportamento geral do agente (ver SystemPromptDoc) |
| **User prompt** | Mensagem do usuário em cada turno da conversa |
| **Grounding** | Ancoragem da resposta em fatos do contexto — evita que o modelo invente |
| **Hallucination** | Quando o modelo gera informação falsa com confiança — causado por prompt vago ou contexto insuficiente |
| **Temperature** | Parâmetro que controla aleatoriedade (0 = determinístico, 1 = criativo) — use 0 para outputs estruturados |
| **Prompt injection** | Quando input do usuário tenta sobrescrever as instruções do system prompt — proteja-se validando inputs |

---

## C) Boas Práticas

### DO ✅

- **Seja específico na instrução** — "Liste 3 problemas de segurança no código" é melhor que "Analise o código"
- **Defina o formato de saída explicitamente** — "Retorne JSON com campos: {issue, severity, line}"
- **Use few-shot para tarefas de classificação** — exemplos concretos reduzem erros
- **Peça chain-of-thought para raciocínio complexo** — "Pense passo a passo antes de responder"
- **Instrua o modelo a dizer quando não sabe** — "Se não tiver informação suficiente, diga 'Não tenho dados para responder'"
- **Use temperatura 0 para outputs estruturados** — maximiza consistência
- **Versione seus prompts** — um prompt é código, trate como tal
- **Teste prompts com casos de borda** — entrada vazia, entrada muito longa, entrada adversarial

### DON'T ❌

- **Não use instrução negativa sem alternativa** — "Não invente" sem dizer "Diga que não sabe" cria ambiguidade
- **Não misture múltiplas tarefas em um prompt** — uma instrução = uma tarefa
- **Não confie em prompt sozinho para segurança** — prompt injection existe; valide inputs no código
- **Não esqueça do formato de saída** — sem ele, o modelo escolhe o formato e raramente é o que você precisa
- **Não use temperatura alta para análise** — aumenta criatividade mas também alucinação

---

## D) Receitas Reutilizáveis

### Anatomia do prompt eficaz

```
[ROLE]       → Quem o modelo é: "Você é um revisor de segurança sênior..."
[CONTEXTO]   → O que ele tem disponível: "Você receberá trechos de código TypeScript..."
[INSTRUÇÃO]  → O que ele deve fazer: "Identifique vulnerabilidades OWASP Top 10..."
[FORMATO]    → Como deve responder: "Retorne JSON: [{issue, severity, line, fix}]"
[EXEMPLO]    → Demonstração concreta (few-shot): Input X → Output Y esperado
```

### Checklist de prompt

- [ ] Role definido (quem é o modelo neste contexto)
- [ ] Contexto fornecido (o que o modelo tem para trabalhar)
- [ ] Instrução clara e específica
- [ ] Formato de saída explícito
- [ ] Instrução sobre o que fazer quando falta informação
- [ ] Pelo menos 1 exemplo (few-shot) para tarefas complexas
- [ ] Testado com input vazio, muito longo e adversarial

### Quando usar cada técnica

```
Zero-shot    → Tarefas simples e bem definidas (traduzir, resumir)
Few-shot     → Classificação, extração, formatação específica
CoT          → Raciocínio multi-passo, matemática, debugging
Structured   → Qualquer output que será parseado por código
```

---

## E) Exemplos Práticos

### Exemplo 1 — Prompt zero-shot bem estruturado

```typescript
const ANALYZER_PROMPT = `Você é um especialista em segurança de software.

Analise o código TypeScript fornecido e identifique vulnerabilidades de segurança.

Retorne EXATAMENTE este JSON, sem markdown, sem texto adicional:
{
  "vulnerabilities": [
    {
      "issue": "nome do problema",
      "severity": "HIGH|MEDIUM|LOW",
      "line": numero_da_linha_ou_null,
      "description": "explicação em 1 frase",
      "fix": "como corrigir em 1 frase"
    }
  ],
  "overall_risk": "HIGH|MEDIUM|LOW|SAFE"
}

Se não houver vulnerabilidades, retorne {"vulnerabilities": [], "overall_risk": "SAFE"}.
Se o código não for TypeScript ou estiver vazio, retorne {"error": "Código inválido ou vazio"}.`;
```

---

### Exemplo 2 — Prompt few-shot para classificação de tarefa

```typescript
const TASK_ROUTER_PROMPT = `Você é um roteador de tarefas. Classifique a tarefa do usuário em uma das categorias.

Categorias disponíveis:
- "bugfix": corrigir um bug existente
- "feature": implementar nova funcionalidade
- "refactor": melhorar código sem mudar comportamento
- "question": responder pergunta sem modificar código
- "other": qualquer outra coisa

Exemplos:
Input: "O botão de login não funciona no Safari"
Output: {"category": "bugfix", "confidence": "HIGH"}

Input: "Adicione autenticação com Google OAuth"
Output: {"category": "feature", "confidence": "HIGH"}

Input: "O que esse arquivo faz?"
Output: {"category": "question", "confidence": "HIGH"}

Input: "Melhore a performance do endpoint /api/users"
Output: {"category": "refactor", "confidence": "MEDIUM"}

Retorne apenas JSON: {"category": "...", "confidence": "HIGH|MEDIUM|LOW"}
Sem markdown. Sem texto adicional.`;
```

---

### Exemplo 3 — Prompt com chain-of-thought para debugging

```typescript
const DEBUGGER_PROMPT = `Você é um engenheiro sênior de debugging.

Ao receber um erro e trecho de código, siga ESTE PROCESSO:

Passo 1 — Leia o erro:
Identifique: tipo do erro, mensagem, linha (se disponível).

Passo 2 — Leia o código:
Localize onde o erro ocorre. Identifique o contexto ao redor.

Passo 3 — Identifique a causa raiz:
Qual é a causa real? (não o sintoma, mas o porquê)

Passo 4 — Proponha a correção:
Mostre o código corrigido. Explique em 1 frase o que mudou.

Formato de saída:
\`\`\`
ANÁLISE:
[resultado dos passos 1 e 2]

CAUSA RAIZ:
[resultado do passo 3]

CORREÇÃO:
\`\`\`typescript
[código corrigido]
\`\`\`
EXPLICAÇÃO: [1 frase]
\`\`\`

Se não tiver informação suficiente para diagnosticar, diga:
"Preciso de mais contexto: [o que está faltando]"
`;
```

---

### Exemplo 4 (RUIM → CORRIGIDO)

```typescript
// ❌ RUIM — prompt vago, sem formato, sem instrução de fallback

const VAGUE_PROMPT = `Você é um assistente útil.
Ajude o usuário com o que ele precisar.
Seja legal.`;
```

**Problemas:**
1. Sem role específico — o modelo vai ser genérico
2. Sem instrução sobre formato de saída
3. Sem instrução sobre o que fazer quando não souber
4. Sem contexto sobre o domínio (coding? suporte? escrita?)

```typescript
// ✅ CORRIGIDO — prompt específico, com formato e fallback

const SPECIFIC_PROMPT = `Você é um assistente de engenharia de software especializado em TypeScript e Python.

Seu trabalho é ajudar desenvolvedores a:
- Debuggar problemas de código
- Revisar e melhorar código existente
- Explicar conceitos técnicos de forma clara

REGRAS:
1. Sempre cite a linha ou função específica ao falar de código
2. Quando sugerir mudanças, mostre o before e after
3. Se não tiver certeza de algo, diga explicitamente: "Não tenho certeza, mas..."
4. Se faltarem informações para responder, pergunte o que precisa: "Para responder precisarei de: [lista]"
5. Nunca invente APIs, funções ou comportamentos de bibliotecas

FORMATO:
- Para análise de código: use seções com cabeçalhos
- Para correções: mostre diff (❌ Antes / ✅ Depois)
- Para explicações: use bullet points e exemplos concretos`;
```

---

## F) Confiabilidade / Anti-Alucinação

### Como evitar que o modelo invente

- **Grounding explícito**: "Baseie sua resposta APENAS nas informações fornecidas no contexto. Se a informação não estiver lá, diga que não sabe."
- **Instrução de incerteza**: "Se não tiver certeza, escreva '(incerto)' ao lado da informação."
- **Validação de formato**: para outputs JSON, sempre valide com `JSON.parse()` — se falhar, reprompt com o erro.

```typescript
import type { BaseLanguageModel } from "@langchain/core/language_models/base";

async function callWithJsonValidation(
  prompt: string,
  userInput: string,
  model: BaseLanguageModel,
  maxRetries = 2
): Promise<Record<string, unknown>> {
  /** Chama o modelo e valida que o output é JSON válido. Reprompta se inválido. */
  const messages: { role: string; content: string }[] = [
    { role: "system", content: prompt },
    { role: "user", content: userInput },
  ];

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const response = await model.invoke(messages);
    let raw = (response as { content: string }).content.trim();

    // Remove markdown code blocks se presentes
    if (raw.startsWith("```")) {
      raw = raw.split("```")[1];
      if (raw.startsWith("json")) {
        raw = raw.slice(4);
      }
    }

    try {
      return JSON.parse(raw) as Record<string, unknown>;
    } catch (err) {
      if (attempt < maxRetries) {
        messages.push({ role: "assistant", content: raw });
        messages.push({
          role: "user",
          content: `Erro de JSON: ${String(err)}. Retorne APENAS JSON válido, sem texto adicional.`,
        });
      } else {
        return { error: `Falha após ${maxRetries + 1} tentativas: ${String(err)}`, raw };
      }
    }
  }
  return { error: "Falha desconhecida" };
}
```

### Quando o modelo não tem informação

O prompt deve instruir explicitamente:
```
"Se você não tiver informação suficiente para responder com confiança:
- NÃO invente
- Diga: 'Não tenho dados suficientes para responder sobre [X]'
- Pergunte o que precisa: 'Para responder, precisaria de: [lista]'"
```

---

## G) Analogia

Escrever um prompt é como dar instruções para um estagiário extremamente inteligente que acabou de entrar na empresa. Ele é capaz de fazer tudo — mas não sabe nada sobre o contexto, os padrões do time, o que é aceitável ou não.

Se você diz "analisa esse código", ele vai analisar — mas pode usar o formato errado, falar de coisas irrelevantes, e quando não souber algo, vai inventar para parecer útil. Se você diz "analisa esse código e me diz se tem algum problema de segurança, retorna JSON com {issue, severity, line}, e se não tiver certeza de algo, escreve (incerto)" — agora ele tem tudo que precisa para fazer um bom trabalho.

O estagiário não precisa de mais inteligência — precisa de mais contexto e instruções claras.

---

## H) Erros Comuns e Como Evitar

| Erro | Causa | Como evitar |
|---|---|---|
| Output em formato errado | Formato não especificado no prompt | Defina explicitamente o formato de saída |
| Modelo inventa APIs | Sem grounding, temperatura alta | Adicione instrução de grounding + use temperatura 0 |
| Modelo não usa tools | Tool descriptions vagas | Melhore descrição das tools (ver ToolsDoc) |
| Modelo para no meio | Instrução ambígua sobre quando terminar | Defina critério explícito de conclusão |
| Prompt injection | Input do usuário sobrescreve instruções | Valide e sanitize inputs antes de inserir no prompt |
| Inconsistência entre chamadas | Temperatura alta | Use temperatura 0 para tarefas determinísticas |
| Output muito longo | Sem limite definido | Especifique "máximo X palavras" ou "máximo X bullets" |

---

## I) Mini-Template Pronto

```typescript
// ============================================================
// TEMPLATE: Prompt estruturado padrão OmniMind
// ============================================================

interface PromptExample {
  input: string;
  output: string;
}

function buildPrompt(params: {
  role: string;
  domainContext: string;
  taskInstruction: string;
  outputFormat: string;
  examples?: PromptExample[];
  fallbackInstruction?: string;
}): string {
  /** Monta um prompt estruturado com todas as seções essenciais. */
  const {
    role,
    domainContext,
    taskInstruction,
    outputFormat,
    examples,
    fallbackInstruction = "Se não tiver informação suficiente, diga o que está faltando.",
  } = params;

  const sections = [
    `[ROLE]\n${role}`,
    `[CONTEXTO]\n${domainContext}`,
    `[TAREFA]\n${taskInstruction}`,
    `[FORMATO DE SAÍDA]\n${outputFormat}`,
    `[QUANDO NÃO SOUBER]\n${fallbackInstruction}`,
  ];

  if (examples?.length) {
    const exampleText = examples
      .map((ex) => `Input: ${ex.input}\nOutput: ${ex.output}`)
      .join("\n\n");
    sections.push(`[EXEMPLOS]\n${exampleText}`);
  }

  return sections.join("\n\n");
}


// Uso:
const SECURITY_PROMPT = buildPrompt({
  role: "Você é um especialista em segurança de software com 10 anos de experiência.",
  domainContext: "Você analisa código TypeScript e Python para encontrar vulnerabilidades.",
  taskInstruction:
    "Analise o código fornecido e identifique vulnerabilidades de segurança. " +
    "Foque em: injeção SQL, XSS, autenticação fraca, dados sensíveis expostos.",
  outputFormat:
    'JSON: {"vulnerabilities": [{"issue": string, "severity": "HIGH|MEDIUM|LOW", "line": number|null, "fix": string}]}',
  examples: [
    {
      input:
        "const password = req.query.password;\nif (password === 'admin123') {",
      output:
        '{"vulnerabilities": [{"issue": "Senha hardcoded", "severity": "HIGH", "line": 2, "fix": "Use variável de ambiente e hash seguro"}]}',
    },
  ],
  fallbackInstruction:
    'Se o código não tiver vulnerabilidades óbvias, retorne {"vulnerabilities": [], "note": "Nenhum problema encontrado"}.',
});
```
