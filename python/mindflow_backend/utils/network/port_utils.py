"""Port management utilities for MindFlow backend.

Manages port allocation and prevents conflicts between
multiple instances.
"""

from __future__ import annotations

import asyncio
import socket
from contextlib import asynccontextmanager

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class PortManager:
    """Manages port allocation for instances."""
    
    def __init__(self, port_range: tuple[int, int] = (9867, 9967)) -> None:
        """Initialize port manager with configurable range.
        
        Args:
            port_range: Tuple of (start_port, end_port) for allocation
        """
        self.port_range = port_range
        self._allocated_ports: set[int] = set()
        self._port_locks: dict[int, asyncio.Lock] = {}
        self._master_lock = asyncio.Lock()
        
    async def is_available(self, port: int) -> bool:
        """Check if a port is available for allocation.
        
        Args:
            port: Port number to check
            
        Returns:
            True if port is available, False otherwise
        """
        if port in self._allocated_ports:
            return False
            
        # Check if port is actually free
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result != 0
        except Exception:
            return False
    
    async def allocate_port(self, preferred_port: Optional[int] = None) -> int:
        """Allocate a port from the configured range.
        
        Args:
            preferred_port: Preferred port number (optional)
            
        Returns:
            Allocated port number
            
        Raises:
            RuntimeError: If no ports are available
        """
        async with self._master_lock:
            # If preferred port is specified, try to allocate it
            if preferred_port is not None:
                if (self.port_range[0] <= preferred_port <= self.port_range[1] and
                    await self.is_available(preferred_port)):
                    self._allocated_ports.add(preferred_port)
                    self._port_locks[preferred_port] = asyncio.Lock()
                    _logger.info("allocated_preferred_port", port=preferred_port)
                    return preferred_port
                else:
                    _logger.warning("preferred_port_unavailable", port=preferred_port)
            
            # Find first available port in range
            for port in range(self.port_range[0], self.port_range[1] + 1):
                if await self.is_available(port):
                    self._allocated_ports.add(port)
                    self._port_locks[port] = asyncio.Lock()
                    _logger.info("allocated_port", port=port)
                    return port
            
            raise RuntimeError(f"No available ports in range {self.port_range}")
    
    async def release_port(self, port: int) -> None:
        """Release a previously allocated port.
        
        Args:
            port: Port number to release
        """
        async with self._master_lock:
            if port in self._allocated_ports:
                self._allocated_ports.remove(port)
                self._port_locks.pop(port, None)
                _logger.info("released_port", port=port)
    
    @asynccontextmanager
    async def managed_port(self, preferred_port: Optional[int] = None):
        """Context manager for managed port allocation.
        
        Args:
            preferred_port: Preferred port number (optional)
            
        Yields:
            Allocated port number
        """
        port = await self.allocate_port(preferred_port)
        try:
            yield port
        finally:
            await self.release_port(port)
    
    async def get_allocated_ports(self) -> list[int]:
        """Get list of currently allocated ports.
        
        Returns:
            List of allocated port numbers
        """
        async with self._master_lock:
            return list(self._allocated_ports)
    
    async def get_available_ports(self) -> list[int]:
        """Get list of available ports in range.
        
        Returns:
            List of available port numbers
        """
        available_ports = []
        for port in range(self.port_range[0], self.port_range[1] + 1):
            if await self.is_available(port):
                available_ports.append(port)
        return available_ports
    
    async def is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use by any process.
        
        Args:
            port: Port number to check
            
        Returns:
            True if port is in use, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result == 0
        except Exception:
            return False
    
    async def wait_for_port(self, port: int, timeout: float = 30.0) -> bool:
        """Wait for a port to become available.
        
        Args:
            port: Port number to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if port became available, False if timeout
        """
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            if await self.is_available(port):
                return True
            await asyncio.sleep(0.1)
        
        return False
    
    def get_port_lock(self, port: int) -> asyncio.Lock:
        """Get lock for specific port.
        
        Args:
            port: Port number
            
        Returns:
            Asyncio lock for the port
        """
        if port not in self._port_locks:
            self._port_locks[port] = asyncio.Lock()
        return self._port_locks[port]
    
    async def reset(self) -> None:
        """Reset port manager, clearing all allocations."""
        async with self._master_lock:
            self._allocated_ports.clear()
            self._port_locks.clear()
            _logger.info("port_manager_reset")
    
    def get_stats(self) -> dict:
        """Get port manager statistics.
        
        Returns:
            Dictionary with port manager statistics
        """
        total_ports = self.port_range[1] - self.port_range[0] + 1
        allocated_count = len(self._allocated_ports)
        available_count = total_ports - allocated_count
        
        return {
            "port_range": self.port_range,
            "total_ports": total_ports,
            "allocated_ports": allocated_count,
            "available_ports": available_count,
            "utilization": allocated_count / total_ports if total_ports > 0 else 0,
            "allocated_list": list(self._allocated_ports),
        }


# Global port manager instance
_port_manager: PortManager | None = None


def get_port_manager() -> PortManager:
    """Get or create global port manager instance.
    
    Returns:
        PortManager singleton instance
    """
    global _port_manager
    if _port_manager is None:
        _port_manager = PortManager()
    return _port_manager


async def find_free_port(start_port: int = 8000, end_port: int = 9000) -> int:
    """Find a free port in the specified range.
    
    Args:
        start_port: Start of port range
        end_port: End of port range
        
    Returns:
        Free port number
        
    Raises:
        RuntimeError: If no free ports found
    """
    for port in range(start_port, end_port + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                if result != 0:
                    return port
        except Exception:
            continue
    
    raise RuntimeError(f"No free ports found in range {start_port}-{end_port}")


def is_port_open(port: int, host: str = 'localhost', timeout: float = 1.0) -> bool:
    """Check if a port is open on the specified host.
    
    Args:
        port: Port number to check
        host: Host to check
        timeout: Connection timeout
        
    Returns:
        True if port is open, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return result == 0
    except Exception:
        return False


async def wait_for_port_open(
    port: int,
    host: str = 'localhost',
    timeout: float = 30.0,
    check_interval: float = 0.5,
) -> bool:
    """Wait for a port to open.
    
    Args:
        port: Port number to wait for
        host: Host to check
        timeout: Maximum time to wait
        check_interval: Time between checks
        
    Returns:
        True if port opened, False if timeout
    """
    start_time = asyncio.get_event_loop().time()
    
    while (asyncio.get_event_loop().time() - start_time) < timeout:
        if is_port_open(port, host, timeout=1.0):
            return True
        await asyncio.sleep(check_interval)
    
    return False


async def wait_for_port_close(
    port: int,
    host: str = 'localhost',
    timeout: float = 30.0,
    check_interval: float = 0.5,
) -> bool:
    """Wait for a port to close.
    
    Args:
        port: Port number to wait for
        host: Host to check
        timeout: Maximum time to wait
        check_interval: Time between checks
        
    Returns:
        True if port closed, False if timeout
    """
    start_time = asyncio.get_event_loop().time()
    
    while (asyncio.get_event_loop().time() - start_time) < timeout:
        if not is_port_open(port, host, timeout=1.0):
            return True
        await asyncio.sleep(check_interval)
    
    return False
