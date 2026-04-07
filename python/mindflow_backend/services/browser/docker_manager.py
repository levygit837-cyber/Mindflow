"""Docker manager for LightPanda browser instances.

Manages creation, destruction, and monitoring of LightPanda browser containers
via Docker SDK for the MindFlow Research Agent.
"""

from __future__ import annotations

import asyncio
import httpx
import os
import socket
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, validator

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class BrowserInstanceConfig(BaseModel):
    """Configuration for browser instance creation."""
    
    max_memory_mb: int = Field(default=512, ge=128, le=2048, description="Max memory in MB")
    max_cpu_percent: float = Field(default=80.0, ge=10.0, le=100.0, description="Max CPU percentage")
    timeout_seconds: int = Field(default=30, ge=5, le=300, description="Operation timeout in seconds")
    require_snapshot: bool = Field(default=False, description="Whether to create initial snapshot")
    
    @validator("max_memory_mb")
    def validate_memory(cls, v):
        if v < 128:
            raise ValueError("Memory must be at least 128MB")
        if v > 2048:
            raise ValueError("Memory cannot exceed 2048MB")
        return v


class InstanceStatus(str, Enum):
    """Status of a browser instance."""
    CREATING = "creating"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class BrowserInstance:
    """Represents a LightPanda browser instance."""
    
    instance_id: str
    container_id: str
    container_name: str
    port: int
    host: str
    status: InstanceStatus
    created_at: datetime
    task_id: str
    last_activity: datetime
    config: BrowserInstanceConfig | None = None
    
    @property
    def cdp_url(self) -> str:
        """Get Chrome DevTools Protocol URL."""
        return f"http://{self.host}:{self.port}"
    
    @property
    def uptime_seconds(self) -> float:
        """Get instance uptime in seconds."""
        return (datetime.utcnow() - self.created_at).total_seconds()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert instance to dictionary."""
        return {
            "instance_id": self.instance_id,
            "container_id": self.container_id,
            "container_name": self.container_name,
            "port": self.port,
            "host": self.host,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "task_id": self.task_id,
            "last_activity": self.last_activity.isoformat(),
            "cdp_url": self.cdp_url,
            "uptime_seconds": self.uptime_seconds,
        }


class DockerManagerError(Exception):
    """Base error for Docker manager operations."""
    pass


class MaxInstancesError(DockerManagerError):
    """Raised when max instances limit is reached."""
    pass


class ContainerCreationError(DockerManagerError):
    """Raised when container creation fails."""
    pass


class ContainerNotFoundError(DockerManagerError):
    """Raised when container is not found."""
    pass


class RateLimitError(DockerManagerError):
    """Raised when rate limit is exceeded."""
    pass


class LightPandaDockerManager:
    """Manages LightPanda browser containers via Docker SDK.
    
    This service provides:
    - Creation and destruction of LightPanda containers
    - Instance status monitoring
    - Health checks
    - Cleanup of stale instances
    - Connection pooling for Docker client
    - Rate limiting for container creation
    """
    
    def __init__(
        self,
        base_port: int = 9222,
        max_instances: int = 5,
        host: str = "127.0.0.1",
        image: str = "lightpanda/browser:nightly",
        rate_limit_per_minute: int = 10,
        health_check_interval: int = 30,
    ):
        """Initialize the Docker manager.
        
        Args:
            base_port: Starting port for CDP servers
            max_instances: Maximum number of concurrent instances
            host: Host address for CDP connections
            image: Docker image to use for LightPanda
            rate_limit_per_minute: Max container creations per minute
            health_check_interval: Health check interval in seconds
        """
        self.base_port = base_port
        self.max_instances = max_instances
        self.host = host
        self.image = image
        self.rate_limit_per_minute = rate_limit_per_minute
        self.health_check_interval = health_check_interval
        
        # In-memory instance storage
        self._instances: dict[str, BrowserInstance] = {}
        self._port_counter = base_port
        self._lock = asyncio.Lock()
        
        # Docker client with connection pooling
        self._docker_client: Any = None
        self._client_lock = asyncio.Lock()
        
        # Rate limiting
        self._creation_timestamps: list[float] = []
        
        # Health check task
        self._health_check_task: asyncio.Task | None = None
    
    async def _get_docker_client(self) -> Any:
        """Get or create Docker client with connection pooling.
        
        Returns:
            Docker client instance
            
        Raises:
            DockerManagerError: If Docker SDK not installed or connection fails
        """
        async with self._client_lock:
            if self._docker_client is None:
                try:
                    import docker
                    self._docker_client = docker.from_env()
                    _logger.info("docker_client_connected")
                except ImportError as exc:
                    _logger.error("docker_sdk_not_installed")
                    raise DockerManagerError(
                        "Docker SDK not installed. Install with: pip install docker"
                    ) from exc
                except Exception as exc:
                    _logger.error("docker_client_connection_failed", error=str(exc))
                    raise DockerManagerError(
                        f"Failed to connect to Docker: {exc}"
                    ) from exc
        
        return self._docker_client
    
    async def _check_rate_limit(self) -> None:
        """Check if rate limit for container creation is exceeded.
        
        Raises:
            RateLimitError: If rate limit is exceeded
        """
        now = time.time()
        # Remove timestamps older than 1 minute
        self._creation_timestamps = [ts for ts in self._creation_timestamps if now - ts < 60]
        
        if len(self._creation_timestamps) >= self.rate_limit_per_minute:
            _logger.warning(
                "rate_limit_exceeded",
                count=len(self._creation_timestamps),
                limit=self.rate_limit_per_minute,
            )
            raise RateLimitError(
                f"Rate limit exceeded: {len(self._creation_timestamps)}/{self.rate_limit_per_minute} per minute"
            )
        
        self._creation_timestamps.append(now)
    
    def _generate_instance_id(self, task_id: str) -> str:
        """Generate unique instance ID."""
        timestamp = int(time.time())
        return f"browser-{task_id}-{timestamp}"
    
    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available for use.
        
        Args:
            port: Port number to check
            
        Returns:
            bool: True if port is available
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((self.host, port))
                return result != 0  # Port is available if connection fails
        except Exception:
            return False
    
    async def _get_next_port(self) -> int:
        """Get next available port with lock protection.
        
        Returns:
            int: Available port number
        """
        async with self._lock:
            max_attempts = 100  # Prevent infinite loop
            attempts = 0
            
            while attempts < max_attempts:
                port = self._port_counter
                self._port_counter += 1
                
                # Check if port is available
                if self._is_port_available(port):
                    _logger.debug("port_available", port=port)
                    return port
                
                _logger.debug("port_in_use_trying_next", port=port)
                attempts += 1
            
            raise RuntimeError(
                f"Could not find available port after {max_attempts} attempts"
            )
    
    async def create_browser_instance(
        self,
        task_id: str,
        config: BrowserInstanceConfig | None = None,
    ) -> BrowserInstance:
        """Create a new LightPanda browser instance.
        
        Args:
            task_id: ID of the task requesting the browser
            config: Browser instance configuration
            
        Returns:
            BrowserInstance: Created browser instance
            
        Raises:
            MaxInstancesError: If max instances reached
            RateLimitError: If rate limit is exceeded
            ContainerCreationError: If container creation fails
        """
        config = config or BrowserInstanceConfig()
        
        # Check rate limit
        await self._check_rate_limit()
        
        async with self._lock:
            # Check max instances limit
            if len(self._instances) >= self.max_instances:
                _logger.error(
                    "max_instances_reached",
                    current=len(self._instances),
                    max=self.max_instances,
                )
                raise MaxInstancesError(
                    f"Maximum {self.max_instances} browser instances reached"
                )
            
            instance_id = self._generate_instance_id(task_id)
            port = self._get_next_port()
            container_name = f"mindflow-lightpanda-{instance_id}"
            
            _logger.info(
                "creating_browser_instance",
                instance_id=instance_id,
                task_id=task_id,
                port=port,
            )
            
            try:
                # Create instance record
                instance = BrowserInstance(
                    instance_id=instance_id,
                    container_id="",  # Will be set by Docker
                    container_name=container_name,
                    port=port,
                    host=self.host,
                    status=InstanceStatus.CREATING,
                    created_at=datetime.utcnow(),
                    task_id=task_id,
                    last_activity=datetime.utcnow(),
                    config=config,
                )
                
                # Get Docker client and create container
                client = await self._get_docker_client()
                
                # Run container with Docker SDK
                container = client.containers.run(
                    self.image,
                    name=container_name,
                    ports={"9222/tcp": port},
                    environment={
                        "LIGHTPANDA_DISABLE_TELEMETRY": "true",
                    },
                    mem_limit=f"{config.max_memory_mb}m",
                    detach=True,
                    auto_remove=False,
                )
                instance.container_id = container.id
                
                # Wait for container to be healthy
                await self._wait_for_container_health(container, config.timeout_seconds)
                
                # Update status to running
                instance.status = InstanceStatus.RUNNING
                self._instances[instance_id] = instance
                
                _logger.info(
                    "browser_instance_created",
                    instance_id=instance_id,
                    cdp_url=instance.cdp_url,
                    container_id=instance.container_id,
                )
                
                return instance
                
            except MaxInstancesError:
                raise
            except RateLimitError:
                raise
            except Exception as exc:
                _logger.error(
                    "browser_instance_creation_failed",
                    instance_id=instance_id,
                    error=str(exc),
                    exc_info=True,
                )
                raise ContainerCreationError(
                    f"Failed to create browser instance: {exc}"
                ) from exc
    
    async def _wait_for_container_health(
        self,
        container: Any,
        timeout_seconds: int = 30,
    ) -> None:
        """Wait for container to become healthy.
        
        Args:
            container: Docker container object
            timeout_seconds: Maximum time to wait in seconds
            
        Raises:
            ContainerCreationError: If container doesn't become healthy
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                container.reload()
                status = container.status
                
                if status == "running":
                    # Try to access CDP endpoint
                    async with httpx.AsyncClient(timeout=5.0) as http_client:
                        response = await http_client.get(
                            f"http://{self.host}:{container.ports['9222/tcp']}",
                        )
                        if response.status_code == 200:
                            _logger.info("container_healthy", container_id=container.id)
                            return
                elif status in {"exited", "dead"}:
                    raise ContainerCreationError(
                        f"Container exited with status: {status}"
                    )
                
                await asyncio.sleep(1)
                
            except httpx.RequestError as exc:
                _logger.debug("container_not_ready_yet", error=str(exc))
                await asyncio.sleep(1)
            except Exception as exc:
                _logger.warning("container_health_check_error", error=str(exc))
                await asyncio.sleep(1)
        
        raise ContainerCreationError(
            f"Container did not become healthy within {timeout_seconds} seconds"
        )
    
    async def destroy_browser_instance(self, instance_id: str) -> bool:
        """Destroy a browser instance.
        
        Args:
            instance_id: ID of the instance to destroy
            
        Returns:
            bool: True if destruction succeeded
        """
        async with self._lock:
            if instance_id not in self._instances:
                _logger.warning("browser_instance_not_found", instance_id=instance_id)
                return False
            
            instance = self._instances[instance_id]
            
            _logger.info(
                "destroying_browser_instance",
                instance_id=instance_id,
                container_id=instance.container_id,
            )
            
            try:
                # Update status
                instance.status = InstanceStatus.STOPPING
                
                # Get Docker client and destroy container
                client = await self._get_docker_client()
                try:
                    container = client.containers.get(instance.container_id)
                    container.stop(timeout=10)
                    container.remove(force=True)
                    _logger.info("docker_container_removed", container_id=instance.container_id)
                except Exception as exc:
                    _logger.warning("docker_container_removal_failed", error=str(exc))
                
                # Remove from storage
                del self._instances[instance_id]
                
                _logger.info("browser_instance_destroyed", instance_id=instance_id)
                return True
                
            except Exception as exc:
                _logger.error(
                    "browser_instance_destruction_failed",
                    instance_id=instance_id,
                    error=str(exc),
                    exc_info=True,
                )
                if instance_id in self._instances:
                    self._instances[instance_id].status = InstanceStatus.ERROR
                return False
    
    async def get_instance_status(self, instance_id: str) -> InstanceStatus:
        """Get the status of a browser instance.
        
        Args:
            instance_id: ID of the instance
            
        Returns:
            InstanceStatus: Current status of the instance
        """
        if instance_id not in self._instances:
            return InstanceStatus.UNKNOWN
        
        instance = self._instances[instance_id]
        
        # In production, check actual container status via Docker SDK
        # client = await self._get_docker_client()
        # container = client.containers.get(instance.container_id)
        # container.reload()
        # status = container.status
        
        return instance.status
    
    async def list_active_instances(self) -> list[BrowserInstance]:
        """List all active browser instances.
        
        Returns:
            list[BrowserInstance]: List of active instances
        """
        return [
            instance for instance in self._instances.values()
            if instance.status in (InstanceStatus.RUNNING, InstanceStatus.CREATING)
        ]
    
    async def cleanup_stale_instances(self, max_age_seconds: int = 3600) -> int:
        """Clean up instances that have been idle for too long.
        
        Args:
            max_age_seconds: Maximum age in seconds before cleanup
            
        Returns:
            int: Number of instances cleaned up
        """
        now = datetime.utcnow()
        cleanup_count = 0
        
        for instance_id, instance in list(self._instances.items()):
            # Check if instance is idle
            if instance.last_activity:
                idle_time = (now - instance.last_activity).total_seconds()
                if idle_time > max_age_seconds:
                    _logger.info(
                        "cleaning_up_idle_instance",
                        instance_id=instance_id,
                        idle_seconds=idle_time,
                    )
                    if await self.destroy_browser_instance(instance_id):
                        cleanup_count += 1
            else:
                # Check if instance is old (no activity recorded)
                age = (now - instance.created_at).total_seconds()
                if age > max_age_seconds:
                    _logger.info(
                        "cleaning_up_old_instance",
                        instance_id=instance_id,
                        age_seconds=age,
                    )
                    if await self.destroy_browser_instance(instance_id):
                        cleanup_count += 1
        
        if cleanup_count > 0:
            _logger.info("cleanup_completed", count=cleanup_count)
        
        return cleanup_count
    
    async def update_instance_activity(self, instance_id: str) -> bool:
        """Update last activity timestamp for an instance.
        
        Args:
            instance_id: ID of the instance
            
        Returns:
            bool: True if update succeeded
        """
        if instance_id not in self._instances:
            return False
        
        self._instances[instance_id].last_activity = datetime.utcnow()
        return True
    
    async def get_instance_metrics(self, instance_id: str) -> dict[str, Any]:
        """Get metrics for a specific instance.
        
        Args:
            instance_id: ID of the instance
            
        Returns:
            dict[str, Any]: Instance metrics
        """
        if instance_id not in self._instances:
            return {}
        
        instance = self._instances[instance_id]
        now = datetime.utcnow()
        
        # In production, get actual Docker container stats:
        # client = await self._get_docker_client()
        # container = client.containers.get(instance.container_id)
        # stats = container.stats(stream=False)
        
        # Mock metrics
        uptime = (now - instance.created_at).total_seconds()
        idle_time = (now - instance.last_activity).total_seconds() if instance.last_activity else 0
        
        return {
            "instance_id": instance_id,
            "status": instance.status.value,
            "uptime_seconds": uptime,
            "idle_time_seconds": idle_time,
            "cpu_usage_percent": 0.0,  # Mock
            "memory_usage_mb": 128.0,  # Mock
            "request_count": 0,  # Mock
            "cdp_url": instance.cdp_url,
        }
    
    async def get_all_metrics(self) -> dict[str, Any]:
        """Get aggregated metrics for all instances.
        
        Returns:
            dict[str, Any]: Aggregated metrics
        """
        active_instances = await self.list_active_instances()
        
        total_memory = 0.0
        total_cpu = 0.0
        total_requests = 0
        
        for instance in active_instances:
            metrics = await self.get_instance_metrics(instance.instance_id)
            total_memory += metrics.get("memory_usage_mb", 0)
            total_cpu += metrics.get("cpu_usage_percent", 0)
            total_requests += metrics.get("request_count", 0)
        
        return {
            "total_instances": len(self._instances),
            "active_instances": len(active_instances),
            "max_instances": self.max_instances,
            "total_memory_usage_mb": total_memory,
            "average_cpu_usage_percent": total_cpu / len(active_instances) if active_instances else 0,
            "total_requests": total_requests,
            "instances": [i.to_dict() for i in active_instances],
        }
