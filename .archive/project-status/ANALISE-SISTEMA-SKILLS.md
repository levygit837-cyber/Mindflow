# Análise e Planejamento: Integração do Sistema de Skills em Markdown no MindFlow

## 1. Análise do Sistema de Skills do Claude Code
O Claude Code utiliza um sistema de skills baseado fortemente em arquivos Markdown (`SKILL.md`), permitindo que usuários adicionem novas capacidades ao agente apenas escrevendo texto e configurações simples, sem necessidade de codificar em TypeScript.

### Características principais (baseado em `loadSkillsDir.ts`):
- **Estrutura de Diretórios:** As skills ficam em diretórios específicos, como `.claude/skills/<nome-da-skill>/SKILL.md`.
- **Frontmatter (YAML):** O cabeçalho do arquivo contém metadados vitais, como:
  - `user-invocable`: Se pode ser chamada diretamente pelo usuário.
  - `model`: Qual modelo usar para essa skill.
  - `effort`: Nível de esforço/timeout.
  - `allowedTools`: Lista de ferramentas que a skill tem permissão para usar.
  - `argumentNames`: Argumentos esperados.
  - `hooks`: Gatilhos automáticos para a skill.
- **Corpo em Markdown:** O conteúdo restante serve como o "prompt" da skill, definindo instruções, regras ou comandos shell a serem executados.
- **Carregamento Dinâmico:** O sistema varre os diretórios de skills no start, faz o parse do frontmatter e registra a skill em memória como um comando ou ferramenta disponível para o LLM.

## 2. Estado Atual do Sistema de Skills do MindFlow
O MindFlow possui um sistema de skills robusto, mas altamente programático e engessado (baseado em Python):
- **Tipagem Forte:** Usa Pydantic (`SkillMetadata`, `SkillConfiguration`, etc.) e enums (`SkillType`).
- **Implementação em Classes:** Requer a criação de subclasses de `BaseSkill` sobrescrevendo métodos como `_execute_internal()`.
- **Registro:** As skills são registradas no `SkillRegistry` e executadas pelo `SkillExecutor`.
- Atualmente, não suporta a criação dinâmica de skills baseada apenas em arquivos de texto/Markdown.

## 3. Plano de Integração (MindFlow + Markdown Skills)
Para trazer a flexibilidade do Claude Code para o MindFlow, precisamos criar uma ponte que transforme arquivos `SKILL.md` em instâncias dinâmicas de `BaseSkill`.

### Passo a Passo da Implementação:

**Passo 1: Definir o Modelo de Dados para Skills em Markdown**
- Atualizar `SkillType` em `schemas/skills/base.py` para incluir `MARKDOWN` ou `PROMPT`.
- Criar um Pydantic Model para representar o Frontmatter esperado nos arquivos `.mindflow/skills/*/SKILL.md`.

**Passo 2: Criar o Parser (Loader)**
- Implementar um loader em `skills/utils/markdown_loader.py`.
- Utilizar bibliotecas como `python-frontmatter` para extrair o YAML header e o conteúdo Markdown separadamente.
- O loader deverá varrer o diretório `.mindflow/skills/` (e caminhos globais).

**Passo 3: Criar a Classe `MarkdownSkill`**
- Criar uma subclasse de `BaseSkill` chamada `MarkdownSkill`.
- O método `__init__` receberá os metadados do parser.
- O método `_execute_internal()` será responsável por injetar o conteúdo Markdown no contexto do agente atual ou engatilhar sub-agentes com o prompt definido.

**Passo 4: Atualizar o Registry e Lifecycle**
- Modificar o método `initialize()` do `SkillRegistry` para invocar o `markdown_loader.py` e registrar automaticamente as instâncias de `MarkdownSkill` encontradas.

**Passo 5: Hooks e Gatilhos (Opcional, mas recomendado)**
- Implementar um sistema de *Hooks* (semelhante ao do Claude) onde o orquestrador do MindFlow verifica o "contexto atual" ou a "intenção do usuário" e ativa a skill Markdown correspondente, passando o conteúdo da skill para o `system_prompt` do agente.

---
**Próximos Passos Sugeridos:**
Se aprovar este plano, podemos começar a implementação pelo **Passo 1** e **Passo 2**, adicionando o suporte no schema e escrevendo a lógica de leitura do `SKILL.md`.