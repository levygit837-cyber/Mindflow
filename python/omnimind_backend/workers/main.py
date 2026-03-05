"""Main worker entry point using the new hierarchical RabbitMQ system."""

from __future__ import annotations

import asyncio
import signal
import sys
from typing import List

from omnimind_backend.infra.logging import get_logger
from omnimind_backend.workers.infrastructure.worker_factory import WorkerFactory
from omnimind_backend.workers.infrastructure.monitoring import WorkerMonitor

_logger = get_logger(__name__)


def _handle_shutdown(signum: int, frame) -> None:
    """Handle shutdown signals gracefully."""
    _logger.info(f"Received signal {signum}, shutting down workers...")
    sys.exit(0)


async def run_workers(worker_types: List[str] | None = None) -> None:
    """Run the specified worker types or all available workers."""
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)
    
    factory = WorkerFactory()
    monitor = WorkerMonitor()
    
    try:
        # Start workers
        if worker_types is None:
            # Start all available workers
            worker_types = list(factory._worker_registry.keys())
        
        _logger.info(f"Starting workers: {', '.join(worker_types)}")
        
        # Create and start worker instances
        for worker_type in worker_types:
            if worker_type not in factory._worker_registry:
                _logger.error(f"Unknown worker type: {worker_type}")
                continue
                
            try:
                worker = factory.create_worker(worker_type)
                await worker.start()
                monitor.register_worker(worker)
                _logger.info(f"Started {worker_type} worker")
            except Exception as e:
                _logger.error(f"Failed to start {worker_type} worker: {e}")
        
        # Start monitoring
        await monitor.start()
        
        _logger.info("All workers started successfully")
        
        # Keep running until shutdown
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        _logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        _logger.error(f"Worker runtime error: {e}")
        raise
    finally:
        # Cleanup
        _logger.info("Shutting down workers...")
        await monitor.stop()
        
        # Stop all workers
        for worker in monitor._workers.values():
            try:
                await worker.stop()
            except Exception as e:
                _logger.error(f"Error stopping worker: {e}")
        
        _logger.info("Workers shutdown complete")


def main() -> None:
    """Main entry point for worker processes."""
    import argparse
    
    parser = argparse.ArgumentParser(description="OmniMind Worker Process")
    parser.add_argument(
        "--workers", 
        nargs="+", 
        help="Specific worker types to start (default: all)"
    )
    parser.add_argument(
        "--list", 
        action="store_true", 
        help="List available worker types"
    )
    
    args = parser.parse_args()
    
    if args.list:
        factory = WorkerFactory()
        print("Available worker types:")
        for worker_type in sorted(factory._worker_registry.keys()):
            print(f"  - {worker_type}")
        return
    
    # Run the workers
    asyncio.run(run_workers(args.workers))


if __name__ == "__main__":
    main()
