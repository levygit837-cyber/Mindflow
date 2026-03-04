"""Port management for PitchTab instances.

Manages port allocation and prevents conflicts between
multiple browser instances.
"""

from __future__ import annotations

import asyncio
import socket
from contextlib import asynccontextmanager
from typing import Set

from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class PortManager:
    """Manages port allocation for PitchTab instances."""
    
    def __init__(self, port_range: tuple[int, int] = (9867, 9967)) -> None:
        """Initialize port manager with configurable range.
        
        Args:
            port_range: Tuple of (start_port, end_port) for allocation
        """
        self.port_range = port_range
        self._allocated_ports: Set[int] = set()
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
        except Exception as exc:
            _logger.warning("port_check_failed", port=port, error=str(exc))
            return False
            
    async def allocate_port(self) -> int:
        """Allocate an available port from the range.
        
        Returns:
            Available port number
            
        Raises:
            RuntimeError: If no ports available
        """
        async with self._master_lock:
            for port in range(self.port_range[0], self.port_range[1] + 1):
                if await self.is_available(port):
                    self._allocated_ports.add(port)
                    self._port_locks[port] = asyncio.Lock()
                    _logger.info("port_allocated", port=port, total_allocated=len(self._allocated_ports))
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
                if port in self._port_locks:
                    del self._port_locks[port]
                _logger.info("port_released", port=port, total_allocated=len(self._allocated_ports))
                
    @asynccontextmanager
    async def lock_port(self, port: int):
        """Context manager for port-exclusive operations.
        
        Args:
            port: Port number to lock
            
        Yields:
            Port lock context
        """
        if port not in self._port_locks:
            self._port_locks[port] = asyncio.Lock()
            
        async with self._port_locks[port]:
            yield
            
    def get_allocated_ports(self) -> Set[int]:
        """Get set of currently allocated ports.
        
        Returns:
            Set of allocated port numbers
        """
        return self._allocated_ports.copy()
        
    def get_status(self) -> dict[str, any]:
        """Get current port manager status.
        
        Returns:
            Dictionary with status information
        """
        total_ports = self.port_range[1] - self.port_range[0] + 1
        available_ports = total_ports - len(self._allocated_ports)
        
        return {
            "total_range": self.port_range,
            "total_ports": total_ports,
            "allocated_ports": len(self._allocated_ports),
            "available_ports": available_ports,
            "utilization_percent": (len(self._allocated_ports) / total_ports) * 100,
            "allocated_list": sorted(list(self._allocated_ports)),
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
