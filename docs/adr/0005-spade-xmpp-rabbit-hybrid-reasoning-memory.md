# ADR 0005 - SPADE + XMPP + RabbitMQ com Motor Cognitivo LangGraph/LangChain e Memoria por Agente

- Status: Proposed
- Data: 2026-03-02
- Decisores: OmniMind maintainers
- Tags: arquitetura, backend, agentes, spade, xmpp, rabbitmq, rag, memoria

## Contexto

O OmniMind atual opera com runtime Python orientado a agentes e orquestracao via LangGraph no mesmo processo, com stream SSE estavel para cliente. O projeto precisa evoluir para:

1. coordenacao multiagente real com agentes autonomos que conversem entre si;
2. execucao assíncrona robusta para tarefas longas e delegadas;
3. preservacao de latencia baixa em fluxos curtos;
4. memoria de longo contexto por agente para continuidade e reducao de repeticao.

Durante o brainstorming tecnico, foi acordado que:

1. SPADE/XMPP deve ser o plano de controle entre agentes;
2. RabbitMQ deve ser o plano de trabalho para filas assíncronas;
3. LangChain/LangGraph deve atuar como motor cognitivo (reasoning engine), nao como barramento principal entre agentes;
4. a politica de execucao deve ser hibrida (sync + async);
5. memoria deve ser separada por agente SPADE, com sumarizacao por janela de 300k tokens e recuperacao RAG.

## Decisao

Adotar a arquitetura abaixo como direcao oficial:

1. **Plano de controle:** agentes SPADE comunicando via XMPP.
2. **Plano de trabalho:** RabbitMQ para delegacao, retries e DLQ.
3. **Plano cognitivo:** LangChain/LangGraph encapsulado como Reasoning Engine invocavel de forma sync ou async.
4. **Execucao hibrida:** caminho sincrono para baixa latencia e fallback/roteamento assíncrono para casos pesados.
5. **Memoria por agente:** armazenamento por `(conversation_id, agent_id)` com resumo por janela de 300k tokens e recuperacao semantica para contexto de raciocinio.

### Contratos base aprovados

1. Envelope unificado versionado (`spade.v1`) para XMPP e Rabbit.
2. Contratos tipados para `ReasoningRequest` e `ReasoningResult`.
3. Correlacao obrigatoria por `correlation_id` e idempotencia por `message_id`.

### Estrategia de memoria aprovada

1. `Raw Memory`: eventos completos.
2. `Window Memory`: resumo consolidado por janela.
3. `Fact Memory`: fatos importantes extraidos.
4. `Working Memory`: cauda recente.

### Estado atual de implementacao (nesta data)

1. memoria por agente + recuperacao RAG ja iniciadas no backend atual;
2. injecao de contexto de memoria no fluxo de raciocinio (orchestrator/decomposition) ja conectada;
3. camada SPADE/XMPP/Rabbit ainda pendente de implementacao completa.

## Alternativas Consideradas

1. **Manter arquitetura atual (LangGraph como coordenador unico)**
   - Pros: menor custo imediato.
   - Contras: acoplamento alto, baixa escalabilidade para rede de agentes e menor isolamento de responsabilidades.

2. **Arquitetura totalmente distribuida desde o inicio (cada agente em processo/pod dedicado)**
   - Pros: isolamento maximo.
   - Contras: custo operacional alto prematuro, maior complexidade de rollout.

3. **SPADE/XMPP + Rabbit + Reasoning Engine (escolhida)**
   - Pros: separacao clara entre coordenacao, execucao e raciocinio; rollout incremental; compativel com stream atual.
   - Contras: adiciona componentes de infraestrutura e contratos de integracao a governar.

## Consequencias

### Positivas

- Arquitetura multiagente com responsabilidade bem separada.
- Melhor robustez operacional para tarefas longas (fila, retry, DLQ).
- Melhor latencia percebida em fluxos simples com caminho sync.
- Continuidade de contexto por agente via memoria com sumarizacao em janelas.
- Maior auditabilidade (correlation id, references de memoria, envelopes versionados).

### Negativas

- Maior complexidade operacional (XMPP + Rabbit + workers).
- Aumento de superficie de falhas distribuidas.
- Necessidade de governanca de schemas/versionamento de mensagens.
- Custos de observabilidade e tuning de filas/memoria.

## Plano de Implementacao

1. **Fase 1 - Fundacao de contratos e barramento**
   - Definir schemas `spade.v1`.
   - Introduzir `TaskBus` abstrato e adaptador RabbitMQ.
   - Provisionar infra XMPP (Prosody) e Rabbit.

2. **Fase 2 - Runtime SPADE**
   - Implementar `SpadeOrchestratorAgent`.
   - Implementar agentes de capacidade e protocolo de mensagens.
   - Integrar publish/consume com Rabbit.

3. **Fase 3 - Reasoning Engine**
   - Encapsular LangChain/LangGraph como servico cognitivo.
   - Habilitar sync path e async path com fallback de latencia.

4. **Fase 4 - Memoria e RAG**
   - Consolidar pipeline de janela (300k por agente), fatos e embeddings.
   - Integrar recuperacao RAG em todos os fluxos de raciocinio.
   - Definir politica de retencao e reindexacao.

5. **Fase 5 - Hardening**
   - Observabilidade distribuida completa.
   - Testes de carga, falha parcial e recuperacao.
   - Tuning de thresholds (latencia, top-k, janela, retries).

## Plano de Migracao (se aplicavel)

Migracao incremental, sem quebra do contrato externo de stream SSE:

1. manter API atual e runtime atual funcionando durante rollout;
2. introduzir feature flags para novo roteamento de execucao;
3. migrar workloads por tipo de tarefa para Rabbit gradualmente;
4. ativar coordenacao SPADE por dominios/agentes progressivamente;
5. manter rollback por flag para caminho legado.

## Referencias

- PR(s): pendente
- Documento(s):
  - `docs/plans/2026-03-02-spade-xmpp-rabbit-langgraph-architecture.md`
  - `docs/architecture/ARCHITECTURE_PLAN.md`
- Issue(s): pendente

