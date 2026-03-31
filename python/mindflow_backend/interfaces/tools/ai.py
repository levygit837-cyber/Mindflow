"""AI and model interfaces for MindFlow backend.

Provides interfaces for local model management,
AI operations, and intelligent tool selection.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from mindflow_backend.schemas.orchestration.orchestrator import AgentType


class ModelInterface(ABC):
    """Interface for local model management and execution."""
    
    @abstractmethod
    async def load_model(self, model_config: dict[str, Any]) -> bool:
        """Load a model with specified configuration.
        
        Args:
            model_config: Model configuration
            
        Returns:
            True if model loaded successfully
        """
        pass
    
    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """Generate text using the loaded model.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text and metadata
        """
        pass
    
    @abstractmethod
    async def get_model_info(self) -> dict[str, Any]:
        """Get information about the loaded model.
        
        Returns:
            Model information dictionary
        """
        pass
    
    @abstractmethod
    async def unload_model(self) -> bool:
        """Unload the current model.
        
        Returns:
            True if model unloaded successfully
        """
        pass


class LocalModelManager(ModelInterface):
    """Interface for managing local AI models."""
    
    @abstractmethod
    async def detect_available_models(self) -> list[dict[str, Any]]:
        """Detect available local models.
        
        Returns:
            List of available model information
        """
        pass
    
    @abstractmethod
    async def recommend_model_for_task(
        self,
        task: str,
        constraints: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Recommend model for specific task.
        
        Args:
            task: Task description
            constraints: Resource constraints
            
        Returns:
            Model recommendation
        """
        pass
    
    @abstractmethod
    async def optimize_model_config(
        self,
        model_name: str,
        system_info: dict[str, Any]
    ) -> dict[str, Any]:
        """Optimize model configuration for system.
        
        Args:
            model_name: Model name
            system_info: System information
            
        Returns:
            Optimized configuration
        """
        pass


class EmbeddingInterface(ABC):
    """Interface for text embedding generation."""
    
    @abstractmethod
    async def generate_embeddings(
        self,
        texts: list[str],
        model_name: str | None = None
    ) -> list[list[float]]:
        """Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed
            model_name: Optional model name
            
        Returns:
            List of embedding vectors
        """
        pass
    
    @abstractmethod
    async def get_embedding_info(self, model_name: str | None = None) -> dict[str, Any]:
        """Get embedding model information.
        
        Args:
            model_name: Optional model name
            
        Returns:
            Model information
        """
        pass


class ToolSelectorInterface(ABC):
    """Interface for intelligent tool selection."""
    
    @abstractmethod
    async def select_tools_for_task(
        self,
        task: str,
        agent_type: AgentType,
        available_tools: list[str],
        context: dict[str, Any] | None = None
    ) -> list[str]:
        """Select appropriate tools for a task.
        
        Args:
            task: Task description
            agent_type: Type of agent
            available_tools: List of available tool names
            context: Additional context
            
        Returns:
            List of selected tool names
        """
        pass
    
    @abstractmethod
    async def rank_tools_by_relevance(
        self,
        task: str,
        tools: list[str],
        agent_type: AgentType
    ) -> list[dict[str, Any]]:
        """Rank tools by relevance to task.
        
        Args:
            task: Task description
            tools: List of tool names
            agent_type: Type of agent
            
        Returns:
            List of ranked tools with scores
        """
        pass


class ModelOptimizerInterface(ABC):
    """Interface for model optimization and tuning."""
    
    @abstractmethod
    async def optimize_for_hardware(
        self,
        model_config: dict[str, Any],
        hardware_info: dict[str, Any]
    ) -> dict[str, Any]:
        """Optimize model configuration for hardware.
        
        Args:
            model_config: Model configuration
            hardware_info: Hardware information
            
        Returns:
            Optimized configuration
        """
        pass
    
    @abstractmethod
    async def benchmark_model(
        self,
        model_config: dict[str, Any],
        test_cases: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Benchmark model performance.
        
        Args:
            model_config: Model configuration
            test_cases: Test cases
            
        Returns:
            Benchmark results
        """
        pass


# Schema classes for AI interfaces
class ModelConfig(BaseModel):
    """Configuration for model loading and execution."""
    
    model_name: str
    model_path: str | None = None
    device: str = "auto"
    precision: str = "fp32"
    max_memory_gb: float | None = None
    batch_size: int = 1
    context_length: int | None = None
    cache_enabled: bool = True


class GenerationRequest(BaseModel):
    """Request for text generation."""
    
    prompt: str
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    stop_sequences: list[str] | None = None
    stream: bool = False


class GenerationResult(BaseModel):
    """Result from text generation."""
    
    text: str
    tokens_generated: int
    generation_time_ms: int
    model_used: str
    metadata: dict[str, Any] = {}


class ModelRecommendation(BaseModel):
    """Model recommendation for a task."""
    
    model_name: str
    confidence_score: float
    reasoning: str
    expected_performance: dict[str, str]
    resource_requirements: dict[str, Any]
    setup_instructions: list[str]


class ToolSelection(BaseModel):
    """Tool selection result."""
    
    selected_tools: list[str]
    confidence_scores: dict[str, float]
    reasoning: str
    alternative_tools: list[str]


# Abstract base classes for implementation
class BaseModelInterface(ModelInterface):
    """Base implementation of ModelInterface."""
    
    def __init__(self):
        self._current_model = None
        self._model_config = None
    
    async def get_model_info(self) -> dict[str, Any]:
        """Get information about the loaded model."""
        if not self._current_model:
            return {"status": "no_model_loaded"}
        
        return {
            "status": "loaded",
            "model_name": self._model_config.get("model_name") if self._model_config else None,
            "config": self._model_config
        }


class BaseLocalModelManager(LocalModelManager):
    """Base implementation of LocalModelManager."""
    
    def __init__(self):
        self._available_models = []
        self._system_info = {}
    
    async def get_system_info(self) -> dict[str, Any]:
        """Get cached system information."""
        return self._system_info
    
    async def update_system_info(self, system_info: dict[str, Any]) -> None:
        """Update cached system information."""
        self._system_info = system_info


class BaseEmbeddingInterface(EmbeddingInterface):
    """Base implementation of EmbeddingInterface."""
    
    def __init__(self):
        self._loaded_models = {}
    
    async def list_available_models(self) -> list[str]:
        """List available embedding models."""
        return list(self._loaded_models.keys())


class BaseToolSelector(ToolSelectorInterface):
    """Base implementation of ToolSelectorInterface."""
    
    def __init__(self):
        self._tool_embeddings = {}
        self._task_history = []
    
    async def update_tool_embeddings(self, tool_descriptions: dict[str, str]) -> None:
        """Update tool description embeddings."""
        self._tool_embeddings = tool_descriptions
