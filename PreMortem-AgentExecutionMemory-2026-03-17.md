# Pre-Mortem Analysis: Agent Execution Memory

**Data:** 2026-03-17  
**Escopo:** Melhorar a memória de execução dos agentes no MindFlow para permitir pausa, congelamento de estado, retomada confiável e preservação de contexto sem perda de coerência.  
**Horizonte imaginado:** O plano foi executado, a retomada foi para produção e falhou. O que deu errado?

---

## Contexto do Plano

O estado atual do MindFlow guarda bem o conteúdo da conversa e já consegue recuperar contexto da sessão, mas ainda não guarda bem o andamento interno do trabalho do agente. Hoje existe memória persistente para mensagens, eventos e blocos de sessão, porém os elementos mais críticos da execução continuam frágeis:

- o grafo principal não está ligado a um checkpoint durável
- listas de planejamento continuam em memória do processo
- abas de shell continuam em memória do processo
- delegação de subagentes preserva contexto de forma desigual
- há caminhos antigos e novos de memória convivendo ao mesmo tempo

Para corrigir isso, o plano proposto é:

### Fase 1 — Unificar a memória oficial de execução
- Eleger um único caminho canônico para memória, pausa e retomada
- Parar de depender de caminhos antigos e estruturas paralelas
- Definir o contrato de “estado pausável”

### Fase 2 — Introduzir diário de execução e snapshots
- Criar um diário durável de eventos da execução
- Criar snapshots de estado em pontos seguros
- Persistir ponteiros para artefatos e resultados, e não só texto corrido

### Fase 3 — Habilitar pausa e retomada reais
- Permitir pausar apenas em fronteiras seguras
- Retomar a partir do último snapshot válido
- Evitar repetir ações já concluídas

### Fase 4 — Preservar coerência entre estados e subagentes
- Reidratar contexto a partir de um pacote estável de estado
- Garantir herança de contexto para subagentes
- Validar coerência de resposta e continuidade após retomada

### Fase 5 — Verificação operacional
- Testar reinício de processo
- Testar retomada após falha
- Testar idempotência de ações com efeito externo
- Testar continuidade de sessões longas e com delegação

---

## Estado Alvo

Ao final, o sistema deve conseguir:

1. Pausar uma execução sem corromper o raciocínio em andamento.
2. Congelar um retrato fiel do estado em um ponto seguro.
3. Retomar depois do mesmo ponto sem duplicar ações nem perder contexto.
4. Reidratar o contexto com consistência entre sessão, agente principal e subagentes.
5. Manter coerência do resultado final, mesmo após pausa, reinício ou troca de processo.

### O que deve ser salvo no estado pausável

- identificação da execução e da sessão
- etapa atual do fluxo
- último ponto seguro confirmado
- últimas decisões relevantes
- itens de plano/todo com status
- resultados de ferramentas já concluídas
- ponteiros para artefatos lidos ou gerados
- contexto consolidado que será reapresentado na retomada
- hash/checksum do snapshot para detectar divergência

### O que não deve ser retomado no meio

- geração de tokens no meio de uma resposta
- execução parcial de ferramenta sem confirmação de término
- subetapas internas sem fronteira segura definida

### Fronteiras seguras de pausa

- fim de turno do usuário
- antes de chamar uma ferramenta
- depois de concluir uma ferramenta e gravar o resultado
- depois de consolidar uma decisão do orquestrador
- depois de finalizar uma subtarefa delegada

---

## Proposta de Arquitetura

### 1. Diário de Execução

Criar um diário durável, append-only, com um evento por mudança relevante. Exemplos:

- execução iniciada
- decisão do orquestrador
- ferramenta chamada
- ferramenta concluída
- delegação iniciada
- delegação concluída
- snapshot criado
- pausa solicitada
- execução pausada
- retomada iniciada
- retomada concluída
- execução finalizada

Esse diário vira a fonte de verdade do “que aconteceu”.

### 2. Snapshot de Estado

Em cada ponto seguro, gerar um snapshot contendo:

- estado lógico da execução
- resumo consolidado do contexto
- referência aos últimos artefatos
- referência ao último evento aplicado
- resumo do plano e status por item
- versão de esquema

Esse snapshot vira a base de retomada.

### 3. Pacote de Contexto

Separar “memória para recuperação” de “contexto para retomada”.

O pacote de contexto de retomada deve conter:

- objetivo atual
- decisão mais recente
- fatos confirmados
- ações já executadas
- ações pendentes
- restrições ativas
- resultados que não podem ser contraditos

Isso evita remontar a sessão só a partir de texto solto.

### 4. Registro de Efeitos Externos

Toda ação que possa produzir efeito fora do raciocínio deve ter registro próprio:

- gravação de arquivo
- edição de arquivo
- chamada externa
- comando de shell
- publicação em fila

Cada efeito precisa de chave de idempotência e status:

- pendente
- aplicado
- confirmado
- falhou
- precisa compensação

Sem isso, retomada confiável vira risco de repetição.

### 5. Retomada por Reidratação, não por improviso

A retomada deve:

1. carregar o último snapshot válido
2. reidratar o pacote de contexto
3. verificar se o último evento aplicado bate com o diário
4. reapresentar ao agente apenas o contexto consolidado e os eventos finais necessários
5. continuar a partir da próxima fronteira segura

Não tentar “adivinhar” o meio do raciocínio perdido.

---

## Plano de Implementação

### Sprint 1 — Base Canônica

- Escolher a pilha oficial de memória e execução
- Marcar explicitamente o que é legado
- Definir o contrato de evento, snapshot e retomada
- Adicionar status de execução: `running`, `pause_requested`, `paused`, `resuming`, `completed`, `failed`

**Critério de saída:** existe uma linguagem única para falar de pausa, snapshot e retomada.

### Sprint 2 — Persistência do Andamento

- Persistir lista de planejamento/todo
- Persistir estado operacional mínimo das sessões de shell
- Criar diário de execução
- Criar snapshots duráveis nos pontos seguros

**Critério de saída:** reiniciar o processo não apaga mais o andamento principal.

### Sprint 3 — Retomada Real

- Integrar checkpoints ao fluxo principal
- Retomar a partir do último snapshot válido
- Bloquear retomada a partir de estados inseguros
- Não repetir efeitos externos já confirmados

**Critério de saída:** uma execução pausada pode ser retomada sem retrabalho indevido.

### Sprint 4 — Coerência de Contexto

- Criar pacote de contexto de retomada
- Diferenciar memória de busca de contexto de retomada
- Garantir herança de contexto para subagentes
- Adicionar guardas de coerência para não contradizer fatos já congelados

**Critério de saída:** retomada e delegação preservam continuidade lógica.

### Sprint 5 — Endurecimento Operacional

- Testes de reinício e retomada em ambiente real
- Testes de duplicação de efeitos externos
- Testes de sessões longas com múltiplas pausas
- Monitoramento de falhas de snapshot, divergência e retomada

**Critério de saída:** o sistema é operável e observável em produção.

---

## Tigers — Riscos Reais

### T1: Tentar retomar de qualquer ponto vai produzir incoerência
**Urgência: Launch-Blocking**

Se o sistema tentar retomar do “meio do pensamento” do agente, ou do meio de uma ferramenta, a resposta final pode parecer fluida, mas ficará logicamente torta. O risco não é só erro técnico; é perda de confiança no resultado.

**Mitigação**
- Permitir pausa apenas em fronteiras seguras
- Tornar inválida a retomada de pontos intermediários
- Registrar explicitamente qual foi o último ponto seguro

**Owner:** Backend / Orquestração  
**Prazo:** 2026-03-24

---

### T2: Persistir só conversa e não persistir execução vai criar falsa sensação de retomada
**Urgência: Launch-Blocking**

Se o time chamar isso de “retomada” sem salvar plano, estado operacional, efeitos concluídos e posição do fluxo, o sistema vai parecer pronto mas só estará relembrando conversa. Em falhas reais, ele recomputa, repete ou se contradiz.

**Mitigação**
- Criar diário de execução e snapshots antes de expor retomada
- Persistir planning/todo e shell state mínimo
- Bloquear entrega de “resume” até cobrir esses componentes

**Owner:** Backend / Runtime  
**Prazo:** 2026-03-27

---

### T3: Repetir efeitos externos na retomada pode causar dano real
**Urgência: Launch-Blocking**

Sem registro de idempotência, uma retomada pode:

- editar arquivo duas vezes
- reexecutar comando de shell
- reenfileirar trabalho
- sobrescrever artefato sem perceber

Esse é o tipo de falha silenciosa que parece sucesso.

**Mitigação**
- Registrar cada efeito externo com chave única
- Separar “planejado”, “executado” e “confirmado”
- Pular automaticamente efeitos já confirmados

**Owner:** Backend / Ferramentas  
**Prazo:** 2026-03-31

---

### T4: Convivência entre memória nova e antiga vai gerar split-brain
**Urgência: Launch-Blocking**

Se uma parte do sistema ler uma memória e outra parte salvar em outra pilha, a retomada pode nascer de uma verdade e executar em outra. Isso é especialmente perigoso quando o código antigo continua existindo e parece funcional.

**Mitigação**
- Nomear a pilha canônica
- Desligar entradas paralelas ou marcá-las como legado
- Criar teste de contrato para garantir um único caminho ativo

**Owner:** Backend / Arquitetura  
**Prazo:** 2026-03-24

---

### T5: Subagentes retomarem sem o mesmo pacote de contexto vai quebrar coerência
**Urgência: Fast-Follow**

Mesmo que a sessão principal retome bem, a coerência vai quebrar se subagentes receberem só resumo solto e não herdarem o mesmo retrato consolidado do estado.

**Mitigação**
- Passar snapshot/context bundle para delegação
- Registrar subtarefa, estado herdado e estado devolvido
- Validar consistência entre resultado do subagente e estado principal

**Owner:** Backend / Orquestração  
**Prazo:** 2026-04-03

---

### T6: Snapshots grandes demais vão degradar custo e latência
**Urgência: Fast-Follow**

Se cada pausa salvar “texto demais”, o sistema vai ficar caro, lento e difícil de manter. O problema não é salvar; é salvar sem disciplina.

**Mitigação**
- Salvar referências para artefatos e não duplicar conteúdo bruto
- Separar histórico completo de snapshot operacional
- Definir limite de tamanho por snapshot

**Owner:** Backend / Infra  
**Prazo:** 2026-04-03

---

## Paper Tigers — Preocupações Superestimadas

### PT1: “Só funciona se conseguirmos retomar token por token”
Isso parece sofisticado, mas não é necessário para entregar retomada confiável. O importante é retomar em pontos seguros, não reconstruir cada pedaço de geração.

**Veredicto:** não é prioridade.

---

### PT2: “Precisamos trocar de banco para resolver isso”
O problema principal hoje não é tecnologia de armazenamento. É modelo de estado, fronteira segura, idempotência e unificação de fluxo.

**Veredicto:** não trocar de infraestrutura antes de corrigir o desenho.

---

### PT3: “Basta guardar mais contexto textual que a coerência vem sozinha”
Guardar mais texto ajuda pouco se o sistema não souber o que é fato confirmado, o que é ação já executada e o que é só conversa.

**Veredicto:** não resolver só aumentando volume de memória.

---

## Elephants — O que não estamos discutindo o suficiente

### E1: Qual é a definição oficial de “ponto seguro” no MindFlow?
Sem essa definição, cada equipe vai implementar pausa de um jeito. Isso destrói a previsibilidade.

**Investigar:** publicar contrato oficial de pausa e retomada antes da implementação.

---

### E2: Como compensar efeitos externos parcialmente aplicados?
Se um comando começou, alterou algo e falhou antes da confirmação, a retomada vai fazer o quê: repetir, pular ou compensar?

**Investigar:** classificar ferramentas por tipo de efeito e estratégia de compensação.

---

### E3: Como versionar snapshots sem travar evolução do sistema?
Sem versionamento, cada mudança de esquema vira risco de quebrar retomadas antigas.

**Investigar:** incluir `schema_version` e política clara de migração.

---

### E4: Como medir coerência pós-retomada?
Sem métrica, a equipe pode achar que funcionou porque “não crashou”, mesmo que a resposta tenha perdido continuidade lógica.

**Investigar:** criar testes comparando execução contínua vs execução pausada/retomada.

---

## Action Plans — Launch-Blocking Tigers

### Action Plan T1: Retomar só de pontos seguros

| Item | Detalhe |
|------|---------|
| **Risco** | Retomada a partir de pontos inseguros produz incoerência |
| **Mitigação** | Formalizar fronteiras seguras e bloquear retomada fora delas |
| **Passo 1** | Definir catálogo de pontos seguros por tipo de execução |
| **Passo 2** | Marcar no diário qual foi o último ponto seguro confirmado |
| **Passo 3** | Negar resume se a execução tiver parado fora desse ponto |
| **Owner** | Backend / Orquestração |
| **Prazo** | 2026-03-24 |

---

### Action Plan T2: Persistir estado de execução, não só conversa

| Item | Detalhe |
|------|---------|
| **Risco** | “Resume” vira só replay de contexto textual |
| **Mitigação** | Persistir plano, etapa, efeitos concluídos e snapshot operacional |
| **Passo 1** | Persistir planning/todo |
| **Passo 2** | Persistir shell state mínimo |
| **Passo 3** | Criar tabela/estrutura de diário e snapshot |
| **Owner** | Backend / Runtime |
| **Prazo** | 2026-03-27 |

---

### Action Plan T3: Tornar efeitos externos idempotentes

| Item | Detalhe |
|------|---------|
| **Risco** | Retomada duplica escrita, shell ou fila |
| **Mitigação** | Registrar efeito externo com chave única e status de confirmação |
| **Passo 1** | Classificar ferramentas com efeito externo |
| **Passo 2** | Adicionar registro de idempotência |
| **Passo 3** | Pular ações já confirmadas na retomada |
| **Owner** | Backend / Ferramentas |
| **Prazo** | 2026-03-31 |

---

### Action Plan T4: Remover split-brain da memória

| Item | Detalhe |
|------|---------|
| **Risco** | Caminhos antigos e novos divergirem na retomada |
| **Mitigação** | Eleger uma única pilha oficial e desativar rotas paralelas |
| **Passo 1** | Mapear todos os pontos que ainda usam memória antiga |
| **Passo 2** | Redirecionar para a fachada oficial |
| **Passo 3** | Adicionar teste de contrato do caminho único |
| **Owner** | Backend / Arquitetura |
| **Prazo** | 2026-03-24 |

---

## Recomendação Final

Se eu resumir em uma frase: **não vale chamar isso de retomada de execução antes de existirem três coisas juntas: diário durável, snapshot em ponto seguro e controle de idempotência de efeitos externos**.

O plano certo não é “guardar mais memória”. O plano certo é **guardar melhor o estado operacional**, separar contexto de busca de contexto de retomada e só permitir retorno a partir de estados realmente congelados.
