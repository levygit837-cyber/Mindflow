#!/usr/bin/env python3
"""Archive legacy workers and complete migration to new system."""

import shutil
from datetime import datetime
from pathlib import Path


def archive_legacy_workers():
    """Archive legacy worker files to prevent accidental use."""
    
    project_root = Path(__file__).parent
    workers_dir = project_root / "python" / "mindflow_backend" / "workers"
    
    # Files to archive
    legacy_files = [
        workers_dir / "queue.py",
        workers_dir / "worker.py", 
        workers_dir / "tasks.py"
    ]
    
    # Create archive directory
    archive_dir = workers_dir / "archive" / f"legacy_rq_workers_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Archiving legacy workers to: {archive_dir}")
    
    archived_count = 0
    for file_path in legacy_files:
        if file_path.exists():
            archive_path = archive_dir / file_path.name
            shutil.move(str(file_path), str(archive_path))
            print(f"  ✓ Archived: {file_path.name}")
            archived_count += 1
        else:
            print(f"  - Not found: {file_path.name}")
    
    print(f"\nArchived {archived_count} legacy worker files")
    
    # Create README in archive directory
    readme_content = """# Legacy RQ Workers Archive

These files were archived during migration to the new RabbitMQ-based worker system.

## Archived Files:
- queue.py - Legacy RQ queue configuration
- worker.py - Legacy RQ worker process  
- tasks.py - Legacy task definitions (mostly deprecated)

## Migration Date:
{date}

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
""".format(date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    readme_path = archive_dir / "README.md"
    readme_path.write_text(readme_content)
    
    return archived_count > 0

def update_documentation():
    """Add migration notes to project documentation."""
    
    project_root = Path(__file__).parent
    readme_path = project_root / "python" / "README.md"
    
    if not readme_path.exists():
        print("README.md not found, skipping documentation update")
        return
    
    migration_note = """

## Worker Migration (2026-03-05)

The project has migrated from RQ/Redis workers to a new hierarchical RabbitMQ-based worker system.

### Old System (Archived):
- `workers/queue.py` - RQ queue with Redis
- `workers/worker.py` - Basic RQ worker
- `workers/tasks.py` - Deprecated tasks

### New System:
- **Main Entry**: `python -m mindflow_backend.workers.main`
- **Organization**: Hierarchical structure by domain
  - `agents/` - Coder, Analyst, Researcher, Orchestrator workers
  - `system/` - Health, Memory, Vector, Session review workers  
  - `research/` - Browser, Content workers
- **Infrastructure**: QueueManager, WorkerFactory, WorkerMonitor
- **Message Broker**: RabbitMQ (instead of Redis)

### Usage:
```bash
# List available workers
python -m mindflow_backend.workers.main --list

# Start specific workers
python -m mindflow_backend.workers.main --workers health coder

# Start all workers
python -m mindflow_backend.workers.main
```

### Environment Variables:
- `MINDFLOW_USE_NEW_WORKERS=1` - Enable new system in launcher
- `MINDFLOW_START_WORKER=1` - Start worker process
- RabbitMQ configuration variables (see .env.example)

### Docker:
Updated `docker-compose.backend.yml` to include RabbitMQ service.
"""
    
    # Read existing content
    content = readme_path.read_text()
    
    # Add migration note if not already present
    if "Worker Migration (2026-03-05)" not in content:
        content += migration_note
        readme_path.write_text(content)
        print("✓ Updated README.md with migration notes")
    else:
        print("- README.md already contains migration notes")

def main():
    """Run the migration completion process."""
    print("=== Worker Migration Completion ===\n")
    
    # Archive legacy files
    if archive_legacy_workers():
        print("\n✓ Legacy workers archived successfully")
    else:
        print("\n- No legacy workers found to archive")
    
    # Update documentation
    update_documentation()
    
    print("\n=== Migration Complete ===")
    print("The new RabbitMQ worker system is ready for use!")
    print("\nNext steps:")
    print("1. Set MINDFLOW_USE_NEW_WORKERS=1 in your environment")
    print("2. Start RabbitMQ: docker-compose -f python/docker-compose.backend.yml up -d rabbitmq")
    print("3. Test new workers: python -m mindflow_backend.workers.main --list")

if __name__ == "__main__":
    main()
