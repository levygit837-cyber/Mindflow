"""MindFlow Skills System.

A comprehensive skill management system for agents with support for:
- Core skills (analysis, coding, research)
- Specialized skills (security, architecture, testing, documentation)
- Skill registry and discovery
- Execution management and monitoring
- Lifecycle management
"""

from .base.skill import BaseSkill
from .base.executor import SkillExecutor
from .core.analysis import AnalysisSkill
from .core.coding import CodingSkill
from .core.research import ResearchSkill
from .registry.skill_registry import SkillRegistry
from .utils.validation import SkillValidator

__version__ = "1.0.0"
__author__ = "MindFlow Team"

__all__ = [
    # Base components
    "BaseSkill",
    "SkillExecutor",
    
    # Core skills
    "AnalysisSkill",
    "CodingSkill", 
    "ResearchSkill",
    
    # Registry
    "SkillRegistry",
    
    # Utilities
    "SkillValidator",
    
    # System components
    "SkillSystem",
]

class SkillSystem:
    """Main entry point for the Skills system."""
    
    def __init__(self):
        self._registry = None
        self._executor = None
        self._validator = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the skill system."""
        if self._initialized:
            return
        
        self._registry = SkillRegistry()
        self._executor = SkillExecutor(self._registry)
        self._validator = SkillValidator()
        
        await self._registry.initialize()
        await self._executor.initialize()
        
        self._initialized = True
    
    async def shutdown(self):
        """Shutdown the skill system."""
        if not self._initialized:
            return
        
        await self._executor.shutdown()
        await self._registry.shutdown()
        
        self._initialized = False
    
    @property
    def registry(self):
        """Get skill registry."""
        if not self._initialized:
            raise RuntimeError("Skill system not initialized")
        return self._registry
    
    @property
    def executor(self):
        """Get skill executor."""
        if not self._initialized:
            raise RuntimeError("Skill system not initialized")
        return self._executor
    
    @property
    def validator(self):
        """Get skill validator."""
        if not self._initialized:
            raise RuntimeError("Skill system not initialized")
        return self._validator

# Global instance
_skill_system = SkillSystem()

def get_skill_system() -> SkillSystem:
    """Get the global skill system instance."""
    return _skill_system
