# SkillsDoc

> Camada: 3 — Qualidade | Depende de: AgentsDoc, ToolsDoc | Referenciado por: OrquestradorDoc
> Stack: deepagents · LangGraph · LangChain · Python

---

## A) Visão Geral

- Uma **skill** é uma capacidade reutilizável de nível mais alto que uma tool, mas mais simples que um agente completo — é um workflow encapsulado com checklist, lógica de execução e output bem definido.
- Skills são invocáveis por agentes, por humanos (via slash command `/skill-name`), ou por outros agentes como se fossem tools especializadas.
- A diferença prática: uma **tool** faz uma ação atômica (ler arquivo), uma **skill** orquestra múltiplas ações para atingir um objetivo (fazer um commit bem formado = verificar diff + escrever mensagem + executar git).
- Skills são **compostas** — uma skill pode usar tools e outras skills.
- O sistema de skills do OmniMind (Claude Code) usa arquivos Markdown com instruções para o LLM — não são código Python puro, são prompts estruturados.
- Para o OmniMind em Python, skills podem ser implementadas como **funções de alto nível**, **grafos LangGraph**, ou **prompts estruturados** que o agente segue.

---

## B) Conceitos Essenciais

| Termo | Definição |
|---|---|
| **Skill** | Workflow reutilizável com propósito definido, checklist de execução e output esperado |
| **Tool** | Ação atômica — faz uma coisa específica e retorna resultado |
| **Agente** | Loop completo de raciocínio + tools — pode lidar com qualquer tarefa do domínio |
| **Skill trigger** | Condição ou comando que ativa a skill — slash command, evento, ou chamada direta |
| **Skill checklist** | Lista de passos que a skill executa em ordem — define o workflow |
| **Skill output** | O que a skill retorna ao chamador — pode ser texto, JSON, artefato |
| **Composite skill** | Skill que invoca outras skills como parte do seu workflow |
| **Skill prompt** | Prompt estruturado que instrui o agente a executar a skill (padrão Claude Code) |
| **Rigid skill** | Skill com checklist obrigatório — deve ser seguida exatamente (ex: TDD, commit) |
| **Flexible skill** | Skill com diretrizes — pode ser adaptada ao contexto (ex: code review, design) |

---

## C) Boas Práticas

### DO ✅

- **Defina o trigger claramente** — quando esta skill deve ser invocada?
- **Crie checklist de passos** — o agente segue a skill como uma receita
- **Defina o output esperado** — o que o chamador recebe de volta?
- **Marque como rigid ou flexible** — o agente precisa saber se pode adaptar
- **Use skills para workflows repetitivos** — qualquer coisa que você faz sempre da mesma forma é candidata
- **Documente edge cases** — o que fazer se um passo falha?
- **Teste a skill isoladamente** — invoque como usuário faria antes de integrar

### DON'T ❌

- **Não crie skill para ação única** — use tool diretamente
- **Não crie skill sem output definido** — o chamador precisa saber o que esperar
- **Não crie skills genéricas demais** — "fazer o trabalho bem" não é uma skill
- **Não anninhe skills demais** — skill → skill → skill → skill dificulta debug
- **Não misture skills rígidas com flexíveis** — defina claramente qual é qual

---

## D) Receitas Reutilizáveis

### Checklist para criar uma skill

- [ ] Nome e propósito definidos (1 frase)
- [ ] Trigger definido (quando invocar)
- [ ] Tipo definido: rigid (seguir exatamente) ou flexible (adaptar ao contexto)
- [ ] Checklist de passos (em ordem)
- [ ] Output esperado definido
- [ ] Comportamento em caso de falha de passo
- [ ] Dependências listadas (tools, outras skills)
- [ ] Exemplo de uso completo

### Estrutura de uma skill (padrão Markdown para LLM)

```markdown
# NomeDaSkill

## Quando usar
[Condição de invocação]

## Tipo
Rigid | Flexible

## Checklist
- [ ] Passo 1: [descrição]
- [ ] Passo 2: [descrição]
- [ ] Passo 3: [descrição]

## Output
[O que retornar ao chamador]

## Em caso de falha
[O que fazer se um passo falha]
```

---

## E) Exemplos Práticos

### Exemplo 1 — Skill de commit (rigid)

```python
# Implementação Python de uma skill rigid
# O agente SEMPRE segue esses passos — sem adaptação

COMMIT_SKILL_PROMPT = """
# Skill: commit

## Quando usar
Quando o usuário pede para fazer commit das mudanças.

## Tipo
RIGID — siga exatamente estes passos, sem pular nenhum.

## Checklist obrigatório
- [ ] Passo 1: Execute `git status` — liste arquivos modificados
- [ ] Passo 2: Execute `git diff --staged` — veja o que já está staged
- [ ] Passo 3: Se nada staged, execute `git diff` — veja mudanças unstaged
- [ ] Passo 4: Analise as mudanças e escreva a mensagem de commit
  - Formato: `tipo: descrição curta`
  - Tipos: feat, fix, docs, refactor, test, chore
  - Máximo 72 chars na primeira linha
- [ ] Passo 5: Execute `git add [arquivos relevantes]` — NUNCA `git add .` sem revisão
- [ ] Passo 6: Execute `git commit -m "mensagem"`
- [ ] Passo 7: Confirme com `git status` — working tree deve estar clean

## Output
Retorne: "Commit realizado: [hash] — [mensagem]"

## Em caso de falha
- Se `git commit` falhar por hook: analise o erro, corrija o problema, tente novamente
- Nunca use `--no-verify` sem aprovação explícita do usuário
- Se não souber corrigir o erro, reporte ao usuário e aguarde instrução
"""
```

---

### Exemplo 2 — Skill de debug (flexible)

```python
DEBUGGING_SKILL_PROMPT = """
# Skill: systematic-debugging

## Quando usar
Ao encontrar qualquer bug, falha de teste ou comportamento inesperado.

## Tipo
FLEXIBLE — adapte ao contexto, mas siga a estrutura geral.

## Processo
1. REPRODUZIR: Confirme que consegue reproduzir o problema
2. ISOLAR: Identifique o menor caso que reproduz o bug
3. HIPÓTESE: Liste 2-3 causas possíveis, da mais para a menos provável
4. INVESTIGAR: Teste cada hipótese com evidências (logs, testes, leitura de código)
5. CORRIGIR: Implemente a correção mínima que resolve o problema
6. VERIFICAR: Confirme que o bug foi corrigido e nenhuma regressão foi introduzida

## Saída esperada
- Causa raiz identificada (não apenas o sintoma)
- Correção implementada
- Teste que previne regressão

## Quando escalar
Se após 3 hipóteses investigadas não encontrou a causa: reportar ao usuário com evidências coletadas.
"""
```

---

### Exemplo 3 — Skill como função Python (composite)

```python
# Skill de code review composta — usa múltiplas ferramentas

import asyncio
from langchain_core.tools import tool
from omnimind_agents import get_model_for_provider
from omnimind_agents.deep_agent_config import create_omnimind_deep_agent

async def code_review_skill(code: str, context: str = "") -> dict:
    """
    Skill: code-review
    Tipo: Flexible
    Passos: análise de segurança + análise de qualidade + sugestões de melhoria
    Output: dict com issues categorizados e score
    """
    model = get_model_for_provider("anthropic", "claude-haiku-4-5-20251001")

    # Passo 1: análise de segurança
    security_agent = create_omnimind_deep_agent(
        model=model,
        system_prompt="Analise vulnerabilidades de segurança. Retorne bullets com [SEVERITY]: issue.",
    )

    # Passo 2: análise de qualidade
    quality_agent = create_omnimind_deep_agent(
        model=model,
        system_prompt="Analise qualidade de código (legibilidade, SOLID, DRY). Retorne bullets.",
    )

    # Executa em paralelo (fan-out)
    input_msg = {"messages": [{"role": "user", "content": f"```\n{code}\n```\nContexto: {context}"}]}
    config = {"recursion_limit": 8}

    security_result, quality_result = await asyncio.gather(
        security_agent.ainvoke(input_msg, config=config),
        quality_agent.ainvoke(input_msg, config=config),
        return_exceptions=True,
    )

    def extract(r) -> str:
        if isinstance(r, Exception):
            return f"[ERRO] {r}"
        return r["messages"][-1].content

    # Passo 3: consolida (fan-in)
    return {
        "security": extract(security_result),
        "quality": extract(quality_result),
        "approved": "HIGH" not in extract(security_result),
    }
```

---

### Exemplo 4 (RUIM → CORRIGIDO)

```python
# ❌ RUIM — "skill" que é só uma tool com nome fancy

@tool
def do_code_review(code: str) -> str:
    """Faz code review."""
    # Chama LLM direto sem processo definido
    result = model.invoke(f"Review this: {code}")
    return result.content
```

**Problemas:**
1. Sem processo definido — cada execução é diferente
2. Sem categorização de output — caller não sabe o que esperar
3. Sem critérios claros — o que é "aprovado"?
4. Deveria ser skill (múltiplos passos), não tool (ação atômica)

```python
# ✅ CORRIGIDO — skill com processo claro e output estruturado

async def code_review_skill(code: str) -> dict:
    """
    Skill: code-review (Flexible)

    Processo:
    1. Análise de segurança (vulnerabilidades OWASP)
    2. Análise de qualidade (legibilidade, manutenibilidade)
    3. Consolidação com score e decisão

    Output: {"security_issues": list, "quality_issues": list, "score": 1-5, "approved": bool}
    """
    security_issues = await analyze_security(code)    # step 1
    quality_issues = await analyze_quality(code)      # step 2

    high_severity = any("HIGH" in i for i in security_issues)
    score = 5 - len(security_issues) - (len(quality_issues) // 2)
    score = max(1, min(5, score))

    return {
        "security_issues": security_issues,
        "quality_issues": quality_issues,
        "score": score,
        "approved": not high_severity and score >= 3,
    }
```

---

## F) Confiabilidade / Anti-Alucinação

### Como validar skills

- **Teste o checklist passo a passo** — execute cada passo isoladamente antes de juntar
- **Valide o output** — skills com output estruturado devem sempre retornar o schema esperado
- **Teste casos de falha** — o que acontece se o passo 2 falha? A skill trata corretamente?
- **Skills rigid devem ser determinísticas** — mesmo input = mesmo processo = mesmo tipo de output

### Quando perguntar vs assumir

- Se o trigger é ambíguo: a skill deve perguntar antes de executar ("Você quer fazer commit de todos os arquivos ou só os staged?")
- Se um passo falha de forma irrecuperável: a skill deve reportar ao chamador, não inventar um resultado

---

## G) Analogia

Uma skill é como um **procedimento operacional padrão (POP)** de uma empresa. Não importa qual funcionário executa — o resultado deve ser consistente porque o processo está documentado passo a passo.

A diferença de uma tool é que um POP tem múltiplos passos com decisões intermediárias. A diferença de um agente completo é que o POP tem um escopo fixo — ele não improvisa, não decide fazer coisas fora do escopo, e tem um output previsível. Você sabe o que vai receber quando invocar.

Uma skill rigid é como o checklist de decolagem de um avião — nenhum passo pode ser pulado. Uma skill flexible é como um roteiro de reunião — você segue a estrutura mas adapta ao contexto.

---

## H) Erros Comuns e Como Evitar

| Erro | Causa | Como evitar |
|---|---|---|
| Skill sem output definido | Foco só no processo, não no resultado | Defina o schema de output antes de implementar |
| Skill muito genérica | Escopo não definido | "O que exatamente esta skill faz e não faz?" |
| Checklist não seguido | Skill não marcada como rigid/flexible | Marque explicitamente e instrua o agente |
| Skill duplica lógica de tool | Falta de clareza entre skill e tool | Skill = workflow multi-passo; tool = ação atômica |
| Debug impossível | Skill composite sem logging por passo | Adicione logging em cada passo da skill |
| Skill não reutilizável | Hardcoded para contexto específico | Parametrize o que varia (model, config, etc.) |

---

## I) Mini-Template Pronto

```python
# ============================================================
# TEMPLATE: Skill como função Python
# ============================================================

from typing import TypedDict

class MinhaSkillOutput(TypedDict):
    """Schema de output da skill — sempre retornar este formato."""
    resultado: str
    sucesso: bool
    detalhes: list[str]
    proximo_passo: str | None


async def minha_skill(
    input_principal: str,
    contexto: str = "",
) -> MinhaSkillOutput:
    """
    Skill: [NOME DA SKILL]
    Tipo: Rigid | Flexible
    Trigger: [quando invocar]

    Processo:
    1. [Passo 1 — o que faz]
    2. [Passo 2 — o que faz]
    3. [Passo 3 — consolida]
    """

    detalhes = []

    # Passo 1
    try:
        resultado_passo1 = await _executar_passo1(input_principal)
        detalhes.append(f"Passo 1 concluído: {resultado_passo1[:50]}...")
    except Exception as e:
        return MinhaSkillOutput(
            resultado="",
            sucesso=False,
            detalhes=[f"Falha no passo 1: {e}"],
            proximo_passo="Verificar [o que verificar] e tentar novamente",
        )

    # Passo 2
    try:
        resultado_passo2 = await _executar_passo2(resultado_passo1, contexto)
        detalhes.append(f"Passo 2 concluído: {resultado_passo2[:50]}...")
    except Exception as e:
        return MinhaSkillOutput(
            resultado=resultado_passo1,
            sucesso=False,
            detalhes=detalhes + [f"Falha no passo 2: {e}"],
            proximo_passo="Passo 1 OK. Verificar passo 2.",
        )

    # Passo 3 — consolida
    resultado_final = f"{resultado_passo1}\n{resultado_passo2}"

    return MinhaSkillOutput(
        resultado=resultado_final,
        sucesso=True,
        detalhes=detalhes,
        proximo_passo=None,
    )
```

```markdown
<!-- ============================================================ -->
<!-- TEMPLATE: Skill como prompt Markdown (padrão Claude Code)   -->
<!-- ============================================================ -->

# NomeDaSkill

## Quando usar
[Condição específica que dispara esta skill]

## Tipo
Rigid

## Checklist
- [ ] Passo 1: [ação concreta com tool/comando específico]
- [ ] Passo 2: [ação concreta]
- [ ] Passo 3: [consolidação / output]

## Output esperado
[Descrição do que retornar]

## Em caso de falha em qualquer passo
[O que fazer]

## Dependências
- Tools: [lista de tools necessárias]
- Skills: [lista de skills que esta invoca, se houver]
```
