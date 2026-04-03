"""Markdown skill loader for discovering and loading skills from files."""

import os
from pathlib import Path
from typing import List, Optional
import structlog

from mindflow_backend.skills.base.markdown_skill import MarkdownSkill
from mindflow_backend.skills.utils.markdown_parser import MarkdownSkillParser

logger = structlog.get_logger(__name__)


class MarkdownSkillLoader:
    """Loader for discovering and instantiating skills from Markdown files."""

    def __init__(self, search_paths: List[str | Path]):
        self._search_paths = [Path(p) for p in search_paths]

    def discover_skills(self) -> List[MarkdownSkill]:
        """
        Discover and load skills from the configured search paths.
        
        Returns:
            A list of instantiated MarkdownSkill objects.
        """
        skills: List[MarkdownSkill] = []
        
        for base_path in self._search_paths:
            if not base_path.exists():
                logger.debug("Skill path does not exist, skipping", path=str(base_path))
                continue
                
            logger.info("Scanning directory for skills", path=str(base_path))
            
            # Look for sub-directories containing SKILL.md
            try:
                for entry in os.scandir(base_path):
                    if entry.is_dir():
                        skill_dir = Path(entry.path)
                        skill_file = skill_dir / "SKILL.md"
                        
                        if skill_file.exists():
                            try:
                                logger.info("Loading skill", file=str(skill_file))
                                skill = self.load_skill(skill_file)
                                skills.append(skill)
                            except Exception as e:
                                logger.error("Failed to load skill", file=str(skill_file), error=str(e))
            except Exception as e:
                logger.error("Error scanning skill directory", path=str(base_path), error=str(e))
                
        return skills

    @staticmethod
    def load_skill(file_path: str | Path) -> MarkdownSkill:
        """
        Load a single skill from a Markdown file.
        
        Args:
            file_path: Path to the SKILL.md file.
            
        Returns:
            A MarkdownSkill instance.
        """
        path = Path(file_path)
        config, content = MarkdownSkillParser.parse_file(path)
        return MarkdownSkill(
            config=config, 
            markdown_content=content, 
            base_dir=path.parent
        )

    @staticmethod
    def get_default_paths() -> List[Path]:
        """Get the default skill search paths (global and project)."""
        paths = []
        
        # 1. Global path (~/.mindflow/skills/)
        global_path = Path.home() / ".mindflow" / "skills"
        if global_path.exists():
            paths.append(global_path)
            
        # 2. Project path (.mindflow/skills/)
        # We assume the project root is the current working directory or can be resolved
        project_path = Path.cwd() / ".mindflow" / "skills"
        if project_path.exists():
            paths.append(project_path)
            
        return paths
