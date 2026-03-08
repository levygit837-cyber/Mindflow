"""Model configuration schemas for MindFlow backend.

Provides schemas for local model configuration, requirements,
and system integration.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator


class ModelInfo(BaseModel):
    """Information about a local model."""
    
    name: str = Field(..., description="Model name")
    type: str = Field(..., description="Model type (llm, embedding, vision, etc.)")
    framework: str = Field(..., description="Framework (pytorch, tensorflow, onnx, etc.)")
    size_gb: Optional[float] = Field(default=None, description="Model size in GB")
    memory_gb: Optional[float] = Field(default=None, description="Required memory in GB")
    gpu_required: bool = Field(default=False, description="Whether GPU is required")
    gpu_memory_gb: Optional[float] = Field(default=None, description="Required GPU memory in GB")
    capabilities: List[str] = Field(default_factory=list, description="Model capabilities")
    supported_tasks: List[str] = Field(default_factory=list, description="Supported tasks")
    performance_metrics: Dict[str, float] = Field(default_factory=dict, description="Performance metrics")
    version: Optional[str] = Field(default=None, description="Model version")
    path: Optional[str] = Field(default=None, description="Model file/directory path")
    
    class Config:
        use_enum_values = True


class SystemInfo(BaseModel):
    """System information for model recommendations."""
    
    cpu_info: Dict[str, Any] = Field(..., description="CPU information")
    memory_info: Dict[str, Any] = Field(..., description="Memory information")
    gpu_info: List[Dict[str, Any]] = Field(default_factory=list, description="GPU information")
    disk_info: Dict[str, Any] = Field(..., description="Disk information")
    os_info: Dict[str, Any] = Field(..., description="Operating system information")
    python_info: Dict[str, Any] = Field(..., description="Python environment information")
    available_memory_gb: float = Field(..., description="Available memory in GB")
    available_disk_gb: float = Field(..., description="Available disk space in GB")
    cpu_cores: int = Field(..., description="Number of CPU cores")
    has_gpu: bool = Field(default=False, description="Whether GPU is available")
    gpu_memory_total_gb: float = Field(default=0.0, description="Total GPU memory in GB")
    
    class Config:
        use_enum_values = True


class ModelRequirement(BaseModel):
    """Requirements for running a model."""
    
    min_memory_gb: float = Field(..., description="Minimum required memory in GB")
    min_cpu_cores: int = Field(default=1, description="Minimum required CPU cores")
    min_disk_gb: float = Field(default=1.0, description="Minimum required disk space in GB")
    gpu_required: bool = Field(default=False, description="Whether GPU is required")
    min_gpu_memory_gb: Optional[float] = Field(default=None, description="Minimum GPU memory in GB")
    supported_os: List[str] = Field(default_factory=lambda: ["linux", "windows", "darwin"], description="Supported operating systems")
    python_version_min: Optional[str] = Field(default="3.8", description="Minimum Python version")
    dependencies: List[str] = Field(default_factory=list, description="Required dependencies")
    
    class Config:
        use_enum_values = True


class ModelConfig(BaseModel):
    """Configuration for a model instance."""
    
    model_name: str = Field(..., description="Model name")
    model_type: str = Field(..., description="Model type")
    model_path: str = Field(..., description="Path to model files")
    config_path: Optional[str] = Field(default=None, description="Path to model configuration")
    device: str = Field(default="auto", description="Device (cpu, cuda, auto)")
    precision: str = Field(default="fp32", description="Precision (fp16, fp32, int8)")
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens for generation")
    temperature: Optional[float] = Field(default=None, description="Generation temperature")
    top_p: Optional[float] = Field(default=None, description="Top-p sampling parameter")
    top_k: Optional[int] = Field(default=None, description="Top-k sampling parameter")
    batch_size: int = Field(default=1, description="Batch size")
    context_length: Optional[int] = Field(default=None, description="Context length")
    cache_enabled: bool = Field(default=True, description="Enable model caching")
    parallel_requests: int = Field(default=1, description="Maximum parallel requests")
    timeout_seconds: int = Field(default=300, description="Request timeout")
    
    class Config:
        use_enum_values = True


class ModelRecommendation(BaseModel):
    """Model recommendation based on system capabilities."""
    
    model_info: ModelInfo = Field(..., description="Recommended model information")
    confidence_score: float = Field(..., description="Confidence in recommendation (0.0 to 1.0)")
    reasoning: str = Field(..., description="Reasoning for recommendation")
    system_compatibility: Dict[str, bool] = Field(..., description="System compatibility checks")
    expected_performance: Dict[str, str] = Field(..., description="Expected performance metrics")
    limitations: List[str] = Field(default_factory=list, description="Known limitations")
    setup_requirements: List[str] = Field(default_factory=list, description="Setup requirements")
    alternative_models: List[ModelInfo] = Field(default_factory=list, description="Alternative models")
    
    class Config:
        use_enum_values = True


class ModelPerformanceMetrics(BaseModel):
    """Performance metrics for a model."""
    
    model_name: str = Field(..., description="Model name")
    task_type: str = Field(..., description="Task type")
    accuracy: Optional[float] = Field(default=None, description="Accuracy score")
    latency_ms: Optional[float] = Field(default=None, description="Average latency in milliseconds")
    throughput_tokens_per_second: Optional[float] = Field(default=None, description="Throughput in tokens/second")
    memory_usage_gb: Optional[float] = Field(default=None, description="Memory usage in GB")
    gpu_utilization_percent: Optional[float] = Field(default=None, description="GPU utilization percentage")
    cpu_utilization_percent: Optional[float] = Field(default=None, description="CPU utilization percentage")
    energy_efficiency: Optional[float] = Field(default=None, description="Energy efficiency score")
    benchmark_date: Optional[str] = Field(default=None, description="Benchmark date")
    
    class Config:
        use_enum_values = True


class ModelLoadConfig(BaseModel):
    """Configuration for loading a model."""
    
    model_name: str = Field(..., description="Model name")
    load_method: str = Field(default="auto", description="Load method (auto, from_file, from_hub)")
    model_path: Optional[str] = Field(default=None, description="Path to model files")
    hub_name: Optional[str] = Field(default=None, description="Model hub name")
    hub_model_id: Optional[str] = Field(default=None, description="Model ID in hub")
    cache_dir: Optional[str] = Field(default=None, description="Cache directory")
    trust_remote_code: bool = Field(default=False, description="Trust remote code")
    use_fast_tokenizer: bool = Field(default=True, description="Use fast tokenizer")
    device_map: Optional[Union[str, Dict[str, str]]] = Field(default="auto", description="Device mapping")
    torch_dtype: Optional[str] = Field(default=None, description="Torch data type")
    low_cpu_mem_usage: bool = Field(default=True, description="Low CPU memory usage")
    
    class Config:
        use_enum_values = True


def create_model_info(
    name: str,
    model_type: str,
    framework: str,
    **kwargs
) -> ModelInfo:
    """Create a ModelInfo instance.
    
    Args:
        name: Model name
        model_type: Model type
        framework: Framework name
        **kwargs: Additional model properties
        
    Returns:
        ModelInfo instance
    """
    return ModelInfo(
        name=name,
        type=model_type,
        framework=framework,
        **kwargs
    )


def create_model_config(
    model_name: str,
    model_type: str,
    model_path: str,
    **kwargs
) -> ModelConfig:
    """Create a ModelConfig instance.
    
    Args:
        model_name: Model name
        model_type: Model type
        model_path: Path to model files
        **kwargs: Additional configuration properties
        
    Returns:
        ModelConfig instance
    """
    return ModelConfig(
        model_name=model_name,
        model_type=model_type,
        model_path=model_path,
        **kwargs
    )


def create_recommendation(
    model_info: ModelInfo,
    confidence_score: float,
    reasoning: str,
    **kwargs
) -> ModelRecommendation:
    """Create a ModelRecommendation instance.
    
    Args:
        model_info: Recommended model information
        confidence_score: Confidence in recommendation
        reasoning: Reasoning for recommendation
        **kwargs: Additional recommendation properties
        
    Returns:
        ModelRecommendation instance
    """
    return ModelRecommendation(
        model_info=model_info,
        confidence_score=confidence_score,
        reasoning=reasoning,
        **kwargs
    )
