# Visual Regression Testing - Chat Visualization V2

## Overview

Este documento descreve o setup e uso dos testes de visual regression testing para os componentes V2 do Chat MindFlow.

**Task:** 25.1 - Setup visual regression testing (optional)  
**Status:** ✅ Configurado e pronto para uso

## Setup

### 1. Instalar Playwright

```bash
cd frontend
npm install -D @playwright/test
```

### 2. Instalar Browsers

```bash
npx playwright install
```

Isso instalará Chromium, Firefox e WebKit para os testes.

### 3. Instalar Dependências do Servidor de Desenvolvimento

Certifique-se de que todas as dependências do frontend estão instaladas:

```bash
npm install
```

## Comandos Disponíveis

### Rodar todos os testes E2E e visuais

```bash
npm run test:e2e
```

### Rodar testes com UI interativa

```bash
npm run test:e2e:ui
```

### Atualizar snapshots (após mudanças intencionais no design)

```bash
npm run test:e2e:update-snapshots
```

### Gerar relatório HTML

```bash
npm run test:e2e:report
```

### Rodar testes de performance

```bash
npm run test:perf
```

## Estrutura de Arquivos

```
frontend/
├── playwright/
│   └── visual-regression.test.ts    # Testes de regressão visual
├── playwright.config.ts              # Configuração do Playwright
├── playwright-report/                # Relatório HTML (gerado após testes)
├── playwright-results.json           # Resultados em JSON (gerado após testes)
└── package.json                      # Scripts atualizados
```

## Componentes Testados

### 1. ThinkingNotifier
- Estados: active, waiting
- Temas: light, dark

### 2. ThoughtBlock
- Estados: collapsed, expanded
- Tipos de agentes: orchestrator, analyst, coder, researcher

### 3. DelegationCard
- Variants: simple, rich
- Múltiplos agentes

### 4. ToolEventCard
- Estados: running, completed, error
- Tipos especializados: read_file, shell, grep_search

### 5. StreamNotifier
- Tones: accent, info, success, warning, error, neutral

### 6. MemoryRecallCard
- Sources: vector, database
- Theme-dependent (apenas dark theme)

### 7. AgentTodoList
- Estados: streaming, completed
- Theme-dependent (apenas dark theme)

### 8. JourneyTimeline
- Estados: live, completed
- Múltiplos steps

### 9. AgentJourneyPanel
- Estados: open, closed
- Múltiplos painéis lado a lado

### 10. ChatStreamFeed
- Estados: streaming, history, complete, error
- Temas: light, dark
- Responsive: mobile, tablet, desktop, large

## Snapshots

Os snapshots são armazenados em:

```
playwright/__snapshots__/visual-regression.test.ts/
├── ThinkingNotifier-active-dark-chromium.png
├── ThinkingNotifier-waiting-dark-chromium.png
├── ThoughtBlock-collapsed-dark-chromium.png
├── ThoughtBlock-expanded-dark-chromium.png
└── ...
```

### Quando Atualizar Snapshots

Atualize os snapshots APENAS quando:

1. ✅ Mudanças intencionais no design foram feitas
2. ✅ Novos componentes foram adicionados
3. ✅ Temas foram modificados deliberadamente

**NÃO atualize** snapshots quando:

1. ❌ Bugs visuais foram introduzidos
2. ❌ Regressões acidentais ocorreram
3. ❌ Testes estão falhando por erro no código

## Responsive Design

Os testes incluem verificações em múltiplos viewports:

| Device | Width | Height |
|--------|-------|--------|
| Mobile | 375px | 667px |
| Tablet | 768px | 1024px |
| Desktop | 1440px | 900px |
| Large | 1920px | 1080px |

## Animações

Os testes de animação capturam frames em diferentes momentos:

- **ThinkingNotifier pulse**: 0ms, 500ms, 1000ms
- **AgentJourneyPanel slide**: 0ms, 100ms, 200ms

## Configurações de Threshold

As configurações de comparação de imagens estão em `playwright.config.ts`:

```typescript
expect: {
  toHaveScreenshot: {
    maxDiffPixels: 100,        // Máximo de pixels diferentes
    maxDiffPixelRatio: 0.05,   // Máximo de 5% de diferença
    threshold: 0.2,            // Threshold de 20% para pixelmatch
  },
}
```

## CI/CD Integration

Para integrar com CI/CD:

```yaml
# Exemplo GitHub Actions
name: Visual Regression Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npm run test:e2e
      - uses: actions/upload-artifact@v3
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
```

## Troubleshooting

### Testes falhando com diferenças pequenas

Se os testes estão falhando por diferenças mínimas (anti-aliasing, renderização de fontes):

1. Ajuste o threshold em `playwright.config.ts`
2. Use `maxDiffPixels` para permitir pequenas diferenças

### Servidor não inicia

Certifique-se de que a porta 5173 está disponível:

```bash
lsof -ti:5173 | xargs kill
```

### Snapshots desatualizados

Se muitos snapshots estão falhando após uma mudança intencional:

```bash
npm run test:e2e:update-snapshots
```

## Performance Tests

Os testes de performance estão em:

```
frontend/src/components/chat/v2/components/ChatStreamFeed.performance.test.tsx
```

### Métricas Monitoradas

- **Render time**: Tempo para renderizar 100, 500, 1000+ eventos
- **Expansion time**: Tempo para expandir/colapsar componentes
- **Memory usage**: Uso de memória estimado
- **FPS**: Frames por segundo durante animações

### Thresholds

| Métrica | Threshold |
|---------|-----------|
| 100 eventos | < 500ms |
| 1000 eventos | < 2000ms |
| Expansão | < 100ms |
| Memória | < 50MB |

## Referências

- [Playwright Documentation](https://playwright.dev/)
- [Visual Regression Testing Guide](https://playwright.dev/docs/test-snapshots)
- [Playwright Test UI Mode](https://playwright.dev/docs/test-ui-mode)
