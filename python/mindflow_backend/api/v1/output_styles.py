"""API endpoints for Output Styles management.

Provides REST API for listing, retrieving, and managing output styles.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from mindflow_backend.agents.prompts.styles.manager import OutputStyleManager

router = APIRouter(prefix="/output-styles", tags=["output-styles"])


class OutputStyleResponse(BaseModel):
    """Response model for an output style."""
    
    name: str
    description: str
    source: str
    keep_coding_instructions: bool
    prompt: Optional[str] = None


class OutputStyleListResponse(BaseModel):
    """Response model for listing output styles."""
    
    styles: list[OutputStyleResponse]
    total: int
    default_style: str


@router.get("/", response_model=OutputStyleListResponse)
async def list_output_styles(
    include_prompt: bool = Query(
        default=False,
        description="Include the full prompt content in the response",
    ),
) -> OutputStyleListResponse:
    """List all available output styles.
    
    Returns all styles from all sources (built-in, user, project, etc.)
    with their metadata. Optionally includes the full prompt content.
    """
    manager = OutputStyleManager()
    styles = await manager.load_all_styles()
    
    response_styles = []
    for style in styles.values():
        response_styles.append(
            OutputStyleResponse(
                name=style.name,
                description=style.description,
                source=style.source.value,
                keep_coding_instructions=style.keep_coding_instructions,
                prompt=style.prompt if include_prompt else None,
            )
        )
    
    return OutputStyleListResponse(
        styles=response_styles,
        total=len(response_styles),
        default_style="default",
    )


@router.get("/{style_name}", response_model=OutputStyleResponse)
async def get_output_style(
    style_name: str,
) -> OutputStyleResponse:
    """Get details of a specific output style.
    
    Returns the full configuration including the prompt content.
    """
    manager = OutputStyleManager()
    style = await manager.get_style_config(style_name)
    
    if not style:
        raise HTTPException(
            status_code=404,
            detail=f"Output style '{style_name}' not found",
        )
    
    return OutputStyleResponse(
        name=style.name,
        description=style.description,
        source=style.source.value,
        keep_coding_instructions=style.keep_coding_instructions,
        prompt=style.prompt,
    )


@router.get("/{style_name}/prompt")
async def get_style_prompt(
    style_name: str,
) -> dict[str, str]:
    """Get the formatted prompt section for a style.
    
    Returns the prompt formatted for injection into the system prompt.
    """
    manager = OutputStyleManager()
    prompt = await manager.get_style_prompt(style_name)
    
    if not prompt:
        raise HTTPException(
            status_code=404,
            detail=f"Output style '{style_name}' not found",
        )
    
    return {
        "style_name": style_name,
        "prompt_section": prompt,
    }