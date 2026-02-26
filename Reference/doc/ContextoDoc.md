# ContextoDoc

> Camada: 1 — Fundação | Depende de: AgentsDoc | Referenciado por: MemoryDoc, PromptGuide, SystemPromptDoc
> Stack: deepagents · LangGraph · LangChain · Python

---

## A) Visão Geral

- **Contexto** é tudo que o LLM consegue "ver" durante uma execução: mensagens, resultados de tools, system prompt, histórico — tudo junto dentro da janela de tokens.
- A janela de contexto é finita — quando enche, informação é cortada ou o modelo erra por sobrecarga.
- Controlar contexto é a habilidade mais crítica para agentes confiáveis e baratos.
- Existem quatro tipos de conteúdo no contexto: **instrução** (system prompt), **histórico** (mensagens), **evidências** (tool results) e **raciocínio** (thinking/chain-of-thought).
- O OmniMind gerencia contexto via `stream_event_queue.py` e `chat_stream_normalizer.py` — esses arquivos são a implementação real do que este doc descreve.
- Estratégias de controle: summarização, sliding window, seleção por relevância, compressão de tool results.

---

## B) Conceitos Essenciais

| Termo | Definição |
|---|---|
| **Janela de contexto** | Número máximo de tokens que o modelo processa de uma vez (ex: 200k para Claude, 128k para GPT-4) |
| **Token** | Unidade de texto que o modelo processa (~0.75 palavras em inglês, ~0.5 em português) |
| **Context window overflow** | Quando o total de tokens excede o limite — causa erro ou truncamento silencioso |
| **Sliding window** | Estratégia de manter apenas as N mensagens mais recentes no contexto |
| **Summarization** | Comprimir mensagens antigas em um resumo curto antes de removê-las do contexto |
| **Relevance filtering** | Selecionar apenas as partes do histórico relevantes para a pergunta atual |
| **Tool result compression** | Truncar ou resumir resultados de tools que são muito longos |
| **System prompt tokens** | Tokens consumidos pelo system prompt — ficam no contexto em TODAS as mensagens |
| **Thinking tokens** | Tokens usados para raciocínio interno (chain-of-thought) — visíveis no stream mas não enviados de volta ao modelo em todos os casos |
| **StreamEvent** | Evento emitido pelo OmniMind durante execução — contém type, data, mode, meta |

---

## C) Boas Práticas

### DO ✅

- **Monitore o tamanho do contexto** — conte tokens antes de enviar (use `tiktoken` para OpenAI, `anthropic.count_tokens` para Claude)
- **Comprima tool results longos** — se uma tool retorna 10.000 tokens, resuma para os 500 mais relevantes antes de inserir no contexto
- **Use sliding window para chats longos** — mantenha as últimas 10–20 mensagens + um resumo das anteriores
- **Separe raciocínio de resposta** — thinking tokens não precisam voltar para o contexto nas iterações seguintes
- **Priorize o system prompt enxuto** — cada token no system prompt é cobrado em TODAS as mensagens
- **Filtre tool results irrelevantes** — se a tool retornou 50 resultados mas apenas 3 importam, passe só os 3

### DON'T ❌

- **Não insira tool results crus no contexto** — um resultado de busca web de 20.000 tokens vai explodir a janela
- **Não acumule histórico indefinidamente** — sem estratégia de sliding window, o agente vai falhar em conversas longas
- **Não repita o system prompt dentro do histórico** — já está no início, não precisa estar em cada mensagem
- **Não ignore erros de context overflow** — eles causam comportamento imprevisível, não apenas lentidão
- **Não use modelos com janela pequena para tarefas de código** — código é verboso em tokens

---

## D) Receitas Reutilizáveis

### Checklist de controle de contexto

- [ ] Calcule os tokens do system prompt (deve ser < 20% da janela total)
- [ ] Defina estratégia para histórico: sliding window (N mensagens) ou summarização
- [ ] Comprima tool results acima de 2.000 tokens antes de inserir
- [ ] Monitore uso de tokens em produção (log por request)
- [ ] Teste com conversas longas (50+ mensagens) para verificar comportamento
- [ ] Configure `recursion_limit` para limitar também o volume de tool calls por sessão

### Estratégias de compressão (ordem de preferência)

```
1. Truncar com aviso     → "... [resultado truncado após 500 chars] ..."
2. Resumir com LLM       → peça ao modelo para resumir antes de inserir
3. Extrair campos chave  → de um JSON de 5000 tokens, extraia só os 3 campos relevantes
4. Sliding window        → remove mensagens antigas, mantém resumo
5. Relevance filter      → embeddings para selecionar trechos mais próximos da query
```

### Cálculo de tokens (aproximação rápida)

```python
# Aproximação: 1 token ≈ 4 caracteres em inglês, ≈ 3 em português
def estimate_tokens(text: str, lang: str = "pt") -> int:
    chars_per_token = 3 if lang == "pt" else 4
    return len(text) // chars_per_token

# Para contar exato com anthropic:
# client.count_tokens(text)  → retorna int

# Para contar exato com OpenAI/tiktoken:
# import tiktoken
# enc = tiktoken.encoding_for_model("gpt-4")
# len(enc.encode(text))
```

---

## E) Exemplos Práticos

### Exemplo 1 — Sliding window simples

```python
from langchain_core.messages import BaseMessage, SystemMessage
from typing import List

def apply_sliding_window(
    messages: List[BaseMessage],
    max_messages: int = 20,
    system_prompt: str = "",
) -> List[BaseMessage]:
    """
    Mantém apenas as últimas `max_messages` mensagens do histórico.
    System prompt é sempre preservado.
    """
    if len(messages) <= max_messages:
        return messages

    recent = messages[-max_messages:]

    # Adiciona aviso de que histórico foi truncado
    truncation_note = SystemMessage(
        content=f"[Contexto: {len(messages) - max_messages} mensagens anteriores foram removidas para manter o contexto gerenciável.]"
    )

    return [truncation_note] + recent
```

---

### Exemplo 2 — Compressão de tool result longo

```python
def compress_tool_result(result: str, max_chars: int = 2000) -> str:
    """
    Trunca tool results longos com aviso explícito.
    Use antes de inserir resultados de busca, leitura de arquivos grandes, etc.
    """
    if len(result) <= max_chars:
        return result

    truncated = result[:max_chars]
    original_len = len(result)

    return (
        f"{truncated}\n\n"
        f"... [RESULTADO TRUNCADO: {original_len} chars totais, "
        f"exibindo primeiros {max_chars}. "
        f"Se precisar de mais, use uma query mais específica.]"
    )
```

---

### Exemplo 3 — Como o OmniMind emite eventos de contexto

```python
# stream_event_queue.py e chat_stream_normalizer.py fazem isso internamente
# Este é o padrão de StreamEvent do projeto (ver types.py)

from omnimind_agents.types import StreamEvent

# Evento de pensamento (não retorna pro contexto do LLM nas iterações)
thought_event = StreamEvent(
    id="evt-001",
    seq=1,
    type="thought",        # raciocínio interno
    mode="messages",
    data="Vou verificar o arquivo antes de editar.",
    meta={"agent_id": "omnimind-agent"},
)

# Evento de tool call (vai pro contexto como "o agente fez X")
tool_call_event = StreamEvent(
    id="evt-002",
    seq=2,
    type="tool_call",
    mode="updates",
    data='{"tool": "read_file", "args": {"path": "src/main.py"}}',
    meta={"tool_name": "read_file"},
)

# Evento de resposta final (vai pro contexto como resposta do assistente)
response_event = StreamEvent(
    id="evt-003",
    seq=3,
    type="response",
    mode="messages",
    data="O arquivo tem 200 linhas. Aqui está o resumo...",
    meta={},
)
```

---

### Exemplo 4 (RUIM → CORRIGIDO)

```python
# ❌ RUIM — insere resultado bruto de busca no contexto

@tool
def search_docs(query: str) -> str:
    """Busca na documentação."""
    results = search_engine.search(query)
    # Retorna TUDO — pode ser 50.000 tokens
    return json.dumps(results, indent=2)
```

```python
# ✅ CORRIGIDO — filtra e comprime antes de retornar

@tool
def search_docs(query: str) -> str:
    """Busca na documentação. Retorna os 3 resultados mais relevantes,
    com título, URL e trecho de 200 chars cada.
    """
    results = search_engine.search(query, max_results=10)

    # Filtra os 3 mais relevantes por score
    top3 = sorted(results, key=lambda r: r["score"], reverse=True)[:3]

    output = []
    for r in top3:
        snippet = r["content"][:200] + "..." if len(r["content"]) > 200 else r["content"]
        output.append(f"**{r['title']}** ({r['url']})\n{snippet}")

    return "\n\n".join(output) if output else "[Nenhum resultado encontrado]"
```

---

## F) Confiabilidade / Anti-Alucinação

### Como detectar problemas de contexto

- **O agente "esquece" coisas ditas no início da conversa** → janela de tokens muito curta ou sliding window muito agressiva
- **O agente começa a alucinar fatos** → contexto sobrecarregado, modelo começa a preencher lacunas
- **Erros de `context_length_exceeded`** → overflow — reduza histórico ou comprima tool results
- **Respostas ficam genéricas no meio da conversa longa** → modelo perdeu o fio após compressão ruim

### Como validar

```python
# Monitore o uso de tokens por request
import anthropic

client = anthropic.Anthropic()
# Após cada invoke, verifique usage:
# response.usage.input_tokens   → tokens enviados
# response.usage.output_tokens  → tokens gerados
# Alerte se input_tokens > 80% da janela do modelo
```

### Quando perguntar vs assumir

- Se o contexto foi truncado e a informação pode estar ausente: **o agente deve perguntar** ("Não encontrei X no contexto. Você pode fornecer?")
- Se o resultado de tool está truncado: **o agente deve informar** ("O arquivo é grande, vi apenas os primeiros 2000 chars. Quer que eu continue?")

---

## G) Analogia

Imagine que o LLM é um detetive com uma **mesa de trabalho de tamanho fixo**. Ele só consegue analisar o que está na mesa — não consegue ver o que está no arquivo ou no gaveta. Cada nova pista (tool result), mensagem ou instrução ocupa espaço na mesa. Quando a mesa enche, você precisa tirar coisas antigas para colocar as novas.

Controlar o contexto é decidir **o que fica na mesa**. Deixar tudo lá é tentador, mas em pouco tempo a mesa fica tão bagunçada que o detetive não consegue mais raciocinar com clareza. A arte está em manter na mesa apenas o que é relevante para o caso atual — e guardar o resto em um resumo organizado na gaveta (memória persistente).

---

## H) Erros Comuns e Como Evitar

| Erro | Causa | Como evitar |
|---|---|---|
| Context overflow em produção | Tool results crus + histórico longo | Comprima tool results, use sliding window |
| Agente "esquece" instruções | System prompt muito longo empurra histórico para fora | Enxugue o system prompt; mova instruções pouco usadas para tool descriptions |
| Alucinação em conversas longas | Janela cheia, modelo preenche lacunas | Adicione summarização ou relevance filtering |
| Custo explodindo | Contexto grande em cada request | Monitore tokens por request; aplique compressão |
| Truncamento silencioso | Alguns providers truncam sem avisar | Conte tokens antes de enviar; valide que input < 90% do limite |
| Thinking tokens não gerenciados | Raciocínio interno acumula no contexto | Configure corretamente o stream_mode; separe thinking de history |

---

## I) Mini-Template Pronto

```python
# ============================================================
# TEMPLATE: Gerenciador de contexto para agentes OmniMind
# ============================================================

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from typing import List

# --- Constantes ---
MAX_HISTORY_MESSAGES = 20      # mensagens recentes a manter
MAX_TOOL_RESULT_CHARS = 2000   # chars máx por tool result
CONTEXT_WARNING_THRESHOLD = 0.8  # alerta se > 80% da janela usada

# --- Sliding window ---
def trim_history(messages: List[BaseMessage], max_msgs: int = MAX_HISTORY_MESSAGES) -> List[BaseMessage]:
    """Mantém as últimas `max_msgs` mensagens. Preserva SystemMessage."""
    system = [m for m in messages if isinstance(m, SystemMessage)]
    others = [m for m in messages if not isinstance(m, SystemMessage)]

    if len(others) > max_msgs:
        note = SystemMessage(content=f"[{len(others) - max_msgs} mensagens anteriores omitidas]")
        others = [note] + others[-max_msgs:]

    return system + others

# --- Compressão de tool result ---
def compress_result(result: str, max_chars: int = MAX_TOOL_RESULT_CHARS) -> str:
    """Trunca resultado longo com aviso."""
    if len(result) <= max_chars:
        return result
    return result[:max_chars] + f"\n... [truncado: {len(result)} chars totais, exibindo {max_chars}]"

# --- Estimativa de tokens ---
def estimate_tokens_pt(text: str) -> int:
    """Estimativa rápida para português (~3 chars/token)."""
    return len(text) // 3

# Uso no pipeline:
# messages = trim_history(state["messages"])
# tool_output = compress_result(raw_tool_output)
# tokens_used = estimate_tokens_pt(str(messages))
```
