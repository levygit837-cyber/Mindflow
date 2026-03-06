# Legacy RQ Workers Archive

These files were archived during migration to the new RabbitMQ-based worker system.

## Archived Files:
- queue.py - Legacy RQ queue configuration
- worker.py - Legacy RQ worker process  
- tasks.py - Legacy task definitions (mostly deprecated)

## Migration Date:
2026-03-05 16:33:46

## New System:
The new hierarchical RabbitMQ worker system is located in the parent directory.
It provides:
- Better organization by domain (agents, system, research)
- Modern RabbitMQ infrastructure
- Proper error handling and monitoring
- Task publishers and queue management

## Usage:
Use the new system via:
```bash
python -m mindflow_backend.workers.main --list
python -m mindflow_backend.workers.main --workers health coder
```
