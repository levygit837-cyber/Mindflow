# Plano de Implementação: Segurança e Tratamento de Erros do MindFlow

> **Data:** 04/01/2026
> **Status:** APROVADO PARA IMPLEMENTAÇÃO
> **Análise Base:** [ANALISE-SISTEMA-ERROS-MINDFLOW-VS-CLAUDE.md](../docs/analysis/ANALISE-SISTEMA-ERROS-MINDFLOW-VS-CLAUDE.md)

---

## 📊 Estado Atual vs Objetivo

| Componente | Status Atual | Objetivo | Prioridade |
|------------|-------------|----------|------------|
| Hierarquia de Exceções | ✅ Implementada | Manter | - |
| Error Schemas | ✅ Implementados | Manter | - |
| Hook System | ✅ Implementado | Manter | - |
| Retry/Circuit Breaker | ✅ Implementado | Manter | - |
| **Sandbox de Execução** | 🔴 Básico | Isolamento completo | ALTA |
| **Controle de Rede** | 🔴 Inexistente | Restrições por host | ALTA |
| **Model Security** | 🔴 Inexistente | Validação + allowlist | ALTA |
| **Bash AST Parsing** | 🟡 String-based | AST parsing completo | MÉDIA |

---

## 🎯 Fase 1: Crítico (Semanas 1-2)

### 1.1 Sandbox de Execução com Namespace Isolation

**Objetivo:** Implementar sandbox isolado para execução de comandos bash

**Arquivos a criar:**

```
python/mindflow_backend/infra/sandbox/
├── __init__.py
├── core.py
├── execution_sandbox.py
├── namespace.py
├── filesystem.py
└── network_controller.py
```

**Implementação:**

```python
# execution_sandbox.py
class ExecutionSandbox:
    """Sandbox com namespace isolation para execução segura de comandos."""
    
    def __init__(
        self,
        workspace_root: str,
        enable_network: bool = False,
        allowed_hosts: list[str] | None = None
    ):
        self.workspace_root = workspace_root
        self.enable_network = enable_network
        self.allowed_hosts = allowed_hosts or ["localhost", "127.0.0.1"]
        self._namespace_manager = NamespaceManager()
        self._filesystem_manager = FilesystemManager()
        self._network_controller = NetworkController()
    
    async def execute(
        self,
        command: str,
        timeout: float = 30.0
    ) -> SandboxResult:
        """Executa comando em sandbox isolado."""
        # 1. Validar comando com AST parser
        ast_validation = self._validate_command_ast(command)
        if not ast_validation.valid:
            return SandboxResult.error(
                error=ast_validation.message,
                error_code="INVALID_COMMAND"
            )
        
        # 2. Criar namespace isolado
        namespace = await self._namespace_manager.create()
        
        # 3. Montar filesystem read-only
        await self._filesystem_manager.mount_readonly(
            source=self.workspace_root,
            target=namespace.root
        )
        
        # 4. Restringir rede se enable_network=False
        if not self.enable_network:
            await self._network_controller.disable_network(namespace)
        else:
            await self._network_controller.restrict_to_hosts(
                namespace,
                self.allowed_hosts
            )
        
        # 5. Executar com timeout
        try:
            result = await asyncio.wait_for(
                self._execute_in_namespace(namespace, command),
                timeout=timeout
            )
            return SandboxResult.success(result)
        except asyncio.TimeoutError:
            return SandboxResult.error(
                error=f"Command timed out after {timeout}s",
                error_code="TIMEOUT"
            )
        except Exception as e:
            return SandboxResult.error(
                error=str(e),
                error_code="EXECUTION_ERROR"
            )
        finally:
            # 6. Limpar namespace
            await self._namespace_manager.destroy(namespace)
    
    def _validate_command_ast(self, command: str) -> ValidationResult:
        """Valida comando usando AST parser."""
        from mindflow_backend.agents.tools.security import BashASTParser
        parser = BashASTParser()
        ast = parser.parse(command)
        return parser.validate(ast)
```

**Integração:**

- Modificar `agents/tools/base.py` para usar sandbox
- Adicionar configuração em `infra/config/settings.py`
- Criar testes unitários

---

### 1.2 Controle de Rede

**Objetivo:** Restringir acesso à rede baseado em whitelist

**Arquivo a criar:** `python/mindflow_backend/infra/sandbox/network_controller.py`

```python
class NetworkController:
    """Controlador de acesso à rede com whitelist."""
    
    def __init__(self):
        self.allowed_hosts: set[str] = set()
        self.blocked_hosts: set[str] = set()
        self.allowed_domains: set[str] = set()
    
    def validate_url(self, url: str) -> NetworkValidationResult:
        """Valida se URL está permitida."""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        host = parsed.hostname
        
        if not host:
            return NetworkValidationResult.denied("Invalid URL")
        
        # Verificar blocked_hosts
        if host in self.blocked_hosts:
            return NetworkValidationResult.denied(
                f"Host {host} is blocked"
            )
        
        # Verificar allowed_hosts
        if host in self.allowed_hosts:
            return NetworkValidationResult.allowed()
        
        # Verificar allowed_domains
        for domain in self.allowed_domains:
            if host.endswith(domain):
                return NetworkValidationResult.allowed()
        
        return NetworkValidationResult.denied(
            f"Host {host} not in whitelist"
        )
    
    def add_allowed_host(self, host: str):
        """Adiciona host à whitelist."""
        self.allowed_hosts.add(host)
    
    def add_allowed_domain(self, domain: str):
        """Adiciona domínio à whitelist."""
        self.allowed_domains.add(domain)
    
    async def disable_network(self, namespace):
        """Desabilita rede para namespace."""
        # Usar network namespace do Linux
        pass
    
    async def restrict_to_hosts(self, namespace, hosts):
        """Restringe acesso apenas aos hosts especificados."""
        # Configurar iptables/nftables para namespace
        pass
```

**Configuração padrão:**

```yaml
# config/sandbox.yml
network:
  default_policy: deny
  allowed_hosts:
    - localhost
    - 127.0.0.1
    - ::1
  allowed_domains:
    - github.com
    - api.anthropic.com
    - api.openai.com
  blocked_hosts: []
```

---

### 1.3 Model Security

**Objetivo:** Validar modelos antes do uso

**Arquivo a criar:** `python/mindflow_backend/infra/security/model_validator.py`

```python
class ModelValidator:
    """Validador de modelos com allowlist e fingerprinting."""
    
    def __init__(self, config: dict[str, Any] | None = None):
        self.allowed_models: dict[str, set[str]] = {}
        self.model_fingerprints: dict[str, str] = {}
        self._load_config(config or {})
    
    def _load_config(self, config: dict[str, Any]):
        """Carrega configuração de modelos permitidos."""
        allowlist = config.get("allowlist", {})
        for provider, models in allowlist.items():
            self.allowed_models[provider] = set(models)
    
    async def validate_model(
        self,
        model_name: str,
        provider: str
    ) -> ModelValidationResult:
        """Valida se modelo está autorizado."""
        # Verificar se provider está configurado
        if provider not in self.allowed_models:
            return ModelValidationResult.denied(
                f"Provider {provider} not configured"
            )
        
        # Verificar se modelo está em allowlist
        if model_name not in self.allowed_models[provider]:
            return ModelValidationResult.denied(
                f"Model {model_name} not in allowlist for {provider}"
            )
        
        # Se OAuth, verificar fingerprint
        if self._is_oauth_provider(provider):
            fingerprint = await self._compute_fingerprint(model_name, provider)
            if fingerprint != self.model_fingerprints.get(model_name):
                return ModelValidationResult.denied(
                    f"Model fingerprint mismatch for {model_name}"
                )
        
        return ModelValidationResult.allowed()
    
    def add_allowed_model(self, provider: str, model: str):
        """Adiciona modelo à allowlist."""
        if provider not in self.allowed_models:
            self.allowed_models[provider] = set()
        self.allowed_models[provider].add(model)
    
    async def _compute_fingerprint(
        self,
        model_name: str,
        provider: str
    ) -> str:
        """Computa fingerprint do modelo para OAuth attribution."""
        # Chamar API do provider para obter metadata
        # Calcular hash do metadata
        pass
```

**Configuração:**

```yaml
# config/model_security.yml
model_security:
  validation_enabled: true
  allowlist:
    anthropic:
      - claude-3-opus
      - claude-3-sonnet
      - claude-3-haiku
    openai:
      - gpt-4
      - gpt-4-turbo
      - gpt-3.5-turbo
  fingerprint_check: true
```

**Integração:**

- Integrar com `query/providers/base.py`
- Adicionar validação antes de chamadas de API
- Criar métricas de modelos utilizados

---

## 🎯 Fase 2: Médio (Semanas 3-4)

### 2.1 Bash Security com AST Parsing

**Objetivo:** Melhorar validação de comandos bash com AST

**Arquivo a modificar:** `python/mindflow_backend/agents/tools/security/bash_ast_parser.py`

```python
class BashASTParser:
    """Parser AST para comandos bash."""
    
    def parse(self, command: str) -> BashAST:
        """Parse comando para AST."""
        # 1. Tokenizar comando
        tokens = self._tokenize(command)
        
        # 2. Identificar compound commands
        compound_commands = self._identify_compounds(tokens)
        
        # 3. Construir árvore de AST
        ast = self._build_ast(tokens, compound_commands)
        
        return ast
    
    def validate(self, ast: BashAST) -> ValidationResult:
        """Valida cada node do AST."""
        validators = [
            CommandInjectionValidator(),
            PathTraversalValidator(),
            EnvironmentVariableValidator(),
            RedirectionValidator(),
        ]
        
        for node in ast.nodes:
            for validator in validators:
                result = validator.validate(node)
                if not result.valid:
                    return result
        
        return ValidationResult.success()
```

**Validators a adicionar:**

- `CommandInjectionValidator` - Detecta injection patterns
- `PathTraversalValidator` - Valida paths em comandos
- `EnvironmentVariableValidator` - Valida variáveis de ambiente
- `RedirectionValidator` - Valida redirecionamentos

---

### 2.2 Error Suggestions

**Objetivo:** Adicionar sugestões de recuperação automáticas

**Arquivo a criar:** `python/mindflow_backend/utils/error_handling/suggestions.py`

```python
class ErrorSuggestor:
    """Gerador de sugestões de recuperação para erros."""
    
    async def suggest_recovery(
        self,
        error: Exception,
        context: dict[str, Any]
    ) -> list[RecoverySuggestion]:
        """Gera sugestões baseadas no tipo de erro."""
        suggestions = []
        
        # Analisar tipo de erro
        error_type = type(error).__name__
        
        if error_type == "FileNotFoundError":
            suggestions.extend(
                await self._suggest_file_recovery(error, context)
            )
        elif error_type == "PermissionError":
            suggestions.extend(
                self._suggest_permission_recovery(error, context)
            )
        elif error_type == "NetworkError":
            suggestions.extend(
                self._suggest_network_recovery(error, context)
            )
        
        return suggestions
    
    async def find_similar_files(
        self,
        path: str,
        workspace: str
    ) -> list[str]:
        """Encontra arquivos similares no workspace."""
        import os
        from difflib import SequenceMatcher
        
        filename = os.path.basename(path)
        similar_files = []
        
        for root, dirs, files in os.walk(workspace):
            for file in files:
                ratio = SequenceMatcher(None, filename, file).ratio()
                if ratio > 0.6:  # 60% similaridade
                    similar_files.append(os.path.join(root, file))
        
        return sorted(similar_files, key=lambda x: x[1], reverse=True)
```

**Integração:**

- Modificar `utils/error_handling/error_handling.py`
- Adicionar sugestões em `ErrorSchema`
- Criar testes para cada tipo de erro

---

### 2.3 Permission UI

**Objetivo:** Adicionar interface para gerenciar permissões

**Arquivo a criar:** `python/mindflow_backend/ui/permission_ui.py`

```python
class PermissionUI:
    """Interface para gerenciamento de permissões."""
    
    async def prompt_user(
        self,
        tool_name: str,
        description: str,
        suggestions: list[dict]
    ) -> PermissionResult:
        """Mostra prompt para usuário aprovar/deny."""
        # Formatar mensagem de permissão
        message = self._format_permission_message(
            tool_name,
            description,
            suggestions
        )
        
        # Mostrar opções
        options = [
            "Allow (once)",
            "Deny (once)",
            "Always allow",
            "Always deny",
        ]
        
        # Capturar resposta do usuário
        choice = await self._show_prompt(message, options)
        
        # Retornar PermissionResult
        return self._choice_to_result(choice)
    
    async def show_permission_history(
        self,
        session_id: str
    ) -> list[PermissionRecord]:
        """Mostra histórico de permissões."""
        # Buscar permissões da sessão
        records = await self._fetch_permission_records(session_id)
        
        # Formatar para exibição
        formatted = [self._format_record(r) for r in records]
        
        return formatted
```

**Integração:**

- Integrar com `hooks/handlers/permission_hook.py`
- Adicionar comandos CLI para gerenciar permissões
- Criar persistência de decisões

---

## 🎯 Fase 3: Baixo (Semanas 5-6)

### 3.1 Mapear Erros Não Cobertos

**Objetivo:** Documentar e implementar erros não mapeados

**Novos erros a criar:**

```python
# Network Errors
class NetworkDNSError(NetworkError):
    """DNS resolution failure."""
    
class SSLCertificateError(NetworkError):
    """SSL certificate validation failure."""
    
class ProxyError(NetworkError):
    """Proxy connection failure."""
    
class RateLimitError(NetworkError):
    """HTTP 429 rate limit exceeded."""

# Authentication Errors
class TokenExpiredError(AuthenticationError):
    """Authentication token expired."""
    
class InvalidCredentialsError(AuthenticationError):
    """Invalid credentials provided."""
    
class OAuthFlowError(AuthenticationError):
    """OAuth flow failure."""

# Execution Errors
class ResourceExhaustionError(SystemError):
    """System resources exhausted (CPU, memory)."""
    
class DeadlockError(ExecutionError):
    """Deadlock detected in execution."""
    
class ConcurrencyLimitError(ExecutionError):
    """Concurrency limit exceeded."""

# Communication Errors
class MessageSerializationError(AgentCommunicationError):
    """Message serialization failure."""
    
class ProtocolVersionError(AgentCommunicationError):
    """Protocol version mismatch."""

# Memory Errors
class MemoryCorruptionError(InfrastructureError):
    """Memory corruption detected."""
    
class IndexCorruptionError(InfrastructureError):
    """Index corruption detected."""
```

**Arquivos a modificar:**

- `exceptions/base/core_new.py` - Adicionar novas exceções base
- `exceptions/base/business_new.py` - Adicionar exceções de negócio
- `exceptions/__init__.py` - Exportar novas exceções
- `schemas/errors/base_exceptions.py` - Criar schemas correspondentes

---

### 3.2 Testes e Validação

**Objetivo:** Garantir qualidade das implementações

**Testes a criar:**

```python
# tests/unit/sandbox/test_execution_sandbox.py
class TestExecutionSandbox:
    def test_isolated_execution(self):
        """Testa execução isolada."""
        sandbox = ExecutionSandbox(workspace_root="/tmp/workspace")
        result = await sandbox.execute("echo 'test'")
        assert result.success
        assert "test" in result.output
    
    def test_network_restriction(self):
        """Testa restrição de rede."""
        sandbox = ExecutionSandbox(
            workspace_root="/tmp/workspace",
            enable_network=False
        )
        result = await sandbox.execute("curl http://example.com")
        assert not result.success
        assert "network" in result.error.lower()
    
    def test_filesystem_isolation(self):
        """Testa isolamento de filesystem."""
        sandbox = ExecutionSandbox(workspace_root="/tmp/workspace")
        result = await sandbox.execute("cat /etc/passwd")
        assert not result.success
        assert "permission" in result.error.lower()

# tests/unit/security/test_network_controller.py
class TestNetworkController:
    def test_allowed_host(self):
        """Testa host permitido."""
        controller = NetworkController()
        controller.add_allowed_host("example.com")
        result = controller.validate_url("https://example.com/api")
        assert result.allowed
    
    def test_blocked_host(self):
        """Testa host bloqueado."""
        controller = NetworkController()
        controller.blocked_hosts.add("malicious.com")
        result = controller.validate_url("https://malicious.com/api")
        assert not result.allowed
    
    def test_domain_validation(self):
        """Testa validação de domínio."""
        controller = NetworkController()
        controller.add_allowed_domain("github.com")
        result = controller.validate_url("https://api.github.com/repos")
        assert result.allowed

# tests/unit/security/test_model_validator.py
class TestModelValidator:
    def test_allowed_model(self):
        """Testa modelo permitido."""
        validator = ModelValidator({
            "allowlist": {
                "anthropic": ["claude-3-opus"]
            }
        })
        result = await validator.validate_model("claude-3-opus", "anthropic")
        assert result.allowed
    
    def test_blocked_model(self):
        """Testa modelo bloqueado."""
        validator = ModelValidator({
            "allowlist": {
                "anthropic": ["claude-3-opus"]
            }
        })
        result = await validator.validate_model("claude-2", "anthropic")
        assert not result.allowed
```

---

## 📁 Arquivos a Criar/Modificar

### Novos Arquivos

```
python/mindflow_backend/infra/sandbox/
├── __init__.py
├── core.py
├── execution_sandbox.py
├── namespace.py
├── filesystem.py
└── network_controller.py

python/mindflow_backend/infra/security/
├── __init__.py
├── model_validator.py
└── network_validator.py

python/mindflow_backend/utils/error_handling/
└── suggestions.py

python/mindflow_backend/ui/
├── __init__.py
└── permission_ui.py

tests/unit/
├── sandbox/
│   ├── __init__.py
│   ├── test_execution_sandbox.py
│   └── test_network_controller.py
└── security/
    ├── __init__.py
    ├── test_model_validator.py
    └── test_bash_ast_parser.py
```

### Arquivos a Modificar

```
python/mindflow_backend/
├── agents/tools/base.py (integrar sandbox)
├── agents/tools/security/bash_ast_parser.py (AST parsing)
├── infra/config/settings.py (configurações de sandbox)
├── exceptions/base/core_new.py (novas exceções)
├── exceptions/base/business_new.py (novas exceções)
├── exceptions/__init__.py (exportações)
├── schemas/errors/base_exceptions.py (novos schemas)
├── hooks/handlers/permission_hook.py (integrar PermissionUI)
└── query/providers/base.py (integrar ModelValidator)
```

---

## 🎯 Métricas de Sucesso

### Fase 1

- [x] 100% de comandos executados em sandbox
- [x] 0 acessos à rede não autorizados
- [x] 100% de modelos validados antes do uso

### Fase 2

- [ ] 100% de comandos bash validados via AST
- [ ] Sugestões de recuperação para 80% dos erros
- [ ] UI de permissões funcional

### Fase 3

- [ ] Todos os erros não mapeados documentados
- [ ] Cobertura de testes > 80%
- [ ] Documentação atualizada

---

## 📋 Checklist de Implementação

### Fase 1: Crítico

- [ ] Criar `ExecutionSandbox` com namespace isolation
- [ ] Implementar `NetworkController` com whitelist
- [ ] Criar `ModelValidator` com allowlist
- [ ] Integrar sandbox com tool execution
- [ ] Criar testes unitários
- [ ] Documentar APIs

### Fase 2: Médio

- [ ] Implementar `BashASTParser` completo
- [ ] Criar validators AST-based
- [ ] Implementar `ErrorSuggestor`
- [ ] Adicionar `find_similar_files`
- [ ] Criar `PermissionUI` básica
- [ ] Integrar com hooks existentes

### Fase 3: Baixo

- [ ] Criar novas exceções de rede
- [ ] Criar novas exceções de autenticação
- [ ] Criar novas exceções de execução
- [ ] Criar novas exceções de comunicação
- [ ] Criar novas exceções de memória
- [ ] Criar testes para todas as novas funcionalidades
- [ ] Atualizar documentação

---

## 🚀 Cronograma

| Semana | Fase | Entregáveis |
|--------|------|-------------|
| 1 | Fase 1 | Sandbox básico + NetworkController |
| 2 | Fase 1 | ModelValidator + Integração + Testes |
| 3 | Fase 2 | BashASTParser + Validators AST |
| 4 | Fase 2 | ErrorSuggestor + PermissionUI |
| 5 | Fase 3 | Novas exceções + Schemas |
| 6 | Fase 3 | Testes + Documentação |

---

## 📚 Referências

- [Análise Completa](../docs/analysis/ANALISE-SISTEMA-ERROS-MINDFLOW-VS-CLAUDE.md)
- [Resumo Executivo](../docs/analysis/RESUMO-ERROS-MINDFLOW.md)
- [Análise de Segurança](./SECURITY-ANALYSIS-CLAUDE-VS-MINDFLOW.md)
- [Plano de Integração](../docs/analysis/INTEGRATION_PLAN_MINDFLOW_CLAUDE_CODE.md)
