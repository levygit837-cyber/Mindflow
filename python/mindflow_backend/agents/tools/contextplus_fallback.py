"""Context+ Fallback Engine — Automatic fallback when semantic tools fail.

Handles timeouts and failures in semantic_code_search and semantic_identifier_search
by falling back to structural tools (get_context_tree, get_file_skeleton).
Includes circuit breaker pattern to prevent cascading failures.
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ToolState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    """Circuit breaker for Context+ tools."""
    
    failure_threshold: int = 3
    recovery_timeout: int = 60
    half_open_max_calls: int = 2
    
    state: ToolState = ToolState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0
    half_open_calls: int = 0
    
    def can_execute(self) -> bool:
        """Check if tool can be called."""
        if self.state == ToolState.CLOSED:
            return True
        
        if self.state == ToolState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = ToolState.HALF_OPEN
                self.half_open_calls = 0
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                return True
            return False
        
        # HALF_OPEN
        if self.half_open_calls < self.half_open_max_calls:
            self.half_open_calls += 1
            return True
        return False
    
    def record_success(self) -> None:
        """Record successful execution."""
        if self.state == ToolState.HALF_OPEN:
            logger.info("Circuit breaker recovering, transitioning to CLOSED")
        self.state = ToolState.CLOSED
        self.failure_count = 0
        self.half_open_calls = 0
    
    def record_failure(self) -> None:
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == ToolState.HALF_OPEN:
            logger.warning("Circuit breaker test failed, reopening")
            self.state = ToolState.OPEN
        elif self.failure_count >= self.failure_threshold:
            logger.warning(
                f"Circuit breaker threshold reached ({self.failure_count} failures), "
                "transitioning to OPEN"
            )
            self.state = ToolState.OPEN


@dataclass
class ToolResult:
    """Result from tool execution."""
    
    success: bool
    data: Any = None
    error: Optional[str] = None
    tool_used: str = ""
    fallback_used: bool = False
    confidence: float = 1.0
    execution_time: float = 0


@dataclass
class FallbackConfig:
    """Configuration for fallback engine."""
    
    timeout_seconds: float = 30.0
    max_retries: int = 2
    min_confidence: float = 0.7
    retry_delay: float = 2.0
    exponential_backoff: bool = True


# Fallback chains: primary tool -> ordered list of fallbacks
FALLBACK_CHAINS: dict[str, list[str]] = {
    "semantic_code_search": [
        "get_context_tree",
        "get_file_skeleton",
    ],
    "semantic_identifier_search": [
        "get_context_tree",
        "get_file_skeleton",
    ],
    "get_blast_radius": [
        "search_memory_graph",
    ],
}

# Metrics tracking
@dataclass
class FallbackMetrics:
    """Track fallback usage metrics."""
    
    total_calls: int = 0
    primary_successes: int = 0
    fallback_successes: int = 0
    total_failures: int = 0
    timeout_count: int = 0
    fallback_usage: dict[str, int] = field(default_factory=dict)
    
    def record_call(
        self,
        primary_tool: str,
        success: bool,
        fallback_used: Optional[str] = None,
        was_timeout: bool = False,
    ) -> None:
        """Record a tool call for metrics."""
        self.total_calls += 1
        
        if was_timeout:
            self.timeout_count += 1
        
        if success:
            if fallback_used:
                self.fallback_successes += 1
                self.fallback_usage[fallback_used] = (
                    self.fallback_usage.get(fallback_used, 0) + 1
                )
            else:
                self.primary_successes += 1
        else:
            self.total_failures += 1
    
    @property
    def success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.total_calls == 0:
            return 1.0
        return (self.primary_successes + self.fallback_successes) / self.total_calls
    
    @property
    def timeout_rate(self) -> float:
        """Calculate timeout rate."""
        if self.total_calls == 0:
            return 0.0
        return self.timeout_count / self.total_calls
    
    def get_report(self) -> dict:
        """Generate metrics report."""
        return {
            "total_calls": self.total_calls,
            "primary_success_rate": (
                self.primary_successes / self.total_calls if self.total_calls > 0 else 0
            ),
            "fallback_success_rate": (
                self.fallback_successes / self.total_calls if self.total_calls > 0 else 0
            ),
            "failure_rate": (
                self.total_failures / self.total_calls if self.total_calls > 0 else 0
            ),
            "timeout_rate": self.timeout_rate,
            "fallback_usage": dict(self.fallback_usage),
        }


class ContextPlusFallbackEngine:
    """Engine with automatic fallback for Context+ tool failures.
    
    When a semantic tool fails or times out, automatically tries
    structural fallbacks in order. Includes circuit breaker to
    prevent cascading failures.
    
    Usage:
        engine = ContextPlusFallbackEngine()
        result = await engine.execute_with_fallback(
            tool_name="semantic_code_search",
            params={"query": "authentication flow"},
            tool_executor=my_executor,
        )
    """
    
    def __init__(self, config: Optional[FallbackConfig] = None):
        self.config = config or FallbackConfig()
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.metrics = FallbackMetrics()
        self._fallback_log: list[dict] = []
    
    def _get_circuit_breaker(self, tool_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for a tool."""
        if tool_name not in self.circuit_breakers:
            self.circuit_breakers[tool_name] = CircuitBreaker()
        return self.circuit_breakers[tool_name]
    
    async def _execute_with_timeout(
        self,
        tool_executor: Callable,
        tool_name: str,
        params: dict,
    ) -> ToolResult:
        """Execute tool with timeout protection."""
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(
                tool_executor(tool_name, params),
                timeout=self.config.timeout_seconds,
            )
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                success=True,
                data=result,
                tool_used=tool_name,
                execution_time=execution_time,
            )
        
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            logger.warning(
                f"Tool {tool_name} timed out after {execution_time:.1f}s "
                f"(limit: {self.config.timeout_seconds}s)"
            )
            
            return ToolResult(
                success=False,
                error=f"Timeout after {execution_time:.1f}s",
                tool_used=tool_name,
                execution_time=execution_time,
            )
        
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Tool {tool_name} failed: {e}")
            
            return ToolResult(
                success=False,
                error=str(e),
                tool_used=tool_name,
                execution_time=execution_time,
            )
    
    async def _try_tool(
        self,
        tool_name: str,
        params: dict,
        tool_executor: Callable,
    ) -> ToolResult:
        """Try executing a tool with circuit breaker and retry logic."""
        breaker = self._get_circuit_breaker(tool_name)
        
        if not breaker.can_execute():
            logger.warning(
                f"Circuit breaker OPEN for {tool_name}, skipping"
            )
            return ToolResult(
                success=False,
                error=f"Circuit breaker open for {tool_name}",
                tool_used=tool_name,
            )
        
        last_result = None
        
        for attempt in range(1, self.config.max_retries + 1):
            result = await self._execute_with_timeout(
                tool_executor, tool_name, params
            )
            
            if result.success:
                breaker.record_success()
                return result
            
            last_result = result
            breaker.record_failure()
            
            if attempt < self.config.max_retries:
                delay = self.config.retry_delay
                if self.config.exponential_backoff:
                    delay *= (2 ** (attempt - 1))
                
                logger.info(
                    f"Retry {attempt}/{self.config.max_retries} for {tool_name} "
                    f"in {delay:.1f}s"
                )
                await asyncio.sleep(delay)
        
        return last_result or ToolResult(
            success=False,
            error="Max retries exceeded",
            tool_used=tool_name,
        )
    
    async def execute_with_fallback(
        self,
        tool_name: str,
        params: dict,
        tool_executor: Callable,
        custom_fallbacks: Optional[list[str]] = None,
    ) -> ToolResult:
        """Execute tool with automatic fallback chain.
        
        Args:
            tool_name: Primary tool to execute
            params: Parameters for the tool
            tool_executor: Async callable(tool_name, params) -> result
            custom_fallbacks: Override default fallback chain
            
        Returns:
            ToolResult with data from successful execution or error
        """
        was_timeout = False
        fallback_used = None
        
        # Try primary tool
        result = await self._try_tool(tool_name, params, tool_executor)
        
        if result.success:
            self.metrics.record_call(
                primary_tool=tool_name,
                success=True,
                fallback_used=None,
                was_timeout=False,
            )
            return result
        
        # Check if failure was timeout
        if "timeout" in (result.error or "").lower():
            was_timeout = True
        
        # Try fallbacks
        fallbacks = custom_fallbacks or FALLBACK_CHAINS.get(tool_name, [])
        
        for fallback_tool in fallbacks:
            logger.info(f"Trying fallback: {fallback_tool} (primary: {tool_name})")
            
            # Adjust params for fallback tool
            fallback_params = self._adapt_params(tool_name, fallback_tool, params)
            
            fallback_result = await self._try_tool(
                fallback_tool, fallback_params, tool_executor
            )
            
            if fallback_result.success:
                fallback_used = fallback_tool
                
                self._log_fallback(
                    primary=tool_name,
                    fallback=fallback_tool,
                    reason=result.error or "unknown",
                )
                
                self.metrics.record_call(
                    primary_tool=tool_name,
                    success=True,
                    fallback_used=fallback_tool,
                    was_timeout=was_timeout,
                )
                
                return ToolResult(
                    success=True,
                    data=fallback_result.data,
                    tool_used=fallback_tool,
                    fallback_used=True,
                    confidence=0.8,  # Lower confidence for fallback
                    execution_time=fallback_result.execution_time,
                )
        
        # All tools failed
        self.metrics.record_call(
            primary_tool=tool_name,
            success=False,
            fallback_used=None,
            was_timeout=was_timeout,
        )
        
        return ToolResult(
            success=False,
            error=f"Primary and all fallbacks failed for {tool_name}",
            tool_used=tool_name,
        )
    
    def _adapt_params(
        self,
        primary_tool: str,
        fallback_tool: str,
        params: dict,
    ) -> dict:
        """Adapt parameters from primary tool to fallback tool."""
        adapted = params.copy()
        
        # semantic_code_search -> get_context_tree
        if primary_tool == "semantic_code_search" and fallback_tool == "get_context_tree":
            adapted.pop("top_k", None)
            adapted.pop("semantic_weight", None)
            adapted.pop("keyword_weight", None)
            adapted.setdefault("depth_limit", 3)
            adapted.setdefault("include_symbols", True)
        
        # semantic_identifier_search -> get_file_skeleton
        elif (
            primary_tool == "semantic_identifier_search"
            and fallback_tool == "get_file_skeleton"
        ):
            # If we have a file path in context, use it
            if "file_path" in params:
                adapted = {"file_path": params["file_path"]}
        
        return adapted
    
    def _log_fallback(
        self,
        primary: str,
        fallback: str,
        reason: str,
    ) -> None:
        """Log fallback usage for analysis."""
        entry = {
            "timestamp": time.time(),
            "primary": primary,
            "fallback": fallback,
            "reason": reason,
        }
        self._fallback_log.append(entry)
        
        logger.info(
            f"Fallback executed: {primary} -> {fallback} "
            f"(reason: {reason})"
        )
    
    def get_health_report(self) -> dict:
        """Generate health report for monitoring."""
        return {
            "metrics": self.metrics.get_report(),
            "circuit_breakers": {
                name: {
                    "state": cb.state.value,
                    "failure_count": cb.failure_count,
                }
                for name, cb in self.circuit_breakers.items()
            },
            "recent_fallbacks": self._fallback_log[-10:],
        }