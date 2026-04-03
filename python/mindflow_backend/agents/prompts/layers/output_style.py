"""Output Style Layer — injects output style into the system prompt.

This layer integrates with the OutputStyleManager to inject style-specific
instructions into the prompt assembly pipeline.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mindflow_backend.agents.prompts.assembler import AssemblyContext
from mindflow_backend.agents.prompts.styles.manager import OutputStyleManager

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class OutputStyleLayer:
    """Layer that injects output style configuration into prompts.
    
    Priority: 90 (high priority, right after base personality layer)
    
    The output style modifies how the agent responds:
    - Tone (formal, casual, educational)
    - Verbosity (concise, explanatory, detailed)
    - Structure (bullet points, paragraphs, step-by-step)
    """
    
    name = "output_style"
    priority = 90  # High priority, right after base (100)
    
    def __init__(
        self,
        style_manager: OutputStyleManager | None = None,
        style_name: str | None = None,
    ) -> None:
        """Initialize the output style layer.
        
        Args:
            style_manager: Manager to load styles. Uses global instance if None.
            style_name: Specific style to use. If None, uses context or default.
        """
        self._style_manager = style_manager or OutputStyleManager()
        self._style_name = style_name
    
    async def render(self, context: AssemblyContext) -> str | None:
        """Render the output style section for injection into the prompt.
        
        Priority for style selection:
        1. Explicit style_name from constructor
        2. output_style from context.extra
        3. Default style from manager
        """
        # Determine which style to use
        style_name = self._style_name
        if style_name is None:
            style_name = context.extra.get("output_style")
        
        try:
            # Get the style prompt from manager
            style_prompt = await self._style_manager.get_style_prompt(style_name)
            
            if style_prompt:
                logger.debug(f"Using output style: {style_name or 'default'}")
                return style_prompt
            
            # No style found, return None (no injection)
            logger.debug("No output style configured, skipping injection")
            return None
            
        except Exception as e:
            logger.error(f"Failed to render output style: {e}", exc_info=True)
            # Fail gracefully - don't break prompt assembly
            return None
    
    def with_style(self, style_name: str) -> "OutputStyleLayer":
        """Create a new layer instance with a specific style.
        
        Useful for creating style-specific agent configurations.
        
        Args:
            style_name: Name of the style to use
            
        Returns:
            New OutputStyleLayer instance with the specified style
        """
        return OutputStyleLayer(
            style_manager=self._style_manager,
            style_name=style_name,
        )