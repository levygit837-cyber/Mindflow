# Legacy RQ Workers Archive

These files were archived during migration to the new RabbitMQ-based worker system on 2026-03-05 16:33:54.

## Archived Files:
- `queue.py` - Legacy RQ queue configuration with Redis
- `worker.py` - Legacy RQ worker process with scheduler
- `tasks.py` - Legacy task definitions (contained deprecated session supervisor)

## Why Archived:
RabbitMQ is now the official async stack for MindFlow. These files remain archived only for historical reference and rollback analysis.

The project migrated to a modern hierarchical RabbitMQ worker system that provides:
- Better organization by domain (agents, system, research)
- Modern RabbitMQ infrastructure instead of RQ/Redis
- Proper error handling and monitoring
- Task publishers and queue management
- Scalable architecture

## New System Location:
The new RabbitMQ worker system is located in the parent directory `../`

## New System Usage:
```bash
# List available workers
python -m mindflow_backend.workers.main --list

# Start specific workers  
python -m mindflow_backend.workers.main --workers health coder

# Start all workers
python -m mindflow_backend.workers.main
```

## Environment Variables:
- `MINDFLOW_USE_NEW_WORKERS=1` - Enable new system in launcher
- `MINDFLOW_START_WORKER=1` - Start worker process
- RabbitMQ configuration variables (see .env.example)

## Docker:
Updated `docker-compose.backend.yml` to include RabbitMQ service.

## Migration Notes:
- Desktop launcher updated to support both systems with feature flag
- All imports and dependencies updated
- RabbitMQ dependencies added to pyproject.toml
- Legacy system only kept for reference and potential rollback
