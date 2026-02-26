# Backends

> Camada: 4 — Operacional | Depende de: AgentsDoc | Referenciado por: OrquestradorDoc
> Stack: deepagents · LangGraph · LangChain · TypeScript

---

## A) Visão Geral

- **Backend** aqui significa o provedor de LLM — o serviço que executa o modelo de linguagem (Anthropic, Google, OpenAI, Ollama, etc.).
- Toda a lógica de seleção de provedor vive em `src/server/agent/providers.ts` — a função `getModelForProvider(provider, model, options?)` é o ponto único de entrada.
- O provedor padrão do OmniMind é `vertexai` com modelo `gemini-3-flash-preview` — configurável via `.env`.
- Trocar de provedor **não exige mudar a lógica do agente** — só muda o modelo passado para `createOmniMindDeepAgent` ou `StateGraph`.
- Cada provedor tem trade-offs de custo, velocidade, tamanho de janela de contexto e capacidade de tool use.

---

## B) Conceitos Essenciais

| Termo | Definição |
|---|---|
| **Provider** | Empresa ou serviço que hospeda o modelo (anthropic, openai, google, vertexai, ollama) |
| **Model** | Versão específica do LLM dentro do provider (ex: claude-sonnet-4-6, gpt-4o, gemini-3-flash) |
| **getModelForProvider** | Função em `providers.ts` que instancia o modelo LangChain correto para o provider |
| **DEFAULT_PROVIDER** | Valor padrão quando nenhum provider é especificado (`vertexai` no projeto atual) |
| **DEFAULT_MODEL** | Modelo padrão (`gemini-3-flash-preview` no projeto atual) |
| **LLMProvider** | Tipo Union: `"anthropic" \| "openai" \| "ollama" \| "google" \| "vertexai"` (de `src/shared/types/agent.ts`) |
| **Tool use** | Capacidade do modelo de chamar tools — nem todos os modelos/providers suportam igualmente |
| **Ollama** | Provider local — roda modelos open-source na própria máquina, sem custo de API |
| **VertexAI** | Google Cloud provider — usa credenciais de service account, não API key direta |

---

## C) Provedores Suportados

| Provider | Classe LangChain | Pacote | Env Var Principal |
|---|---|---|---|
| `anthropic` | `ChatAnthropic` | `@langchain/anthropic` | `ANTHROPIC_API_KEY` |
| `openai` | `ChatOpenAI` | `@langchain/openai` | `OPENAI_API_KEY` |
| `google` | `ChatGoogleGenerativeAI` | `@langchain/google-genai` | `GOOGLE_API_KEY` |
| `vertexai` | `ChatVertexAI` | `@langchain/google-vertexai` | `GOOGLE_APPLICATION_CREDENTIALS` |
| `ollama` | `ChatOllama` | `@langchain/ollama` | `OLLAMA_BASE_URL` (opcional) |

---

## D) Boas Práticas

### DO ✅

- **Configure provider e model via env vars** — nunca hardcode no código
- **Use Ollama para desenvolvimento** — sem custo, sem latência de rede
- **Use modelos menores para sub-agentes** — Haiku (Anthropic) ou Flash (Google) são muito mais baratos
- **Reserve modelos grandes para o orquestrador** — onde a qualidade de decisão importa mais
- **Trate erros de import** — cada provider tem dependência opcional; a função já faz isso, mas saiba que pode falhar

### DON'T ❌

- **Não hardcode API keys** — use `.env` e `process.env`
- **Não use modelo máximo para tudo** — custo 10x maior para qualidade marginal
- **Não ignore diferenças de tool use** — alguns modelos são melhores que outros para chamar tools

---

## E) Exemplos Práticos

### Exemplo 1 — Seleção de provider via env var (padrão do projeto)

```typescript
// src/server/agent/providers.ts — código real do projeto
import { getModelForProvider, DEFAULT_PROVIDER, DEFAULT_MODEL } from "@/server/agent/providers";

// Lê do ambiente — configurado no .env
const provider = (process.env.LLM_PROVIDER ?? DEFAULT_PROVIDER) as LLMProvider; // "vertexai"
const model = process.env.LLM_MODEL ?? DEFAULT_MODEL;                            // "gemini-3-flash-preview"

const modelClient = getModelForProvider(provider, model);
```

---

### Exemplo 2 — Configuração por provider no .env

```bash
# .env — exemplos por provider

# Anthropic
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...

# Google (API Key direta)
LLM_PROVIDER=google
LLM_MODEL=gemini-2.0-flash
GOOGLE_API_KEY=AIza...

# VertexAI (Google Cloud — service account)
LLM_PROVIDER=vertexai
LLM_MODEL=gemini-3-flash-preview
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Ollama (local, sem API key)
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434  # opcional, este é o padrão
```

---

### Exemplo 3 — Trade-offs por provider

```
ANTHROPIC (claude-sonnet-4-6 / haiku-4-5)
  ✅ Excelente para tool use e raciocínio complexo
  ✅ Janela de 200k tokens
  ❌ Custo mais alto
  Uso: orquestrador, agente principal

GOOGLE VERTEXAI (gemini-3-flash-preview)
  ✅ Custo baixo, velocidade alta
  ✅ Janela grande
  ⚠️  Requer setup de service account (mais complexo)
  Uso: padrão do OmniMind, sub-agentes de volume

OPENAI (gpt-4o / gpt-4o-mini)
  ✅ Tool use confiável
  ✅ Amplamente documentado
  ❌ Custo intermediário
  Uso: quando compatibilidade com ecossistema OpenAI é necessária

OLLAMA (llama3.2, qwen, etc.)
  ✅ Gratuito, privado, sem latência de rede
  ✅ Ideal para desenvolvimento e testes
  ❌ Qualidade menor que modelos comerciais
  ❌ Precisa de hardware adequado
  Uso: desenvolvimento local, testes offline
```

---

### Exemplo 4 (RUIM → CORRIGIDO)

```typescript
// RUIM — provider e model hardcoded, API key no código
import { ChatAnthropic } from "@langchain/anthropic";

const model = new ChatAnthropic({
  model: "claude-sonnet-4-6",
  apiKey: "sk-ant-CHAVE-REAL-AQUI",  // NUNCA faça isso
});
```

```typescript
// CORRIGIDO — provider via env, chave via env, função centralizada
import { getModelForProvider } from "@/server/agent/providers";
import type { LLMProvider } from "@/shared/types/agent";

const model = getModelForProvider(
  (process.env.LLM_PROVIDER ?? "vertexai") as LLMProvider,
  process.env.LLM_MODEL ?? "gemini-3-flash-preview"
);
// ANTHROPIC_API_KEY, GOOGLE_APPLICATION_CREDENTIALS etc. ficam no .env
// nunca no código
```

---

## F) Confiabilidade

- **Teste que o provider está configurado** antes de iniciar — `getModelForProvider` lança `Error` se falta dependência ou configuração
- **Valide env vars na inicialização** — se `ANTHROPIC_API_KEY` está ausente e provider é `anthropic`, falhe rápido com mensagem clara
- **Incerteza**: modelos disponíveis no VertexAI variam por região e plano. **(incerto)** — confirme disponibilidade no Google Cloud Console.

---

## G) Analogia

O provider é o **fornecedor de energia** para o agente. O agente não sabe nem se importa se a energia vem de hidrelétrica, solar ou nuclear — ele só precisa que chegue na voltagem certa. A função `getModelForProvider` é o adaptador universal: você diz qual tomada quer usar (`anthropic`, `openai`, `ollama`) e ela entrega a corrente no formato que o LangChain espera.

---

## H) Erros Comuns e Como Evitar

| Erro | Causa | Como evitar |
|---|---|---|
| `Error: Cannot find module` ao trocar provider | Pacote não instalado | Instale o pacote do provider antes de usar |
| `AuthenticationError` | API key ausente ou incorreta | Verifique `.env` e variáveis de ambiente |
| VertexAI não autentica | `GOOGLE_APPLICATION_CREDENTIALS` não configurado | Siga a doc do Google Cloud para service account |
| Ollama não conecta | Serviço não rodando | Execute `ollama serve` antes de usar |
| Modelo não encontrado | Nome de modelo incorreto | Verifique nome exato na documentação do provider |
| Custo alto inesperado | Modelo caro para todos os agentes | Use modelo menor para sub-agentes (Haiku, Flash) |

---

## I) Mini-Template Pronto

```typescript
// ============================================================
// TEMPLATE: Seleção de provider + modelo
// Baseado em src/server/agent/providers.ts
// ============================================================

import { getModelForProvider, DEFAULT_PROVIDER, DEFAULT_MODEL } from "@/server/agent/providers";
import type { LLMProvider } from "@/shared/types/agent";

// --- Orquestrador (modelo mais capaz) ---
const orchestratorModel = getModelForProvider(
  (process.env.ORCHESTRATOR_PROVIDER ?? "anthropic") as LLMProvider,
  process.env.ORCHESTRATOR_MODEL ?? "claude-sonnet-4-6"
);

// --- Sub-agentes (modelo mais rápido e barato) ---
const subagentModel = getModelForProvider(
  (process.env.SUBAGENT_PROVIDER ?? "anthropic") as LLMProvider,
  process.env.SUBAGENT_MODEL ?? "claude-haiku-4-5-20251001"
);

// --- Desenvolvimento local (ollama, sem custo) ---
const localModel = getModelForProvider(
  "ollama",
  process.env.OLLAMA_MODEL ?? "llama3.2"
);

// .env recomendado para desenvolvimento:
// ORCHESTRATOR_PROVIDER=vertexai
// ORCHESTRATOR_MODEL=gemini-3-flash-preview
// SUBAGENT_PROVIDER=vertexai
// SUBAGENT_MODEL=gemini-3-flash-preview
// GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json
```
