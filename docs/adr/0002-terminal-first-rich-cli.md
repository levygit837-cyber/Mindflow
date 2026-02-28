# ADR 0002 - Terminal-First com Rich CLI e Depreciação de Mind/PySide6

- Status: Accepted
- Data: 2026-02-28
- Decisores: @LevyBonito
- Tags: arquitetura, runtime, cli, frontend, produtividade

## Contexto

O OmniMind consolidou o runtime principal em Python (`omnimind_backend`) e removeu o domínio `mind` do aplicativo.
Ao mesmo tempo, a manutenção de um frontend desktop Python com PySide6/QML adiciona custo de evolução, acoplamento de UI e overhead operacional para fluxos que são essencialmente de engenharia (chat, execução, observabilidade e automação).

Além disso, o produto precisa de:

- feedback em tempo real para streaming de eventos;
- workflows customizáveis por comando;
- baixo custo de iteração para novos fluxos;
- experiência consistente com uso local em terminal.

## Decisao

Adotar arquitetura `terminal-first` para a camada de interação principal, com CLI em Python baseada em `Typer + Rich`, e descontinuar o frontend Python atual (`omnimind_desktop`) por fases.

A decisão inclui:

1. `mind` permanece fora do escopo do runtime principal.
2. O canal principal de UX passa a ser CLI (`omnimind_cli`).
3. `Rich` será a base de renderização para:
   - timelines e stream de eventos (`thought`, `tool_call`, `tool_result`, `response`),
   - progresso de execução (workflows),
   - diagnóstico e logs operacionais.
4. `Typer` será a base de comandos e composição de workflows.
5. API backend mantém contrato HTTP/SSE estável como interface para CLI.

## Alternativas Consideradas

1. Manter PySide6/QML como frontend principal.
2. Migrar imediatamente para frontend web (React/Next/Vue).
3. Operar exclusivamente backend headless sem interface de produto.

Trade-offs:

- (1) preserva UI visual, mas aumenta custo de manutenção e desacelera ciclo de entrega.
- (2) pode entregar UX rica, porém exige investimento maior de frontend e infraestrutura de produto neste momento.
- (3) simplifica arquitetura, mas reduz usabilidade e operação diária para casos de uso humanos.

## Consequencias

### Positivas

- Maior velocidade de entrega para fluxos de engenharia.
- Observabilidade melhor em runtime via terminal (stream e status em tempo real).
- Menor superfície de manutenção de frontend no curto prazo.
- Melhor alinhamento com execução local e automação.

### Negativas

- Redução temporária de UX visual para usuários não técnicos.
- Necessidade de desenhar padrões de UX textual (navegação, estados e erros).
- Curva de adaptação para workflows orientados a comando.

## Plano de Implementacao

1. Criar pacote `omnimind_cli` com comandos base (`health`, `chat`, `workflow`).
2. Definir tema visual e contrato de renderização de eventos no terminal (Rich).
3. Integrar CLI ao endpoint `POST /v1/agent/chat/stream` com parsing SSE robusto.
4. Adicionar comandos de operação (logs, diagnósticos, smoke checks).
5. Atualizar documentação principal para refletir arquitetura terminal-first.

## Plano de Migracao

1. Congelar novas features no `omnimind_desktop`.
2. Entregar paridade funcional mínima no `omnimind_cli` para uso diário.
3. Marcar `omnimind_desktop` como `Deprecated` em docs e scripts de execução.
4. Remover gradualmente módulos e dependências de desktop quando a paridade for atingida.
5. Caso necessário, manter branch/tag de rollback da UI desktop durante a transição.

## Referencias

- PR(s):
- Documento(s): `docs/architecture/python-backend.md`, `docs/architecture/python-engineering-standards.md`
- Issue(s):
