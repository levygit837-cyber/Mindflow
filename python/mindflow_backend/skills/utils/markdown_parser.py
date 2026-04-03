"""Markdown parser for Skills."""

import frontmatter
from pathlib import Path
from typing import Any, Tuple
import re

from mindflow_backend.schemas.skills.markdown import MarkdownSkillConfig


class MarkdownSkillParser:
    """Parser for skills defined in Markdown files."""

    @staticmethod
    def parse_file(file_path: str | Path) -> Tuple[MarkdownSkillConfig, str]:
        """
        Parse a SKILL.md file and return configuration and content.
        
        Args:
            file_path: Path to the SKILL.md file.
            
        Returns:
            Tuple containing the parsed configuration and the markdown body.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Skill file not found: {file_path}")

        post = frontmatter.load(path)
        metadata = post.metadata
        content = post.content

        # Extract name from directory if not provided in frontmatter
        name = metadata.get("name") or path.parent.name
        
        # Extract description from content if not provided in frontmatter
        description = metadata.get("description")
        if not description:
            description = MarkdownSkillParser.extract_description(content)

        # Build configuration
        config_data = {
            "display_name": metadata.get("name"),
            "description": description,
            "when_to_use": metadata.get("when_to_use") or metadata.get("when-to-use"),
            "arguments": metadata.get("arguments") or [],
            "allowed_tools": metadata.get("allowed_tools") or metadata.get("allowed-tools") or [],
            "paths": metadata.get("paths") or [],
            "user_invocable": metadata.get("user_invocable", metadata.get("user-invocable", True)),
            "version": metadata.get("version", "1.0.0"),
            "model": metadata.get("model"),
            "disable_model_invocation": metadata.get("disable_model_invocation", metadata.get("disable-model-invocation", False)),
            "context": metadata.get("context"),
            "agent": metadata.get("agent"),
            "effort": metadata.get("effort")
        }

        # Handle string or list of arguments
        if isinstance(config_data["arguments"], str):
            config_data["arguments"] = [config_data["arguments"]]

        # Handle list of allowed tools
        if isinstance(config_data["allowed_tools"], str):
            config_data["allowed_tools"] = [config_data["allowed_tools"]]

        # Handle paths
        if isinstance(config_data["paths"], str):
            config_data["paths"] = [config_data["paths"]]

        config = MarkdownSkillConfig(**config_data)
        return config, content

    @staticmethod
    def extract_description(content: str) -> str:
        """Extract description from markdown content (usually the first paragraph)."""
        # Simple extraction: first non-header line that isn't empty
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                return line
        return "No description available"

    @staticmethod
    def substitute_arguments(content: str, arguments: dict[str, Any]) -> str:
        """
        Substitute {{arg}} or ${arg} placeholders in content.
        
        Args:
            content: Markdown content with placeholders.
            arguments: Dictionary of arguments to substitute.
            
        Returns:
            Processed content with substitutions.
        """
        for key, value in arguments.items():
            # Support both {{key}} and ${key} formats
            content = content.replace(f"{{{{{key}}}}}", str(value))
            content = content.replace(f"${{{key}}}", str(value))
        return content
