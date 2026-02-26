# ToolsDoc

> Camada: 1 — Fundação | Depende de: — | Referenciado por: AgentsDoc, SubAgentsDoc, OrquestradorDoc
> Stack: deepagents · LangGraph · LangChain · TypeScript

---

## A) Visão Geral

- Uma **tool** é uma função com schema bem definido que um agente pode invocar para agir no mundo (ler arquivo, buscar na web, executar código, etc.).
- O LLM não executa a tool diretamente — ele decide chamá-la e passa os argumentos; o runtime executa e devolve o resultado.
- Tools são a ponte entre o raciocínio do LLM e o mundo real.
- Cada tool deve ter **um único propósito** — tools genéricas demais causam erros de uso pelo modelo.
- LangChain, LangGraph e deepagents usam o mesmo conceito de tool, com APIs ligeiramente diferentes mas compatíveis.
- O schema da tool (nome, descrição, parâmetros) é o que o LLM lê para decidir quando e como usá-la — a descrição é tão importante quanto o código.

---

## B) Conceitos Essenciais

| Termo | Definição |
|---|---|
| **Tool** | Função registrada com nome, descrição e schema de input que o agente pode chamar |
| **Schema** | Estrutura de dados que define quais parâmetros a tool aceita (geralmente Zod) |
| **Tool call** | Quando o LLM decide invocar uma tool e gera os argumentos no formato esperado |
| **Tool result** | O que a tool retorna após execução — vai de volta para o LLM como contexto |
| **tool()** | Forma mais simples de criar uma tool no LangChain — envolve uma função TypeScript |
| **DynamicStructuredTool** | Classe base do LangChain para tools mais complexas com estado ou lógica extra |
| **StructuredTool** | Tool LangChain que aceita schema Zod explícito para validação de input |
| **schema** | Atributo que define o schema Zod da tool (usado em DynamicStructuredTool e StructuredTool) |
| **Tool síncrona** | Tool que retorna um valor direto |
| **Tool assíncrona** | Tool que retorna uma Promise — necessária em agentes async |

---

## C) Boas Práticas

### DO ✅

- **Nomes descritivos e únicos** — `readFile` é melhor que `get` ou `fileTool`
- **Descrição explica QUANDO usar** — "Use esta tool para ler o conteúdo de um arquivo local. NÃO use para URLs."
- **Um único propósito por tool** — se a tool faz A e B, separe em duas
- **Validação de input com Zod** — evita que o LLM passe tipos errados
- **Retorno sempre string ou objeto serializável** — o LLM recebe o resultado como texto
- **Erro explícito com mensagem útil** — `return "[ERRO] Arquivo não encontrado: " + path` é melhor que retornar undefined
- **Implementar função async quando o agente é async** — evitar bloqueios no event loop
- **Documentar casos de borda na descrição** — "retorna string vazia se o arquivo estiver vazio"

### DON'T ❌

- **Não crie tools com efeitos colaterais silenciosos** — se deletar algo, avise na descrição
- **Não use nomes genéricos** — `tool1`, `helper`, `doThing` confundem o LLM
- **Não retorne objetos JavaScript complexos não serializáveis** — o LLM não consegue interpretar; serialize para string/JSON
- **Não faça a tool "inteligente"** — lógica de decisão fica no agente, não na tool
- **Não ignore erros** — retornar resultado vazio sem avisar causa alucinações
- **Não crie uma tool para tudo** — tools demais sobrecarregam o contexto do LLM

---

## D) Receitas Reutilizáveis

### Checklist para criar uma nova tool

- [ ] Nome único e descritivo (camelCase)
- [ ] Descrição explica: o que faz, quando usar, quando NÃO usar
- [ ] Schema Zod com tipos e descrições em todos os campos
- [ ] Retorno sempre serializável (string, object, array)
- [ ] Tratamento de erro com mensagem clara
- [ ] Função async se o agente usar Promises
- [ ] Teste unitário que valida input, output e comportamento de erro
- [ ] Registrada no agente/runtime correto

### Passos para criar uma tool com `tool()`

```
1. Definir a função com tipagem TypeScript
2. Adicionar description — ela vira a descrição da tool
3. Definir schema Zod para os parâmetros
4. Envolver com tool()
5. Registrar na lista de tools do agente
```

### Passos para criar uma tool com `DynamicStructuredTool`

```
1. Criar instância de DynamicStructuredTool
2. Definir name (string) e description (string)
3. Criar schema Zod para os parâmetros
4. Implementar func: async (args) => string
5. Registrar no agente
```

---

## E) Exemplos Práticos

### Exemplo 1 — Tool simples com tool() (LangChain)

```typescript
import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { readFileSync } from "fs";

const readFile = tool(
  async ({ path }: { path: string }): Promise<string> => {
    try {
      return readFileSync(path, "utf-8");
    } catch (err: unknown) {
      if ((err as NodeJS.ErrnoException).code === "ENOENT") {
        return `[ERRO] Arquivo não encontrado: ${path}`;
      }
      return `[ERRO] Falha ao ler arquivo: ${(err as Error).message}`;
    }
  },
  {
    name: "read_file",
    description:
      "Lê o conteúdo de um arquivo local e retorna como string. " +
      "Use quando o agente precisar inspecionar o conteúdo de um arquivo. " +
      "NÃO use para URLs ou arquivos remotos. " +
      "Retorna mensagem de erro se o arquivo não existir.",
    schema: z.object({
      path: z.string().describe("Caminho absoluto ou relativo do arquivo"),
    }),
  }
);
```

---

### Exemplo 2 — Tool estruturada com DynamicStructuredTool + Zod (LangChain)

```typescript
import { DynamicStructuredTool } from "@langchain/core/tools";
import { z } from "zod";

const searchWebSchema = z.object({
  query: z.string().describe("Termo de busca em linguagem natural"),
  maxResults: z.number().int().min(1).max(10).default(5).describe("Número máximo de resultados (1–10)"),
});

const searchWebTool = new DynamicStructuredTool({
  name: "search_web",
  description:
    "Busca informações na web usando uma query em linguagem natural. " +
    "Use quando precisar de informações atuais ou externas ao contexto. " +
    "NÃO use para arquivos locais.",
  schema: searchWebSchema,
  func: async ({ query, maxResults = 5 }): Promise<string> => {
    // integração real aqui (ex: Tavily, SerpAPI)
    // const results = await tavilyClient.search(query, { maxResults });
    throw new Error("Implemente com seu provider de busca");
  },
});
```

---

### Exemplo 3 — Tool com deepagents

```typescript
// deepagents usa tools compatíveis com LangChain
// A diferença está em como elas são registradas no backend

import { createDeepAgent } from "deepagents";
import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { readdirSync } from "fs";

const listDirectory = tool(
  async ({ path }: { path: string }): Promise<string> => {
    try {
      const entries = readdirSync(path);
      return entries.length > 0 ? entries.join("\n") : "[vazio]";
    } catch (err: unknown) {
      if ((err as NodeJS.ErrnoException).code === "ENOENT") {
        return `[ERRO] Diretório não encontrado: ${path}`;
      }
      return `[ERRO] ${(err as Error).message}`;
    }
  },
  {
    name: "list_directory",
    description:
      "Lista arquivos e pastas em um diretório. " +
      "Retorna uma lista formatada. Use '.' para o diretório atual. " +
      "Retorna mensagem de erro se o diretório não existir.",
    schema: z.object({
      path: z.string().describe("Caminho do diretório a listar"),
    }),
  }
);

// Registrando no agente deepagents
const agent = createDeepAgent({
  model,
  systemPrompt: "Você é um assistente de filesystem.",
  tools: [listDirectory], // tools LangChain funcionam direto
  name: "fs-agent",
});
```

---

### Exemplo 4 (RUIM → CORRIGIDO)

```typescript
// ❌ RUIM — vários problemas

import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { execSync } from "child_process";

const doStuff = tool(
  async ({ input }: { input: string }) => {
    const result = execSync(input, { shell: true }); // executa qualquer coisa
    return result.toString(); // pode lançar exceção sem tratamento
  },
  {
    name: "do_stuff",
    description: "Faz coisas.", // descrição inútil — LLM não sabe quando usar
    schema: z.object({ input: z.string() }),
  }
);
```

**Problemas:**
1. Nome genérico — LLM não sabe quando usar
2. Descrição vazia — LLM não sabe o que faz
3. `shell: true` com input livre — risco de injeção de comandos
4. Sem tratamento de erro — quebra o pipeline silenciosamente

```typescript
// ✅ CORRIGIDO

import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { execFileSync } from "child_process";

const ALLOWED_COMMANDS = new Set(["ls", "pwd", "echo", "cat"]);

const runSafeCommand = tool(
  async ({ command }: { command: string }): Promise<string> => {
    const parts = command.trim().split(/\s+/);
    if (parts.length === 0 || !parts[0]) {
      return "[ERRO] Comando vazio.";
    }
    if (!ALLOWED_COMMANDS.has(parts[0])) {
      return `[ERRO] Comando '${parts[0]}' não permitido. Permitidos: ${[...ALLOWED_COMMANDS].sort().join(", ")}`;
    }
    try {
      const output = execFileSync(parts[0], parts.slice(1), {
        encoding: "utf-8",
        timeout: 10_000,
      });
      return output || "[sem output]";
    } catch (err: unknown) {
      if ((err as NodeJS.ErrnoException).code === "ETIMEDOUT") {
        return "[ERRO] Comando ultrapassou o tempo limite de 10s";
      }
      return `[ERRO] ${(err as Error).constructor.name}: ${(err as Error).message}`;
    }
  },
  {
    name: "run_safe_command",
    description:
      "Executa um comando shell de inspeção (ls, pwd, echo, cat). " +
      "Use para inspecionar o sistema de arquivos. " +
      "NÃO executa comandos destrutivos ou fora da lista permitida. " +
      "Retorna stdout do comando ou mensagem de erro.",
    schema: z.object({
      command: z.string().describe("Comando a executar (ex: 'ls /tmp')"),
    }),
  }
);
```

---

## F) Confiabilidade / Anti-Alucinação

### Como validar resultados de tools

- **Sempre retorne contexto suficiente** — em vez de `true`/`false`, retorne `"Arquivo criado em /path/to/file"` ou `"[ERRO] Permissão negada"`
- **Valide o schema de input antes de executar** — Zod faz isso automaticamente; se não usar Zod, valide manualmente
- **Log de tool calls** — registre inputs e outputs para debug posterior

### Quando falta informação

- Se o path não existe: **retorne erro explícito**, não string vazia
- Se o parâmetro está ambíguo: **retorne instrução de como passar corretamente**
- Se a tool depende de serviço externo offline: **informe o status**, não silencie o erro

```typescript
// Retorno informativo em vez de silêncio
const func = async ({ query }: { query: string }): Promise<string> => {
  if (!query.trim()) {
    return "[ERRO] Query vazia. Forneça um termo de busca válido.";
  }
  if (query.length > 500) {
    return "[ERRO] Query muito longa (máx. 500 chars). Resuma a busca.";
  }
  // execução normal...
  return "";
};
```

### Incertezas desta documentação

- A API exata do `deepagents` para registrar tools custom pode variar por versão. **(incerto)** — confirme em `src/server/agent/deep-agent-config.ts` e na documentação do pacote `deepagents`.

---

## G) Analogia

Imagine um chef de cozinha (o LLM) com uma cozinha cheia de utensílios (as tools). O chef não usa as mãos diretamente para cortar, fritar ou medir — ele usa a faca, a frigideira, a colher de pau. Cada utensílio tem uma função específica e um jeito certo de usar. A faca corta; a colher mexe. Se o chef tentar usar a colher para cortar, vai funcionar mal.

Da mesma forma, o LLM decide qual tool usar baseado no nome e na descrição — ele "lê o rótulo do utensílio". Se o rótulo diz "faca — use para cortar legumes", o chef vai usá-la nos momentos certos. Se o rótulo diz apenas "utensílio", o chef vai adivinhar e provavelmente errar. Por isso a descrição é parte do código — não é comentário, é instrução de uso para o modelo.

---

## H) Erros Comuns e Como Evitar

| Erro | Causa | Como evitar |
|---|---|---|
| LLM usa a tool errada | Descrição genérica ou nome confuso | Descreva QUANDO usar e QUANDO NÃO usar |
| Tool quebra o agente | Retorna tipo não-string | Sempre serialize o retorno para `string` |
| Tool trava o event loop | Função síncrona bloqueante em agente async | Use `fs/promises` e APIs async nativas |
| Erro silencioso | Exceção capturada e ignorada | Retorne `[ERRO]` com mensagem no lugar de `undefined` ou `""` |
| Tool com muitos parâmetros | Schema complexo que o LLM não preenche bem | Quebre em duas tools menores |
| Descrição desatualizada | Código mudou mas description não | Trate a descrição como parte do código — atualize junto |
| Tool sem teste | Bug descoberto em produção | Escreva teste unitário antes de registrar no agente |

---

## I) Mini-Template Pronto

```typescript
// ============================================================
// TEMPLATE: Tool com DynamicStructuredTool + Zod
// Copie, renomeie e adapte para sua tool
// Arquivo: src/server/agent/prompts/tools/minha-tool.ts
// ============================================================

import { DynamicStructuredTool } from "@langchain/core/tools";
import { z } from "zod";

const minhaToolSchema = z.object({
  param1: z.string().describe("Descrição do parâmetro 1"),
  param2: z.number().int().optional().describe("Parâmetro opcional"),
});

export const minhaTool = new DynamicStructuredTool({
  name: "minha_tool",
  description:
    "O que esta tool faz em uma frase. " +
    "Use quando [condição específica]. " +
    "NÃO use quando [caso contrário]. " +
    "Retorna [descrição do output].",
  schema: minhaToolSchema,
  func: async ({ param1, param2 }): Promise<string> => {
    try {
      const resultado = `processado: ${param1}${param2 !== undefined ? ` (${param2})` : ""}`;
      return resultado;
    } catch (err: unknown) {
      return `[ERRO] ${(err as Error).constructor.name}: ${(err as Error).message}`;
    }
  },
});

// Uso:
// import { minhaTool } from "./prompts/tools/minha-tool";
// const agent = createDeepAgent({ ..., tools: [minhaTool] });
```
