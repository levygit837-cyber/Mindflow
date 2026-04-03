"""Registry for managing and discovering skills."""

from typing import Dict, List, Optional, Any
from pathlib import Path
import uuid
from datetime import datetime
import structlog

from mindflow_backend.interfaces.skills.registry import SkillRegistryInterface
from mindflow_backend.schemas.skills.base import (
    SkillCategory,
    SkillConfiguration,
    SkillMetadata,
    SkillStatus,
    SkillType,
)
from mindflow_backend.schemas.skills.registry import (
    SkillRegistration,
    SkillRegistryEntry,
    SkillFilter,
)
from mindflow_backend.skills.base.skill import BaseSkill
from mindflow_backend.skills.utils.markdown_loader import MarkdownSkillLoader

logger = structlog.get_logger(__name__)


class SkillRegistry(SkillRegistryInterface):
    """Implementation of the skill registry."""

    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}
        self._entries: Dict[str, SkillRegistryEntry] = {}
        self._name_to_id: Dict[str, str] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the registry and load skills."""
        if self._initialized:
            return

        logger.info("Initializing SkillRegistry")
        
        # Load Markdown skills from default paths
        search_paths = MarkdownSkillLoader.get_default_paths()
        loader = MarkdownSkillLoader(search_paths)
        markdown_skills = loader.discover_skills()
        
        for skill in markdown_skills:
            await self.register_skill_instance(skill)
            
        self._initialized = True

    async def shutdown(self) -> None:
        """Shutdown the registry and cleanup skills."""
        for skill in self._skills.values():
            await skill.cleanup()
        self._skills.clear()
        self._entries.clear()
        self._name_to_id.clear()
        self._initialized = False

    async def register_skill_instance(self, skill: BaseSkill) -> str:
        """Register an existing skill instance."""
        skill_id = skill.skill_id
        metadata = skill.get_metadata()
        
        # Check if already registered by name
        if metadata.name in self._name_to_id:
            old_id = self._name_to_id[metadata.name]
            logger.warn("Skill with same name already registered, overwriting", name=metadata.name, old_id=old_id, new_id=skill_id)
            await self.unregister_skill(old_id)
            
        registration = SkillRegistration(
            skill_name=metadata.name,
            skill_type=skill.skill_type,
            category=skill.category,
            metadata=metadata,
            implementation_path=str(getattr(skill, "base_dir", "virtual")) if hasattr(skill, "base_dir") else "internal",
            configuration_schema=skill.get_configuration_schema(),
            dependencies=[]
        )
        
        entry = SkillRegistryEntry(
            id=skill_id,
            registration=registration,
            registered_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        self._skills[skill_id] = skill
        self._entries[skill_id] = entry
        self._name_to_id[metadata.name] = skill_id
        
        # Initialize the skill
        await skill.initialize()
        
        return skill_id

    async def register_skill(self, registration: SkillRegistration) -> str:
        """Register a new skill from registration data."""
        # For programmatic registration, we might need a factory
        # For now, this is a placeholder for dynamic registration
        skill_id = str(uuid.uuid4())
        # ... logic to instantiate skill based on type ...
        return skill_id

    async def unregister_skill(self, skill_id: str) -> bool:
        """Unregister a skill."""
        if skill_id not in self._skills:
            return False
            
        skill = self._skills[skill_id]
        await skill.cleanup()
        
        name = skill.get_name()
        del self._skills[skill_id]
        del self._entries[skill_id]
        if name in self._name_to_id:
            del self._name_to_id[name]
            
        return True

    async def get_skill(self, skill_id: str) -> SkillRegistryEntry | None:
        """Get skill entry by ID."""
        return self._entries.get(skill_id)

    def get_skill_instance(self, skill_id: str) -> BaseSkill | None:
        """Get skill instance by ID."""
        return self._skills.get(skill_id)

    async def get_skill_by_name(self, skill_name: str) -> SkillRegistryEntry | None:
        """Get skill entry by name."""
        skill_id = self._name_to_id.get(skill_name)
        if skill_id:
            return self._entries.get(skill_id)
        return None

    def get_skill_instance_by_name(self, skill_name: str) -> BaseSkill | None:
        """Get skill instance by name."""
        skill_id = self._name_to_id.get(skill_name)
        if skill_id:
            return self._skills.get(skill_id)
        return None

    async def list_skills(
        self, 
        filter_params: SkillFilter | None = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[SkillRegistryEntry]:
        """List registered skills."""
        entries = list(self._entries.values())
        
        if filter_params:
            if filter_params.query:
                query = filter_params.query.lower()
                entries = [e for e in entries if query in e.registration.name.lower() or query in e.registration.description.lower()]
            
            if filter_params.skill_types:
                entries = [e for e in entries if e.registration.skill_type in filter_params.skill_types]
                
            if filter_params.categories:
                entries = [e for e in entries if e.registration.category in filter_params.categories]
                
            if filter_params.status:
                # SkillRegistryEntry doesn't have status, but we can filter by the skill's current status
                entries = [e for e in entries if self._skills[e.id].get_status() == filter_params.status]

        return entries[offset : offset + limit]

    async def update_skill(
        self, 
        skill_id: str, 
        registration: SkillRegistration
    ) -> bool:
        """Update skill registration."""
        if skill_id not in self._entries:
            return False
            
        entry = self._entries[skill_id]
        entry.registration = registration
        entry.last_updated = datetime.now()
        
        # Update instance configuration if needed
        skill = self._skills.get(skill_id)
        if skill:
            skill.update_configuration(registration.configuration)
            
        return True

    async def get_skill_count(self, filter_params: SkillFilter | None = None) -> int:
        """Get total count of registered skills."""
        skills = await self.list_skills(filter_params, limit=10000)
        return len(skills)
