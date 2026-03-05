# Migration Guide: PostgreSQL/Redis → DuckDB + KuzuDB

## Overview

This migration replaces PostgreSQL + Redis + SearXNG with DuckDB (main database) and KuzuDB (vector embeddings).

## What Changed

### Database Stack
- **Before**: PostgreSQL (relational) + Redis (cache) + SearXNG (search)
- **After**: DuckDB (analytics database) + KuzuDB (graph/vector database)

### Container Changes
- **Removed**: `postgres`, `redis`, `searxng`
- **Added**: `duckdb` (port 5434), `kuzudb` (port 8000)

### Code Changes
- New DuckDB storage layer (`duckdb_db.py`, `duckdb_models.py`, `duckdb_repositories.py`)
- New KuzuDB vector store (`kuzudb_vector_store.py`)
- Removed SearXNG search tool
- Updated configuration and dependencies

## New Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   DuckDB        │    │   KuzuDB        │
│   (port 5434)   │    │   (port 8000)   │
│                 │    │                 │
│ • Chat Sessions │    │ • Vector Embeds │
│ • Messages      │    │ • Graph Search  │
│ • Memory Events │    │ • Context       │
│ • Research Data │    │                 │
└─────────────────┘    └─────────────────┘
```

## Environment Variables

### New Variables
```bash
# DuckDB
DUCKDB_CONTAINER_NAME=omnimind-duckdb-v1
DUCKDB_DATABASE=omnimind_v1
DUCKDB_PORT=5434
DATABASE_URL=duckdb:///data/omnimind_v1.db

# KuzuDB
KUZUDB_CONTAINER_NAME=omnimind-kuzudb-v1
KUZUDB_DATABASE=omnimind_vectors
KUZUDB_PORT=8000
KUZUDB_URL=http://localhost:8000
```

### Removed Variables
```bash
# PostgreSQL (removed)
POSTGRES_*
DATABASE_URL=postgresql+psycopg://...

# Redis (removed)
REDIS_*
REDIS_URL=redis://...

# SearXNG (removed)
SEARXNG_URL
```

## Migration Steps

### 1. Update Environment
```bash
# Copy new .env.example
cp .env.example .env

# Edit .env with your settings
vim .env
```

### 2. Start New Containers
```bash
# Stop old containers
docker-compose down

# Start new containers
docker-compose up -d
```

### 3. Install Dependencies
```bash
cd python
uv sync  # Will install duckdb and kuzu packages
```

### 4. Initialize Database
```bash
# Initialize DuckDB schema
python -c "from omnimind_backend.storage.duckdb_db import initialize_database; initialize_database()"
```

### 5. Update Application Code
Any code using SQLAlchemy models needs to be updated:

```python
# Before (SQLAlchemy)
from omnimind_backend.storage.models import ChatSession
from omnimind_backend.storage.repositories import ChatSessionRepository

# After (DuckDB)
from omnimind_backend.storage.duckdb_models import ChatSession
from omnimind_backend.storage.duckdb_repositories import ChatSessionRepository
```

### 6. Vector Store Changes
```python
# Before (InMemory)
from omnimind_backend.agents.context.vector_store import InMemoryVectorStore

# After (KuzuDB)
from omnimind_backend.agents.context.kuzudb_vector_store import KuzuDBVectorStore
```

## Data Migration

### Existing Data
If you have existing PostgreSQL data, you'll need to migrate it:

```python
# Export from PostgreSQL
pg_dump -h localhost -p 5433 -U omnind_app omnimind_v1 > backup.sql

# Import to DuckDB (manual process required)
# DuckDB doesn't have direct PostgreSQL import
# You'll need to write a migration script
```

### Vector Data
Vector embeddings from other systems need to be migrated to KuzuDB format.

## Benefits

### DuckDB Advantages
- **Performance**: Faster analytics queries
- **Simplicity**: Single file database, no complex setup
- **Features**: Built-in JSON support, excellent for analytics
- **Size**: Smaller footprint than PostgreSQL

### KuzuDB Advantages
- **Graph Native**: Perfect for connected data
- **Vector Search**: Built-in similarity search capabilities
- **Performance**: Optimized for graph traversals
- **Flexibility**: Handles both structured and unstructured data

## Troubleshooting

### Common Issues

1. **DuckDB Connection Failed**
   ```bash
   # Check if container is running
   docker ps | grep duckdb
   
   # Check logs
   docker logs omnimind-duckdb-v1
   ```

2. **KuzuDB Not Ready**
   ```bash
   # Wait for KuzuDB to start
   curl http://localhost:8000
   
   # Should return KuzuDB interface
   ```

3. **Missing Dependencies**
   ```bash
   # Install missing packages
   uv add duckdb kuzu
   ```

4. **Schema Issues**
   ```bash
   # Re-initialize database
   python -c "from omnimind_backend.storage.duckdb_db import initialize_database; initialize_database()"
   ```

## Performance Notes

### DuckDB
- Excellent for analytical queries
- Good for read-heavy workloads
- Single-threaded writes (but very fast)

### KuzuDB
- Optimized for graph queries
- Great for vector similarity search
- Scales well with connected data

## Next Steps

1. **Test**: Verify all functionality works with new stack
2. **Benchmark**: Compare performance with old stack
3. **Monitor**: Set up monitoring for new containers
4. **Optimize**: Tune queries for DuckDB/KuzuDB strengths

## Rollback Plan

If needed, you can rollback:

```bash
# Stop new containers
docker-compose down

# Restore old docker-compose.yml
git checkout HEAD~1 -- docker-compose.yml

# Start old containers
docker-compose up -d

# Restore old dependencies
uv sync --refresh
```

## Support

For issues:
1. Check container logs: `docker logs <container-name>`
2. Verify connectivity: `curl http://localhost:5434` (DuckDB), `curl http://localhost:8000` (KuzuDB)
3. Review migration scripts for data issues
4. Check application logs for database connection errors
