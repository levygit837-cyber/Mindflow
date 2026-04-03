"""Output Style Manager — manages and loads output styles from multiple sources.

Inspired by Claude Code's output styles system:
- Built-in styles (lowest priority)
- Plugin styles
- User styles (~/.mindflow/output-styles/*.md)
- Project styles (.mindflow/output-styles/*.md)
- Policy styles (highest priority)
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional

import yaml

from mindflow_backend.schemas.prompts.output_style import (
    DEFAULT_OUTPUT_STYLE_DESCRIPTION,
    DEFAULT_OUTPUT_STYLE_NAME,
    OutputStyleConfig,
    OutputStyleSource,
    OutputStyles,
)

logger = logging.getLogger(__name__)


# Built-in style prompts
BUILTIN_STYLES: Dict[str, str] = {
    OutputStyles.DEFAULT.value: (
        "You complete tasks efficiently and provide concise responses. "
        "Focus on delivering working solutions without unnecessary explanations."
    ),
    OutputStyles.EXPLANATORY.value: (
        "When providing solutions, explain your reasoning step-by-step. "
        "Help the user understand WHY you made each decision. "
        "Include relevant context and alternatives considered."
    ),
    OutputStyles.LEARNING.value: (
        "Act as a patient teacher. Provide detailed explanations with examples. "
        "Break down complex concepts into digestible pieces. "
        "Use analogies and real-world examples to clarify ideas. "
        "Encourage questions and provide additional resources when helpful."
    ),
    OutputStyles.CONCISE.value: (
        "Be extremely concise. Provide only essential information. "
        "Use bullet points and short sentences. "
        "Avoid pleasantries and unnecessary context. "
        "Focus on actionable items and results."
    ),
}

BUILTIN_DESCRIPTIONS: Dict[str, str] = {
    OutputStyles.DEFAULT.value: DEFAULT_OUTPUT_STYLE_DESCRIPTION,
    OutputStyles.EXPLANATORY.value: "Explains decisions in detail with step-by-step reasoning",
    OutputStyles.LEARNING.value: "Educational mode with examples and detailed explanations",
    OutputStyles.CONCISE.value: "Minimal and direct responses with only essential information",
}


class OutputStyleManager:
    """Manages output styles from multiple sources with priority-based loading."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        user_root: Optional[Path] = None,
    ) -> None:
        self._project_root = project_root or Path.cwd()
        self._user_root = user_root or Path.home()
        self._cache: Dict[str, OutputStyleConfig] = {}
        self._initialized = False

    async def load_all_styles(self) -> Dict[str, OutputStyleConfig]:
        """Load all available styles from all sources.
        
        Priority (lowest to highest):
        1. Built-in styles
        2. Plugin styles
        3. User styles (~/.mindflow/output-styles/*.md)
        4. Project styles (.mindflow/output-styles/*.md)
        5. Policy styles
        """
        if self._initialized and self._cache:
            return self._cache

        styles: Dict[str, OutputStyleConfig] = {}

        # 1. Built-in styles (lowest priority)
        styles.update(self._load_builtin_styles())

        # 2. Plugin styles
        styles.update(await self._load_plugin_styles())

        # 3. User styles
        user_dir = self._user_root / ".mindflow" / "output-styles"
        styles.update(await self._load_styles_from_dir(
            user_dir,
            OutputStyleSource.USER_SETTINGS,
        ))

        # 4. Project styles
        project_dir = self._project_root / ".mindflow" / "output-styles"
        styles.update(await self._load_styles_from_dir(
            project_dir,
            OutputStyleSource.PROJECT_SETTINGS,
        ))

        # 5. Policy styles (highest priority)
        styles.update(await self._load_policy_styles())

        self._cache = styles
        self._initialized = True

        logger.info(f"Loaded {len(styles)} output styles")
        return styles

    async def get_style_config(
        self,
        style_name: Optional[str] = None,
    ) -> Optional[OutputStyleConfig]:
        """Get configuration for a specific style.
        
        Checks for forced plugin styles first, then falls back to
        the requested style or default.
        """
        all_styles = await self.load_all_styles()

        # Check for forced plugin styles
        forced_styles = [
            s for s in all_styles.values()
            if s.source == OutputStyleSource.PLUGIN and s.force_for_plugin
        ]

        if forced_styles:
            if len(forced_styles) > 1:
                logger.warning(
                    f"Multiple plugins have forced output styles: "
                    f"{[s.name for s in forced_styles]}. "
                    f"Using: {forced_styles[0].name}"
                )
            return forced_styles[0]

        # Use configured style or default
        target_style = style_name or DEFAULT_OUTPUT_STYLE_NAME
        return all_styles.get(target_style)

    async def get_style_prompt(
        self,
        style_name: Optional[str] = None,
    ) -> Optional[str]:
        """Get the prompt section for a style, formatted for injection."""
        style_config = await self.get_style_config(style_name)

        if not style_config:
            return None

        return (
            f"# Output Style: {style_config.name}\n\n"
            f"{style_config.prompt}"
        )

    def clear_cache(self) -> None:
        """Clear the styles cache to force reload."""
        self._cache.clear()
        self._initialized = False

    def _load_builtin_styles(self) -> Dict[str, OutputStyleConfig]:
        """Load built-in styles."""
        styles: Dict[str, OutputStyleConfig] = {}

        for name, prompt in BUILTIN_STYLES.items():
            styles[name] = OutputStyleConfig(
                name=name,
                description=BUILTIN_DESCRIPTIONS.get(name, "Built-in style"),
                prompt=prompt,
                source=OutputStyleSource.BUILT_IN,
                keep_coding_instructions=True,
                force_for_plugin=False,
            )

        return styles

    async def _load_plugin_styles(self) -> Dict[str, OutputStyleConfig]:
        """Load styles from plugins.
        
        TODO: Implement plugin style loading when plugin system is ready.
        """
        # Placeholder for future plugin integration
        return {}

    async def _load_policy_styles(self) -> Dict[str, OutputStyleConfig]:
        """Load styles from policy settings.
        
        TODO: Implement policy style loading when policy system is ready.
        """
        # Placeholder for future policy integration
        return {}

    async def _load_styles_from_dir(
        self,
        directory: Path,
        source: OutputStyleSource,
    ) -> Dict[str, OutputStyleConfig]:
        """Load styles from a directory of .md files."""
        styles: Dict[str, OutputStyleConfig] = {}

        if not directory.exists():
            return styles

        for md_file in directory.glob("*.md"):
            try:
                style_config = await self._parse_style_file(md_file, source)
                if style_config:
                    styles[style_config.name] = style_config
                    logger.debug(f"Loaded style '{style_config.name}' from {md_file}")
            except Exception as e:
                logger.error(f"Failed to load style from {md_file}: {e}")

        return styles

    async def _parse_style_file(
        self,
        file_path: Path,
        source: OutputStyleSource,
    ) -> Optional[OutputStyleConfig]:
        """Parse a .md style file with YAML frontmatter.
        
        Expected format:
        ---
        name: explanatory
        description: "Explains decisions in detail"
        keep_coding_instructions: true
        ---
        [prompt content]
        """
        content = file_path.read_text(encoding="utf-8")

        # Parse YAML frontmatter
        frontmatter: Dict[str, str] = {}
        prompt_content = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    prompt_content = parts[2].strip()
                except yaml.YAMLError as e:
                    logger.warning(f"Invalid YAML frontmatter in {file_path}: {e}")

        # Extract configuration from frontmatter
        name = frontmatter.get("name", file_path.stem)
        description = frontmatter.get(
            "description",
            f"Custom style from {file_path.name}"
        )
        keep_coding = frontmatter.get("keep_coding_instructions", True)

        if not prompt_content:
            logger.warning(f"Empty prompt content in {file_path}")
            return None

        return OutputStyleConfig(
            name=name,
            description=description,
            prompt=prompt_content,
            source=source,
            keep_coding_instructions=bool(keep_coding),
            force_for_plugin=False,
            file_path=file_path,
        )


# Global instance for convenience
_manager_instance: Optional[OutputStyleManager] = None


def get_output_style_manager() -> OutputStyleManager:
    """Get the global OutputStyleManager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = OutputStyleManager()
    return _manager_instance


async def get_output_style_prompt(
    style_name: Optional[str] = None,
) -> Optional[str]:
    """Convenience function to get an output style prompt."""
    manager = get_output_style_manager()
    return await manager.get_style_prompt(style_name)