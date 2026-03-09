"""Lifecycle management interfaces for Skills system."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

from mindflow_backend.interfaces.core import BaseComponentInterface
from mindflow_backend.schemas.skills.base import SkillStatus
from mindflow_backend.schemas.skills.execution import (
    ExecutionContext,
    ExecutionResult,
    PerformanceMetrics
)


class SkillManagerInterface(BaseComponentInterface):
    """Interface for skill lifecycle management."""
    
    @abstractmethod
    async def load_skill(self, skill_id: str) -> bool:
        """Load a skill into memory.
        
        Args:
            skill_id: ID of skill to load
            
        Returns:
            bool: True if skill was loaded successfully
        """
        pass
    
    @abstractmethod
    async def unload_skill(self, skill_id: str) -> bool:
        """Unload a skill from memory.
        
        Args:
            skill_id: ID of skill to unload
            
        Returns:
            bool: True if skill was unloaded successfully
        """
        pass
    
    @abstractmethod
    async def reload_skill(self, skill_id: str) -> bool:
        """Reload a skill.
        
        Args:
            skill_id: ID of skill to reload
            
        Returns:
            bool: True if skill was reloaded successfully
        """
        pass
    
    @abstractmethod
    async def enable_skill(self, skill_id: str) -> bool:
        """Enable a skill.
        
        Args:
            skill_id: ID of skill to enable
            
        Returns:
            bool: True if skill was enabled successfully
        """
        pass
    
    @abstractmethod
    async def disable_skill(self, skill_id: str) -> bool:
        """Disable a skill.
        
        Args:
            skill_id: ID of skill to disable
            
        Returns:
            bool: True if skill was disabled successfully
        """
        pass
    
    @abstractmethod
    async def get_skill_status(self, skill_id: str) -> SkillStatus:
        """Get current status of a skill.
        
        Args:
            skill_id: ID of skill
            
        Returns:
            SkillStatus: Current status
        """
        pass
    
    @abstractmethod
    async def list_loaded_skills(self) -> List[str]:
        """Get list of currently loaded skills.
        
        Returns:
            List[str]: List of skill IDs
        """
        pass
    
    @abstractmethod
    async def get_skill_health(self, skill_id: str) -> Dict[str, Any]:
        """Get health information for a skill.
        
        Args:
            skill_id: ID of skill
            
        Returns:
            Dict[str, Any]: Health information
        """
        pass


class SkillOrchestratorInterface(BaseComponentInterface):
    """Interface for skill orchestration."""
    
    @abstractmethod
    async def orchestrate_execution(
        self, 
        skills: List[str],
        execution_plan: Dict[str, Any]
    ) -> List[ExecutionResult]:
        """Orchestrate execution of multiple skills.
        
        Args:
            skills: List of skill IDs to execute
            execution_plan: Execution plan with dependencies
            
        Returns:
            List[ExecutionResult]: Results from all skill executions
        """
        pass
    
    @abstractmethod
    async def create_execution_plan(
        self, 
        objective: str,
        available_skills: List[str]
    ) -> Dict[str, Any]:
        """Create execution plan for objective.
        
        Args:
            objective: Objective to achieve
            available_skills: List of available skill IDs
            
        Returns:
            Dict[str, Any]: Execution plan
        """
        pass
    
    @abstractmethod
    async def optimize_execution_order(
        self, 
        skills: List[str],
        dependencies: Dict[str, List[str]]
    ) -> List[str]:
        """Optimize execution order based on dependencies.
        
        Args:
            skills: List of skill IDs
            dependencies: Skill dependencies
            
        Returns:
            List[str]: Optimized execution order
        """
        pass
    
    @abstractmethod
    async def handle_execution_failures(
        self, 
        failed_skill: str,
        context: ExecutionContext,
        error: str
    ) -> Optional[Dict[str, Any]]:
        """Handle execution failures.
        
        Args:
            failed_skill: ID of failed skill
            context: Execution context
            error: Error message
            
        Returns:
            Optional[Dict[str, Any]]: Recovery plan if available
        """
        pass


class SkillMonitoringInterface(BaseComponentInterface):
    """Interface for skill monitoring."""
    
    @abstractmethod
    async def start_monitoring(self, skill_id: str) -> bool:
        """Start monitoring a skill.
        
        Args:
            skill_id: ID of skill to monitor
            
        Returns:
            bool: True if monitoring started successfully
        """
        pass
    
    @abstractmethod
    async def stop_monitoring(self, skill_id: str) -> bool:
        """Stop monitoring a skill.
        
        Args:
            skill_id: ID of skill to stop monitoring
            
        Returns:
            bool: True if monitoring stopped successfully
        """
        pass
    
    @abstractmethod
    async def get_skill_metrics(
        self, 
        skill_id: str,
        time_range: Optional[Dict[str, datetime]] = None
    ) -> PerformanceMetrics:
        """Get performance metrics for a skill.
        
        Args:
            skill_id: ID of skill
            time_range: Optional time range for metrics
            
        Returns:
            PerformanceMetrics: Performance metrics
        """
        pass
    
    @abstractmethod
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get overall system metrics.
        
        Returns:
            Dict[str, Any]: System-wide metrics
        """
        pass
    
    @abstractmethod
    async def set_alert_thresholds(
        self, 
        skill_id: str,
        thresholds: Dict[str, Any]
    ) -> bool:
        """Set alert thresholds for a skill.
        
        Args:
            skill_id: ID of skill
            thresholds: Alert thresholds
            
        Returns:
            bool: True if thresholds were set successfully
        """
        pass
    
    @abstractmethod
    async def get_alerts(
        self, 
        skill_id: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get alerts for skills.
        
        Args:
            skill_id: Optional skill ID filter
            severity: Optional severity filter
            limit: Maximum results to return
            
        Returns:
            List[Dict[str, Any]]: List of alerts
        """
        pass


class SkillDependencyManagerInterface(BaseComponentInterface):
    """Interface for skill dependency management."""
    
    @abstractmethod
    async def resolve_dependencies(self, skill_id: str) -> List[str]:
        """Resolve dependencies for a skill.
        
        Args:
            skill_id: ID of skill
            
        Returns:
            List[str]: List of dependency skill IDs in order
        """
        pass
    
    @abstractmethod
    async def check_dependency_conflicts(self, skills: List[str]) -> Dict[str, Any]:
        """Check for dependency conflicts.
        
        Args:
            skills: List of skill IDs
            
        Returns:
            Dict[str, Any]: Conflict analysis results
        """
        pass
    
    @abstractmethod
    async def get_dependency_graph(self) -> Dict[str, List[str]]:
        """Get complete dependency graph.
        
        Returns:
            Dict[str, List[str]]: Dependency graph
        """
        pass
    
    @abstractmethod
    async def update_dependencies(
        self, 
        skill_id: str,
        dependencies: List[str]
    ) -> bool:
        """Update dependencies for a skill.
        
        Args:
            skill_id: ID of skill
            dependencies: New dependency list
            
        Returns:
            bool: True if update was successful
        """
        pass


class SkillVersionManagerInterface(BaseComponentInterface):
    """Interface for skill version management."""
    
    @abstractmethod
    async def create_skill_version(
        self, 
        skill_id: str,
        version: str,
        changes: List[str]
    ) -> bool:
        """Create a new version of a skill.
        
        Args:
            skill_id: ID of skill
            version: New version string
            changes: List of changes
            
        Returns:
            bool: True if version was created successfully
        """
        pass
    
    @abstractmethod
    async def get_skill_versions(self, skill_id: str) -> List[Dict[str, Any]]:
        """Get all versions of a skill.
        
        Args:
            skill_id: ID of skill
            
        Returns:
            List[Dict[str, Any]]: List of version information
        """
        pass
    
    @abstractmethod
    async def rollback_skill_version(
        self, 
        skill_id: str,
        target_version: str
    ) -> bool:
        """Rollback skill to previous version.
        
        Args:
            skill_id: ID of skill
            target_version: Target version to rollback to
            
        Returns:
            bool: True if rollback was successful
        """
        pass
    
    @abstractmethod
    async def compare_skill_versions(
        self, 
        skill_id: str,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """Compare two versions of a skill.
        
        Args:
            skill_id: ID of skill
            version1: First version
            version2: Second version
            
        Returns:
            Dict[str, Any]: Comparison results
        """
        pass
