# Pre-Mortem: MindFlow v2 — Design Refactor + Desktop Enterprise

**Data:** 2026-03-17
**Produto:** Aplicação desktop enterprise multi-plataforma (Windows, Mac, Linux) com usuários reais
**Modelo:** Híbrido — cloud (servidores MindFlow) + self-hosted (infra do cliente). Mesmo cliente desktop serve ambos.
**Escopo:** Refatoração de design para v2, Delegation Inspector interativo, empacotamento nativo
**Imaginação de falha:** Lançamento em 14 dias → usuários cloud não conseguem autenticar, usuários self-hosted ficam presos em setup, o app é bloqueado pelo SO, o chat trava, e o inspector não sincroniza com os agentes reais

---

## Contexto do Produto

MindFlow será uma aplicação desktop **enterprise** com distribuição real para usuários pagantes em Windows, Mac e Linux. O produto central é um Chat UI que orquestra agentes de IA especializados. O design v2 (`mindflow.pen`) define o novo sistema visual com 6 famílias tipográficas, delegation inspector com stacked cards, agent todo list e memory recall notifiers.

**Modelo de deployment híbrido:** o mesmo binário desktop suporta dois modos:
- **Cloud**: conecta nos servidores MindFlow — usuário faz login, zero setup
- **Self-hosted**: usuário aponta o app para a URL do seu próprio servidor (Docker Compose na infra deles)

Esse modelo elimina o Elephant E1 original (descoberta do backend), mas cria uma nova camada de riscos em autenticação, onboarding e distribuição do backend.

### Mapa de Componentes: Atual → v2

| Componente atual | Equivalente v2 | Complexidade |
|---|---|---|
| `AgentBubble.tsx` | Message Cards (por agente, Cormorant Garamond) | Média |
| `ThoughtBubble.tsx` | Thinking States (pills animados) | Baixa |
| `DelegationCard.tsx` | Delegation Card (NZTyZ) com header CPU + footer timer | Alta |
| `DelegationInspector.tsx` | Delegation Inspector (HWv2m) stacked cards + left rail | **Muito Alta** |
| `StreamNotifier.tsx` | Notifier Pills (5 variantes: routing/tool/done/error/warn) | Média |
| `ToolCallBlock.tsx` + `FSNotifier.tsx` | Notifier Pills + Inspector | Média |
| `TopBar.tsx` | Top Bar v2 simplificado | Baixa |
| `Sidebar.tsx` | Sidebar v2 (cosmético) | Baixa |
| `FolderPathBar.tsx` | Integrar como subtítulo no Top Bar | Baixa |
| `MainLayout.tsx` | Layout com 3 slots: Sidebar | Chat | Inspector | Alta |
| **NOVO** | Agent Todo List (todoListCompLight/Dark) | Alta |
| **NOVO** | Memory Recall notifiers (Vector + DB, 4 variantes) | Média |
| `ChatInterface.tsx` | Chat Area (orquestra tudo) | **Crítico** |

---

## Tigers (Riscos Reais)

### 🐯 T1 — Code Signing é obrigatório e leva semanas para obter [LAUNCH-BLOCKING]

**O risco:** Para distribuir para **usuários reais** em Windows e macOS:

- **Windows**: Sem assinatura digital, o SmartScreen bloqueia a instalação com aviso vermelho "App Unknown Publisher". Usuários corporativos têm políticas de segurança que bloqueiam executáveis não assinados automaticamente. Certificados EV (Extended Validation) custam $200–400/ano e levam 1–3 semanas para verificação de identidade empresarial.
- **macOS**: Gatekeeper bloqueia totalmente apps não assinados em macOS 10.15+. Notarização pela Apple é obrigatória mesmo para distribuição fora da App Store. Requer Apple Developer Program ($99/ano) + processo de notarização com 15–30 min por build.
- **Linux**: AppImage não requer assinatura, mas `.deb` para repositórios requer GPG key.

**Por que é Launch-Blocking:** Sem code signing, usuários corporativos simplesmente não conseguem instalar o produto. Isso não é negociável em enterprise.

**Mitigação:**
1. Registrar Apple Developer Program imediatamente (processo leva dias)
2. Comprar certificado EV Windows — DigiCert ou Sectigo são os mais compatíveis com SmartScreen
3. Configurar pipeline de notarização macOS no CI desde o início (não no final)
4. Para Linux: GPG key própria para repositório apt/yum opcional; AppImage é suficiente para V1

**Owner:** Fundador / Juridico
**Prazo:** Iniciar processo **hoje** — o clock já está correndo

---

### 🐯 T2 — Self-hosted requer Docker e setup de infra que usuários não-técnicos não farão [LAUNCH-BLOCKING]

**O risco:** No modelo self-hosted, o usuário precisa rodar o backend MindFlow na própria infra. O sistema atual depende de PostgreSQL (via Docker) + Python venv + variáveis de ambiente + Alembic migrations + Redis (workers). Mesmo com um `docker-compose.yml` bem feito, esse processo assume que o usuário:
- Tem Docker instalado
- Entende de redes e portas
- Consegue resolver conflitos de porta
- Sabe ler logs para debugar

Em contexto enterprise IT/DevOps isso é razoável. Para equipes pequenas ou startups sem DevOps, é uma barreira de entrada alta.

**O que o modelo híbrido resolve:** Usuários que não querem lidar com infra simplesmente usam o modo cloud. Self-hosted é para clientes que têm requisito de dados on-premise (compliance, LGPD/GDPR, dados sensíveis). Esses clientes geralmente têm equipe técnica.

**O risco residual:** A UX de configuração do modo self-hosted no cliente desktop. O usuário precisa de uma tela onde insere a URL do seu servidor — e o app precisa validar conectividade, versão do backend compatível, e autenticar antes de liberar o acesso.

**Mitigação:**
1. Docker Compose como único método de distribuição self-hosted (não PyInstaller — muito complexo)
2. Tela de onboarding no desktop: "Usar MindFlow Cloud" vs "Conectar ao meu servidor (URL)"
3. Health check endpoint no backend que retorna versão compatível — o cliente valida antes de permitir uso
4. Documentação de instalação self-hosted como produto em si (não afterthought)

**Owner:** Backend + Product
**Prazo:** Docker Compose funcional: Semana 2. Tela de conexão: Semana 1

---

### 🐯 T3 — Framework desktop sem suporte enterprise multi-plataforma [LAUNCH-BLOCKING]

**O risco:** A decisão Electron vs. Tauri tem implicações enterprise muito diferentes:

| Critério | Electron | Tauri |
|---|---|---|
| Code signing | ✅ `electron-builder` tem suporte nativo a Win+Mac signing | ✅ `tauri-bundler` também, mas setup mais manual |
| Auto-updater | ✅ `electron-updater` (battle-tested, GitHub Releases) | ⚠️ Plugin `tauri-plugin-updater` (mais novo) |
| Bundle size | ❌ ~150MB (Chromium bundlado) | ✅ ~10-15MB (usa WebView do SO) |
| Windows 7/8 | ✅ Chromium cobre versões antigas | ❌ WebView2 requer Windows 10+ |
| macOS WebView | N/A (usa Chromium) | ⚠️ WKWebView — bugs em SSE em versões antigas |
| SSE (streaming) | ✅ Nativo via browser Chromium | ⚠️ WKWebView tem limitações com SSE de longa duração |
| CI/CD 3 plataformas | ✅ GitHub Actions `macos-latest + windows-latest + ubuntu-latest` | ✅ Similar |
| Equipe Rust necessária | ❌ Não | ✅ Sim para plugins nativos |

**Recomendação para enterprise:** **Electron** — o ecossistema de distribuição enterprise é mais maduro. O tamanho do bundle (150MB) é aceitável para desktop enterprise (VS Code, Slack, Discord, todos usam Electron). SSE é crítico para o streaming do produto — o comportamento em WebView pode ser imprevisível.

**Owner:** Tech Lead
**Prazo:** Decidir antes de qualquer código (Dia 1)

---

### 🐯 T4 — Auto-updater é obrigatório em enterprise [LAUNCH-BLOCKING]

**O risco:** Usuários enterprise não atualizam manualmente. Sem auto-updater:
- Bugs críticos de segurança ficam em produção nos clientes
- Features novas não chegam
- Versões fragmentadas impossibilitam suporte

`electron-updater` (com GitHub Releases ou S3) resolve isso mas requer:
1. Servidor de update (GitHub Releases funciona para V1)
2. Build assinado (sem assinatura, o updater falha no macOS/Windows)
3. Canal de rollout (staged releases para não quebrar todos ao mesmo tempo)

**Mitigação:** Configurar `electron-updater` + GitHub Releases no pipeline CI desde o primeiro build. Não é possível adicionar isso "depois" sem reconfigurar toda a pipeline de release.

**Owner:** DevOps / CI
**Prazo:** Junto com setup inicial do Electron (Semana 1)

---

### 🐯 T5 — `ChatInterface.tsx` é um monólito de alto risco [LAUNCH-BLOCKING]

**O risco:** `ChatInterface.tsx` gerencia simultaneamente: stream SSE, renderização de mensagens, tool calls, delegations, salvamento no DB, e estado do inspector. Refatorar visual + lógica + adicionar inspector ao mesmo tempo no componente central = regressão silenciosa no produto principal.

Um evento SSE que deixa de ser renderizado corretamente é invisível nos testes manuais mas destrói a experiência do usuário real.

**Mitigação:**
1. **Fase A** (visual puro): só trocar estilos/tokens, sem mover lógica — PR separado
2. **Fase B** (extração): criar `useDelegationStack()`, `useMessageRenderer()` — PR separado
3. **Fase C** (inspector): integrar stacked cards após hooks estáveis

**Owner:** Frontend
**Prazo:** Sequencial — A antes de B, B antes de C

---

### 🐯 T6 — Delegation Inspector: state machine não trivial [FAST-FOLLOW]

**O risco:** O design `HWv2m` exige uma fila de agentes delegados com animação de stack (front/back1/back2 com `transform: translateY + scale + opacity`), sincronizada com eventos SSE reais. Sem um model de estado explícito, o resultado é jank visual e desync com o estado real da orquestração.

**Mitigação:** `useDelegationStack()` como hook isolado. Testar com mock SSE antes de integrar stream real. Limitar stack a 3 cards visíveis.

**Owner:** Frontend
**Prazo:** Semana 2

---

### 🐯 T7 — Banco de dados local vs. sincronização cloud [FAST-FOLLOW]

**O risco:** Atualmente o backend usa PostgreSQL em Docker. Para usuários enterprise desktop:
- SQLite embarcado: simples, zero configuração, sem Docker
- PostgreSQL local: requer instalação separada — inaceitável para usuários não-técnicos
- Backend SaaS (cloud): resolve tudo mas muda o modelo de negócio

Se o modelo for self-hosted, o banco precisa ser bundlado (SQLite via SQLAlchemy tem suporte no código atual via troca do driver).

**Mitigação:** Avaliar migração para SQLite para o modo desktop self-hosted. A maioria das queries existentes é compatível — exceto as que usam `pgvector`. Vector search em SQLite pode usar `sqlite-vss` ou ser desabilitado em V1.

**Owner:** Backend
**Prazo:** Decisão junto com T2

---

### 🐯 T8 — Bundling de 6 famílias tipográficas [FAST-FOLLOW]

**O risco:** O design v2 usa: JetBrains Mono, Newsreader, Cormorant Garamond, Familjen Grotesk, Azeret Mono, Space Grotesk. Em desktop, essas fontes precisam ser bundladas como `.woff2` locais. Sem isso, o app cai para fallback genérico destruindo o design.

**Mitigação:** Baixar todas as `.woff2`, importar via `@font-face` no `index.css`. Validar no Electron antes de qualquer trabalho visual.

**Owner:** Frontend
**Prazo:** Semana 1, Dia 2

---

## Paper Tigers (Preocupações Infundadas)

### 📄 PT1 — "Performance do Electron vai ser ruim para enterprise"

**Por que não é real:** VS Code, Slack, Figma, Linear, Notion e 1Password usam Electron em produção enterprise com milhões de usuários. Para uma aplicação de chat com streaming de texto, Chromium tem performance mais que suficiente. O gargalo é latência da LLM, não o renderer.

### 📄 PT2 — "Dark/Light theme vai ser complexo"

**Por que não é real:** O design v2 fornece explicitamente ambos os temas com tokens distintos. O `ThemeController` já existe no código. A implementação é trocar variáveis CSS, não reescrever lógica.

### 📄 PT3 — "Usuários Linux são um problema"

**Por que não é real:** AppImage é zero-install, roda em qualquer distro sem root, e não requer assinatura. É o formato mais aceito para apps Linux modernos. Para V1, AppImage é suficiente.

### 📄 PT4 — "Será necessário reescrever o backend em outra linguagem"

**Por que não é real:** Python com PyInstaller ou via backend cloud é uma solução válida. Empresas como Dropbox e Spotify rodaram Python em produção por anos. A linguagem não é o problema — a distribuição é.

### 📄 PT5 — "Conformidade GDPR/SOC2 bloqueará o lançamento"

**Por que não é real:** Para V1 enterprise early access, conformidade formal não é necessária. O que é necessário é uma política de privacidade honesta e não coletar dados sem consentimento. Certificações formais vêm com tração.

---

## Elephants (Preocupações Não Discutidas)

### 🐘 E1 — Autenticação: o sistema atual não tem auth real para multi-tenant

O modelo híbrido (cloud + self-hosted) resolve a questão de "onde está o backend" — mas cria um requisito de auth que o sistema atual não tem. O middleware `infra/middleware/auth.py` existe mas aparenta não estar implementado com usuários reais.

No modelo híbrido:
- **Cloud**: JWT por usuário, organizações, billing, rate limiting por tenant
- **Self-hosted**: o cliente aponta para o próprio servidor, mas ainda precisa autenticar usuários da empresa (quem pode usar o MindFlow daquela instância?)

Adicionar auth multi-tenant é uma refatoração de fundação, não uma feature. Não há como incrementar isso depois sem breaking changes na API.

**Recomendação:** Supabase Auth ou Clerk como provider externo — eliminam implementação do zero e já têm suporte a organizations/teams. O backend valida o JWT do provider, sem gerenciar senhas.

---

### 🐘 E2 — A tela de conexão (cloud vs. self-hosted) não existe no design v2

O cliente desktop precisa de uma tela de onboarding onde o usuário escolhe:
- "Usar MindFlow Cloud" (conecta nos servidores MindFlow, faz login)
- "Conectar ao meu servidor" (insere URL, valida conectividade, autentica)

Essa tela **não existe no design v2** (`mindflow.pen`). Ela precisa ser desenhada e implementada antes do launch. É o primeiro ponto de contato do usuário com o produto.

**Recomendação:** Desenhar essa tela antes de qualquer implementação de auth — é onde o modo cloud vs. self-hosted se bifurca na UX.

---

### 🐘 E3 — Segurança das chaves de API dos LLM providers no modo self-hosted

No self-hosted, o cliente traz os próprios LLM providers (Vertex AI, OpenAI, Anthropic). As credenciais precisam ser armazenadas de forma segura:
- **Hoje:** `serviceAccountVertex.json` em path hardcoded no servidor de desenvolvimento
- **Self-hosted enterprise:** credenciais devem viver no keystore do SO (macOS Keychain, Windows Credential Store, Linux Secret Service) — não em arquivos de texto no filesystem
- **Cloud:** as chaves ficam no backend MindFlow — o usuário nunca as vê

BYOK (Bring Your Own Key) é um diferencial enterprise importante para self-hosted. Não está implementado nem desenhado.

---

### 🐘 E4 — `displayPolicy.ts` não mapeia eventos de Todo List e Memory Recall

O design v2 inclui `Agent Todo List` e `Memory Recall notifiers` (Vector + DB, 4 variantes). O backend tem `todo_planning_service.py`. Mas o schema do evento SSE, o mapeamento em `notifierMapping.ts`, e a lógica em `displayPolicy.ts` não estão definidos para esses novos componentes.

Se não forem auditados antes da implementação, esses componentes serão construídos contra um contrato de evento imaginário e quebrarão com o backend real.

---

### 🐘 E5 — Versionamento de API entre cliente desktop e backend (cloud + self-hosted)

No modelo híbrido, o cliente desktop pode estar em versão `1.2` enquanto:
- O backend cloud está em `1.3` (você fez deploy antes do cliente atualizar)
- O backend self-hosted do cliente está em `1.0` (cliente não atualizou a infra dele)

Sem versionamento explícito da API e compatibilidade retroativa declarada, clientes self-hosted em versão antiga vão quebrar silenciosamente quando o cliente desktop atualizar.

**Recomendação:** Health check endpoint com `{"version": "1.x", "min_client": "1.y"}`. O cliente desktop verifica compatibilidade no startup e exibe aviso claro se incompatível.

---

### 🐘 E6 — Telemetria e crash reporting: como você sabe que algo quebrou?

Para usuários reais, quando algo falha silenciosamente (stream SSE para, inspector não sincroniza, auth expira):
- Você não saberá — a menos que o usuário reclame
- Em self-hosted, você tem ainda menos visibilidade

Sentry funciona em ambos os modos: para cloud, captura erros no backend e frontend. Para self-hosted, o cliente desktop envia crash reports para o Sentry do MindFlow (com consentimento do usuário). Isso é o que GitLab e Sentry fazem com as próprias instâncias.

Nenhuma dessas infraestruturas existe no projeto atual.

---

## Planos de Ação — Tigers Launch-Blocking

### Plano 1: Code Signing (T1)
| Campo | Detalhe |
|---|---|
| **Risco** | Usuários enterprise não conseguem instalar sem assinatura |
| **Ação imediata** | Registrar Apple Developer Program + iniciar compra de certificado EV Windows |
| **Ação técnica** | Configurar `electron-builder` com entitlements macOS + Windows signtool no CI |
| **Owner** | Fundador |
| **Prazo** | Iniciar hoje; certificado EV leva 1–3 semanas |

### Plano 2: Self-hosted via Docker Compose + tela de conexão (T2)
| Campo | Detalhe |
|---|---|
| **Risco** | Usuários self-hosted travam no setup sem guia claro |
| **Ação** | Docker Compose com todos os serviços (backend + PostgreSQL + Redis) em um único `docker-compose.yml` |
| **Ação UX** | Tela de onboarding no desktop: "MindFlow Cloud" vs "Meu servidor (URL)" com health check de compatibilidade |
| **Owner** | Backend + Product |
| **Prazo** | Docker Compose: Semana 2. Tela de conexão: Semana 1 |

### Plano 3: Framework Desktop (T3)
| Campo | Detalhe |
|---|---|
| **Risco** | Decisão tardia bloqueia toda a arquitetura |
| **Recomendação** | Electron + `electron-vite` + `electron-builder` |
| **Justificativa** | Ecossistema enterprise maduro, SSE nativo, equipe sem Rust |
| **Owner** | Tech Lead |
| **Prazo** | 2026-03-18 |

### Plano 4: Auto-updater (T4)
| Campo | Detalhe |
|---|---|
| **Risco** | Bugs em produção ficam nos clientes sem update channel |
| **Ação** | Configurar `electron-updater` + GitHub Releases no primeiro build |
| **Dependência** | Requer code signing (T1) para funcionar em Mac/Win |
| **Owner** | DevOps |
| **Prazo** | Semana 1 do setup Electron |

### Plano 5: Refatoração Sequencial de ChatInterface.tsx (T5)
| Campo | Detalhe |
|---|---|
| **Risco** | Regressão silenciosa no produto central |
| **Fase A** | Visual puro (tokens/CSS) — sem mover lógica |
| **Fase B** | Extração de hooks (`useDelegationStack`, `useMessageRenderer`) |
| **Fase C** | Inspector integration após hooks estáveis |
| **Owner** | Frontend |
| **Prazo** | A: Semana 1. B: Semana 2. C: Semana 2-3 |

---

## Sequência de Implementação Recomendada

```
Agora (esta semana):
├── Decisão: SaaS vs. Self-hosted (T2) — tudo depende disso
├── Decisão: Electron vs. Tauri (T3)
├── Iniciar: Apple Developer Program + certificado EV Windows (T1)
└── Iniciar: tokens-v2.css + bundling de fontes

Semana 1 (após decisões):
├── Setup Electron + electron-builder + electron-updater
├── tokens-v2.css com todas as variáveis CSS do v2
├── Bundling das 6 fontes (.woff2 local)
└── Refatoração visual leaf components (AgentBubble, ThoughtBubble, NotifierPill)

Semana 2:
├── Extração de hooks de ChatInterface.tsx (Fase B)
├── MainLayout com rightPanel slot
├── Delegation Inspector (state machine + stacked cards)
└── Agent Todo List + Memory Recall notifiers

Semana 3:
├── CI/CD multi-plataforma (GitHub Actions: mac, win, linux)
├── Code signing integrado no pipeline
├── Testes de instalação em cada SO
└── Crash reporting (Sentry)
```

---

## Resumo Executivo

| Tipo | Quantidade | Criticidade |
|---|---|---|
| Tigers Launch-Blocking | 5 (T1–T5) | Todos bloqueiam distribuição enterprise |
| Tigers Fast-Follow | 3 (T6–T8) | Qualidade pós-V1 |
| Paper Tigers | 5 | Descartados |
| Elephants | 5 | Investigar antes da implementação |

**O modelo híbrido (cloud + self-hosted) é a decisão certa para enterprise.** Ele resolve o conflito anterior e alinha o produto com o que empresas como GitLab, Metabase e Sentry fazem com sucesso. Mas ele cria dois novos requisitos não triviais que precisam de atenção imediata: **autenticação multi-tenant** (E1) e **tela de conexão/onboarding** (E2).

**O risco mais urgente continua sendo code signing (T1)** — processo burocrático que não pode ser acelerado. Iniciar hoje.

**No frontend, o risco é sequenciamento** — visual → extração de lógica → features novas, nunca em paralelo no `ChatInterface.tsx`.

**O diferencial do modelo híbrido:** usuários cloud têm zero friction de setup. Usuários self-hosted têm controle total dos dados — argumento decisivo para enterprise com compliance LGPD/GDPR/HIPAA. Os dois segmentos se complementam sem canibalizar.
