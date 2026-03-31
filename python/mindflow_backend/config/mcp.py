"""
MCP Configuration Module

Configuration settings and management for MCP (Model Context Protocol)
components in the MindFlow system.
"""

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.schemas.mcp.base import (
    MCPCapability,
    MCPClientInfo,
    MCPServerInfo,
)
from mindflow_backend.schemas.mcp.transport import HTTPConfig, StdioConfig, WebSocketConfig


class MCPSettings(BaseModel):
    """Main MCP configuration settings."""
    
    enabled: bool = Field(default=True, description="Whether MCP is enabled")
    log_level: str = Field(default="INFO", description="MCP logging level")
    max_connections: int = Field(default=100, description="Maximum concurrent connections")
    request_timeout: float = Field(default=30.0, description="Default request timeout in seconds")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    
    # Server settings
    server_info: MCPServerInfo = Field(
        default_factory=lambda: MCPServerInfo(
            name="MindFlow MCP Server",
            version="1.0.0"
        ),
        description="Server information"
    )
    
    # Client settings
    client_info: MCPClientInfo = Field(
        default_factory=lambda: MCPClientInfo(
            name="MindFlow MCP Client",
            version="1.0.0"
        ),
        description="Client information"
    )
    
    # Capabilities
    capabilities: list[MCPCapability] = Field(
        default_factory=list,
        description="MCP capabilities"
    )
    
    # Transport configurations
    stdio_configs: list[StdioConfig] = Field(
        default_factory=list,
        description="Stdio transport configurations"
    )
    
    http_configs: list[HTTPConfig] = Field(
        default_factory=list,
        description="HTTP transport configurations"
    )
    
    websocket_configs: list[WebSocketConfig] = Field(
        default_factory=list,
        description="WebSocket transport configurations"
    )


class MCPEnvironmentConfig:
    """Environment-based MCP configuration loader."""
    
    def __init__(self, prefix: str = "MCP_"):
        """
        Initialize environment configuration loader.
        
        Args:
            prefix: Environment variable prefix
        """
        self.prefix = prefix
    
    def load_settings(self) -> MCPSettings:
        """
        Load MCP settings from environment variables.
        
        Returns:
            MCPSettings: Loaded configuration
        """
        # Basic settings
        enabled = self._get_bool("ENABLED", True)
        log_level = self._get_str("LOG_LEVEL", "INFO")
        max_connections = self._get_int("MAX_CONNECTIONS", 100)
        request_timeout = self._get_float("REQUEST_TIMEOUT", 30.0)
        enable_metrics = self._get_bool("ENABLE_METRICS", True)
        
        # Server info
        server_name = self._get_str("SERVER_NAME", "MindFlow MCP Server")
        server_version = self._get_str("SERVER_VERSION", "1.0.0")
        
        # Client info
        client_name = self._get_str("CLIENT_NAME", "MindFlow MCP Client")
        client_version = self._get_str("CLIENT_VERSION", "1.0.0")
        
        # Create settings
        settings = MCPSettings(
            enabled=enabled,
            log_level=log_level,
            max_connections=max_connections,
            request_timeout=request_timeout,
            enable_metrics=enable_metrics,
            server_info=MCPServerInfo(
                name=server_name,
                version=server_version
            ),
            client_info=MCPClientInfo(
                name=client_name,
                version=client_version
            )
        )
        
        # Load transport configurations
        self._load_stdio_configs(settings)
        self._load_http_configs(settings)
        self._load_websocket_configs(settings)
        
        return settings
    
    def _get_str(self, key: str, default: str) -> str:
        """Get string environment variable."""
        return os.getenv(f"{self.prefix}{key}", default)
    
    def _get_int(self, key: str, default: int) -> int:
        """Get integer environment variable."""
        try:
            return int(os.getenv(f"{self.prefix}{key}", str(default)))
        except ValueError:
            return default
    
    def _get_float(self, key: str, default: float) -> float:
        """Get float environment variable."""
        try:
            return float(os.getenv(f"{self.prefix}{key}", str(default)))
        except ValueError:
            return default
    
    def _get_bool(self, key: str, default: bool) -> bool:
        """Get boolean environment variable."""
        value = os.getenv(f"{self.prefix}{key}", "").lower()
        return value in ("true", "1", "yes", "on") if value else default
    
    def _load_stdio_configs(self, settings: MCPSettings) -> None:
        """Load stdio transport configurations from environment."""
        # Example: MCP_STDIO_0_COMMAND=python,mcp_server.py
        #          MCP_STDIO_0_WORKING_DIR=/path/to/dir
        i = 0
        while True:
            prefix = f"{self.prefix}STDIO_{i}_"
            command_str = os.getenv(f"{prefix}COMMAND")
            
            if not command_str:
                break
            
            command = [cmd.strip() for cmd in command_str.split(",")]
            working_dir = os.getenv(f"{prefix}WORKING_DIR")
            
            # Parse environment variables
            env_vars = {}
            env_str = os.getenv(f"{prefix}ENV", "")
            if env_str:
                for env_pair in env_str.split(","):
                    if "=" in env_pair:
                        key, value = env_pair.split("=", 1)
                        env_vars[key.strip()] = value.strip()
            
            config = StdioConfig(
                command=command,
                working_directory=working_dir,
                environment=env_vars if env_vars else None
            )
            
            settings.stdio_configs.append(config)
            i += 1
    
    def _load_http_configs(self, settings: MCPSettings) -> None:
        """Load HTTP transport configurations from environment."""
        # Example: MCP_HTTP_0_URL=http://localhost:8080/mcp
        #          MCP_HTTP_0_TIMEOUT=30
        i = 0
        while True:
            prefix = f"{self.prefix}HTTP_{i}_"
            url = os.getenv(f"{prefix}URL")
            
            if not url:
                break
            
            timeout = self._get_float(f"HTTP_{i}_TIMEOUT", 30.0)
            verify_ssl = self._get_bool(f"HTTP_{i}_VERIFY_SSL", True)
            follow_redirects = self._get_bool(f"HTTP_{i}_FOLLOW_REDIRECTS", True)
            
            config = HTTPConfig(
                url=url,
                timeout=timeout,
                verify_ssl=verify_ssl,
                follow_redirects=follow_redirects
            )
            
            settings.http_configs.append(config)
            i += 1
    
    def _load_websocket_configs(self, settings: MCPSettings) -> None:
        """Load WebSocket transport configurations from environment."""
        # Example: MCP_WS_0_URL=ws://localhost:8081/mcp
        #          MCP_WS_0_PING_INTERVAL=20
        i = 0
        while True:
            prefix = f"{self.prefix}WS_{i}_"
            url = os.getenv(f"{prefix}URL")
            
            if not url:
                break
            
            ping_interval = self._get_float(f"WS_{i}_PING_INTERVAL", 20.0)
            ping_timeout = self._get_float(f"WS_{i}_PING_TIMEOUT", 10.0)
            max_size = self._get_int(f"WS_{i}_MAX_SIZE", 2**20)
            
            config = WebSocketConfig(
                url=url,
                ping_interval=ping_interval,
                ping_timeout=ping_timeout,
                max_size=max_size
            )
            
            settings.websocket_configs.append(config)
            i += 1


class MCPFileConfig:
    """File-based MCP configuration loader."""
    
    def __init__(self, config_path: str | Path | None = None):
        """
        Initialize file configuration loader.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path) if config_path else None
    
    def load_settings(self) -> MCPSettings:
        """
        Load MCP settings from file.
        
        Returns:
            MCPSettings: Loaded configuration
        """
        if not self.config_path or not self.config_path.exists():
            # Return default settings
            return MCPSettings()
        
        try:
            import json
            
            with open(self.config_path) as f:
                config_data = json.load(f)
            
            return MCPSettings.model_validate(config_data)
            
        except Exception as e:
            # Log error and return defaults
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error loading MCP config from {self.config_path}: {e}")
            return MCPSettings()
    
    def save_settings(self, settings: MCPSettings) -> None:
        """
        Save MCP settings to file.
        
        Args:
            settings: Settings to save
        """
        if not self.config_path:
            raise ValueError("No config path specified")
        
        # Create directory if it doesn't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            import json
            
            with open(self.config_path, 'w') as f:
                json.dump(settings.model_dump(), f, indent=2, default=str)
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error saving MCP config to {self.config_path}: {e}")
            raise


class MCPConfigManager:
    """
    Main MCP configuration manager.
    
    This manager combines environment and file-based configuration
    to provide a unified configuration interface.
    """
    
    def __init__(
        self,
        config_path: str | Path | None = None,
        env_prefix: str = "MCP_"
    ):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file
            env_prefix: Environment variable prefix
        """
        self.env_config = MCPEnvironmentConfig(env_prefix)
        self.file_config = MCPFileConfig(config_path)
        self._settings: MCPSettings | None = None
    
    def get_settings(self) -> MCPSettings:
        """
        Get MCP settings, loading from file and environment.
        
        Returns:
            MCPSettings: Current configuration
        """
        if self._settings is None:
            # Load base settings from file
            self._settings = self.file_config.load_settings()
            
            # Override with environment variables
            env_settings = self.env_config.load_settings()
            
            # Merge settings (environment takes precedence)
            if env_settings.enabled is not None:
                self._settings.enabled = env_settings.enabled
            if env_settings.log_level:
                self._settings.log_level = env_settings.log_level
            if env_settings.max_connections != 100:  # Default value
                self._settings.max_connections = env_settings.max_connections
            if env_settings.request_timeout != 30.0:  # Default value
                self._settings.request_timeout = env_settings.request_timeout
            if env_settings.enable_metrics is not None:
                self._settings.enable_metrics = env_settings.enable_metrics
            
            # Merge server info
            if env_settings.server_info:
                self._settings.server_info = env_settings.server_info
            
            # Merge client info
            if env_settings.client_info:
                self._settings.client_info = env_settings.client_info
            
            # Merge transport configs
            self._settings.stdio_configs.extend(env_settings.stdio_configs)
            self._settings.http_configs.extend(env_settings.http_configs)
            self._settings.websocket_configs.extend(env_settings.websocket_configs)
        
        return self._settings
    
    def save_settings(self, settings: MCPSettings | None = None) -> None:
        """
        Save settings to file.
        
        Args:
            settings: Settings to save (uses current if None)
        """
        if settings:
            self._settings = settings
        
        if self._settings:
            self.file_config.save_settings(self._settings)
    
    def reload_settings(self) -> MCPSettings:
        """
        Reload settings from file and environment.
        
        Returns:
            MCPSettings: Reloaded configuration
        """
        self._settings = None
        return self.get_settings()
    
    def update_setting(self, key: str, value: Any) -> None:
        """
        Update a specific setting.
        
        Args:
            key: Setting key (dot notation for nested)
            value: New value
        """
        settings = self.get_settings()
        
        # Navigate to the nested key
        keys = key.split(".")
        current = settings
        
        for k in keys[:-1]:
            if not hasattr(current, k):
                raise AttributeError(f"Setting key '{key}' not found")
            current = getattr(current, k)
        
        # Set the final value
        setattr(current, keys[-1], value)
        
        # Update cached settings
        self._settings = settings


# Global configuration instance
_config_manager: MCPConfigManager | None = None


def get_config_manager(
    config_path: str | Path | None = None,
    env_prefix: str = "MCP_"
) -> MCPConfigManager:
    """
    Get the global configuration manager instance.
    
    Args:
        config_path: Path to configuration file
        env_prefix: Environment variable prefix
        
    Returns:
        MCPConfigManager: Configuration manager instance
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = MCPConfigManager(config_path, env_prefix)
    
    return _config_manager


def get_mcp_settings() -> MCPSettings:
    """
    Get current MCP settings.
    
    Returns:
        MCPSettings: Current configuration
    """
    return get_config_manager().get_settings()


def save_mcp_settings(settings: MCPSettings | None = None) -> None:
    """
    Save MCP settings to file.
    
    Args:
        settings: Settings to save (uses current if None)
    """
    get_config_manager().save_settings(settings)
