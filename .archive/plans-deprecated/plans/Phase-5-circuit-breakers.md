# Fase 5: Integrar Circuit Breakers nos Serviços

## Estado Atual da Análise (30/03/2026)

### ✅ O que JÁ existe

1. **CircuitBreaker** (`communication/circuit_breaker/breaker.py`) — completo e funcional
   - Estados: CLOSED, OPEN, HALF_OPEN
   - Configuração com thresholds
   - Estatísticas detalhadas
   - Fallback handler
   - Método `execute()` para proteger chamadas assíncronas

2. **RedisMessageBus** — JÁ usa CircuitBreaker no `publish()`
3. **RabbitMQMessageBus** — JÁ usa CircuitBreaker no `publish()`

### ❌ O que NÃO tem circuit breaker

1. **XMPPService** — operações críticas sem proteção:
   - `register_agent()` — pode falhar se servidor XMPP estiver down
   - `connect_agent()` — pode falhar por timeout/recusa
   - `disconnect_agent()` — pode falhar silenciosamente
   - `send_message()` — operação mais crítica, sem proteção

2. **P2PService** — operações críticas sem proteção:
   - `send_direct_message()` — depende do XMPP funcionando
   - `send_request()` — pode falhar sem resposta
   - `send_response()` — pode falhar sem entregar
   - `send_urgent_message()` — urgente mas sem garantia
   - `send_notification()` — pode ser perdida

3. **TeamService** — operações críticas sem proteção:
   - `send_team_message()` — broadcast pode falhar

---

## Plano de Implementação

### Passo 1: Criar Decorator `@circuit_protected`

**Arquivo:** `communication/circuit_breaker/decorator.py`

Criar um decorator reutilizável que:

- Aceita um nome de circuit breaker
- Configura thresholds via parâmetros
- Retorna fallback quando circuito está aberto
- Registra métricas automaticamente

```python
def circuit_protected(
    breaker_name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 30,
    success_threshold: int = 3,
    fallback_return: Any = None
):
    """Decorator para proteger métodos com circuit breaker."""
```

### Passo 2: Aplicar em XMPPService

**Arquivo:** `communication/services/xmpp_service.py`

Métodos a proteger:

- `register_agent()` → fallback: `{"success": False, "error": "XMPP circuit open"}`
- `connect_agent()` → fallback: `{"success": False, "error": "XMPP circuit open"}`
- `disconnect_agent()` → fallback: `False`
- `send_message()` → fallback: `{"success": False, "error": "XMPP circuit open"}`

Configuração:

- `failure_threshold: 5` (5 falhas consecutivas)
- `recovery_timeout: 30` (30 segundos)
- `success_threshold: 3` (3 sucessos para fechar)

### Passo 3: Aplicar em P2PService

**Arquivo:** `communication/services/p2p_service.py`

Métodos a proteger:

- `send_direct_message()` → fallback: `{"success": False, "error": "P2P circuit open"}`
- `send_request()` → fallback: `{"success": False, "error": "P2P circuit open"}`
- `send_response()` → fallback: `{"success": False, "error": "P2P circuit open"}`
- `send_urgent_message()` → fallback: `{"success": False, "error": "P2P circuit open"}`
- `send_notification()` → fallback: `{"success": False, "error": "P2P circuit open"}`

### Passo 4: Aplicar em TeamService

**Arquivo:** `communication/services/team_service.py`

Método a proteger:

- `send_team_message()` → fallback: `None` (mensagem não enviada)

### Passo 5: Adicionar Métricas Estruturadas

**Arquivo:** `communication/circuit_breaker/metrics.py`

Criar sistema de métricas que:

- Loga estado de cada circuit breaker
- Exporta métricas para Prometheus/monitoring
- Alerta quando circuito abre

### Passo 6: Atualizar `__init__.py`

**Arquivo:** `communication/circuit_breaker/__init__.py`

Exportar novos componentes:

- `circuit_protected` decorator
- `CircuitBreakerMetrics` (se criado)

---

## Thresholds Definidos no Roadmap

| Serviço | failure_threshold | recovery_timeout | half_open_max_calls |
|---------|-------------------|------------------|---------------------|
| XMPPService | 5 | 30s | 3 |
| P2PService | 5 | 30s | 3 |
| TeamService | 5 | 30s | 3 |
| Message Bus | 5 (já configurado) | 30s | 3 |

---

## Fallback Strategy

Quando o circuito abre, o sistema deve:

1. Logar warning estruturado com métricas
2. Retornar resultado de fallback (não crashar)
3. Permitir que orquestração manual assuma (degradação graceful)

---

## Arquivos a Criar/Modificar

| Arquivo | Ação |
|---------|------|
| `communication/circuit_breaker/decorator.py` | CRIAR |
| `communication/circuit_breaker/__init__.py` | MODIFICAR (exportar decorator) |
| `communication/services/xmpp_service.py` | MODIFICAR (adicionar decorator) |
| `communication/services/p2p_service.py` | MODIFICAR (adicionar decorator) |
| `communication/services/team_service.py` | MODIFICAR (adicionar decorator) |

---

## Ordem de Execução

1. Criar `decorator.py` — base reutilizável
2. Atualizar `__init__.py` — exportar decorator
3. Aplicar em `xmpp_service.py` — serviço mais crítico
4. Aplicar em `p2p_service.py` — depende do XMPP
5. Aplicar em `team_service.py` — menos crítico mas importante
6. Validar com testes unitários

---

## Critérios de Conclusão

- [ ] Decorator `@circuit_protected` criado e testado
- [ ] XMPPService com circuit breaker em todos os métodos críticos
- [ ] P2PService com circuit breaker em todos os métodos de envio
- [ ] TeamService com circuit breaker em `send_team_message()`
- [ ] Logs estruturados quando circuito abre/fecha
- [ ] Testes unitários passando
- [ ] Nenhum import quebrado no projeto
