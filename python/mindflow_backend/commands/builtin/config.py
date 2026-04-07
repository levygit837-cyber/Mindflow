"""
Config command - manage runtime configuration (get, set, list, reset).
"""

from mindflow_backend.commands.types import (
    CommandCategory,
    CommandContext,
    CommandMetadata,
    CommandResult,
)


class ConfigCommand:
    """
    Manage runtime configuration.

    Usage:
        /config get <key>         - Get config value
        /config set <key> <value> - Set config value (requires admin)
        /config list              - List all config keys
        /config reset <key>       - Reset to default value
    """

    metadata = CommandMetadata(
        name="config",
        description="Manage runtime configuration",
        category=CommandCategory.CONFIG,
        aliases=("cfg",),
        examples=(
            "/config get max_agents",
            "/config set max_agents 10",
            "/config list",
            "/config reset max_agents",
        ),
        permission_required="admin",
    )

    async def execute(self, context: CommandContext) -> CommandResult:
        """Execute config command."""
        if not context.args:
            return CommandResult(
                success=False,
                message="Missing subcommand. Usage: /config <get|set|list|reset>",
                error="MISSING_SUBCOMMAND",
            )

        subcommand = context.args[0].lower()

        if subcommand == "get":
            if len(context.args) < 2:
                return CommandResult(
                    success=False,
                    message="Missing config key. Usage: /config get <key>",
                    error="MISSING_KEY",
                )
            key = context.args[1]
            return await self._get_config(key)
        elif subcommand == "set":
            if len(context.args) < 3:
                return CommandResult(
                    success=False,
                    message="Missing key or value. Usage: /config set <key> <value>",
                    error="MISSING_ARGUMENTS",
                )
            key = context.args[1]
            value = " ".join(context.args[2:])
            return await self._set_config(key, value)
        elif subcommand == "list":
            return await self._list_config()
        elif subcommand == "reset":
            if len(context.args) < 2:
                return CommandResult(
                    success=False,
                    message="Missing config key. Usage: /config reset <key>",
                    error="MISSING_KEY",
                )
            key = context.args[1]
            return await self._reset_config(key)
        else:
            return CommandResult(
                success=False,
                message=f"Unknown subcommand '{subcommand}'. Valid: get, set, list, reset",
                error="INVALID_SUBCOMMAND",
            )

    async def _get_config(self, key: str) -> CommandResult:
        """Get config value from settings."""
        try:
            from mindflow_backend.infra.config.settings import get_settings
            
            settings = get_settings()
            
            # Get attribute from settings using dot notation (e.g., "database.url")
            value = settings
            for part in key.split("."):
                if hasattr(value, part):
                    value = getattr(value, part)
                elif isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return CommandResult(
                        success=False,
                        message=f"Config key not found: {key}",
                        error="CONFIG_KEY_NOT_FOUND",
                        data={"key": key},
                    )
            
            return CommandResult(
                success=True,
                message=f"{key} = {value}",
                data={"key": key, "value": value},
            )
            
        except Exception as exc:
            return CommandResult(
                success=False,
                message=f"Failed to get config {key}: {exc}",
                error="CONFIG_ERROR",
                data={"key": key, "error": str(exc)},
            )

    async def _set_config(self, key: str, value: str) -> CommandResult:
        """Set runtime config value (in-memory only, not persisted)."""
        try:
            from mindflow_backend.infra.config.settings import get_settings
            
            settings = get_settings()
            
            # Parse value to appropriate type
            parsed_value = self._parse_config_value(value)
            
            # Try to set the attribute
            parts = key.split(".")
            target = settings
            
            # Navigate to parent object
            for part in parts[:-1]:
                if hasattr(target, part):
                    target = getattr(target, part)
                else:
                    return CommandResult(
                        success=False,
                        message=f"Config key not found: {key}",
                        error="CONFIG_KEY_NOT_FOUND",
                        data={"key": key},
                    )
            
            # Set the final attribute
            final_key = parts[-1]
            if hasattr(target, final_key):
                setattr(target, final_key, parsed_value)
                
                return CommandResult(
                    success=True,
                    message=f"Config {key} set to {parsed_value}",
                    data={"key": key, "value": parsed_value},
                )
            else:
                return CommandResult(
                    success=False,
                    message=f"Config key not found: {key}",
                    error="CONFIG_KEY_NOT_FOUND",
                    data={"key": key},
                )
            
        except Exception as exc:
            return CommandResult(
                success=False,
                message=f"Failed to set config {key}: {exc}",
                error="CONFIG_ERROR",
                data={"key": key, "value": value, "error": str(exc)},
            )

    def _parse_config_value(self, value: str) -> Any:
        """Parse config value to appropriate type."""
        # Try bool
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False
        
        # Try int
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value

    async def _list_config(self) -> CommandResult:
        """List all config keys from settings."""
        try:
            from mindflow_backend.infra.config.settings import get_settings
            
            settings = get_settings()
            
            # Build list of all config keys
            keys = []
            
            # Core settings
            for attr in dir(settings):
                if not attr.startswith("_") and not callable(getattr(settings, attr)):
                    keys.append(attr)
            
            # Nested configs
            nested_configs = ["database", "cache", "monitoring", "security", "orchestration_fallback"]
            for config_name in nested_configs:
                if hasattr(settings, config_name):
                    config = getattr(settings, config_name)
                    for attr in dir(config):
                        if not attr.startswith("_") and not callable(getattr(config, attr)):
                            keys.append(f"{config_name}.{attr}")
            
            return CommandResult(
                success=True,
                message=f"Configuration keys ({len(keys)} total):",
                data={"keys": keys, "count": len(keys)},
            )
            
        except Exception as exc:
            return CommandResult(
                success=True,
                message="Configuration keys:\n  (Error loading config)",
                data={"keys": [], "error": str(exc)},
            )

    async def _reset_config(self, key: str) -> CommandResult:
        """Reset config to default (reload from environment)."""
        try:
            from mindflow_backend.infra.config.settings import get_settings, Settings
            
            # Get default value from fresh Settings instance
            fresh_settings = Settings()
            
            # Get the default value
            parts = key.split(".")
            default_value = fresh_settings
            
            for part in parts:
                if hasattr(default_value, part):
                    default_value = getattr(default_value, part)
                else:
                    return CommandResult(
                        success=False,
                        message=f"Config key not found: {key}",
                        error="CONFIG_KEY_NOT_FOUND",
                        data={"key": key},
                    )
            
            # Set it on current settings
            settings = get_settings()
            target = settings
            
            for part in parts[:-1]:
                target = getattr(target, part)
            
            setattr(target, parts[-1], default_value)
            
            return CommandResult(
                success=True,
                message=f"Config {key} reset to default: {default_value}",
                data={"key": key, "default_value": default_value},
            )
            
        except Exception as exc:
            return CommandResult(
                success=False,
                message=f"Failed to reset config {key}: {exc}",
                error="CONFIG_ERROR",
                data={"key": key, "error": str(exc)},
            )
