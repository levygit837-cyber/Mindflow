"""Input normalization configuration schema."""

from __future__ import annotations

from pydantic import BaseModel


class NormalizationConfig(BaseModel):
    """Configuration for the input normalization layer."""

    enabled: bool = True
    max_input_tokens: int = 2000
    rewrite_threshold: int = 500
    rewrite_model: str = "flash"
    preserve_code_blocks: bool = True
