"""Dynamic skill manager for conditional activation based on context."""

from pathlib import Path
from typing import List, Set, Any, TYPE_CHECKING
import pathspec
import structlog

from mindflow_backend.skills.base.markdown_skill import MarkdownSkill

if TYPE_CHECKING:
    from mindflow_backend.skills.registry.skill_registry import SkillRegistry

logger = structlog.get_logger(__name__)


class DynamicSkillManager:
    """Manager for activating conditional skills based on file paths."""

    def __init__(self, registry: 'SkillRegistry'):
        self._registry = registry
        self._active_dynamic_skills: Set[str] = set()

    async def update_active_skills(self, file_paths: List[str | Path], cwd: str | Path | None = None) -> List[str]:
        """
        Update the set of active dynamic skills based on the provided file paths.
        
        Args:
            file_paths: List of file paths to check against skill patterns.
            cwd: Current working directory for relative path matching.
            
        Returns:
            List of names of newly activated skills.
        """
        if not cwd:
            cwd = Path.cwd()
        else:
            cwd = Path(cwd)

        # Get all registered skills
        all_skills = await self._registry.list_skills(limit=1000)
        newly_activated = []

        for entry in all_skills:
            skill_id = entry.id
            skill = self._registry.get_skill_instance(skill_id)
            
            if not isinstance(skill, MarkdownSkill):
                continue
                
            config = skill.get_configuration()
            if not config.paths:
                continue
                
            skill_name = entry.registration.skill_name
            
            # Use pathspec for gitignore-style matching
            spec = pathspec.PathSpec.from_lines('gitwildmatch', config.paths)
            
            matches = False
            for fp in file_paths:
                rel_path = str(fp)
                if Path(fp).is_absolute():
                    try:
                        rel_path = str(Path(fp).relative_to(cwd))
                    except ValueError:
                        # Path is outside cwd, skip or handle accordingly
                        continue
                
                if spec.match_file(rel_path):
                    matches = True
                    break
            
            if matches:
                if skill_name not in self._active_dynamic_skills:
                    self._active_dynamic_skills.add(skill_name)
                    newly_activated.append(skill_name)
                    logger.info("Activated dynamic skill", skill=skill_name)
            else:
                if skill_name in self._active_dynamic_skills:
                    self._active_dynamic_skills.remove(skill_name)
                    logger.info("Deactivated dynamic skill", skill=skill_name)

        return newly_activated

    def get_active_dynamic_skills(self) -> List[MarkdownSkill]:
        """Get instances of all currently active dynamic skills."""
        active_skills = []
        for name in self._active_dynamic_skills:
            skill = self._registry.get_skill_instance_by_name(name)
            if skill:
                active_skills.append(skill)
        return active_skills
