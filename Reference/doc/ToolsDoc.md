# ToolsDoc

> Camada: 1 — Fundação | Depende de: — | Referenciado por: AgentsDoc, SubAgentsDoc, OrquestradorDoc
> Stack: deepagents · LangGraph · LangChain · Python

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
| **Schema** | Estrutura de dados que define quais parâmetros a tool aceita (geralmente Pydantic) |
| **Tool call** | Quando o LLM decide invocar uma tool e gera os argumentos no formato esperado |
| **Tool result** | O que a tool retorna após execução — vai de volta para o LLM como contexto |
| **@tool decorator** | Forma mais simples de criar uma tool no LangChain — decora uma função Python |
| **BaseTool** | Classe base do LangChain para tools mais complexas com estado ou lógica extra |
| **StructuredTool** | Tool LangChain que aceita schema Pydantic explícito para validação de input |
| **args_schema** | Atributo que define o schema Pydantic da tool (usado em BaseTool e StructuredTool) |
| **Tool síncrona** | Tool que retorna um valor direto (`_run`) |
| **Tool assíncrona** | Tool que retorna uma coroutine (`_arun`) — necessária em agentes async |

---

## C) Boas Práticas

### DO ✅

- **Nomes descritivos e únicos** — `read_file` é melhor que `get` ou `file_tool`
- **Descrição explica QUANDO usar** — "Use esta tool para ler o conteúdo de um arquivo local. NÃO use para URLs."
- **Um único propósito por tool** — se a tool faz A e B, separe em duas
- **Validação de input com Pydantic** — evita que o LLM passe tipos errados
- **Retorno sempre string ou objeto serializável** — o LLM recebe o resultado como texto
- **Erro explícito com mensagem útil** — `return "[ERRO] Arquivo não encontrado: {path}"` é melhor que retornar None
- **Implementar `_arun` quando o agente é async** — evitar bloqueios no event loop
- **Documentar casos de borda na descrição** — "retorna string vazia se o arquivo estiver vazio"

### DON'T ❌

- **Não crie tools com efeitos colaterais silenciosos** — se deletar algo, avise na descrição
- **Não use nomes genéricos** — `tool1`, `helper`, `do_thing` confundem o LLM
- **Não retorne objetos Python complexos** — o LLM não consegue interpretar; serialize para string/JSON
- **Não faça a tool "inteligente"** — lógica de decisão fica no agente, não na tool
- **Não ignore erros** — retornar resultado vazio sem avisar causa alucinações
- **Não crie uma tool para tudo** — tools demais sobrecarregam o contexto do LLM

---

## D) Receitas Reutilizáveis

### Checklist para criar uma nova tool

- [ ] Nome único e descritivo (snake_case)
- [ ] Descrição explica: o que faz, quando usar, quando NÃO usar
- [ ] Schema Pydantic com tipos e descrições em todos os campos
- [ ] Retorno sempre serializável (str, dict, list)
- [ ] Tratamento de erro com mensagem clara
- [ ] Versão async (`_arun`) se o agente usar asyncio
- [ ] Teste unitário que valida input, output e comportamento de erro
- [ ] Registrada no agente/runtime correto

### Passos para criar uma tool com `@tool`

```
1. Definir a função com type hints
2. Adicionar docstring — ela vira a descrição da tool
3. Decorar com @tool
4. Registrar na lista de tools do agente
```

### Passos para criar uma tool com `BaseTool`

```
1. Criar classe que herda de BaseTool
2. Definir name (str) e description (str)
3. Criar classe Pydantic para args_schema
4. Implementar _run(self, **kwargs) -> str
5. Implementar _arun(self, **kwargs) -> str (se async)
6. Registrar no agente
```

---

## E) Exemplos Práticos

### Exemplo 1 — Tool simples com @tool (LangChain)

```python
from langchain_core.tools import tool

@tool
def read_file(path: str) -> str:
    """Lê o conteúdo de um arquivo local e retorna como string.
    Use quando o agente precisar inspecionar o conteúdo de um arquivo.
    NÃO use para URLs ou arquivos remotos.
    Retorna mensagem de erro se o arquivo não existir.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"[ERRO] Arquivo não encontrado: {path}"
    except Exception as e:
        return f"[ERRO] Falha ao ler arquivo: {e}"
```

---

### Exemplo 2 — Tool estruturada com BaseTool + Pydantic (LangChain)

```python
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

class SearchWebInput(BaseModel):
    query: str = Field(description="Termo de busca em linguagem natural")
    max_results: int = Field(default=5, description="Número máximo de resultados (1–10)")

class SearchWebTool(BaseTool):
    name: str = "search_web"
    description: str = (
        "Busca informações na web usando uma query em linguagem natural. "
        "Use quando precisar de informações atuais ou externas ao contexto. "
        "NÃO use para arquivos locais."
    )
    args_schema: Type[BaseModel] = SearchWebInput

    def _run(self, query: str, max_results: int = 5) -> str:
        # integração real aqui (ex: Tavily, SerpAPI)
        # results = tavily_client.search(query, max_results=max_results)
        raise NotImplementedError("Implemente com seu provider de busca")

    async def _arun(self, query: str, max_results: int = 5) -> str:
        # versão async para agentes assíncronos
        raise NotImplementedError("Implemente com seu provider de busca async")
```

---

### Exemplo 3 — Tool com deepagents

```python
# deepagents usa tools compatíveis com LangChain
# A diferença está em como elas são registradas no backend

from deepagents import create_deep_agent
from langchain_core.tools import tool
import os

@tool
def list_directory(path: str) -> str:
    """Lista arquivos e pastas em um diretório.
    Retorna uma lista formatada. Use '.' para o diretório atual.
    Retorna mensagem de erro se o diretório não existir.
    """
    try:
        entries = os.listdir(path)
        return "\n".join(entries) if entries else "[vazio]"
    except FileNotFoundError:
        return f"[ERRO] Diretório não encontrado: {path}"

# Registrando no agente deepagents
agent = create_deep_agent(
    model=model,
    system_prompt="Você é um assistente de filesystem.",
    tools=[list_directory],  # tools LangChain funcionam direto
    name="fs-agent",
)
```

---

### Exemplo 4 (RUIM → CORRIGIDO)

```python
# ❌ RUIM — vários problemas

@tool
def do_stuff(input: str) -> str:
    """Faz coisas."""        # descrição inútil — LLM não sabe quando usar
    import subprocess
    result = subprocess.run(input, shell=True)  # executa qualquer coisa
    return result.returncode  # retorna int, não string!
```

**Problemas:**
1. Nome genérico — LLM não sabe quando usar
2. Descrição vazia — LLM não sabe o que faz
3. `shell=True` com input livre — risco de injeção de comandos
4. Retorna `int` em vez de `str` — quebra o pipeline

```python
# ✅ CORRIGIDO

import subprocess
import shlex
from langchain_core.tools import tool

ALLOWED_COMMANDS = frozenset(["ls", "pwd", "echo", "cat"])

@tool
def run_safe_command(command: str) -> str:
    """Executa um comando shell de inspeção (ls, pwd, echo, cat).
    Use para inspecionar o sistema de arquivos.
    NÃO executa comandos destrutivos ou fora da lista permitida.
    Retorna stdout do comando ou mensagem de erro.
    """
    parts = shlex.split(command)
    if not parts:
        return "[ERRO] Comando vazio."
    if parts[0] not in ALLOWED_COMMANDS:
        return f"[ERRO] Comando '{parts[0]}' não permitido. Permitidos: {sorted(ALLOWED_COMMANDS)}"
    try:
        result = subprocess.run(parts, capture_output=True, text=True, timeout=10)
        return result.stdout or result.stderr or "[sem output]"
    except subprocess.TimeoutExpired:
        return "[ERRO] Comando ultrapassou o tempo limite de 10s"
    except Exception as e:
        return f"[ERRO] {type(e).__name__}: {e}"
```

---

## F) Confiabilidade / Anti-Alucinação

### Como validar resultados de tools

- **Sempre retorne contexto suficiente** — em vez de `True`/`False`, retorne `"Arquivo criado em /path/to/file"` ou `"[ERRO] Permissão negada"`
- **Valide o schema de input antes de executar** — Pydantic faz isso automaticamente; se não usar Pydantic, valide manualmente
- **Log de tool calls** — registre inputs e outputs para debug posterior

### Quando falta informação

- Se o path não existe: **retorne erro explícito**, não string vazia
- Se o parâmetro está ambíguo: **retorne instrução de como passar corretamente**
- Se a tool depende de serviço externo offline: **informe o status**, não silencie o erro

```python
# Retorno informativo em vez de silêncio
def _run(self, query: str) -> str:
    if not query.strip():
        return "[ERRO] Query vazia. Forneça um termo de busca válido."
    if len(query) > 500:
        return "[ERRO] Query muito longa (máx. 500 chars). Resuma a busca."
    # execução normal...
```

### Incertezas desta documentação

- A API exata do `deepagents` para registrar tools custom pode variar por versão. **(incerto)** — confirme em `python/omnimind_agents/deep_agent_config.py` e na documentação do pacote `deepagents`.

---

## G) Analogia

Imagine um chef de cozinha (o LLM) com uma cozinha cheia de utensílios (as tools). O chef não usa as mãos diretamente para cortar, fritar ou medir — ele usa a faca, a frigideira, a colher de pau. Cada utensílio tem uma função específica e um jeito certo de usar. A faca corta; a colher mexe. Se o chef tentar usar a colher para cortar, vai funcionar mal.

Da mesma forma, o LLM decide qual tool usar baseado no nome e na descrição — ele "lê o rótulo do utensílio". Se o rótulo diz "faca — use para cortar legumes", o chef vai usá-la nos momentos certos. Se o rótulo diz apenas "utensílio", o chef vai adivinhar e provavelmente errar. Por isso a descrição é parte do código — não é comentário, é instrução de uso para o modelo.

---

## H) Erros Comuns e Como Evitar

| Erro | Causa | Como evitar |
|---|---|---|
| LLM usa a tool errada | Descrição genérica ou nome confuso | Descreva QUANDO usar e QUANDO NÃO usar |
| Tool quebra o agente | Retorna tipo não-string | Sempre serialize o retorno para `str` |
| Tool trava o event loop | `_run` faz I/O bloqueante em agente async | Implemente `_arun` com `await` |
| Erro silencioso | Exceção capturada e ignorada | Retorne `[ERRO]` com mensagem no lugar de `None` ou `""` |
| Tool com muitos parâmetros | Schema complexo que o LLM não preenche bem | Quebre em duas tools menores |
| Descrição desatualizada | Código mudou mas docstring não | Trate a descrição como parte do código — atualize junto |
| Tool sem teste | Bug descoberto em produção | Escreva teste unitário antes de registrar no agente |

---

## I) Mini-Template Pronto

```python
# ============================================================
# TEMPLATE: Tool com BaseTool + Pydantic
# Copie, renomeie e adapte para sua tool
# ============================================================

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional


class MinhaToolInput(BaseModel):
    """Schema de input da tool. Adicione os campos necessários."""
    param1: str = Field(description="Descrição do parâmetro 1")
    param2: Optional[int] = Field(default=None, description="Parâmetro opcional")


class MinhaTool(BaseTool):
    name: str = "minha_tool"
    description: str = (
        "O que esta tool faz em uma frase. "
        "Use quando [condição específica]. "
        "NÃO use quando [caso contrário]. "
        "Retorna [descrição do output]."
    )
    args_schema: Type[BaseModel] = MinhaToolInput

    def _run(self, param1: str, param2: Optional[int] = None) -> str:
        """Implementação síncrona."""
        try:
            resultado = f"processado: {param1}"
            return resultado
        except Exception as e:
            return f"[ERRO] {type(e).__name__}: {e}"

    async def _arun(self, param1: str, param2: Optional[int] = None) -> str:
        """Implementação assíncrona (necessária para agentes async)."""
        try:
            resultado = f"processado async: {param1}"
            return resultado
        except Exception as e:
            return f"[ERRO] {type(e).__name__}: {e}"


# Uso:
# tool = MinhaTool()
# agent = create_deep_agent(..., tools=[tool])
```
