"""Base skill implementation."""

import uuid
from abc import abstractmethod
from datetime import datetime
from typing import Any

from mindflow_backend.interfaces.skills.base import (
    SkillConfigurableInterface,
    SkillInterface,
    SkillLifecycleInterface,
    SkillValidatableInterface,
)
from mindflow_backend.schemas.skills.base import (
    SkillCategory,
    SkillConfiguration,
    SkillInput,
    SkillMetadata,
    SkillOutput,
    SkillStatus,
    SkillType,
)


class BaseSkill(SkillInterface, SkillLifecycleInterface, SkillConfigurableInterface, SkillValidatableInterface):
    """Base implementation for all skills."""
    
    def __init__(
        self,
        skill_type: SkillType,
        category: SkillCategory,
        metadata: SkillMetadata,
        configuration: SkillConfiguration | None = None
    ):
        self._skill_type = skill_type
        self._category = category
        self._metadata = metadata
        self._configuration = configuration or self.get_default_configuration()
        self._status = SkillStatus.INACTIVE
        self._id = str(uuid.uuid4())
        self._created_at = datetime.now()
        self._last_health_check = None
    
    @property
    def skill_id(self) -> str:
        """Get unique skill identifier."""
        return self._id
    
    @property
    def skill_type(self) -> SkillType:
        """Get skill type."""
        return self._skill_type
    
    @property
    def category(self) -> SkillCategory:
        """Get skill category."""
        return self._category
    
    async def execute(self, input_data: SkillInput) -> SkillOutput:
        """Execute the skill with given input."""
        if self._status != SkillStatus.ACTIVE:
            raise RuntimeError(f"Skill {self._metadata.name} is not active")
        
        if not self.validate_input(input_data):
            raise ValueError("Invalid input data")
        
        start_time = datetime.now()
        
        try:
            # Set status to running
            self._status = SkillStatus.ACTIVE  # Keep as active during execution
            
            # Call the actual implementation
            result = await self._execute_internal(input_data)
            
            # Calculate execution time
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            result.execution_time_ms = execution_time_ms
            
            return result
            
        except Exception as e:
            # Return error output
            return SkillOutput(
                success=False,
                error=str(e),
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
    
    @abstractmethod
    async def _execute_internal(self, input_data: SkillInput) -> SkillOutput:
        """Internal execution method to be implemented by subclasses."""
        pass
    
    def get_metadata(self) -> SkillMetadata:
        """Get skill metadata."""
        return self._metadata
    
    def get_configuration(self) -> SkillConfiguration:
        """Get current skill configuration."""
        return self._configuration
    
    def update_configuration(self, configuration: SkillConfiguration) -> None:
        """Update skill configuration."""
        if self.validate_configuration(configuration):
            self._configuration = configuration
            self._metadata.updated_at = datetime.now()
        else:
            raise ValueError("Invalid configuration")
    
    def validate_input(self, input_data: SkillInput) -> bool:
        """Validate input data for this skill."""
        # Basic validation
        if not input_data or not input_data.data:
            return False
        
        # Call subclass validation
        return self._validate_input_internal(input_data)
    
    def _validate_input_internal(self, input_data: SkillInput) -> bool:
        """Internal input validation to be implemented by subclasses."""
        return True
    
    def get_capabilities(self) -> list[str]:
        """Get list of skill capabilities."""
        return self._get_capabilities_internal()
    
    @abstractmethod
    def _get_capabilities_internal(self) -> list[str]:
        """Internal capabilities to be implemented by subclasses."""
        return []
    
    async def initialize(self) -> None:
        """Initialize the skill."""
        try:
            await self._initialize_internal()
            self._status = SkillStatus.ACTIVE
        except Exception as e:
            self._status = SkillStatus.FAILED
            raise RuntimeError(f"Failed to initialize skill {self._metadata.name}: {e}")
    
    @abstractmethod
    async def _initialize_internal(self) -> None:
        """Internal initialization to be implemented by subclasses."""
        pass
    
    async def cleanup(self) -> None:
        """Cleanup skill resources."""
        await self._cleanup_internal()
        self._status = SkillStatus.INACTIVE
    
    @abstractmethod
    async def _cleanup_internal(self) -> None:
        """Internal cleanup to be implemented by subclasses."""
        pass
    
    def get_status(self) -> SkillStatus:
        """Get current skill status."""
        return self._status
    
    async def health_check(self) -> bool:
        """Check if skill is healthy."""
        try:
            result = await self._health_check_internal()
            self._last_health_check = datetime.now()
            return result
        except Exception:
            return False
    
    @abstractmethod
    async def _health_check_internal(self) -> bool:
        """Internal health check to be implemented by subclasses."""
        return True
    
    def get_default_configuration(self) -> SkillConfiguration:
        """Get default configuration."""
        return SkillConfiguration()
    
    def validate_configuration(self, configuration: SkillConfiguration) -> bool:
        """Validate configuration."""
        # Basic validation
        if not configuration:
            return False
        
        if configuration.timeout_seconds <= 0:
            return False
        
        if configuration.max_retries < 0:
            return False
        
        # Call subclass validation
        return self._validate_configuration_internal(configuration)
    
    def _validate_configuration_internal(self, configuration: SkillConfiguration) -> bool:
        """Internal configuration validation to be implemented by subclasses."""
        return True
    
    def get_configuration_schema(self) -> dict[str, Any]:
        """Get JSON schema for configuration."""
        return {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean"},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "timeout_seconds": {"type": "integer", "minimum": 1},
                "max_retries": {"type": "integer", "minimum": 0},
                "custom_settings": {"type": "object"}
            }
        }
    
    def validate_execution_context(self, context: dict[str, Any]) -> bool:
        """Validate execution context."""
        # Basic context validation
        if not isinstance(context, dict):
            return False
        
        return self._validate_execution_context_internal(context)
    
    def _validate_execution_context_internal(self, context: dict[str, Any]) -> bool:
        """Internal context validation to be implemented by subclasses."""
        return True
    
    def validate_permissions(self, permissions: list[str]) -> bool:
        """Validate required permissions."""
        required_permissions = self.get_requirements().get("permissions", [])
        
        # Check if all required permissions are provided
        for required in required_permissions:
            if required not in permissions:
                return False
        
        return True
    
    def get_requirements(self) -> dict[str, Any]:
        """Get skill requirements."""
        return self._get_requirements_internal()
    
    @abstractmethod
    def _get_requirements_internal(self) -> dict[str, Any]:
        """Internal requirements to be implemented by subclasses."""
        return {
            "permissions": [],
            "memory": "128MB",
            "cpu": "0.5",
            "dependencies": []
        }
    
    def get_name(self) -> str:
        """Get skill name."""
        return self._metadata.name
    
    def get_version(self) -> str:
        """Get skill version."""
        return self._metadata.version
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self._metadata.name} v{self._metadata.version} ({self._skill_type.value})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"BaseSkill(id={self._id}, name={self._metadata.name}, type={self._skill_type.value})"
