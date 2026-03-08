"""AI and model interfaces for MindFlow backend.

Provides interfaces for local model management,
AI operations, and intelligent tool selection.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod

from pydantic import BaseModel

from mindflow_backend.schemas.orchestration.orchestrator import AgentType


class ModelInterface(ABC):
    """Interface for local model management and execution."""
    
    @abstractmethod
    async def load_model(self, model_config: Dict[str, Any]) -> bool:
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
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
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
    async def get_model_info(self) -> Dict[str, Any]:
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
    async def detect_available_models(self) -> List[Dict[str, Any]]:
        """Detect available local models.
        
        Returns:
            List of available model information
        """
        pass
    
    @abstractmethod
    async def recommend_model_for_task(
        self,
        task: str,
        constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
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
        system_info: Dict[str, Any]
    ) -> Dict[str, Any]:
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
        texts: List[str],
        model_name: Optional[str] = None
    ) -> List[List[float]]:
        """Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed
            model_name: Optional model name
            
        Returns:
            List of embedding vectors
        """
        pass
    
    @abstractmethod
    async def get_embedding_info(self, model_name: Optional[str] = None) -> Dict[str, Any]:
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
        available_tools: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
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
        tools: List[str],
        agent_type: AgentType
    ) -> List[Dict[str, Any]]:
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
        model_config: Dict[str, Any],
        hardware_info: Dict[str, Any]
    ) -> Dict[str, Any]:
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
        model_config: Dict[str, Any],
        test_cases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
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
    model_path: Optional[str] = None
    device: str = "auto"
    precision: str = "fp32"
    max_memory_gb: Optional[float] = None
    batch_size: int = 1
    context_length: Optional[int] = None
    cache_enabled: bool = True


class GenerationRequest(BaseModel):
    """Request for text generation."""
    
    prompt: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    stop_sequences: Optional[List[str]] = None
    stream: bool = False


class GenerationResult(BaseModel):
    """Result from text generation."""
    
    text: str
    tokens_generated: int
    generation_time_ms: int
    model_used: str
    metadata: Dict[str, Any] = {}


class ModelRecommendation(BaseModel):
    """Model recommendation for a task."""
    
    model_name: str
    confidence_score: float
    reasoning: str
    expected_performance: Dict[str, str]
    resource_requirements: Dict[str, Any]
    setup_instructions: List[str]


class ToolSelection(BaseModel):
    """Tool selection result."""
    
    selected_tools: List[str]
    confidence_scores: Dict[str, float]
    reasoning: str
    alternative_tools: List[str]


# Abstract base classes for implementation
class BaseModelInterface(ModelInterface):
    """Base implementation of ModelInterface."""
    
    def __init__(self):
        self._current_model = None
        self._model_config = None
    
    async def get_model_info(self) -> Dict[str, Any]:
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
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get cached system information."""
        return self._system_info
    
    async def update_system_info(self, system_info: Dict[str, Any]) -> None:
        """Update cached system information."""
        self._system_info = system_info


class BaseEmbeddingInterface(EmbeddingInterface):
    """Base implementation of EmbeddingInterface."""
    
    def __init__(self):
        self._loaded_models = {}
    
    async def list_available_models(self) -> List[str]:
        """List available embedding models."""
        return list(self._loaded_models.keys())


class BaseToolSelector(ToolSelectorInterface):
    """Base implementation of ToolSelectorInterface."""
    
    def __init__(self):
        self._tool_embeddings = {}
        self._task_history = []
    
    async def update_tool_embeddings(self, tool_descriptions: Dict[str, str]) -> None:
        """Update tool description embeddings."""
        self._tool_embeddings = tool_descriptions
