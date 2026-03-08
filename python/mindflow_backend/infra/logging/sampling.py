"""Log sampling for production environments.

Provides intelligent log sampling to reduce log volume
while maintaining visibility into important events.
"""

from __future__ import annotations

import random
import time
from typing import Dict, Any, Optional, Set, List
from dataclasses import dataclass, field
from enum import Enum
import hashlib

import structlog

# IMPORTANT: avoid importing mindflow_backend.infra.logging here to prevent
# circular imports during logging bootstrap.
_logger = structlog.get_logger(__name__)


class SamplingStrategy(Enum):
    """Log sampling strategies."""
    ALWAYS = "always"          # Always sample
    NEVER = "never"            # Never sample
    PROBABILITY = "probability"  # Probability-based sampling
    RATE_LIMITED = "rate_limited"  # Rate-limited sampling
    INTELLIGENT = "intelligent"   # Intelligent sampling based on content


@dataclass
class SamplingRule:
    """Rule for log sampling decisions."""
    name: str
    strategy: SamplingStrategy
    priority: int = 0
    sample_rate: float = 1.0
    rate_limit_per_second: float = 10.0
    conditions: Dict[str, Any] = field(default_factory=dict)
    exempt_levels: Set[str] = field(default_factory=lambda: {"ERROR", "CRITICAL"})
    last_sample_time: float = field(default=0.0)
    sample_count: int = field(default=0)
    
    def should_sample(self, event_dict: Dict[str, Any]) -> bool:
        """Determine if event should be sampled.
        
        Args:
            event_dict: Log event dictionary
            
        Returns:
            True if event should be sampled
        """
        # Check for exempt levels
        log_level = event_dict.get("level", "INFO")
        if log_level in self.exempt_levels:
            return True
            
        # Check conditions
        if not self._check_conditions(event_dict):
            return False
            
        # Apply sampling strategy
        current_time = time.time()
        
        if self.strategy == SamplingStrategy.ALWAYS:
            return True
        elif self.strategy == SamplingStrategy.NEVER:
            return False
        elif self.strategy == SamplingStrategy.PROBABILITY:
            return random.random() < self.sample_rate
        elif self.strategy == SamplingStrategy.RATE_LIMITED:
            # Check if we've exceeded rate limit
            time_since_last = current_time - self.last_sample_time
            if time_since_last < 1.0 / self.rate_limit_per_second:
                return False
            self.last_sample_time = current_time
            return True
        elif self.strategy == SamplingStrategy.INTELLIGENT:
            return self._intelligent_sampling(event_dict, current_time)
            
        return True
        
    def _check_conditions(self, event_dict: Dict[str, Any]) -> bool:
        """Check if event matches sampling conditions.
        
        Args:
            event_dict: Log event dictionary
            
        Returns:
            True if conditions match
        """
        for key, expected_value in self.conditions.items():
            if key not in event_dict:
                return False
                
            actual_value = event_dict[key]
            
            # Handle different condition types
            if isinstance(expected_value, dict):
                # Complex condition with operator
                operator = expected_value.get("operator", "equals")
                value = expected_value.get("value")
                
                if operator == "equals":
                    if actual_value != value:
                        return False
                elif operator == "contains":
                    if value not in str(actual_value):
                        return False
                elif operator == "starts_with":
                    if not str(actual_value).startswith(str(value)):
                        return False
                elif operator == "ends_with":
                    if not str(actual_value).endswith(str(value)):
                        return False
                elif operator == "regex":
                    import re
                    if not re.search(value, str(actual_value)):
                        return False
                elif operator == "in":
                    if actual_value not in value:
                        return False
            else:
                # Simple equality check
                if actual_value != expected_value:
                    return False
                    
        return True
        
    def _intelligent_sampling(self, event_dict: Dict[str, Any], current_time: float) -> bool:
        """Intelligent sampling based on event content.
        
        Args:
            event_dict: Log event dictionary
            current_time: Current timestamp
            
        Returns:
            True if event should be sampled
        """
        # Always sample errors and critical events
        log_level = event_dict.get("level", "INFO")
        if log_level in ["ERROR", "CRITICAL"]:
            return True
            
        # Sample based on event importance
        event_name = event_dict.get("event", "")
        logger_name = event_dict.get("logger", "")
        
        # High importance events
        high_importance_patterns = [
            "error", "exception", "failed", "timeout", "retry",
            "security", "auth", "login", "logout", "permission",
            "performance", "slow", "latency", "timeout",
            "business", "transaction", "payment", "order",
        ]
        
        for pattern in high_importance_patterns:
            if pattern in event_name.lower() or pattern in logger_name.lower():
                return True
                
        # Sample based on correlation ID (sample first event per correlation)
        correlation_id = event_dict.get("correlation_id")
        if correlation_id:
            # Create hash for consistent sampling
            hash_input = f"{correlation_id}:{int(current_time // 60)}"  # Per minute bucket
            hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
            
            # Sample based on hash to ensure consistent sampling
            return (hash_value % 1000) < (self.sample_rate * 1000)
            
        # Default probability sampling
        return random.random() < self.sample_rate


@dataclass
class SamplingMetrics:
    """Metrics for sampling performance."""
    total_events: int = 0
    sampled_events: int = 0
    dropped_events: int = 0
    sample_rate: float = 0.0
    last_reset_time: float = field(default_factory=time.time)
    
    def update(self, sampled: bool) -> None:
        """Update metrics with new event.
        
        Args:
            sampled: Whether event was sampled
        """
        self.total_events += 1
        if sampled:
            self.sampled_events += 1
        else:
            self.dropped_events += 1
            
        self.sample_rate = self.sampled_events / max(self.total_events, 1)
        
    def reset(self) -> None:
        """Reset metrics."""
        self.total_events = 0
        self.sampled_events = 0
        self.dropped_events = 0
        self.sample_rate = 0.0
        self.last_reset_time = time.time()


class LogSampler:
    """Advanced log sampling system.
    
    Features:
    - Multiple sampling strategies
    - Rule-based sampling
    - Performance metrics
    - Intelligent content-based sampling
    - Rate limiting
    """
    
    def __init__(self) -> None:
        """Initialize log sampler."""
        self._rules: List[SamplingRule] = []
        self._default_rule = SamplingRule(
            name="default",
            strategy=SamplingStrategy.PROBABILITY,
            sample_rate=1.0,
        )
        self._metrics = SamplingMetrics()
        self._configured = False
        self._debug_mode = False
        
        # Initialize default rules
        self._initialize_default_rules()
        
    def _initialize_default_rules(self) -> None:
        """Initialize default sampling rules."""
        # Always sample errors and critical events
        self.add_rule(SamplingRule(
            name="always_sample_errors",
            strategy=SamplingStrategy.ALWAYS,
            priority=100,
            conditions={"level": {"operator": "in", "value": ["ERROR", "CRITICAL"]}},
        ))
        
        # Sample health checks at lower rate
        self.add_rule(SamplingRule(
            name="health_checks",
            strategy=SamplingStrategy.PROBABILITY,
            priority=50,
            sample_rate=0.1,  # 10% sampling
            conditions={"logger": {"operator": "contains", "value": "health"}},
        ))
        
        # Sample performance metrics
        self.add_rule(SamplingRule(
            name="performance_metrics",
            strategy=SamplingStrategy.PROBABILITY,
            priority=40,
            sample_rate=0.5,  # 50% sampling
            conditions={"event": {"operator": "contains", "value": "performance"}},
        ))
        
        # Rate limit debug logs in production
        self.add_rule(SamplingRule(
            name="debug_logs",
            strategy=SamplingStrategy.RATE_LIMITED,
            priority=30,
            rate_limit_per_second=5.0,
            conditions={"level": "DEBUG"},
        ))
        
    def configure(self, sample_rate: float = 1.0, debug_mode: bool = False) -> None:
        """Configure log sampler.
        
        Args:
            sample_rate: Default sample rate
            debug_mode: Enable debug mode
        """
        self._default_rule.sample_rate = sample_rate
        self._debug_mode = debug_mode
        self._configured = True
        
        _logger.info(
            "log_sampler_configured",
            sample_rate=sample_rate,
            debug_mode=debug_mode,
            rules_count=len(self._rules),
        )
        
    def add_rule(self, rule: SamplingRule) -> None:
        """Add a sampling rule.
        
        Args:
            rule: Sampling rule to add
        """
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        
        _logger.debug(
            "sampling_rule_added",
            name=rule.name,
            strategy=rule.strategy.value,
            priority=rule.priority,
        )
        
    def remove_rule(self, name: str) -> bool:
        """Remove a sampling rule.
        
        Args:
            name: Rule name to remove
            
        Returns:
            True if rule was removed
        """
        for i, rule in enumerate(self._rules):
            if rule.name == name:
                del self._rules[i]
                _logger.debug("sampling_rule_removed", name=name)
                return True
        return False
        
    def should_sample(self, event_dict: Dict[str, Any]) -> bool:
        """Determine if event should be sampled.
        
        Args:
            event_dict: Log event dictionary
            
        Returns:
            True if event should be sampled
        """
        if not self._configured:
            return True
            
        # In debug mode, sample everything
        if self._debug_mode:
            return True
            
        # Check rules in priority order
        for rule in self._rules:
            if rule.should_sample(event_dict):
                self._metrics.update(True)
                return True
                
        # Use default rule if no other rules matched
        sampled = self._default_rule.should_sample(event_dict)
        self._metrics.update(sampled)
        return sampled
        
    def get_metrics(self) -> SamplingMetrics:
        """Get sampling metrics.
        
        Returns:
            Current sampling metrics
        """
        return self._metrics
        
    def reset_metrics(self) -> None:
        """Reset sampling metrics."""
        self._metrics.reset()
        _logger.debug("sampling_metrics_reset")
        
    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all sampling rules.
        
        Returns:
            List of sampling rule information
        """
        rules_info = []
        for rule in self._rules:
            rules_info.append({
                "name": rule.name,
                "strategy": rule.strategy.value,
                "priority": rule.priority,
                "sample_rate": rule.sample_rate,
                "rate_limit_per_second": rule.rate_limit_per_second,
                "conditions": rule.conditions,
                "exempt_levels": list(rule.exempt_levels),
                "sample_count": rule.sample_count,
            })
            
        # Add default rule
        rules_info.append({
            "name": self._default_rule.name,
            "strategy": self._default_rule.strategy.value,
            "priority": 0,
            "sample_rate": self._default_rule.sample_rate,
            "conditions": self._default_rule.conditions,
            "exempt_levels": list(self._default_rule.exempt_levels),
        })
        
        return rules_info
        
    def update_rule(
        self,
        name: str,
        strategy: Optional[SamplingStrategy] = None,
        sample_rate: Optional[float] = None,
        priority: Optional[int] = None,
        conditions: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update an existing sampling rule.
        
        Args:
            name: Rule name to update
            strategy: New sampling strategy
            sample_rate: New sample rate
            priority: New priority
            conditions: New conditions
            
        Returns:
            True if rule was updated
        """
        for rule in self._rules:
            if rule.name == name:
                if strategy is not None:
                    rule.strategy = strategy
                if sample_rate is not None:
                    rule.sample_rate = sample_rate
                if priority is not None:
                    rule.priority = priority
                if conditions is not None:
                    rule.conditions = conditions
                    
                # Re-sort rules by priority
                self._rules.sort(key=lambda r: r.priority, reverse=True)
                
                _logger.debug("sampling_rule_updated", name=name)
                return True
                
        return False
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive sampling statistics.
        
        Returns:
            Dictionary with sampling statistics
        """
        metrics = self.get_metrics()
        rules = self.get_rules()
        
        return {
            "configured": self._configured,
            "debug_mode": self._debug_mode,
            "metrics": {
                "total_events": metrics.total_events,
                "sampled_events": metrics.sampled_events,
                "dropped_events": metrics.dropped_events,
                "sample_rate": metrics.sample_rate,
                "last_reset_time": metrics.last_reset_time,
            },
            "rules": rules,
            "default_sample_rate": self._default_rule.sample_rate,
        }


# Global log sampler instance
_log_sampler: Optional[LogSampler] = None


def get_log_sampler() -> LogSampler:
    """Get global log sampler instance.
    
    Returns:
        LogSampler instance
    """
    global _log_sampler
    if _log_sampler is None:
        _log_sampler = LogSampler()
    return _log_sampler
