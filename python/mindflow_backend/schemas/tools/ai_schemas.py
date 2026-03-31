"""AI tool schemas for MindFlow agents.

Provides standardized schemas for AI-related tools including
model management, embedding generation, and text processing.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools.tool_config import ToolParameter, ToolSchema


class LocalModelParameters(BaseModel):
    """Parameters for local model operations."""
    
    action: str = Field(..., description="Action to perform (load, unload, list, generate, info)")
    model_name: str | None = Field(None, description="Model name or path")
    model_type: str = Field(default="llm", description="Model type (llm, embedding, classifier)")
    prompt: str | None = Field(None, description="Text prompt for generation")
    max_tokens: int = Field(default=100, description="Maximum tokens to generate")
    temperature: float = Field(default=0.7, description="Generation temperature")


class EmbeddingParameters(BaseModel):
    """Parameters for embedding generation."""
    
    action: str = Field(..., description="Action to perform (generate, list_models, load_model)")
    text: str | None = Field(None, description="Text to embed")
    model_name: str = Field(default="default", description="Embedding model name")
    texts: list[str] | None = Field(default_factory=list, description="Multiple texts to embed")


# Predefined schemas for AI tools
LOCAL_MODEL_SCHEMA = ToolSchema(
    name="local_model_manager",
    description="Local model management and execution",
    category="ai",
    parameters=[
        ToolParameter(
            name="action",
            type="string",
            description="Action to perform (load, unload, list, generate, info)",
            required=True
        ),
        ToolParameter(
            name="model_name",
            type="string",
            description="Model name or path",
            required=False
        ),
        ToolParameter(
            name="model_type",
            type="string",
            description="Model type (llm, embedding, classifier)",
            required=False,
            default="llm"
        ),
        ToolParameter(
            name="prompt",
            type="string",
            description="Text prompt for generation",
            required=False
        ),
        ToolParameter(
            name="max_tokens",
            type="integer",
            description="Maximum tokens to generate",
            required=False,
            default=100
        ),
        ToolParameter(
            name="temperature",
            type="float",
            description="Generation temperature",
            required=False,
            default=0.7
        )
    ],
    returns={
        "type": "object",
        "description": "Model operation result",
        "properties": {
            "action": {"type": "string", "description": "Action performed"},
            "result": {"type": "object", "description": "Operation result"}
        }
    }
)


EMBEDDING_SCHEMA = ToolSchema(
    name="embedding_generator",
    description="Generate text embeddings using various models",
    category="ai",
    parameters=[
        ToolParameter(
            name="action",
            type="string",
            description="Action to perform (generate, list_models, load_model)",
            required=True
        ),
        ToolParameter(
            name="text",
            type="string",
            description="Text to embed",
            required=False
        ),
        ToolParameter(
            name="model_name",
            type="string",
            description="Embedding model name",
            required=False,
            default="default"
        ),
        ToolParameter(
            name="texts",
            type="array",
            description="Multiple texts to embed",
            required=False
        )
    ],
    returns={
        "type": "object",
        "description": "Embedding operation result",
        "properties": {
            "action": {"type": "string", "description": "Action performed"},
            "embeddings": {"type": "array", "description": "Generated embeddings"},
            "model": {"type": "string", "description": "Model used"}
        }
    }
)


# Export schemas for easy import
__all__ = [
    "LocalModelParameters",
    "EmbeddingParameters",
    "LOCAL_MODEL_SCHEMA",
    "EMBEDDING_SCHEMA",
]
