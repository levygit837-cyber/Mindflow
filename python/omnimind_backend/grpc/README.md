# gRPC Implementation for OmniMind

This directory contains the enhanced gRPC implementation for the OmniMind backend, providing real network communication, proper error handling, monitoring, and integration with the FastAPI application.

## Overview

The gRPC implementation consists of:

- **Real gRPC Client**: `GrpcAgentClient` with network communication and retry logic
- **Enhanced gRPC Server**: `GrpcAgentServer` with interceptors and monitoring
- **Configuration Management**: Centralized gRPC settings
- **Interface Contracts**: Protocol-based interfaces for consistency
- **Comprehensive Testing**: Unit and integration tests
- **Backward Compatibility**: `LocalAgentClient` for development

## Architecture

```
python/omnimind_backend/grpc/
├── __init__.py                 # Package initialization
├── client.py                   # gRPC client implementation
├── server.py                   # gRPC server implementation
├── config.py                   # Configuration management
├── interfaces/                 # Interface contracts
│   ├── __init__.py
│   ├── client.py              # GrpcClient interface
│   └── server.py              # GrpcServer interface
├── interceptors/              # gRPC interceptors
│   ├── __init__.py
│   └── error_handler.py       # Error handling interceptor
├── services/                  # Service implementations
│   ├── __init__.py
│   └── agent_runtime_service.py
├── proto/                      # Protocol buffer definitions
│   └── omnimind_backend.proto
└── generated/                  # Generated gRPC code
    ├── __init__.py
    ├── omnimind_backend_pb2.py
    └── omnimind_backend_pb2_grpc.py
```

## Quick Start

### 1. Generate gRPC Bindings

```bash
cd python
bash scripts/gen_proto.sh
```

### 2. Configure Environment

```bash
# Enable gRPC (default: true)
export GRPC_ENABLED=true

# Auto-start gRPC server (default: true)
export GRPC_AUTO_START=true

# Server configuration
export GRPC_HOST=0.0.0.0
export GRPC_PORT=50051

# Security (optional)
export GRPC_SECURE=false
export GRPC_TLS_CERT_PATH=/path/to/cert.pem
export GRPC_TLS_KEY_PATH=/path/to/key.pem

# Performance tuning
export GRPC_MAX_CONNECTIONS=100
export GRPC_CONNECTION_TIMEOUT_SECONDS=30
export GRPC_MAX_ATTEMPTS=3
```

### 3. Start the Application

```bash
cd python
python -m omnimind_backend.main
```

The application will start both FastAPI and gRPC servers automatically.

### 4. Test the Implementation

```bash
cd python
python examples/grpc_usage_example.py
```

## Usage Examples

### Real gRPC Client

```python
from omnimind_backend.grpc.client import GrpcAgentClient

# Use with context manager (recommended)
async with GrpcAgentClient(host="localhost", port=50051) as client:
    # Health check
    health = await client.health_check()
    print(f"Server status: {health['status']}")
    
    # Stream chat
    async for event in client.stream_chat(
        session_id="my-session",
        message="Hello, gRPC!",
        provider="openai",
        model="gpt-4"
    ):
        print(f"Event: {event.type} - {event.data}")
```

### Manual Client Management

```python
from omnimind_backend.grpc.client import GrpcAgentClient

client = GrpcAgentClient(
    host="localhost",
    port=50051,
    max_attempts=3,
    timeout_seconds=30
)

try:
    await client.connect()
    
    # Use client
    health = await client.health_check()
    print(f"Health: {health}")
    
finally:
    await client.close()
```

### Server Management

```python
from omnimind_backend.grpc.server import start_grpc_server, stop_grpc_server

# Start server
server = await start_grpc_server()
print(f"Server running on {server.get_host()}:{server.get_port()}")

# Stop server
await stop_grpc_server()
```

### Configuration

```python
from omnimind_backend.grpc.config import GrpcConfig, GrpcClientConfig

# Server configuration
config = GrpcConfig(
    enabled=True,
    host="localhost",
    port=50051,
    secure=False,
    max_connections=100,
    enable_metrics=True
)

# Client configuration from server config
client_config = GrpcClientConfig.from_server_config(config)
```

## Features

### ✅ Implemented Features

1. **Real gRPC Communication**: Network-based client-server communication
2. **Connection Management**: Automatic connection, retry logic, graceful shutdown
3. **Error Handling**: Comprehensive error handling with proper gRPC status codes
4. **Interceptors**: Error handling interceptor (with metrics interceptor planned)
5. **Configuration**: Centralized configuration management
6. **Health Monitoring**: Server health checks and status reporting
7. **Backward Compatibility**: LocalAgentClient for development/testing
8. **Testing**: Comprehensive unit and integration tests
9. **Integration**: Seamless integration with FastAPI application
10. **Security**: TLS support for production environments

### 🚧 Planned Features

1. **Metrics Interceptor**: Performance metrics collection
2. **Health Service**: Dedicated gRPC health check service
3. **Load Balancing**: Multiple server instances support
4. **Circuit Breaker**: Fault tolerance for client connections
5. **gRPC-Web**: Browser client support
6. **Service Discovery**: Dynamic service registration
7. **Distributed Tracing**: Request tracing across services

## Configuration Reference

### Server Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `GRPC_ENABLED` | `true` | Enable gRPC server |
| `GRPC_AUTO_START` | `true` | Auto-start with application |
| `GRPC_HOST` | `0.0.0.0` | Server bind address |
| `GRPC_PORT` | `50051` | Server port |
| `GRPC_SECURE` | `false` | Use TLS encryption |
| `GRPC_TLS_CERT_PATH` | `null` | TLS certificate path |
| `GRPC_TLS_KEY_PATH` | `null` | TLS private key path |
| `GRPC_MAX_CONNECTIONS` | `100` | Maximum concurrent connections |
| `GRPC_CONNECTION_TIMEOUT_SECONDS` | `30` | Connection timeout |
| `GRPC_MAX_ATTEMPTS` | `3` | Maximum retry attempts |
| `GRPC_ENABLE_METRICS` | `true` | Enable metrics collection |
| `GRPC_ENABLE_HEALTH_CHECK` | `true` | Enable health checks |

### Client Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `host` | `localhost` | Server host |
| `port` | `50051` | Server port |
| `secure` | `false` | Use secure connection |
| `max_attempts` | `3` | Maximum retry attempts |
| `timeout_seconds` | `30` | Request timeout |
| `pool_size` | `10` | Connection pool size |

## Error Handling

The implementation includes comprehensive error handling:

### Client Errors

- **Connection Errors**: Automatic retry with exponential backoff
- **Timeout Errors**: Configurable timeouts per operation
- **gRPC Errors**: Proper gRPC status code mapping
- **Parsing Errors**: Graceful handling of malformed responses

### Server Errors

- **Interceptor Errors**: Global error handling with structured responses
- **Service Errors**: Proper error propagation to clients
- **Connection Errors**: Connection pool management
- **Resource Errors**: Resource exhaustion handling

## Monitoring

### Health Checks

```bash
# FastAPI health endpoint (includes gRPC status)
curl http://localhost:8000/health

# Response example
{
  "status": "ok",
  "app_name": "OmniMind Python Backend",
  "environment": "development",
  "grpc": {
    "enabled": true,
    "status": "running",
    "host": "0.0.0.0",
    "port": 50051,
    "uptime_seconds": 123.45
  }
}
```

### Logging

The implementation uses structured logging with context:

```python
_logger.info("grpc_client_connected", host="localhost", port=50051)
_logger.error("grpc_connection_failed", attempt=2, error="Connection refused")
```

## Testing

### Run Tests

```bash
# Unit tests
cd python
pytest tests/unit/grpc/ -v

# Integration tests
pytest tests/integration/grpc/ -v

# All gRPC tests
pytest tests/ -k grpc -v
```

### Test Coverage

- ✅ Client connection management
- ✅ Server lifecycle management
- ✅ Configuration handling
- ✅ Error scenarios
- ✅ Health monitoring
- ✅ Backward compatibility
- ✅ Integration scenarios

## Migration Guide

### From LocalAgentClient to GrpcAgentClient

1. **Replace Import**:
   ```python
   # Old
   from omnimind_backend.grpc.client import LocalAgentClient
   
   # New
   from omnimind_backend.grpc.client import GrpcAgentClient
   ```

2. **Update Usage**:
   ```python
   # Old
   client = LocalAgentClient()
   
   # New (recommended)
   async with GrpcAgentClient() as client:
       # Use client
   
   # Or manual management
   client = GrpcAgentClient()
   await client.connect()
   try:
       # Use client
   finally:
       await client.close()
   ```

3. **Handle Connection Errors**:
   ```python
   try:
       async with GrpcAgentClient() as client:
           # Use client
   except ConnectionError as exc:
       # Handle connection failure
       logger.error(f"gRPC connection failed: {exc}")
   ```

## Troubleshooting

### Common Issues

1. **Missing Generated Bindings**
   ```bash
   # Solution: Generate protobuf bindings
   bash scripts/gen_proto.sh
   ```

2. **Connection Refused**
   ```bash
   # Check if server is running
   curl http://localhost:8000/health
   
   # Verify gRPC status in response
   ```

3. **TLS Certificate Errors**
   ```bash
   # Verify certificate paths and permissions
   ls -la /path/to/cert.pem
   ls -la /path/to/key.pem
   ```

4. **Port Already in Use**
   ```bash
   # Check port usage
   netstat -tlnp | grep 50051
   
   # Use different port
   export GRPC_PORT=50052
   ```

### Debug Mode

Enable debug mode for detailed logging:

```bash
export APP_ENV=development
export GRPC_REFLECTION_ENABLED=true
```

## Performance Tuning

### Server Optimization

```python
# Increase connection pool
GRPC_MAX_CONNECTIONS=200

# Adjust timeouts
GRPC_CONNECTION_TIMEOUT_SECONDS=60
GRPC_DEFAULT_TIMEOUT_SECONDS=600

# Enable metrics for monitoring
GRPC_ENABLE_METRICS=true
```

### Client Optimization

```python
# Use connection pooling
client = GrpcAgentClient(
    pool_size=20,
    max_pool_size=100
)

# Configure timeouts
client = GrpcAgentClient(
    connection_timeout_seconds=10,
    request_timeout_seconds=120
)
```

## Security

### TLS Configuration

```bash
# Enable TLS
export GRPC_SECURE=true
export GRPC_TLS_CERT_PATH=/etc/ssl/certs/server.crt
export GRPC_TLS_KEY_PATH=/etc/ssl/private/server.key
```

### Certificate Management

```bash
# Generate self-signed certificate (for development)
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

## Contributing

When contributing to the gRPC implementation:

1. **Add Tests**: Ensure comprehensive test coverage
2. **Update Documentation**: Keep README and code comments current
3. **Follow Patterns**: Use established patterns for consistency
4. **Error Handling**: Include proper error handling for new features
5. **Backward Compatibility**: Maintain compatibility with existing code

## License

This gRPC implementation is part of the OmniMind project and follows the same license terms.
