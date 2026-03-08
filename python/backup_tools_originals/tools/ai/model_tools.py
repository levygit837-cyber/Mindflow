"""AI tools for MindFlow agents.

Provides local model management, embedding generation,
and AI-powered text processing capabilities.
"""

from __future__ import annotations

import asyncio
import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import torch
    import transformers
    from sentence_transformers import SentenceTransformer
    AI_LIBRARIES_AVAILABLE = True
except ImportError:
    AI_LIBRARIES_AVAILABLE = False
    torch = None
    transformers = None
    SentenceTransformer = None

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.interfaces.tools.base import AsyncToolInterface
from mindflow_backend.schemas.tools.tool_config import create_tool_schema
from mindflow_backend.schemas.orchestration.orchestrator import AgentType

_logger = get_logger(__name__)


class LocalModelTool(AsyncToolInterface):
    """Local model manager with multiple model support."""
    
    def __init__(self, backend: Optional[Any] = None):
        """Initialize the local model manager.
        
        Args:
            backend: Optional backend for compatibility
        """
        super().__init__()
        self.backend = backend
        self.name = "local_model_manager"
        self.description = "Local model management and execution"
        self._loaded_models = {}
        self._model_configs = {}
        self._system_info = {}
        
        self._schema = create_tool_schema(
            name=self.name,
            description=self.description,
            category="ai",
            parameters=[
                {
                    "name": "action",
                    "type": "string",
                    "description": "Action to perform (load, unload, list, generate, info)",
                    "required": True
                },
                {
                    "name": "model_name",
                    "type": "string",
                    "description": "Model name or path",
                    "required": False
                },
                {
                    "name": "model_type",
                    "type": "string",
                    "description": "Model type (llm, embedding, classifier)",
                    "required": False,
                    "default": "llm"
                },
                {
                    "name": "prompt",
                    "type": "string",
                    "description": "Text prompt for generation",
                    "required": False
                },
                {
                    "name": "max_tokens",
                    "type": "integer",
                    "description": "Maximum tokens to generate",
                    "required": False,
                    "default": 100
                },
                {
                    "name": "temperature",
                    "type": "float",
                    "description": "Generation temperature",
                    "required": False,
                    "default": 0.7
                }
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
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute model operation.
        
        Args:
            action: Action to perform
            model_name: Model name or path
            model_type: Model type
            prompt: Text prompt for generation
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature
            
        Returns:
            Dictionary with operation result
        """
        try:
            action = kwargs["action"]
            model_name = kwargs.get("model_name")
            model_type = kwargs.get("model_type", "llm")
            prompt = kwargs.get("prompt")
            max_tokens = kwargs.get("max_tokens", 100)
            temperature = kwargs.get("temperature", 0.7)
            
            if not AI_LIBRARIES_AVAILABLE:
                return self._format_result(
                    success=False,
                    error="AI libraries not available. Install with: pip install torch transformers sentence-transformers"
                )
            
            if action == "list":
                return await self._list_models()
            elif action == "info":
                return await self._get_system_info()
            elif action == "load":
                if not model_name:
                    return self._format_result(
                        success=False,
                        error="Model name required for load action"
                    )
                return await self._load_model(model_name, model_type)
            elif action == "unload":
                if not model_name:
                    return self._format_result(
                        success=False,
                        error="Model name required for unload action"
                    )
                return await self._unload_model(model_name)
            elif action == "generate":
                if not model_name or not prompt:
                    return self._format_result(
                        success=False,
                        error="Model name and prompt required for generate action"
                    )
                return await self._generate_text(model_name, prompt, max_tokens, temperature)
            else:
                return self._format_result(
                    success=False,
                    error=f"Unknown action: {action}"
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Model operation failed: {str(e)}"
            )
    
    async def _list_models(self) -> Dict[str, Any]:
        """List loaded models."""
        try:
            models = []
            for model_name, model_info in self._loaded_models.items():
                models.append({
                    "name": model_name,
                    "type": model_info["type"],
                    "loaded_at": model_info["loaded_at"],
                    "memory_usage": model_info.get("memory_usage", "unknown")
                })
            
            return self._format_result(
                success=True,
                result={
                    "action": "list",
                    "models": models,
                    "count": len(models)
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to list models: {str(e)}"
            )
    
    async def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for AI models."""
        try:
            if not self._system_info:
                self._system_info = {
                    "torch_available": torch is not None,
                    "transformers_available": transformers is not None,
                    "sentence_transformers_available": SentenceTransformer is not None,
                    "cuda_available": torch.cuda.is_available() if torch else False,
                    "device_count": torch.cuda.device_count() if torch and torch.cuda.is_available() else 0,
                    "cpu_count": os.cpu_count()
                }
            
            return self._format_result(
                success=True,
                result={
                    "action": "info",
                    "system_info": self._system_info
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to get system info: {str(e)}"
            )
    
    async def _load_model(self, model_name: str, model_type: str) -> Dict[str, Any]:
        """Load a model."""
        try:
            if model_name in self._loaded_models:
                return self._format_result(
                    success=False,
                    error=f"Model {model_name} already loaded"
                )
            
            # Simulate model loading (actual implementation would load real models)
            self._loaded_models[model_name] = {
                "type": model_type,
                "loaded_at": asyncio.get_event_loop().time(),
                "memory_usage": "simulated"
            }
            
            return self._format_result(
                success=True,
                result={
                    "action": "load",
                    "model_name": model_name,
                    "model_type": model_type,
                    "status": "loaded"
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to load model: {str(e)}"
            )
    
    async def _unload_model(self, model_name: str) -> Dict[str, Any]:
        """Unload a model."""
        try:
            if model_name not in self._loaded_models:
                return self._format_result(
                    success=False,
                    error=f"Model {model_name} not loaded"
                )
            
            del self._loaded_models[model_name]
            
            return self._format_result(
                success=True,
                result={
                    "action": "unload",
                    "model_name": model_name,
                    "status": "unloaded"
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to unload model: {str(e)}"
            )
    
    async def _generate_text(self, model_name: str, prompt: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Generate text using a model."""
        try:
            if model_name not in self._loaded_models:
                return self._format_result(
                    success=False,
                    error=f"Model {model_name} not loaded"
                )
            
            # Simulate text generation (actual implementation would use real model)
            generated_text = f"Generated response for: {prompt[:50]}..."
            
            return self._format_result(
                success=True,
                result={
                    "action": "generate",
                    "model_name": model_name,
                    "prompt": prompt,
                    "generated_text": generated_text,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to generate text: {str(e)}"
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema."""
        return self._schema.dict()


class EmbeddingTool(AsyncToolInterface):
    """Embedding generation tool."""
    
    def __init__(self, backend: Optional[Any] = None):
        """Initialize the embedding tool.
        
        Args:
            backend: Optional backend for compatibility
        """
        super().__init__()
        self.backend = backend
        self.name = "embedding_generator"
        self.description = "Generate text embeddings using various models"
        self._loaded_models = {}
        
        self._schema = create_tool_schema(
            name=self.name,
            description=self.description,
            category="ai",
            parameters=[
                {
                    "name": "action",
                    "type": "string",
                    "description": "Action to perform (generate, list_models, load_model)",
                    "required": True
                },
                {
                    "name": "text",
                    "type": "string",
                    "description": "Text to embed",
                    "required": False
                },
                {
                    "name": "model_name",
                    "type": "string",
                    "description": "Embedding model name",
                    "required": False,
                    "default": "default"
                },
                {
                    "name": "texts",
                    "type": "array",
                    "description": "Multiple texts to embed",
                    "required": False
                }
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
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute embedding operation.
        
        Args:
            action: Action to perform
            text: Text to embed
            model_name: Embedding model name
            texts: Multiple texts to embed
            
        Returns:
            Dictionary with operation result
        """
        try:
            action = kwargs["action"]
            text = kwargs.get("text")
            model_name = kwargs.get("model_name", "default")
            texts = kwargs.get("texts", [])
            
            if not AI_LIBRARIES_AVAILABLE:
                return self._format_result(
                    success=False,
                    error="AI libraries not available. Install with: pip install sentence-transformers"
                )
            
            if action == "generate":
                if not text and not texts:
                    return self._format_result(
                        success=False,
                        error="Text or texts required for generate action"
                    )
                return await self._generate_embeddings(text, texts, model_name)
            elif action == "list_models":
                return await self._list_models()
            elif action == "load_model":
                if not model_name:
                    return self._format_result(
                        success=False,
                        error="Model name required for load_model action"
                    )
                return await self._load_model(model_name)
            else:
                return self._format_result(
                    success=False,
                    error=f"Unknown action: {action}"
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Embedding operation failed: {str(e)}"
            )
    
    async def _generate_embeddings(self, text: Optional[str], texts: List[str], model_name: str) -> Dict[str, Any]:
        """Generate embeddings."""
        try:
            # Combine single text and texts array
            all_texts = []
            if text:
                all_texts.append(text)
            all_texts.extend(texts)
            
            if not all_texts:
                return self._format_result(
                    success=False,
                    error="No texts provided for embedding"
                )
            
            # Simulate embedding generation (actual implementation would use real model)
            embeddings = []
            for txt in all_texts:
                # Simulate embedding vector (768 dimensions for typical models)
                embedding = [0.1] * 768
                embeddings.append(embedding)
            
            return self._format_result(
                success=True,
                result={
                    "action": "generate",
                    "embeddings": embeddings,
                    "model": model_name,
                    "count": len(embeddings),
                    "dimension": 768
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to generate embeddings: {str(e)}"
            )
    
    async def _list_models(self) -> Dict[str, Any]:
        """List available embedding models."""
        try:
            models = [
                {
                    "name": "default",
                    "description": "Default embedding model",
                    "dimension": 768,
                    "language": "multilingual"
                },
                {
                    "name": "fast",
                    "description": "Fast embedding model",
                    "dimension": 384,
                    "language": "english"
                }
            ]
            
            return self._format_result(
                success=True,
                result={
                    "action": "list_models",
                    "models": models
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to list models: {str(e)}"
            )
    
    async def _load_model(self, model_name: str) -> Dict[str, Any]:
        """Load an embedding model."""
        try:
            # Simulate model loading
            self._loaded_models[model_name] = {
                "loaded_at": asyncio.get_event_loop().time(),
                "status": "loaded"
            }
            
            return self._format_result(
                success=True,
                result={
                    "action": "load_model",
                    "model": model_name,
                    "status": "loaded"
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to load model: {str(e)}"
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema."""
        return self._schema.dict()
