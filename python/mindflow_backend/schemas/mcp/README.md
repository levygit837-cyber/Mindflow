# MCP (Model Context Protocol) Schemas

Este módulo contém todas as definições de schemas para o protocolo MCP no sistema MindFlow.

## Estrutura

- **base/**: Schemas base para mensagens, requests, responses e errors
- **transport/**: Configurações de transporte (stdio, http, websocket)
- **tools/**: Definições de ferramentas e parâmetros
- **resources/**: Definições de recursos e acesso

## Principais Componentes

### Mensagens Base
- `MCPMessage`: Mensagem base do protocolo
- `MCPRequest`: Mensagem de requisição
- `MCPResponse`: Mensagem de resposta
- `MCPError`: Estrutura de erro

### Transportes
- `StdioConfig`: Configuração para transporte stdio
- `HTTPConfig`: Configuração para transporte HTTP
- `WebSocketConfig`: Configuração para transporte WebSocket

### Ferramentas
- `MCPToolDefinition`: Definição completa de uma ferramenta
- `MCPToolParameter`: Parâmetro de ferramenta
- `MCPToolResult`: Resultado de execução

### Recursos
- `MCPResourceDefinition`: Definição de recurso
- `MCPResourceResult`: Resultado de acesso a recurso

## Uso

```python
from mindflow_backend.schemas.mcp import (
    MCPRequest, MCPResponse, MCPToolDefinition,
    StdioConfig, HTTPConfig
)

# Criar configuração stdio
stdio_config = StdioConfig(
    command=["python", "mcp_server.py"],
    working_directory="/path/to/server"
)

# Criar definição de ferramenta
tool_def = MCPToolDefinition(
    name="calculator",
    description="Simple calculator",
    input_schema=...
)
```
