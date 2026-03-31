"""gRPC performance tuner with automated recommendations.

Provides intelligent tuning recommendations based on
system characteristics and workload patterns.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class TuningType(Enum):
    """Types of tuning recommendations."""
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    SCALABILITY = "scalability"
    EFFICIENCY = "efficiency"


@dataclass
class TuningConfig:
    """Configuration for performance tuner."""
    enabled: bool = True
    analysis_interval_seconds: int = 300
    min_confidence_score: float = 70.0


@dataclass
class TuningRecommendation:
    """Tuning recommendation."""
    tuning_type: TuningType
    parameter: str
    current_value: Any
    recommended_value: Any
    reasoning: str
    confidence_score: float
    impact_level: str  # low, medium, high


class GrpcTuner:
    """gRPC performance tuner with automated recommendations."""
    
    def __init__(self, config: TuningConfig | None = None):
        self.config = config or TuningConfig()
        _logger.info("grpc_tuner_initialized", enabled=self.config.enabled)
    
    def generate_recommendations(self, current_config: dict[str, Any],
                               performance_data: list[dict[str, Any]]) -> list[TuningRecommendation]:
        """Generate tuning recommendations based on analysis."""
        if not self.config.enabled:
            return []
        
        recommendations = []
        
        # Generate recommendations based on performance data
        recommendations.extend(self._analyze_performance_tuning(current_config, performance_data))
        recommendations.extend(self._analyze_reliability_tuning(current_config, performance_data))
        
        # Filter by confidence score
        recommendations = [r for r in recommendations if r.confidence_score >= self.config.min_confidence_score]
        
        return recommendations
    
    def _analyze_performance_tuning(self, config: dict[str, Any],
                                   data: list[dict[str, Any]]) -> list[TuningRecommendation]:
        """Analyze performance-related tuning opportunities."""
        recommendations = []
        
        # Example: Connection pool tuning based on utilization
        if 'connection_utilization' in data:
            avg_utilization = sum(d['connection_utilization'] for d in data) / len(data)
            
            if avg_utilization < 0.3 and config.get('max_connections', 100) > 20:
                recommendations.append(TuningRecommendation(
                    tuning_type=TuningType.PERFORMANCE,
                    parameter='max_connections',
                    current_value=config['max_connections'],
                    recommended_value=max(10, config['max_connections'] // 2),
                    reasoning=f"Low connection utilization ({avg_utilization:.1%}) suggests pool size can be reduced",
                    confidence_score=80.0,
                    impact_level='medium'
                ))
        
        return recommendations
    
    def _analyze_reliability_tuning(self, config: dict[str, Any],
                                    data: list[dict[str, Any]]) -> list[TuningRecommendation]:
        """Analyze reliability-related tuning opportunities."""
        recommendations = []
        
        # Example: Retry policy tuning based on failure patterns
        failure_rate = len([d for d in data if not d.get('success', True)]) / len(data)
        
        if failure_rate > 0.1 and config.get('max_attempts', 3) < 5:
            recommendations.append(TuningRecommendation(
                tuning_type=TuningType.RELIABILITY,
                parameter='max_attempts',
                current_value=config['max_attempts'],
                recommended_value=min(5, config['max_attempts'] + 1),
                reasoning=f"High failure rate ({failure_rate:.1%}) suggests increasing retry attempts",
                confidence_score=75.0,
                impact_level='high'
            ))
        
        return recommendations
