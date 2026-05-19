# Codebase Rules

## Re-indexação após Longas Interações

**Sempre executar re-indexação após alterações em sessões longas de trabalho.**

Após qualquer interação extensa que resulte em múltiplas modificações no código, é obrigatório executar os seguintes passos de re-indexação:

### Quando Aplicar

- Após sessões de refatoração com múltiplas alterações
- Após implementação de novas features que tocam vários arquivos
- Após correções de bugs que afetam múltiplos módulos
- Após reorganização de estrutura de diretórios
- Qualquer interação com mais de 5 arquivos modificados

### Procedimento de Re-indexação

1. **Re-indexar o Codebase (arquivos)**

   ```bash
   # Via MCP socraticode
   codebase_update - atualiza incrementalmente os arquivos modificados
   ```

2. **Re-indexar o Dependency Graph**

   ```bash
   # Via MCP socraticode
   codebase_graph_build - reconstrói o grafo de dependências
   ```

3. **Verificar Status**

   ```bash
   # Confirmar que a indexação está completa
   codebase_status - verificar progresso
   codebase_graph_status - verificar status do grafo
   ```

### Motivação

- Garante que buscas semânticas retornem resultados atualizados
- Mantém o grafo de dependências sincronizado com o código atual
- Previne análises baseadas em código desatualizado
- Melhora a precisão do ContextPlus e ferramentas de exploração

### Ordem Recomendada

1. Finalizar todas as alterações de código
2. Executar `codebase_update` (mais rápido, incremental)
3. Executar `codebase_graph_build` (reconstrói dependências)
4. Verificar com `codebase_status` e `codebase_graph_status`
5. Prosseguir com análises ou novas tarefas

---
*Última atualização: 2026-03-31*
