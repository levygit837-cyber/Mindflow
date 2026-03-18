# Pre-Mortem Analysis: MindFlow Backend Stabilization

## Contexto e Premissa

Este pre-mortem parte de uma hipótese simples: o MindFlow passou por uma análise estrutural ampla, foram encontradas várias áreas fortes, mas também muitos caminhos paralelos, partes antigas, dependências frágeis e módulos que parecem mais completos na documentação do que no uso real.

Agora imaginamos o seguinte cenário: a iniciativa de estabilização do backend foi lançada, consumiu tempo do time e, ainda assim, falhou. O produto continua difícil de evoluir, os erros seguem aparecendo em cascata, o time não confia na documentação e o custo de manutenção continua alto.

A pergunta é: o que deu errado?

## Tigers (Riscos Reais)

### 1. Fluxos oficiais continuam duplicados

- **Tipo**: Tiger
- **Urgência**: Launch-Blocking
- **Risco**: O sistema continua com mais de um caminho para executar a mesma coisa. Isso mantém o time sem saber qual fluxo é o oficial e faz correções em um lugar não resolverem o problema real.
- **Por que isso é sério**: Esse é o tipo de risco que não só gera bug. Ele também gera retrabalho, decisões confusas e regressão escondida.
- **Mitigação sugerida**: Escolher e documentar um único fluxo oficial para execução, orquestração e streaming. Tudo que for compatibilidade antiga deve virar adaptador explícito, com prazo de remoção.

### 2. Configuração segue espalhada

- **Tipo**: Tiger
- **Urgência**: Launch-Blocking
- **Risco**: Variáveis, defaults e locais de leitura continuam diferentes entre módulos.
- **Por que isso é sério**: O projeto continua abrindo espaço para bugs de ambiente, setups quebrados e comportamento diferente entre máquina local, teste e produção.
- **Mitigação sugerida**: Consolidar uma fonte única de configuração, com um caminho oficial para `.env`, defaults únicos e regras claras de override.

### 3. A base de memória e armazenamento continua derrubando outras áreas

- **Tipo**: Tiger
- **Urgência**: Launch-Blocking
- **Risco**: Dependências de armazenamento vetorial continuam quebrando partes que não deveriam cair junto, como gRPC, workers e memória.
- **Por que isso é sério**: Uma única peça frágil segue causando falhas em vários módulos ao mesmo tempo.
- **Mitigação sugerida**: Tornar a dependência realmente opcional ou oficializá-la como obrigatória no setup. O estado intermediário atual é o pior dos dois mundos.

### 4. Recursos simulados continuam parecendo prontos

- **Tipo**: Tiger
- **Urgência**: Launch-Blocking
- **Risco**: Workers, serviços, partes do gRPC e o sistema de skills continuam expostos como se fossem entregas reais, quando várias partes ainda estão simuladas ou incompletas.
- **Por que isso é sério**: Isso cria falsa confiança no time, gera planejamento ruim e faz a prioridade errada parecer correta.
- **Mitigação sugerida**: Remover da superfície principal tudo que ainda não é confiável, ou fechar de vez a implementação mínima para cada recurso exposto.

### 5. Modelo de sessão e ownership segue inconsistente

- **Tipo**: Tiger
- **Urgência**: Launch-Blocking
- **Risco**: A lógica de sessão continua usando nomes e regras diferentes em áreas que deveriam concordar entre si.
- **Por que isso é sério**: Esse tipo de divergência costuma gerar bug silencioso, principalmente em autorização, listagem, contagem e recuperação de histórico.
- **Mitigação sugerida**: Fechar um contrato único para sessão, ownership e mensagens e alinhar API, serviços e armazenamento a essa decisão.

### 6. Documentação e testes continuam fora da realidade

- **Tipo**: Tiger
- **Urgência**: Fast-Follow
- **Risco**: O projeto continua com documentação otimista e testes baseados em estruturas antigas.
- **Por que isso é sério**: O time perde tempo, corrige o lugar errado e passa a duvidar da própria base.
- **Mitigação sugerida**: Tratar atualização de docs e testes como parte da entrega da estabilização, e não como sobra de tempo.

### 7. O sistema de skills continua quebrado na carga

- **Tipo**: Tiger
- **Urgência**: Fast-Follow
- **Risco**: O módulo de skills continua falhando logo na inicialização.
- **Por que isso é sério**: Isso bloqueia qualquer evolução real dessa área e mantém uma vitrine de capacidade que hoje não se sustenta.
- **Mitigação sugerida**: Decidir rapidamente entre corrigir o núcleo de skills ou tirá-lo do caminho principal até estar pronto.

### 8. O acúmulo de ajustes adiados vira um novo legado

- **Tipo**: Tiger
- **Urgência**: Track
- **Risco**: A iniciativa melhora alguns pontos, mas evita cortes difíceis. O resultado é apenas mais uma camada sobre o que já existe.
- **Por que isso é sério**: O sistema fica “menos ruim”, mas não realmente mais simples.
- **Mitigação sugerida**: Incluir remoção explícita no plano. Não estabilizar apenas adicionando mais código.

## Paper Tigers (Preocupações Superestimadas)

### 1. “Se removermos caminhos antigos, vamos perder flexibilidade”

- **Tipo**: Paper Tiger
- **Leitura**: O projeto hoje sofre mais por excesso de caminhos do que por falta deles. Reduzir duplicidade melhora clareza e velocidade.

### 2. “Temos que finalizar todas as áreas ao mesmo tempo”

- **Tipo**: Paper Tiger
- **Leitura**: Não precisa. O ganho maior vem de fechar primeiro o núcleo real do sistema e esconder ou adiar o que ainda está cru.

### 3. “A camada de segurança pequena significa que o sistema inteiro está inseguro”

- **Tipo**: Paper Tiger
- **Leitura**: A análise mostrou uma base simples, porém saudável. O problema hoje é mais de cobertura e amplitude do que de colapso total.

### 4. “Apenas atualizar testes resolve a situação”

- **Tipo**: Paper Tiger
- **Leitura**: Atualizar testes ajuda, mas não resolve o problema central. Primeiro é preciso reduzir ambiguidade estrutural.

## Elephants (Assuntos Pouco Enfrentados)

### 1. O projeto parece maior do que realmente é

- **Tipo**: Elephant
- **Dúvida central**: O time pode estar sustentando uma narrativa de produto mais ampla do que a base confiável atual.
- **O que investigar**: Quais capacidades são realmente usadas hoje? Quais são apenas planejadas? Quais devem sair do centro do discurso?

### 2. Não existe uma política clara de remoção

- **Tipo**: Elephant
- **Dúvida central**: O projeto adiciona compatibilidade e adaptação, mas raramente encerra ciclos antigos.
- **O que investigar**: Criar regra objetiva para remover legado, com data e dono.

### 3. Não está claro se execução distribuída é prioridade agora

- **Tipo**: Elephant
- **Dúvida central**: gRPC e parte dos workers parecem mais avançados na intenção do que na necessidade real atual.
- **O que investigar**: Confirmar se isso é prioridade de produto ou se está consumindo espaço demais antes da hora.

### 4. O time pode estar subestimando o custo da inconsistência de contratos

- **Tipo**: Elephant
- **Dúvida central**: Interfaces, serviços, schemas e persistência já mostram sinais de desencontro.
- **O que investigar**: Mapear os contratos que precisam virar referência oficial antes de qualquer expansão.

## Action Plans for Launch-Blocking Tigers

### 1. Fluxos oficiais continuam duplicados

- **Risco**: Mais de um caminho para executar a mesma coisa.
- **Mitigação**: Definir o fluxo oficial de execução e marcar explicitamente os adaptadores antigos para remoção.
- **Owner**: Engenharia de Plataforma / Arquitetura
- **Due Date**: 2026-03-24

### 2. Configuração segue espalhada

- **Risco**: Comportamento inconsistente entre módulos e ambientes.
- **Mitigação**: Publicar uma política única de configuração e migrar os módulos principais para ela.
- **Owner**: Engenharia Backend
- **Due Date**: 2026-03-26

### 3. Memória e armazenamento seguem derrubando outras áreas

- **Risco**: Dependência frágil continua bloqueando testes e módulos importantes.
- **Mitigação**: Decidir entre tornar a dependência obrigatória no setup padrão ou isolar a carga para ela não quebrar o restante.
- **Owner**: Backend + Infraestrutura
- **Due Date**: 2026-03-25

### 4. Recursos simulados continuam parecendo prontos

- **Risco**: O time e os consumidores internos planejam em cima de algo que ainda não está pronto.
- **Mitigação**: Revisar a superfície pública do projeto e esconder, rotular ou remover o que ainda está em estado parcial.
- **Owner**: Produto Técnico + Engenharia
- **Due Date**: 2026-03-28

### 5. Modelo de sessão e ownership segue inconsistente

- **Risco**: Sessões e permissões continuam frágeis.
- **Mitigação**: Fechar contrato único de sessão, ownership e histórico, depois alinhar API, serviços e persistência.
- **Owner**: Backend
- **Due Date**: 2026-03-27

## Critério de Saída deste Pre-Mortem

Esta iniciativa só deve ser considerada pronta para seguir sem alto risco quando:

- existir um fluxo oficial claro para execução;
- a configuração estiver centralizada;
- memória e armazenamento não derrubarem módulos vizinhos;
- recursos incompletos deixarem de parecer prontos;
- o contrato de sessão estiver unificado;
- documentação e testes já refletirem a realidade do sistema.
