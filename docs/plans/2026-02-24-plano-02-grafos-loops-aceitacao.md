# Plano 02 — Grafo com Loop por % de Aceitação (adaptado ao estado atual)

Data base: 24/02/2026

## 1) Objetivo
Evoluir o grafo atual para um loop controlado por score de aceitação, com parada determinística e auditável.

---

## 2) Estado atual do grafo (hoje)

Implementação real: `src/lib/swarm/graph.ts`

Fluxo atual:
1. `START -> orchestrator`
2. `orchestrator -> coder`
3. `coder -> live_analyst`
4. `live_analyst -> orchestrator` (quando há interrupção crítica) ou `sandbox_renderer`
5. `sandbox_renderer -> reviewer -> notifier -> END`

Ponto importante: já existe loop funcional por criticidade do analyst, mas ainda não existe loop orientado por score/aceitação.

---

## 3) Gap para o modelo de aceitação

Hoje falta no estado (`src/lib/swarm/state.ts`):
1. `iteration`
2. `acceptance_score`
3. `acceptance_target`
4. `min_delta_score`
5. `stagnation_count`

Hoje falta na malha do grafo:
1. Nó de avaliação de aceite (`acceptance_evaluator`)
2. Rotas condicionais por score
3. Eventos específicos de evolução do score

---

## 4) Novo desenho recomendado (mínima mudança)

Novo fluxo:
1. `START -> orchestrator`
2. `orchestrator -> coder`
3. `coder -> live_analyst`
4. `live_analyst -> sandbox_renderer`
5. `sandbox_renderer -> reviewer`
6. `reviewer -> acceptance_evaluator`
7. `acceptance_evaluator -> notifier` (se score atingido)
8. `acceptance_evaluator -> orchestrator` (se precisa iterar)

Mantém o loop de interrupção crítica do analyst como está.

---

## 5) Função de score de aceitação

```text
score =
  0.35 * functional_correctness +
  0.20 * test_pass_rate +
  0.20 * safety_compliance +
  0.15 * architecture_quality +
  0.10 * observability_quality
```

Regras:
1. sucesso: `score >= acceptance_target`
2. falha: `iteration >= max_iterations`
3. falha: `stagnation_count >= 2` quando `delta_score < min_delta_score`

---

## 6) Contrato JSON para decisão do orquestrador

```json
{
  "task_id": "uuid",
  "selected_model": {
    "provider": "vertexai",
    "model": "gemini-3-flash-preview"
  },
  "loop_policy": {
    "acceptance_target": 0.85,
    "max_iterations": 5,
    "min_delta_score": 0.03
  },
  "next_action": "execute|replan|stop",
  "reason": "string"
}
```

---

## 7) Ajustes concretos no código

1. Expandir `SwarmStateAnnotation` em `src/lib/swarm/state.ts`.
2. Adicionar `createAcceptanceEvaluatorNode()` em `src/lib/swarm/acceptance-evaluator.ts`.
3. Atualizar `src/lib/swarm/graph.ts` com novas arestas condicionais.
4. Emitir evento `ACCEPTANCE_SCORE_UPDATED` via `NotifierService`.
5. Atualizar `src/stores/swarm-store.ts` para exibir score e iteração.

---

## 8) Eventos obrigatórios no loop

1. `ITERATION_STARTED`
2. `ITERATION_COMPLETED`
3. `ACCEPTANCE_SCORE_UPDATED`
4. `LOOP_DECISION_MADE`
5. `TASK_TERMINATED` (com motivo: `target_reached|max_iterations|stagnation|error`)

---

## 9) Critérios de aceite
1. Toda task mostra score, target e iteração corrente.
2. Toda decisão de repetir/parar é explicável por evento.
3. Não há loop infinito.
4. Reconexão SSE reconstrói corretamente a iteração atual.
