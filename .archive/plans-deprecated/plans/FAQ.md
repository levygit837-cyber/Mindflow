# FAQ - Perguntas Frequentes sobre a Refatoração

**Última Atualização:** 2026-03-31

---

## 🎯 Perguntas Gerais

### P: Por que refatorar agora?

**R:** O MindFlow tem boa lógica de negócio mas falta padrões enterprise-level críticos:
- **Segurança:** Sem sistema de permissões formal
- **Extensibilidade:** Sem hooks para customização
- **Contexto:** Gerenciamento de contexto ad-hoc
- **UX:** Falta sistema de comandos intuitivo

Refatorar agora evita tech debt crescente e nos alinha com padrões battle-tested do Claude Code.

### P: Por que usar Claude Code como referência?

**R:** Claude Code CLI é:
- ✅ **Battle-tested:** Usado em produção por milhares de desenvolvedores
- ✅ **Enterprise-grade:** Padrões robustos de segurança e performance
- ✅ **Bem arquitetado:** Separação clara de responsabilidades
- ✅ **Extensível:** Sistema de hooks e plugins maduro

### P: Quanto tempo vai levar?

**R:** 14 semanas (~3.5 meses) divididas em 4 fases:
- Fase 1: 3 semanas (Permissions + Context)
- Fase 2: 3 semanas (Hooks + Tasks)
- Fase 3: 4 semanas (Commands + Sub-Agents)
- Fase 4: 2 semanas (Loops + Scheduling)
- Hardening: 2 semanas (Testing + Docs)

### P: Vai quebrar o sistema atual?

**R:** **NÃO.** Garantimos:
- ✅ 100% backward compatibility
- ✅ Feature flags para rollout gradual
- ✅ Rollback rápido (<5 minutos)
- ✅ Zero downtime durante deploy

---

## 🏗️ Perguntas Arquiteturais

### P: Vamos substituir SPADE/XMPP?

**R:** **NÃO.** Vamos **manter** SPADE/XMPP e adicionar uma camada de abstração (AgentTool) por cima. Isso:
- ✅ Preserva investimento existente
- ✅ Mantém escalabilidade
- ✅ Adiciona padrões do Claude Code
- ✅ Permite evolução futura

### P: Vamos migrar de PostgreSQL para file-based?

**R:** **NÃO.** Vamos **manter** PostgreSQL e adicionar file-based cache para hot data. Isso:
- ✅ Mantém queries SQL complexas
- ✅ Mantém pgvector para semantic search
- ✅ Adiciona performance para dados frequentes
- ✅ Melhor dos dois mundos

### P: Vamos substituir RabbitMQ?

**R:** **NÃO.** Vamos **manter** RabbitMQ e adicionar Task abstraction por cima. Isso:
- ✅ Mantém distribuição e escalabilidade
- ✅ Mantém fault-tolerance
- ✅ Adiciona interface padronizada
- ✅ Facilita gerenciamento de tasks

### P: Por que não reescrever do zero?

**R:** Reescrever do zero seria:
- ❌ **Arriscado:** Perder funcionalidades existentes
- ❌ **Caro:** 6-12 meses de desenvolvimento
- ❌ **Desnecessário:** Core do MindFlow é sólido
- ✅ **Melhor:** Refatoração gradual preserva investimento

---

## 🔧 Perguntas Técnicas

### P: Como funcionam as feature flags?

**R:** Feature flags permitem habilitar/desabilitar funcionalidades via environment variables:

```bash
# Desabilitado (default)
FEATURE_ENABLE_PERMISSION_SYSTEM=false

# Habilitado
FEATURE_ENABLE_PERMISSION_SYSTEM=true
```

Código verifica flag antes de usar nova funcionalidade:

```python
if get_feature_flags().enable_permission_system:
    # Usar novo sistema
    await permission_manager.check_permission(...)
else:
    # Usar sistema legado (ou nada)
    pass
```

### P: Como funciona o rollback?

**R:** Rollback em 3 níveis:

**Nível 1: Feature Flag (< 1 minuto)**
```bash
# Desabilitar via environment
kubectl set env deployment/mindflow-api FEATURE_ENABLE_PERMISSION_SYSTEM=false
```

**Nível 2: Restart (< 5 minutos)**
```bash
# Restart pods
kubectl rollout restart deployment/mindflow-api
```

**Nível 3: Revert Code (< 30 minutos)**
```bash
# Revert commit
git revert <commit-hash>
docker build -t mindflow:rollback .
kubectl set image deployment/mindflow-api mindflow=mindflow:rollback
```

### P: Como garantir backward compatibility?

**R:** Múltiplas estratégias:

1. **Adapter Pattern:** Código novo funciona com ou sem features
2. **Dual-Write:** Escrever em ambos os sistemas durante transição
3. **Facade Pattern:** Abstração sobre sistemas legados
4. **Testes de Regressão:** Suite completa de testes backward compat

### P: Como medir performance?

**R:** Métricas Prometheus:

```python
# Latência
permission_check_duration = Histogram(
    "permission_check_duration_seconds",
    "Permission check duration",
)

# Uso
permission_checks_total = Counter(
    "permission_checks_total",
    "Total permission checks",
    ["decision", "tool_name"],
)
```

Alertas se performance degrada:
```yaml
- alert: PermissionCheckSlow
  expr: histogram_quantile(0.95, permission_check_duration_seconds) > 0.1
  for: 5m
```

---

## 🚀 Perguntas de Implementação

### P: Por onde começar?

**R:** Siga o [QUICK-START-GUIDE.md](./QUICK-START-GUIDE.md):

1. **Dia 1:** Criar estrutura + types (2-3h)
2. **Dia 2:** Base handler protocol (2-3h)
3. **Dia 3-4:** PermissionManager (4-6h)
4. **Dia 5:** Integração com runtime (3-4h)

### P: Preciso conhecer TypeScript?

**R:** **NÃO.** Os padrões do Claude Code são conceituais, não específicos de TypeScript. Documentação fornece:
- ✅ Exemplos em Python
- ✅ Padrões adaptados para Python
- ✅ Código pronto para usar

### P: Como testar durante desenvolvimento?

**R:** Testes em 3 níveis:

**Unit Tests:**
```bash
uv run pytest tests/unit/permissions/ -v
```

**Integration Tests:**
```bash
uv run pytest tests/integration/ -v
```

**Coverage:**
```bash
uv run pytest --cov=mindflow_backend.permissions --cov-report=term-missing
```

### P: Como fazer code review?

**R:** Checklist de code review:

- [ ] Testes unitários passando (85%+ coverage)
- [ ] Testes de integração passando
- [ ] Backward compatibility verificada
- [ ] Feature flags funcionando
- [ ] Performance aceitável (<100ms overhead)
- [ ] Documentação atualizada
- [ ] Ruff/mypy sem erros

---

## 📊 Perguntas de Processo

### P: Como funciona o rollout gradual?

**R:** Rollout em 4 etapas:

**Etapa 1: Development (Semana 1-2)**
- Todas as features habilitadas
- Testes locais

**Etapa 2: Staging (Semana 3)**
- Deploy em staging
- Testes de carga
- Validação

**Etapa 3: Canary (Semana 4)**
- 10% do tráfego em produção
- Monitorar por 48h
- Comparar métricas

**Etapa 4: Full Rollout (Semana 5)**
- 100% do tráfego
- Monitorar por 1 semana
- Coletar feedback

### P: Como monitorar durante transição?

**R:** Dashboard Grafana com:

- **Usage:** Legacy path vs New path
- **Performance:** Latência p50/p95/p99
- **Errors:** Error rate comparison
- **Resources:** CPU/Memory usage

Alertas automáticos se:
- Error rate aumenta >5%
- Latência aumenta >20%
- Memory usage aumenta >15%

### P: Quem faz o quê?

**R:** Ownership por fase:

**Fase 1 (Permissions + Context):**
- Dev 1: PermissionManager + handlers
- Dev 2: QueryEngine + providers
- DevOps: Feature flags + monitoring

**Fase 2 (Hooks + Tasks):**
- Dev 1: HookManager
- Dev 2: TaskManager
- DevOps: Task monitoring

**Fase 3 (Commands + Sub-Agents):**
- Dev 1: CommandRegistry
- Dev 2: AgentTool
- DevOps: Agent monitoring

**Fase 4 (Loops + Scheduling):**
- Dev 1: Scheduler
- Dev 2: Job persistence
- DevOps: Cron monitoring

---

## 🚨 Perguntas de Risco

### P: E se der errado?

**R:** Plano de contingência em 3 níveis:

**Nível 1: Rollback Rápido**
- Desabilitar feature flag
- Restart pods
- Tempo: <5 minutos

**Nível 2: Rollback Completo**
- Revert código
- Rebuild imagem
- Redeploy
- Tempo: <30 minutos

**Nível 3: Restaurar Backup**
- Restaurar DB backup (se necessário)
- Restaurar configuração
- Tempo: <2 horas

### P: E se performance degradar?

**R:** Ações baseadas em threshold:

**<10% degradação:** Aceitável, monitorar
**10-20% degradação:** Investigar, otimizar
**>20% degradação:** Rollback imediato

Profiling contínuo para identificar bottlenecks.

### P: E se descobrirmos breaking changes?

**R:** Processo de correção:

1. **Rollback imediato**
2. **Adicionar teste de regressão**
3. **Corrigir código**
4. **Validar backward compatibility**
5. **Re-testar extensivamente**
6. **Rollout novamente**

### P: E se a equipe não conseguir?

**R:** Suporte em múltiplos níveis:

- **Documentação:** 7 documentos detalhados
- **Treinamento:** Workshops e pair programming
- **Code Review:** Tech Lead revisa tudo
- **Consultoria:** Claude Code como referência
- **Comunidade:** Slack channel dedicado

---

## 💰 Perguntas de Custo

### P: Quanto vai custar?

**R:** Custo estimado:

**Desenvolvimento:**
- 2-3 desenvolvedores × 3.5 meses = 10.5 person-months
- Custo: Alto (mas necessário)

**Infraestrutura:**
- Staging environment: Baixo
- Monitoring adicional: Baixo
- Total infra: Baixo

**Treinamento:**
- Workshops: 1 semana
- Pair programming: Contínuo
- Total: Médio

**Total:** ~10.5 person-months de desenvolvimento

### P: Qual o ROI?

**R:** ROI positivo em 6-9 meses:

**Curto Prazo (3-6 meses):**
- Segurança melhorada
- Menos bugs
- Código mais limpo

**Médio Prazo (6-12 meses):**
- Desenvolvimento mais rápido
- Menos tech debt
- Onboarding mais fácil

**Longo Prazo (12+ meses):**
- Plataforma extensível
- Competitiva no mercado
- Escalável

### P: Vale a pena?

**R:** **SIM**, pelos seguintes motivos:

1. **Segurança:** Sistema de permissões é CRÍTICO
2. **Extensibilidade:** Hooks permitem customização
3. **Manutenibilidade:** Código mais limpo e testável
4. **Competitividade:** Padrões enterprise-level
5. **Tech Debt:** Evita acúmulo de dívida técnica

---

## 🎓 Perguntas de Aprendizado

### P: Preciso estudar antes?

**R:** Recomendado mas não obrigatório:

**Essencial (1-2 dias):**
- Ler EXECUTIVE-SUMMARY.md
- Ler QUICK-START-GUIDE.md
- Revisar código do Claude Code (src/)

**Opcional (1 semana):**
- Estudar padrões Python enterprise
- Aprender sobre Strangler Fig Pattern
- Praticar com feature flags

### P: Onde encontrar ajuda?

**R:** Recursos disponíveis:

**Documentação:**
- 7 documentos neste diretório
- CLAUDE.md do projeto
- README.md principal

**Código:**
- Claude Code CLI (src/)
- Exemplos em PHASE-1-IMPLEMENTATION-GUIDE.md

**Pessoas:**
- Tech Lead (decisões arquiteturais)
- DevOps (infraestrutura)
- Equipe (pair programming)

**Comunidade:**
- Slack #mindflow-refactoring
- GitHub issues
- Code reviews

### P: Como contribuir?

**R:** Processo de contribuição:

1. **Ler documentação**
2. **Escolher tarefa** (ver QUICK-START-GUIDE.md)
3. **Criar branch** (feature/phase-X-component)
4. **Implementar** (seguir guias)
5. **Testar** (85%+ coverage)
6. **Code review** (solicitar aprovação)
7. **Merge** (após aprovação)

---

## 📅 Perguntas de Timeline

### P: Podemos acelerar?

**R:** Possível mas **não recomendado**:

**Riscos de acelerar:**
- ❌ Menos testes
- ❌ Mais bugs
- ❌ Menos code review
- ❌ Equipe sobrecarregada

**Alternativa:**
- ✅ Adicionar mais desenvolvedores
- ✅ Paralelizar tarefas independentes
- ✅ Reduzir escopo (remover Fase 4)

### P: Podemos fazer em fases menores?

**R:** **SIM**, podemos dividir ainda mais:

**Fase 1A (1.5 semanas):** Apenas Permissions
**Fase 1B (1.5 semanas):** Apenas QueryEngine
**Fase 2A (1.5 semanas):** Apenas Hooks
**Fase 2B (1.5 semanas):** Apenas Tasks

Isso aumenta controle mas adiciona overhead de coordenação.

### P: E se atrasar?

**R:** Buffer de 2 semanas incluído no cronograma:

**Timeline oficial:** 14 semanas
**Timeline real:** 12 semanas de trabalho + 2 semanas de buffer

Se atrasar além do buffer:
1. Reavaliar escopo
2. Adicionar recursos
3. Comunicar stakeholders
4. Ajustar timeline

---

## ✅ Perguntas de Aprovação

### P: O que precisa para aprovar?

**R:** Checklist de aprovação:

**Técnico:**
- [ ] Arquitetura revisada e aprovada
- [ ] Decisões técnicas documentadas
- [ ] Riscos identificados e mitigados
- [ ] Plano de rollback testado

**Processo:**
- [ ] Timeline aprovado
- [ ] Recursos alocados
- [ ] Budget aprovado
- [ ] Ownership definido

**Equipe:**
- [ ] Equipe treinada
- [ ] Documentação lida
- [ ] Dúvidas esclarecidas
- [ ] Confiança estabelecida

### P: Quando começar?

**R:** Após aprovação:

**Semana 1:** Preparação
- Setup de ambiente
- Treinamento
- Configuração

**Semana 2:** Início
- Seguir QUICK-START-GUIDE.md
- Implementar Dia 1-5
- Daily standups

**Semana 3+:** Execução
- Continuar implementação
- Code reviews
- Testes contínuos

---

## 🎯 Perguntas Finais

### P: Qual a principal recomendação?

**R:** **APROVAR E INICIAR** pelos seguintes motivos:

1. ✅ Plano bem documentado (7 documentos)
2. ✅ Riscos controlados (feature flags + rollback)
3. ✅ Backward compatible (zero breaking changes)
4. ✅ ROI positivo (6-9 meses)
5. ✅ Preserva investimento (mantém infra atual)
6. ✅ Enterprise-ready (padrões battle-tested)

### P: E se ainda tiver dúvidas?

**R:** Múltiplos canais de suporte:

**Documentação:**
- Revisar FAQ.md (este documento)
- Ler documentos específicos
- Consultar código de exemplo

**Pessoas:**
- Perguntar no Slack #mindflow-refactoring
- Agendar reunião com Tech Lead
- Pair programming com colega

**Processo:**
- Criar issue no GitHub
- Propor ADR para decisões
- Atualizar documentação

---

**Última Atualização:** 2026-03-31  
**Próxima Revisão:** Após Fase 1 (Semana 4)

---

**Não encontrou sua pergunta?** Crie uma issue ou pergunte no Slack!
