# PRD: MindFlow Backend Stabilization

## 1. Summary

Este documento define a iniciativa de estabilização e consolidação estrutural do backend do MindFlow. O foco é simples: tornar o sistema mais confiável, mais claro para o time e mais barato de manter, reduzindo caminhos duplicados, dependências frágeis e áreas que hoje parecem prontas sem estarem realmente fechadas.

## 2. Contacts

| Papel | Responsável | Comentário |
| --- | --- | --- |
| Produto Técnico | A definir | Guarda escopo, prioridade e corte de legado |
| Engenharia Backend | A definir | Dona das mudanças no núcleo da aplicação |
| Plataforma / Arquitetura | A definir | Dona da simplificação estrutural e fluxo oficial |
| Infraestrutura | A definir | Dona de ambiente, dependências e setup |
| QA / Qualidade | A definir | Dona da revisão de testes e critérios de estabilidade |

## 3. Background

### Contexto

O backend do MindFlow cresceu rápido e acumulou várias camadas: fluxo principal, compatibilidade antiga, módulos prometidos para o futuro, serviços simulados e documentação muito otimista.

Hoje o projeto já tem um núcleo útil, mas também sofre com:

- mais de um caminho para fazer a mesma coisa;
- configuração espalhada;
- dependências frágeis derrubando módulos vizinhos;
- contratos que já não batem entre si;
- documentação e testes desatualizados.

### Por que agora?

Porque o custo da ambiguidade já ficou alto. Sem uma rodada séria de consolidação, cada nova feature vai ficar mais cara, mais arriscada e mais difícil de testar.

### O que mudou?

A análise estrutural recente mostrou que o problema principal não é ausência de capacidade. É excesso de superfície incompleta misturada com um núcleo que até funciona bem.

## 4. Objective

### Objetivo principal

Estabilizar o backend do MindFlow para que o time tenha um caminho oficial de execução, configuração consistente, base de memória e armazenamento previsível e uma superfície de produto que reflita apenas o que está realmente pronto.

### Por que isso importa?

- reduz falhas em cascata;
- corta retrabalho;
- acelera onboarding;
- melhora a confiança do time;
- prepara a base para crescimento real.

### Benefício para a empresa

- menor custo de manutenção;
- menos tempo perdido em bugs confusos;
- entregas futuras com menos risco;
- base mais honesta para evolução de produto.

### Benefício para usuários e consumidores internos

- comportamento mais previsível;
- menos inconsistência entre rotas, serviços e execução;
- maior confiança em retomada, memória e monitoramento.

### Alinhamento estratégico

Essa iniciativa não é “arrumação cosmética”. Ela protege o crescimento do produto. Sem isso, o sistema continua crescendo em largura, mas enfraquecendo em profundidade.

### Key Results

#### KR1

Até o fim da iniciativa, o backend terá **um único fluxo oficial documentado** para execução principal, com caminhos antigos explicitamente marcados como compatibilidade ou removidos.

#### KR2

Até o fim da iniciativa, os módulos centrais terão **configuração unificada**, sem divergência entre defaults, locais de leitura e nomes de parâmetros críticos.

#### KR3

Até o fim da iniciativa, `memory`, `storage`, `grpc` e `workers` deixarão de quebrar em cascata por causa de dependências de armazenamento vetorial.

#### KR4

Até o fim da iniciativa, a superfície pública do backend refletirá apenas recursos realmente utilizáveis, com recursos incompletos removidos, escondidos ou rotulados.

#### KR5

Até o fim da iniciativa, a documentação principal e a bateria de testes prioritários estarão alinhadas com o comportamento real do sistema.

## 5. Market Segment(s)

### Segmento principal

Times internos que constroem, mantêm e evoluem o MindFlow.

### Jobs que esse segmento precisa resolver

- entender rápido qual é o caminho oficial do sistema;
- mudar código sem quebrar áreas distantes;
- confiar nos contratos centrais;
- depurar problemas sem navegar por camadas duplicadas;
- planejar novas features em cima de uma base real.

### Restrições

- o sistema já está em uso e não pode ser “reiniciado do zero”;
- parte do legado ainda precisa continuar disponível por um período curto;
- o time precisa melhorar a base sem travar toda a evolução do produto.

## 6. Value Proposition(s)

### Job principal atendido

“Quando o time precisar evoluir o backend do MindFlow, ele quer uma base clara, previsível e confiável, para conseguir entregar mudanças sem medo de quebrar áreas que não deveriam ser afetadas.”

### Ganhos para o time

- menos dúvida sobre onde mexer;
- menos retrabalho;
- menor tempo de investigação;
- menor custo para introduzir novas capacidades.

### Dores que serão evitadas

- correções feitas no lugar errado;
- divergência entre código, teste e documentação;
- módulos quebrando por dependências indiretas;
- excesso de confiança em recursos parciais.

### Onde podemos ser melhores do que o estado atual

- clareza do caminho oficial;
- honestidade sobre maturidade real do sistema;
- isolamento melhor entre módulos;
- base mais sustentável para evolução.

## 7. Solution

### 7.1 UX / Prototypes

Por ser uma iniciativa interna de plataforma, o “UX” aqui é o UX do time que desenvolve.

Os entregáveis esperados são:

- um mapa simples do fluxo oficial do backend;
- uma visão clara do que é núcleo real e do que é compatibilidade;
- uma lista pública de módulos ativos, módulos parciais e módulos em remoção;
- uma documentação curta de setup e configuração sem ambiguidades.

### 7.2 Key Features

#### Feature 1: Fluxo oficial único

Definir e publicar qual é o fluxo principal de execução, orquestração e streaming. Adaptadores antigos continuam só como ponte curta, não como segunda arquitetura.

#### Feature 2: Configuração centralizada

Concentrar a configuração em uma referência única, com defaults consistentes, caminho claro de ambiente e nomes estáveis para parâmetros críticos.

#### Feature 3: Base de memória e armazenamento previsível

Eliminar o efeito cascata causado por dependências frágeis. O sistema precisa ter uma decisão clara sobre o uso do armazenamento vetorial.

#### Feature 4: Limpeza de superfície pública

Recursos incompletos não devem parecer prontos. A iniciativa precisa esconder, remover ou fechar o mínimo necessário de áreas simuladas.

#### Feature 5: Contrato único de sessão

Sessão, ownership e histórico precisam seguir a mesma regra em API, serviços e persistência.

#### Feature 6: Documentação e testes alinhados

Documentação principal e testes prioritários passam a refletir o comportamento real do sistema, sem depender de estruturas antigas já abandonadas.

### 7.3 Technology

O objetivo não é trocar tecnologia por trocar. O objetivo é reduzir ambiguidade.

Princípios técnicos desta iniciativa:

- preferir um caminho oficial em vez de múltiplos caminhos “quase iguais”;
- isolar dependências pesadas;
- remover compatibilidade antiga com prazo;
- tratar documentação e testes como parte do produto interno.

### 7.4 Assumptions

- o núcleo real do sistema já é forte o suficiente para ser consolidado;
- o time aceita reduzir superfície aparente para ganhar confiabilidade real;
- parte do trabalho exigirá remoção, e não apenas adição;
- a prioridade do curto prazo é estabilização, não expansão de escopo.

## 8. Release

### Versão 1

Primeira etapa da iniciativa:

- definir fluxo oficial;
- centralizar configuração;
- estabilizar memória e armazenamento;
- alinhar contrato de sessão;
- remover ou esconder recursos incompletos mais críticos.

### Versão 2

Segunda etapa:

- revisar gRPC e workers para deixá-los realmente prontos ou claramente secundários;
- corrigir áreas estruturais como skills e módulos ainda quebrados;
- ampliar a cobertura de documentação e testes após a simplificação inicial.

### Futuro

Depois da estabilização:

- expandir capacidades só em cima do caminho oficial;
- reabrir áreas distribuídas e especializadas com metas claras de maturidade;
- manter uma política ativa de remoção de legado.

### Horizonte esperado

- **Curto prazo**: definir, cortar e estabilizar o núcleo
- **Médio prazo**: alinhar superfície pública, testes e docs
- **Depois**: retomar expansão com uma base confiável

## Anexo: Escopo inicial sugerido

Entram no escopo inicial:

- `API`
- `CONFIG`
- `EXECUTION_MEMORY`
- `GRAPHS`
- `MEMORY`
- `ORCHESTRATOR`
- `RUNTIME`
- `SERVICES`
- `STORAGE`
- `WORKERS`

Ficam sob revisão controlada:

- `CHAINS`
- `DECOMPOSITION`
- `GRPC`
- `INTERFACES`
- `NODES`
- `SKILLS`
- `UTILS`
- `SECURITY`
- `INFRA`

## Critério de sucesso da iniciativa

Vamos considerar esta iniciativa bem-sucedida quando o time conseguir responder rapidamente, sem discussão longa:

- qual é o fluxo oficial do sistema;
- onde a configuração vive;
- como memória e armazenamento se comportam;
- quais recursos estão realmente prontos;
- quais partes estão em compatibilidade;
- quais testes e documentos ainda merecem confiança.
