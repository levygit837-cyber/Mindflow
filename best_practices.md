📘 Project Best Practices

#### 1. Project Purpose
_Short paragraph summarizing what the project does and its domain_

Este repositório implementa uma plataforma chamada MindFlow que orquestra agentes, ferramentas e memória para construir fluxos de trabalho inteligentes. Contém uma aplicação backend Python (gestão de agentes, gRPC, execução de workflows, armazenamentos), uma camada CLI para interação/automação, uma versão desktop (QML/python) e um frontend web em TypeScript + React (Vite). Há também infra/ops (Docker, certificados, scripts) e utilitários para testes, migrações e demonstrações.

#### 2. Project Structure
- Overview of folder layout
  - /frontend — Aplicação web em TypeScript/React (Vite). Contém componentes, hooks, páginas, stores e utilities.
  - /python/backend — Exemplos e código auxiliar de integração gRPC e outros utilitários.
  - /mindflow_backend — Core do servidor: agentes, chains, orchestrator, memória, grpc, infra, services, skills, storage, schemas, tests, etc.
  - /mindflow_cli — Ferramenta CLI para interagir com o backend e renderizar saídas.
  - /mindflow_desktop — Versão desktop usando QML/pyqt (interfaces e viewmodels).
  - /docs — Documentação analítica e notas (ex.: notifier-analysis.md).
  - /certs — Certificados usados para TLS e testes locais.
  - /docker, docker-compose.yml, docker-compose.backend.yml — Infração para desenvolvimento e deployment.
  - /scripts — Scripts utilitários para geração de certificados, backups, start/stop, migrações.
  - /tests — Casos de teste e utilitários de teste globais; cada submódulo (ex: mindflow_backend/tests) contém testes específicos.
  - Arquivos de configuração principais: pyproject.toml, requirements-test.txt, pytest.ini, alembic.ini, .pre-commit-config.yaml, eslint.config.js, tsconfig.json

- Description of roles of key directories/files
  - mindflow_backend/: implementação do domínio e infra do sistema. Separe claramente: agents/ (lógica de agentes), services/ (regras de negócio), infra/ (acessos a banco/gRPC/wrappers), storage/ (persistência), schemas/ (validação/serialização), orchestrator/ (coordenação de execução).
  - frontend/: interface do usuário. Mantê-la isolada do backend por meio de APIs bem definidas (REST/gRPC-Web) e contratos de tipos (shared types se necessário).
  - mindflow_cli/: scripts e comandos para automação e debug; bons candidatos para testes de integração e scripts de e2e.
  - certs/: manter fora de commits públicos (evitar chaves privadas em repositório público). Aqui parece conter certificados locais — trate-os como exemplos e rotacione em produção.

#### 3. Test Strategy
- Framework(s) used
  - Backend: pytest (presença de pytest.ini e múltiplos test_*.py). Use fixtures e parametrização do pytest.
  - Frontend: Playwright é usado para e2e (pastas output/playwright). O frontend também pode usar vitest/jest se configurado (ver package.json).
  - Integração: existem exemplos com gRPC e scripts de integração (examples/ e python/examples/). Use containers para testes de integração que precisem de dependências (banco, serviços grpc).

- How and where tests are organized
  - Unit tests próximos ao código do domínio: mindflow_backend/tests/ para componentes do backend.
  - Scripts de exemplo e demos em python/examples/ servem como testes de integração / smoke tests.
  - Playwright/E2E: output/playwright/ e frontend testes e2e devem ser colocados em frontend/tests/e2e.

- Mocking guidelines
  - Mock thin external boundaries: redes (gRPC), banco, e serviços externos. Use pytest fixtures para fornecer mocks reutilizáveis.
  - Evite mocks de lógica de domínio; prefira testes unitários sem infraestrutura quando possível.
  - Para gRPC: simule canais e stubs em testes unitários; reserve testes de integração para validar comportamento real entre serviços.

- When/how to write unit vs integration tests
  - Unit: regras de negócio, transformações puras, utilitários, validações de schemas. Rápidos, determinísticos, isolados de I/O.
  - Integration: orquestração de agentes, pipelines que tocam armazenamento, migrações (alembic), comportamento gRPC, e2e do frontend-backend. Use containers ou fixtures que inicializam infra necessária.
  - Cobertura: priorizar cobertura de lógica crítica (orquestração, execução de skills, manipulação de memória). Não tratar cobertura como objetivo final, mas como indicador.

#### 4. Code Style
- Language-specific rules (e.g. typing, async)
  - Python:
    - Use typing estático (typing, TypedDict, pydantic se já usado nos schemas) para contratos entre camadas.
    - Favor funções e classes pequenas e testáveis. Separe pure functions das que fazem I/O.
    - Use async/await nas camadas de I/O que suportam concorrência (gRPC async, chamadas HTTP/DB assíncronas). Padronize entre async e sync: não misture sem necessidade.
    - Use context managers para recursos (conexões DB, arquivos, sessões gRPC).
  - TypeScript/Frontend:
    - Use tipos estritos (noImplicitAny, strict). Centralize tipos compartilhados entre frontend e backend quando possível.
    - Prefira hooks e componentes funcionais. Mantenha side-effects isolados em hooks customizados.

- Naming conventions (functions, files, classes, variables)
  - Python: snake_case para funções e arquivos, PascalCase para classes, UPPER_SNAKE para constantes.
  - TypeScript: camelCase para funções/variáveis, PascalCase para componentes e tipos/interfaces, kebab-case para arquivos de componentes quando apropriado.
  - Arquivos de teste: test_<module>.py ou <module>_test.py (seguir convenção do pytest já em uso).

- Commenting and docstring habits
  - Use docstrings em módulos, classes e funções públicas explicando propósito, parâmetros e valores retornados. Preferencialmente no estilo Google ou numpydoc consistente.
  - Comentários inline apenas para explicar porquês não óbvios, não o quê (o código deve mostrar o quê).
  - Mantenha docs atualizados junto ao código; use validate_documentation.py para checar cobertura de documentação quando aplicável.

- Error and exception handling
  - Centralize erros customizados em exceptions/ para fácil mapeamento e tratamento (já existe pasta exceptions/).
  - Nunca suprimir exceções silenciosamente; capture, enriqueça e relance ou registre com contexto suficiente.
  - Padronize códigos de erro na camada API/gRPC para facilitar resolução (mapear Exception -> status gRPC/HTTP consistente).
  - Para operações críticas, adicione monitoramento e métricas (instrumentar erros que levam a retrys/exaustão).

#### 5. Common Patterns
- Reusable utilities or base classes
  - Separação clara entre domain, services e infra sugere uso de portas e adaptadores (hexagonal). Reutilizar interfaces/abstract base classes para storage e transport.
  - Utilitários em utils/ para funções puras reutilizáveis (serialização, validações, helper de logging).

- Design patterns or architectural approaches
  - Orquestrador central (orchestrator/) para coordenar execução de agentes/skills — use patterns de comando, controlador e pipeline.
  - Serviços (services/) contêm regras de negócio; infra/providers implementam detalhes (DB, gRPC).
  - Event-driven / worker patterns para execução assíncrona (workers/), com filas ou mecanismos de retry.

- Frequently used idioms
  - Fixtures de teste e configuração via arquivos e env vars (config/), com loaders centralizados.
  - Scripts e exemplos para demonstrar integrações (mantê-los como testes vivas). Sempre documentar a intenção e o pré-requisito para rodar cada demo.

#### 6. Do's and Don'ts
- ✅ Things developers should always do
  - ✅ Escrever testes novos ao adicionar lógica de orquestração ou manipulação de memória.
  - ✅ Manter contratos de tipos entre frontend e backend atualizados (usar typedefs compartilhadas quando possível).
  - ✅ Isolar I/O: escrever funções puras e testáveis separadas da camada de infra.
  - ✅ Utilizar fixtures pytest para recursos caros (DB, gRPC) e para limpar estado entre testes.
  - ✅ Usar pre-commit para formatação e lint (há .pre-commit-config.yaml).
  - ✅ Registrar contextos ricos em logs (correlation ids, agent ids) para rastreabilidade.
  - ✅ Tratar credenciais e chaves com cuidado: nunca comitar chaves privadas em repositório público.

- ❌ Common mistakes to avoid
  - ❌ Não misturar lógica de negócios com acesso direto a I/O.
  - ❌ Escrever testes que dependam de estado global não reinicializado.
  - ❌ Fazer mudanças em APIs sem atualizar contratos (schemas/ e clientes).
  - ❌ Supor sincronização em ambiente assíncrono; race conditions podem ocorrer em memory/workers.
  - ❌ Ignorar erros silenciosos em loops/retries — sempre logue e exponha métricas.

#### 7. Tools & Dependencies
- Key libraries and their purpose
  - Python: pytest (testes), gRPC libraries (proto/grpc infra), alembic (migrações), pydantic/typing (schemas) — confirme versões em requirements.txt/pyproject.toml.
  - Frontend: React, Vite, Playwright (e2e). eslint.config.js para linting.
  - Dev tooling: pre-commit, Docker, docker-compose para ambientes replicáveis.

- Project setup instructions (if relevant)
  - Desenvolvimento backend local (exemplo):
    1. Criar e ativar virtualenv: python -m venv .venv && source .venv/bin/activate
    2. Instalar dependências: pip install -r backend/requirements.txt (ou usar pyproject/poetry conforme configurado)
    3. Inicializar infra local: docker-compose up -d (se necessário) ou usar scripts/start_dev_fixed.sh
    4. Rodar migrações: alembic upgrade head (se aplicável)
    5. Rodar testes: pytest -q
  - Frontend:
    1. cd frontend && npm install
    2. npm run dev (Vite) para rodar localmente
    3. npm run test:e2e para Playwright
  - Uso de containers para testes de integração é recomendado — ver docker-compose.backend.yml e scripts/setup_local_stack.sh.

#### 8. Other Notes
- Anything important for an LLM to know when generating new code in this repo
  - Mantenha as camadas separadas: quando gerar código novo, identifique se é domain/service/infra e coloque no pacote correto.
  - Preferir tipagem explícita e validação de entrada (schemas/). Para endpoints/gRPC, atualizar os protos e gerar stubs correspondentes.
  - Para qualquer mudança em APIs, atualizar exemplos (python/examples/), docs/ e testes de integração.
  - Há scripts e demos que servem como referência de integração — utilize-os como testes manuais automatizáveis.
  - Evitar gerar ou commitar certificados reais; forneça caminhos configuráveis via variáveis de ambiente.

- Special edge cases or constraints
  - Concurrency & State: o sistema lida com memória e execução de agentes; atenção especial a condições de corrida, consistência e sincronização das operações de escrita na memória.
  - Migrations: o projeto tem alembic.ini — organizar e testar scripts de migração antes de rodar em produção.
  - Backwards compatibility: mantenha compatibilidade de mensagens gRPC/serialização ao evoluir schemas para não quebrar agentes existentes.


----

Versão gerada automaticamente: sumariza a estrutura atual do repositório e práticas recomendadas. Atualize este arquivo quando a arquitetura do projeto mudar ou quando novas convenções forem adotadas.
