"""Configuration file watcher for hot reload functionality.

Monitors configuration files for changes and triggers
automatic reloads of gRPC configuration.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mindflow_backend.grpc.config.dynamic.manager import DynamicConfigManager
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class FileWatchConfig:
    """Configuration for file watching."""
    watch_directories: set[str]
    file_patterns: set[str]
    ignore_patterns: set[str]
    check_interval: float = 1.0
    debounce_delay: float = 2.0


class ConfigWatcher:
    """Watches configuration files for changes and triggers reloads."""
    
    def __init__(
        self,
        config_manager: DynamicConfigManager,
        watch_config: FileWatchConfig | None = None
    ):
        self.config_manager = config_manager
        self.watch_config = watch_config or self._default_watch_config()
        
        # Watcher state
        self._running: bool = False
        self._watch_task: asyncio.Task | None = None
        self._file_mtimes: Dict[str, float] = {}
        self._pending_changes: set[str] = set()
        self._debounce_task: asyncio.Task | None = None
        
        # Callbacks for change notifications
        self._change_callbacks: list[Callable[[str, float], None]] = []
        
        _logger.info("config_watcher_initialized", directories=list(self.watch_config.watch_directories))
    
    def _default_watch_config(self) -> FileWatchConfig:
        """Create default watch configuration."""
        return FileWatchConfig(
            watch_directories={
                ".",  # Current directory
                "config",
                "grpc/config",
            },
            file_patterns={
                "*.json",
                "*.yaml",
                "*.yml",
                "*.toml",
                "*.env",
                "grpc_config.*",
                "config.*",
            },
            ignore_patterns={
                "*.pyc",
                "__pycache__",
                ".git",
                "node_modules",
                "*.tmp",
                "*.swp",
                "*.log",
            },
            check_interval=1.0,
            debounce_delay=2.0
        )
    
    async def start(self) -> bool:
        """Start the configuration watcher."""
        if self._running:
            _logger.warning("config_watcher_already_running")
            return False
        
        try:
            # Initialize file modification times
            await self._initialize_file_mtimes()
            
            # Start watching task
            self._watch_task = asyncio.create_task(self._watch_loop())
            self._running = True
            
            _logger.info("config_watcher_started", check_interval=self.watch_config.check_interval)
            return True
            
        except Exception as exc:
            _logger.error("config_watcher_start_failed", error=str(exc))
            return False
    
    async def stop(self) -> bool:
        """Stop the configuration watcher."""
        if not self._running:
            _logger.warning("config_watcher_not_running")
            return False
        
        try:
            self._running = False
            
            # Cancel watch task
            if self._watch_task:
                self._watch_task.cancel()
                try:
                    await self._watch_task
                except asyncio.CancelledError:
                    pass
                self._watch_task = None
            
            # Cancel debounce task
            if self._debounce_task:
                self._debounce_task.cancel()
                try:
                    await self._debounce_task
                except asyncio.CancelledError:
                    pass
                self._debounce_task = None
            
            _logger.info("config_watcher_stopped")
            return True
            
        except Exception as exc:
            _logger.error("config_watcher_stop_failed", error=str(exc))
            return False
    
    def add_change_callback(self, callback: Callable[[str, float], None]) -> None:
        """Add callback for configuration changes."""
        self._change_callbacks.append(callback)
        _logger.debug("config_change_callback_added")
    
    def remove_change_callback(self, callback: Callable[[str, float], None]) -> bool:
        """Remove configuration change callback."""
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)
            _logger.debug("config_change_callback_removed")
            return True
        return False
    
    async def _initialize_file_mtimes(self):
        """Initialize modification times for watched files."""
        self._file_mtimes.clear()
        
        for directory in self.watch_config.watch_directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                _logger.warning("watch_directory_not_found", directory=directory)
                continue
            
            # Find all matching files
            for file_path in self._find_matching_files(dir_path):
                try:
                    mtime = file_path.stat().st_mtime
                    self._file_mtimes[str(file_path)] = mtime
                except OSError:
                    _logger.warning("failed_to_get_mtime", file=str(file_path))
        
        _logger.info("file_mtimes_initialized", count=len(self._file_mtimes))
    
    async def _watch_loop(self):
        """Main watch loop for detecting file changes."""
        _logger.debug("starting_watch_loop")
        
        while self._running:
            try:
                # Check for file changes
                changed_files = await self._check_file_changes()
                
                if changed_files:
                    # Add to pending changes
                    self._pending_changes.update(changed_files)
                    
                    # Trigger debounce timer
                    await self._schedule_debounce_reload()
                
                # Wait for next check
                await asyncio.sleep(self.watch_config.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _logger.error("watch_loop_error", error=str(exc))
                await asyncio.sleep(self.watch_config.check_interval)
        
        _logger.debug("watch_loop_ended")
    
    async def _check_file_changes(self) -> set[str]:
        """Check for file modifications."""
        changed_files = set()
        
        for directory in self.watch_config.watch_directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                continue
            
            # Find all matching files
            for file_path in self._find_matching_files(dir_path):
                file_str = str(file_path)
                
                try:
                    current_mtime = file_path.stat().st_mtime
                    previous_mtime = self._file_mtimes.get(file_str, 0)
                    
                    if current_mtime > previous_mtime:
                        changed_files.add(file_str)
                        self._file_mtimes[file_str] = current_mtime
                        
                        _logger.debug("file_changed", file=file_str, mtime=current_mtime)
                
                except OSError:
                    # File might have been deleted
                    if file_str in self._file_mtimes:
                        changed_files.add(file_str)
                        del self._file_mtimes[file_str]
                        _logger.debug("file_deleted", file=file_str)
        
        # Check for deleted files
        existing_files = set()
        for directory in self.watch_config.watch_directories:
            dir_path = Path(directory)
            if dir_path.exists():
                for file_path in self._find_matching_files(dir_path):
                    existing_files.add(str(file_path))
        
        deleted_files = set(self._file_mtimes.keys()) - existing_files
        for deleted_file in deleted_files:
            changed_files.add(deleted_file)
            del self._file_mtimes[deleted_file]
            _logger.debug("file_removed", file=deleted_file)
        
        return changed_files
    
    def _find_matching_files(self, directory: Path) -> list[Path]:
        """Find files matching watch patterns in directory."""
        matching_files = []
        
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    # Check if file matches any pattern
                    if self._matches_patterns(file_path):
                        matching_files.append(file_path)
        
        except OSError:
            _logger.warning("failed_to_scan_directory", directory=str(directory))
        
        return matching_files
    
    def _matches_patterns(self, file_path: Path) -> bool:
        """Check if file matches watch patterns."""
        file_str = str(file_path)
        
        # Check ignore patterns first
        for ignore_pattern in self.watch_config.ignore_patterns:
            if ignore_pattern in file_str:
                return False
        
        # Check include patterns
        for file_pattern in self.watch_config.file_patterns:
            if file_path.match(file_pattern):
                return True
        
        return False
    
    async def _schedule_debounce_reload(self):
        """Schedule debounced configuration reload."""
        # Cancel existing debounce task
        if self._debounce_task:
            self._debounce_task.cancel()
            try:
                await self._debounce_task
            except asyncio.CancelledError:
                pass
        
        # Schedule new debounce task
        self._debounce_task = asyncio.create_task(self._debounce_reload())
    
    async def _debounce_reload(self):
        """Debounced configuration reload."""
        try:
            # Wait for debounce delay
            await asyncio.sleep(self.watch_config.debounce_delay)
            
            if not self._running:
                return
            
            # Get pending changes
            changed_files = self._pending_changes.copy()
            self._pending_changes.clear()
            
            if changed_files:
                _logger.info("triggering_config_reload", changed_files=list(changed_files))
                
                # Trigger configuration reload
                success = await self.config_manager.reload_configuration()
                
                if success:
                    # Notify callbacks
                    timestamp = time.time()
                    for callback in self._change_callbacks:
                        try:
                            callback("config_reload", timestamp)
                        except Exception as exc:
                            _logger.error("config_change_callback_error", error=str(exc))
                    
                    _logger.info("config_reload_completed", changed_files=list(changed_files))
                else:
                    _logger.error("config_reload_failed", changed_files=list(changed_files))
        
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            _logger.error("debounce_reload_error", error=str(exc))
    
    async def get_statistics(self) -> dict[str, any]:
        """Get watcher statistics."""
        return {
            "running": self._running,
            "watched_directories": list(self.watch_config.watch_directories),
            "watched_files": len(self._file_mtimes),
            "pending_changes": len(self._pending_changes),
            "check_interval": self.watch_config.check_interval,
            "debounce_delay": self.watch_config.debounce_delay,
            "callbacks": len(self._change_callbacks),
        }


class EnvironmentVariableWatcher:
    """Watches environment variables for changes."""
    
    def __init__(self, config_manager: DynamicConfigManager):
        self.config_manager = config_manager
        self._running: bool = False
        self._watch_task: asyncio.Task | None = None
        self._env_values: Dict[str, str] = {}
        self._check_interval: float = 5.0
        self._change_callbacks: list[Callable[[str, float], None]] = []
        
        # Environment variables to watch
        self._watched_vars = {
            "GRPC_",
            "APP_ENV",
            "LOG_LEVEL",
        }
    
    async def start(self) -> bool:
        """Start environment variable watcher."""
        if self._running:
            _logger.warning("env_watcher_already_running")
            return False
        
        try:
            # Initialize environment values
            self._initialize_env_values()
            
            # Start watching task
            self._watch_task = asyncio.create_task(self._watch_loop())
            self._running = True
            
            _logger.info("env_watcher_started", check_interval=self._check_interval)
            return True
            
        except Exception as exc:
            _logger.error("env_watcher_start_failed", error=str(exc))
            return False
    
    async def stop(self) -> bool:
        """Stop environment variable watcher."""
        if not self._running:
            _logger.warning("env_watcher_not_running")
            return False
        
        try:
            self._running = False
            
            if self._watch_task:
                self._watch_task.cancel()
                try:
                    await self._watch_task
                except asyncio.CancelledError:
                    pass
                self._watch_task = None
            
            _logger.info("env_watcher_stopped")
            return True
            
        except Exception as exc:
            _logger.error("env_watcher_stop_failed", error=str(exc))
            return False
    
    def add_change_callback(self, callback: Callable[[str, float], None]) -> None:
        """Add callback for environment variable changes."""
        self._change_callbacks.append(callback)
    
    def _initialize_env_values(self):
        """Initialize environment variable values."""
        self._env_values.clear()
        
        for key, value in os.environ.items():
            if self._should_watch_var(key):
                self._env_values[key] = value
        
        _logger.debug("env_values_initialized", count=len(self._env_values))
    
    def _should_watch_var(self, var_name: str) -> bool:
        """Check if environment variable should be watched."""
        return any(var_name.startswith(prefix) for prefix in self._watched_vars)
    
    async def _watch_loop(self):
        """Main watch loop for environment variables."""
        _logger.debug("starting_env_watch_loop")
        
        while self._running:
            try:
                # Check for environment variable changes
                changed_vars = await self._check_env_changes()
                
                if changed_vars:
                    _logger.info("env_variables_changed", changed_vars=list(changed_vars))
                    
                    # Trigger configuration reload
                    success = await self.config_manager.reload_configuration()
                    
                    if success:
                        # Notify callbacks
                        timestamp = time.time()
                        for callback in self._change_callbacks:
                            try:
                                callback("env_change", timestamp)
                            except Exception as exc:
                                _logger.error("env_change_callback_error", error=str(exc))
                        
                        _logger.info("env_change_reload_completed")
                    else:
                        _logger.error("env_change_reload_failed")
                
                await asyncio.sleep(self._check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _logger.error("env_watch_loop_error", error=str(exc))
                await asyncio.sleep(self._check_interval)
        
        _logger.debug("env_watch_loop_ended")
    
    async def _check_env_changes(self) -> set[str]:
        """Check for environment variable changes."""
        changed_vars = set()
        
        for key, value in os.environ.items():
            if self._should_watch_var(key):
                old_value = self._env_values.get(key)
                if old_value != value:
                    changed_vars.add(key)
                    self._env_values[key] = value
        
        # Check for deleted variables
        current_vars = {key for key in os.environ.keys() if self._should_watch_var(key)}
        deleted_vars = set(self._env_values.keys()) - current_vars
        
        for deleted_var in deleted_vars:
            changed_vars.add(deleted_var)
            del self._env_values[deleted_var]
        
        return changed_vars
    
    async def get_statistics(self) -> dict[str, any]:
        """Get environment watcher statistics."""
        return {
            "running": self._running,
            "watched_variables": len(self._env_values),
            "check_interval": self._check_interval,
            "callbacks": len(self._change_callbacks),
        }


class CombinedConfigWatcher:
    """Combined watcher for both files and environment variables."""
    
    def __init__(self, config_manager: DynamicConfigManager):
        self.config_manager = config_manager
        self.file_watcher = ConfigWatcher(config_manager)
        self.env_watcher = EnvironmentVariableWatcher(config_manager)
        self._running: bool = False
    
    async def start(self) -> bool:
        """Start both watchers."""
        if self._running:
            _logger.warning("combined_watcher_already_running")
            return False
        
        try:
            # Start both watchers
            file_success = await self.file_watcher.start()
            env_success = await self.env_watcher.start()
            
            self._running = file_success or env_success
            
            if self._running:
                _logger.info("combined_watcher_started", file_watcher=file_success, env_watcher=env_success)
            else:
                _logger.error("combined_watcher_start_failed")
            
            return self._running
            
        except Exception as exc:
            _logger.error("combined_watcher_start_error", error=str(exc))
            return False
    
    async def stop(self) -> bool:
        """Stop both watchers."""
        if not self._running:
            _logger.warning("combined_watcher_not_running")
            return False
        
        try:
            # Stop both watchers
            file_success = await self.file_watcher.stop()
            env_success = await self.env_watcher.stop()
            
            self._running = False
            
            _logger.info("combined_watcher_stopped", file_watcher=file_success, env_watcher=env_success)
            return True
            
        except Exception as exc:
            _logger.error("combined_watcher_stop_error", error=str(exc))
            return False
    
    def add_change_callback(self, callback: Callable[[str, float], None]) -> None:
        """Add change callback to both watchers."""
        self.file_watcher.add_change_callback(callback)
        self.env_watcher.add_change_callback(callback)
    
    async def get_statistics(self) -> dict[str, any]:
        """Get combined watcher statistics."""
        return {
            "running": self._running,
            "file_watcher": await self.file_watcher.get_statistics(),
            "env_watcher": await self.env_watcher.get_statistics(),
        }
