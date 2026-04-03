"""Markdown skill implementation."""

from typing import Any
from pathlib import Path

from mindflow_backend.schemas.skills.base import (
    SkillCategory,
    SkillInput,
    SkillMetadata,
    SkillOutput,
    SkillType,
)
from mindflow_backend.schemas.skills.markdown import MarkdownSkillConfig
from mindflow_backend.skills.base.skill import BaseSkill
from mindflow_backend.skills.utils.markdown_parser import MarkdownSkillParser


class MarkdownSkill(BaseSkill):
    """A skill loaded from a Markdown file."""

    def __init__(
        self,
        config: MarkdownSkillConfig,
        markdown_content: str,
        base_dir: str | Path | None = None
    ):
        metadata = SkillMetadata(
            name=config.display_name or "Markdown Skill",
            description=config.description,
            version=config.version or "1.0.0"
        )
        
        super().__init__(
            skill_type=SkillType.CUSTOM,
            category=SkillCategory.DOMAIN_SPECIFIC,
            metadata=metadata,
            configuration=config
        )
        
        self._markdown_content = markdown_content
        self._base_dir = Path(base_dir) if base_dir else None

    @property
    def markdown_content(self) -> str:
        """Get the raw markdown content."""
        return self._markdown_content

    @property
    def base_dir(self) -> Path | None:
        """Get the skill's base directory."""
        return self._base_dir

    async def _execute_internal(self, input_data: SkillInput) -> SkillOutput:
        """
        Execute the markdown skill.
        
        For markdown skills, 'execution' means substituting arguments 
        and returning the final prompt content.
        """
        # Substitute arguments in markdown content
        processed_content = MarkdownSkillParser.substitute_arguments(
            self._markdown_content, 
            input_data.data or {}
        )
        
        # Inject context variables
        if self._base_dir:
            processed_content = processed_content.replace(
                "${MINDFLOW_SKILL_DIR}", 
                str(self._base_dir.absolute())
            )
            
        # In a real scenario, we might want to substitute session ID etc.
        # For now, we return the processed content in the output data.
        
        return SkillOutput(
            success=True,
            data={"prompt": processed_content},
            metadata={"skill_name": self.get_name()}
        )

    def _get_capabilities_internal(self) -> list[str]:
        """Get skill capabilities (allowed tools)."""
        return self.get_configuration().allowed_tools

    async def _initialize_internal(self) -> None:
        """Initialize the skill."""
        pass

    async def _cleanup_internal(self) -> None:
        """Cleanup skill resources."""
        pass

    async def _health_check_internal(self) -> bool:
        """Health check for markdown skill."""
        return True

    def _get_requirements_internal(self) -> dict[str, Any]:
        """Requirements for markdown skill."""
        return {
            "permissions": [],
            "memory": "16MB",
            "cpu": "0.1",
            "dependencies": []
        }
