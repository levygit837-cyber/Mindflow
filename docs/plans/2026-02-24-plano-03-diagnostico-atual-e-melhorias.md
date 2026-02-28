# Plano 03 — Diagnóstico Objetivo da Arquitetura Atual + Refatoração de Pastas

Data base: 24/02/2026

## 1) Diagnóstico de ponta a ponta

## 1.1 Fluxo `agent` (chat)
1. `POST /api/agent/chat` recebe input.
2. Cria agente (`createOmniMindAgent`) com modelo LangChain.
3. Usa `createDeepAgent` com `PostgresSaver` + backend de tools.
4. Stream de mensagens/updates é normalizado.
5. SSE envia eventos para UI.
6. Store frontend converte eventos em `contentParts`.

Conclusão: fluxo funcional e moderno, mas ainda com acoplamento alto entre transporte/evento/render.

## 1.2 Fluxo `swarm` (multiagente)
1. `POST /api/swarm` cria task e compila grafo LangGraph.
2. Grafo executa em background com nós mistos (determinísticos + LLM agents).
3. Coder/Analyst/Reviewer usam `createDeepAgent` com tools LangChain.
4. Notifier publica eventos com replay SSE.
5. Frontend consome eventos e atualiza dashboard.

Conclusão: desenho bom para produto multiagente, com base sólida para escalar.

---

## 2) Onde o projeto está aderente a Clean Architecture

1. Existe separação parcial entre rotas, lógica de agente e ferramentas.
2. Grafo do swarm está bem encapsulado por nó.
3. Ferramentas foram isoladas por perfil de agente.
4. Há tipagem e validação (`zod`) em partes importantes.

---

## 3) Onde o projeto NÃO está aderente (principais dores)

## P0
1. Persistência crítica in-memory:
   - `src/lib/agent/conversations.ts`
   - `src/app/api/settings/route.ts`
   - `src/lib/swarm/registry.ts`
2. `pnpm test` com falhas no streaming (8 testes falhando).

## P1
1. Contrato de evento duplicado/incompatível entre `agent` e `swarm`.
2. Execução de comando no swarm sem política central equivalente ao SafeBackend.
3. Defaults de provider/model inconsistentes entre stores.

## P2
1. Tipos genéricos legados em `src/types/index.ts` pouco integrados ao fluxo atual.
2. Organização de pastas ainda orientada por "biblioteca técnica" (`lib`) e não por módulo de negócio.

---

## 4) Refatoração de pastas (pequena, segura e incremental)

## Fase 1 — Organização sem quebra de runtime

Objetivo: reorganizar por domínio mantendo imports via aliases.

Estrutura alvo inicial:

```text
src/
  modules/
    agent/
      application/
      infrastructure/
      interface/
    swarm/
      application/
      infrastructure/
      interface/
  shared/
    events/
    llm/
    tools/
    security/
    observability/
    types/
  app/
    api/
```

Movimentos sugeridos:
1. `src/lib/agent/providers.ts` -> `src/shared/llm/providers.ts`
2. `src/lib/db/postgres.ts` -> `src/shared/infrastructure/postgres.ts`
3. `src/lib/agent/tools/*` -> `src/modules/agent/infrastructure/tools/*`
4. `src/lib/swarm/tools/*` -> `src/modules/swarm/infrastructure/tools/*`

## Fase 2 — Separação real de camadas
1. Casos de uso para chat/swarm em `application/use-cases`.
2. Rotas API viram adaptadores finos (`interface/http`).
3. Repositórios explícitos para sessão, conversa e evento.

## Fase 3 — Governança de arquitetura
1. ADRs em `docs/adr`.
2. Lint de fronteira de módulo (evitar import cruzado inválido).
3. Checklist de PR com regras de camada.

---

## 5) Plano de qualidade para evitar dor de cabeça

1. Corrigir testes do streaming antes de refatorar pastas.
2. Congelar contrato de evento único (`v1`) antes de mexer no frontend.
3. Refatorar por fatias pequenas (não big-bang).
4. A cada fatia: `test`, validação de SSE e smoke no chat/swarm.

---

## 6) Recomendações específicas para LangChain/LangGraph

1. Centralizar criação de modelos em um único ponto (`shared/llm`).
2. Padronizar inicialização de agentes deepagents (factory única com policies).
3. Isolar normalização de stream por provider para reduzir complexidade.
4. No LangGraph, manter nós determinísticos para controle e LLM nodes só para geração/análise.
5. Persistir checkpoint e eventos com o mesmo `thread_id/task_id` para auditoria.

---

## 7) Prioridade de execução (ordem realista)

1. Corrigir `chat-stream-normalizer` e testes de rota (`agent/chat`).
2. Unificar evento global (`agent + swarm`).
3. Migrar persistência in-memory para PostgreSQL (conversa/settings/registry).
4. Aplicar Fase 1 de refatoração de pastas.
5. Introduzir loop por aceitação (Plano 02) com nó dedicado.

---

## 8) Critérios de sucesso

1. Projeto sobe sem regressão após reorganização de pastas.
2. Fluxos `agent` e `swarm` possuem rastreabilidade homogênea.
3. Estado não se perde em restart.
4. Equipe consegue localizar responsabilidades por módulo sem ambiguidade.
