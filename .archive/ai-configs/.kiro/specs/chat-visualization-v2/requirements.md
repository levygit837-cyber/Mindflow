    # Requirements Document

## Introduction

Este documento especifica os requisitos para a melhoria da visualização do Chat principal (chat-visualization-v2). O objetivo é resolver problemas de usabilidade na interface atual e adicionar novos componentes visuais V2 que melhoram a experiência de visualização das interações entre o Orquestrador e os Agentes delegados.

## Glossary

- **Chat_Principal**: Interface principal de conversação onde o usuário interage com o Orquestrador
- **Orquestrador**: Agente principal que coordena e delega tarefas para outros agentes
- **Agente**: Componente especializado que executa tarefas específicas delegadas pelo Orquestrador
- **Thinking_State**: Estado visual que indica que o Orquestrador ou Agente está processando informações
- **Delegation_Card**: Componente visual que representa a delegação de uma tarefa para um Agente
- **Notifier_Pill**: Indicador visual compacto de estado ou ação (ex: "Routing", "Read", "Success", "Error")
- **Tool_Call**: Execução de uma ferramenta específica por um Agente (ex: leitura de arquivo, busca, comando shell)
- **Agent_Journey**: Visualização expandida da sequência de ações executadas por um Agente delegado
- **Thought_Block**: Componente que exibe os pensamentos do Orquestrador de forma estruturada
- **Memory_Recall**: Componente que indica recuperação de contexto de memória
- **Token_by_Token**: Animação de escrita que exibe texto progressivamente, caractere por caractere
- **Pencil**: Arquivo principal do sistema de visualização do Chat

## Requirements

### Requirement 1: Remover Componentes Visuais Excessivos

**User Story:** Como usuário, eu quero uma interface mais compacta e limpa, para que eu possa visualizar mais conteúdo sem rolagem excessiva

#### Acceptance Criteria

1. THE Chat_Principal SHALL reduzir o tamanho dos componentes visuais em pelo menos 30% comparado à versão atual
2. THE Chat_Principal SHALL reduzir o tamanho dos textos para melhorar a densidade de informação
3. THE Chat_Principal SHALL remover eventos e notifiers desnecessários durante o envio de mensagens
4. THE Chat_Principal SHALL remover a mensagem "Recuperando Contexto de memória" da visualização
5. THE Chat_Principal SHALL remover completamente a jornada do Chat antiga

### Requirement 2: Corrigir Referências de Frontend Antigo

**User Story:** Como desenvolvedor, eu quero que todas as referências estejam atualizadas, para que o sistema não use código obsoleto

#### Acceptance Criteria

1. WHEN uma mensagem "Routing Request" é exibida, THE Chat_Principal SHALL usar referências do frontend atual
2. THE Chat_Principal SHALL remover todas as referências ao frontend antigo do código de visualização

### Requirement 3: Implementar Thinking States para Orquestrador

**User Story:** Como usuário, eu quero ver quando o Orquestrador está pensando, para que eu entenda que o sistema está processando minha solicitação

#### Acceptance Criteria

1. WHEN o Orquestrador está processando, THE Chat_Principal SHALL exibir um Thinking_State visual
2. THE Thinking_State SHALL incluir animação Token_by_Token para os pensamentos do Orquestrador
3. THE Chat_Principal SHALL NEVER exibir o thinking ou output completo instantaneamente
4. THE Thought_Block SHALL ser automaticamente colapsado após conclusão

### Requirement 4: Implementar Indicação Visual de Agentes

**User Story:** Como usuário, eu quero identificar visualmente cada Agente, para que eu saiba qual agente está executando cada tarefa

#### Acceptance Criteria

1. WHEN um Agente é ativado, THE Chat_Principal SHALL exibir uma indicação visual única para aquele Agente
2. THE Chat_Principal SHALL diferenciar visualmente o Orquestrador dos Agentes delegados
3. THE Chat_Principal SHALL manter a indicação visual consistente durante toda a execução do Agente

### Requirement 5: Implementar Card de Mensagens para Agentes

**User Story:** Como usuário, eu quero ver as mensagens de cada Agente organizadas em cards, para que eu possa distinguir facilmente as comunicações de diferentes agentes

#### Acceptance Criteria

1. WHEN um Agente envia uma mensagem, THE Chat_Principal SHALL exibir a mensagem em um Card de Mensagem específico
2. THE Card de Mensagem SHALL incluir identificação visual do Agente emissor
3. THE Chat_Principal SHALL dar prioridade visual aos cards do Orquestrador

### Requirement 6: Implementar Delegation Cards

**User Story:** Como usuário, eu quero ver quando o Orquestrador delega tarefas, para que eu entenda o fluxo de trabalho distribuído

#### Acceptance Criteria

1. WHEN o Orquestrador delega uma tarefa, THE Chat_Principal SHALL exibir um Delegation_Card
2. THE Delegation_Card SHALL indicar o AgentType que recebeu a delegação
3. THE Delegation_Card SHALL exibir o estado atual da delegação em tempo real
4. THE Delegation_Card SHALL incluir uma summary bar com o estado atual
5. THE Delegation_Card SHALL incluir um indicador de progresso da jornada em tempo real

### Requirement 7: Implementar Notifiers Pills

**User Story:** Como usuário, eu quero ver indicadores visuais compactos de estado, para que eu possa acompanhar ações sem poluição visual

#### Acceptance Criteria

1. WHEN o sistema está roteando uma solicitação, THE Chat_Principal SHALL exibir um Notifier_Pill "Routing" que transiciona para "Delegated"
2. WHEN o sistema lê dados, THE Chat_Principal SHALL exibir um Notifier_Pill "Read"
3. WHEN uma operação é concluída com sucesso, THE Chat_Principal SHALL exibir um Notifier_Pill "Success"
4. WHEN ocorre um erro, THE Chat_Principal SHALL exibir um Notifier_Pill "Error"
5. THE Notifier_Pill SHALL ter design compacto e não intrusivo

### Requirement 8: Implementar Memory Recall Visual

**User Story:** Como usuário, eu quero ver quando o sistema recupera contexto de memória, para que eu entenda de onde vem o conhecimento contextual

#### Acceptance Criteria

1. WHEN o sistema recupera contexto de memória, THE Chat_Principal SHALL exibir um componente Memory_Recall
2. THE Memory_Recall SHALL ter versão dark theme
3. WHERE light theme está ativo, THE Chat_Principal SHALL NOT exibir Memory_Recall

### Requirement 9: Implementar Agent Todo-list para Orquestrador

**User Story:** Como usuário, eu quero ver a lista de tarefas do Orquestrador, para que eu entenda o plano de execução

#### Acceptance Criteria

1. WHEN o Orquestrador cria um plano de tarefas, THE Chat_Principal SHALL exibir um Agent_Todo_list
2. THE Agent_Todo_list SHALL ter versão dark theme
3. WHERE light theme está ativo, THE Chat_Principal SHALL NOT exibir Agent_Todo_list
4. THE Agent_Todo_list SHALL atualizar em tempo real conforme tarefas são concluídas

### Requirement 10: Implementar Thought Block com Formatação Rica

**User Story:** Como usuário, eu quero ver os pensamentos do Orquestrador formatados, para que eu possa entender melhor o raciocínio

#### Acceptance Criteria

1. WHEN o Orquestrador gera pensamentos, THE Chat_Principal SHALL criar um Thought_Block automaticamente
2. THE Thought_Block SHALL suportar texto sublinhado, negrito e organização em colunas
3. THE Thought_Block SHALL ser colapsado por padrão
4. WHEN o usuário clica no Thought_Block, THE Chat_Principal SHALL expandir o bloco mostrando todo o conteúdo
5. THE Thought_Block SHALL usar animação Token_by_Token durante geração

### Requirement 11: Implementar Thought Chains

**User Story:** Como usuário, eu quero ver sequências de pensamentos relacionados agrupados, para que eu entenda o encadeamento lógico

#### Acceptance Criteria

1. WHEN o Orquestrador gera múltiplos pensamentos relacionados, THE Chat_Principal SHALL agrupá-los em Thought_Chains
2. THE Thought_Chains SHALL exibir a sequência de pensamentos ou tarefas em conjunto
3. THE Chat_Principal SHALL NOT incluir "Delegated" indicators dentro dos chains
4. THE Chat_Principal SHALL NOT incluir reasoning depth indicators
5. THE Chat_Principal SHALL NOT incluir Thought Summary nos chains

### Requirement 12: Implementar Agent Journey Expandível

**User Story:** Como usuário, eu quero ver detalhes da execução de um Agente, para que eu possa entender o que foi feito

#### Acceptance Criteria

1. WHEN o usuário clica em um Delegation_Card, THE Chat_Principal SHALL expandir o card para baixo
2. THE Agent_Journey expandido SHALL exibir uma timeline iniciando com "Delegation Received"
3. THE Agent_Journey SHALL exibir tool calls e thinking em tempo real
4. THE Agent_Journey SHALL ter área limitada com scroll vertical
5. WHEN o Agente finaliza, THE Agent_Journey SHALL exibir indicador verde e resumo
6. THE Chat_Principal SHALL suportar visualização de múltiplos Agent_Journey lado a lado

### Requirement 13: Implementar Tool Calls Colapsáveis

**User Story:** Como usuário, eu quero ver tool calls de forma compacta, para que eu possa expandir apenas quando necessário

#### Acceptance Criteria

1. WHEN um Tool_Call está em execução, THE Chat_Principal SHALL exibir resultado parcial visível
2. WHEN um Tool_Call é concluído, THE Chat_Principal SHALL colapsar o resultado automaticamente
3. WHEN o usuário clica em um Tool_Call colapsado, THE Chat_Principal SHALL expandir mostrando o resultado completo
4. THE Tool_Call SHALL suportar expansão de tool call para tool result

### Requirement 14: Implementar Tool Calls V2 Especializados

**User Story:** Como usuário, eu quero ver diferentes tipos de tool calls com visualizações apropriadas, para que eu entenda melhor cada operação

#### Acceptance Criteria

1. WHEN um Tool_Call do tipo Read é executado, THE Chat_Principal SHALL exibir o path e resultado com dados estruturados
2. WHEN um Tool_Call do tipo Shell é executado, THE Chat_Principal SHALL exibir visualização apropriada para comandos shell
3. WHEN um Tool_Call do tipo Grep_Search é executado, THE Chat_Principal SHALL exibir visualização apropriada para resultados de busca
4. THE Chat_Principal SHALL suportar Tool_Call_Group para exibir sequências de tool calls relacionados

### Requirement 15: Suportar Temas Light e Dark

**User Story:** Como usuário, eu quero que os componentes V2 respeitem meu tema preferido, para que a interface seja confortável visualmente

#### Acceptance Criteria

1. THE Chat_Principal SHALL fornecer versões light e dark de todos os componentes V2
2. WHERE dark theme está ativo, THE Chat_Principal SHALL exibir Memory_Recall e Agent_Todo_list
3. WHERE light theme está ativo, THE Chat_Principal SHALL NOT exibir Memory_Recall e Agent_Todo_list
4. THE Chat_Principal SHALL aplicar o tema consistentemente em todos os componentes

### Requirement 16: Integrar com Arquivo Pencil

**User Story:** Como desenvolvedor, eu quero que os componentes V2 sejam integrados ao arquivo principal, para que o sistema funcione de forma coesa

#### Acceptance Criteria

1. THE Chat_Principal SHALL integrar todos os componentes V2 através do arquivo Pencil
2. THE Pencil SHALL servir como ponto central de coordenação dos componentes visuais
3. THE Chat_Principal SHALL usar os componentes V2 existentes como referência visual
