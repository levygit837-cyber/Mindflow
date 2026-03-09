"""Base interfaces for Skills system."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel

from mindflow_backend.interfaces.core import BaseComponentInterface
from mindflow_backend.schemas.skills.base import (
    SkillInput,
    SkillOutput,
    SkillConfiguration,
    SkillMetadata,
    SkillStatus
)


class SkillInterface(BaseComponentInterface):
    """Base interface for all skills."""
    
    @abstractmethod
    async def execute(self, input_data: SkillInput) -> SkillOutput:
        """Execute the skill with given input.
        
        Args:
            input_data: Input data for skill execution
            
        Returns:
            SkillOutput: Result of skill execution
            
        Raises:
            SkillExecutionError: If execution fails
        """
        pass
    
    @abstractmethod
    def get_metadata(self) -> SkillMetadata:
        """Get skill metadata.
        
        Returns:
            SkillMetadata: Skill metadata information
        """
        pass
    
    @abstractmethod
    def get_configuration(self) -> SkillConfiguration:
        """Get current skill configuration.
        
        Returns:
            SkillConfiguration: Current configuration
        """
        pass
    
    @abstractmethod
    def update_configuration(self, configuration: SkillConfiguration) -> None:
        """Update skill configuration.
        
        Args:
            configuration: New configuration to apply
        """
        pass
    
    @abstractmethod
    def validate_input(self, input_data: SkillInput) -> bool:
        """Validate input data for this skill.
        
        Args:
            input_data: Input data to validate
            
        Returns:
            bool: True if input is valid
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Get list of skill capabilities.
        
        Returns:
            List[str]: List of capability names
        """
        pass


class SkillLifecycleInterface(ABC):
    """Interface for skill lifecycle management."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the skill.
        
        Raises:
            SkillInitializationError: If initialization fails
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup skill resources.
        """
        pass
    
    @abstractmethod
    def get_status(self) -> SkillStatus:
        """Get current skill status.
        
        Returns:
            SkillStatus: Current status
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if skill is healthy.
        
        Returns:
            bool: True if skill is healthy
        """
        pass


class SkillConfigurableInterface(ABC):
    """Interface for configurable skills."""
    
    @abstractmethod
    def get_default_configuration(self) -> SkillConfiguration:
        """Get default configuration.
        
        Returns:
            SkillConfiguration: Default configuration
        """
        pass
    
    @abstractmethod
    def validate_configuration(self, configuration: SkillConfiguration) -> bool:
        """Validate configuration.
        
        Args:
            configuration: Configuration to validate
            
        Returns:
            bool: True if configuration is valid
        """
        pass
    
    @abstractmethod
    def get_configuration_schema(self) -> Dict[str, Any]:
        """Get JSON schema for configuration.
        
        Returns:
            Dict[str, Any]: JSON schema
        """
        pass


class SkillValidatableInterface(ABC):
    """Interface for skill validation."""
    
    @abstractmethod
    def validate_execution_context(self, context: Dict[str, Any]) -> bool:
        """Validate execution context.
        
        Args:
            context: Execution context to validate
            
        Returns:
            bool: True if context is valid
        """
        pass
    
    @abstractmethod
    def validate_permissions(self, permissions: List[str]) -> bool:
        """Validate required permissions.
        
        Args:
            permissions: List of required permissions
            
        Returns:
            bool: True if permissions are sufficient
        """
        pass
    
    @abstractmethod
    def get_requirements(self) -> Dict[str, Any]:
        """Get skill requirements.
        
        Returns:
            Dict[str, Any]: Requirements dictionary
        """
        pass


class ComposableSkillInterface(SkillInterface, SkillLifecycleInterface, SkillConfigurableInterface):
    """Composable interface combining basic skill interfaces."""
    
    @abstractmethod
    async def compose(self, skills: List['ComposableSkillInterface']) -> 'ComposableSkillInterface':
        """Compose multiple skills into a composite skill.
        
        Args:
            skills: List of skills to compose
            
        Returns:
            ComposableSkillInterface: Composite skill
        """
        pass
    
    @abstractmethod
    def get_composition_strategy(self) -> str:
        """Get composition strategy.
        
        Returns:
            str: Composition strategy name
        """
        pass
