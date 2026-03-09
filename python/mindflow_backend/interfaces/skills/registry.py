"""Registry interfaces for Skills system."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from mindflow_backend.interfaces.core import BaseComponentInterface
from mindflow_backend.schemas.skills.registry import (
    SkillRegistration,
    SkillDiscovery,
    SkillRegistryEntry,
    SkillQuery,
    SkillFilter,
    SkillRecommendation
)


class SkillRegistryInterface(BaseComponentInterface):
    """Interface for skill registry management."""
    
    @abstractmethod
    async def register_skill(self, registration: SkillRegistration) -> str:
        """Register a new skill.
        
        Args:
            registration: Skill registration data
            
        Returns:
            str: Unique skill identifier
            
        Raises:
            SkillRegistrationError: If registration fails
        """
        pass
    
    @abstractmethod
    async def unregister_skill(self, skill_id: str) -> bool:
        """Unregister a skill.
        
        Args:
            skill_id: ID of skill to unregister
            
        Returns:
            bool: True if unregistration was successful
        """
        pass
    
    @abstractmethod
    async def get_skill(self, skill_id: str) -> Optional[SkillRegistryEntry]:
        """Get skill by ID.
        
        Args:
            skill_id: ID of skill
            
        Returns:
            Optional[SkillRegistryEntry]: Skill entry if found
        """
        pass
    
    @abstractmethod
    async def get_skill_by_name(self, skill_name: str) -> Optional[SkillRegistryEntry]:
        """Get skill by name.
        
        Args:
            skill_name: Name of skill
            
        Returns:
            Optional[SkillRegistryEntry]: Skill entry if found
        """
        pass
    
    @abstractmethod
    async def list_skills(
        self, 
        filter_params: Optional[SkillFilter] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[SkillRegistryEntry]:
        """List registered skills.
        
        Args:
            filter_params: Optional filter parameters
            limit: Maximum results to return
            offset: Results offset
            
        Returns:
            List[SkillRegistryEntry]: List of skill entries
        """
        pass
    
    @abstractmethod
    async def update_skill(
        self, 
        skill_id: str, 
        registration: SkillRegistration
    ) -> bool:
        """Update skill registration.
        
        Args:
            skill_id: ID of skill to update
            registration: New registration data
            
        Returns:
            bool: True if update was successful
        """
        pass
    
    @abstractmethod
    async def get_skill_count(self, filter_params: Optional[SkillFilter] = None) -> int:
        """Get total count of registered skills.
        
        Args:
            filter_params: Optional filter parameters
            
        Returns:
            int: Total count of skills
        """
        pass


class SkillDiscoveryInterface(BaseComponentInterface):
    """Interface for skill discovery."""
    
    @abstractmethod
    async def discover_skills(self, discovery: SkillDiscovery) -> List[SkillRegistryEntry]:
        """Discover skills based on criteria.
        
        Args:
            discovery: Discovery criteria
            
        Returns:
            List[SkillRegistryEntry]: Matching skills
        """
        pass
    
    @abstractmethod
    async def search_skills(self, query: str) -> List[SkillRegistryEntry]:
        """Search skills by text query.
        
        Args:
            query: Search query
            
        Returns:
            List[SkillRegistryEntry]: Matching skills
        """
        pass
    
    @abstractmethod
    async def get_similar_skills(self, skill_id: str) -> List[SkillRegistryEntry]:
        """Get skills similar to given skill.
        
        Args:
            skill_id: ID of reference skill
            
        Returns:
            List[SkillRegistryEntry]: Similar skills
        """
        pass
    
    @abstractmethod
    async def get_popular_skills(self, limit: int = 10) -> List[SkillRegistryEntry]:
        """Get most popular skills.
        
        Args:
            limit: Maximum results to return
            
        Returns:
            List[SkillRegistryEntry]: Popular skills
        """
        pass
    
    @abstractmethod
    async def get_recent_skills(self, limit: int = 10) -> List[SkillRegistryEntry]:
        """Get recently registered skills.
        
        Args:
            limit: Maximum results to return
            
        Returns:
            List[SkillRegistryEntry]: Recent skills
        """
        pass


class SkillRecommendationInterface(BaseComponentInterface):
    """Interface for skill recommendation."""
    
    @abstractmethod
    async def recommend_skills(self, query: SkillQuery) -> List[SkillRecommendation]:
        """Recommend skills based on requirements.
        
        Args:
            query: Skill requirements and context
            
        Returns:
            List[SkillRecommendation]: Recommended skills with confidence scores
        """
        pass
    
    @abstractmethod
    async def get_skill_for_task(
        self, 
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[SkillRecommendation]:
        """Get best skill for a specific task.
        
        Args:
            task_description: Description of the task
            context: Optional execution context
            
        Returns:
            Optional[SkillRecommendation]: Best matching skill
        """
        pass
    
    @abstractmethod
    async def get_skill_combination(
        self, 
        requirements: Dict[str, Any]
    ) -> List[SkillRecommendation]:
        """Get combination of skills for complex requirements.
        
        Args:
            requirements: Complex requirements
            
        Returns:
            List[SkillRecommendation]: Recommended skill combination
        """
        pass
    
    @abstractmethod
    async def update_recommendation_model(
        self, 
        skill_id: str,
        feedback: Dict[str, Any]
    ) -> None:
        """Update recommendation model with feedback.
        
        Args:
            skill_id: ID of skill
            feedback: Feedback data
        """
        pass


class SkillValidationInterface(BaseComponentInterface):
    """Interface for skill validation."""
    
    @abstractmethod
    async def validate_skill_registration(
        self, 
        registration: SkillRegistration
    ) -> Dict[str, Any]:
        """Validate skill registration.
        
        Args:
            registration: Registration to validate
            
        Returns:
            Dict[str, Any]: Validation result with errors/warnings
        """
        pass
    
    @abstractmethod
    async def validate_skill_implementation(
        self, 
        skill_id: str
    ) -> Dict[str, Any]:
        """Validate skill implementation.
        
        Args:
            skill_id: ID of skill to validate
            
        Returns:
            Dict[str, Any]: Validation result
        """
        pass
    
    @abstractmethod
    async def test_skill_execution(
        self, 
        skill_id: str,
        test_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test skill execution.
        
        Args:
            skill_id: ID of skill to test
            test_input: Test input data
            
        Returns:
            Dict[str, Any]: Test results
        """
        pass
