"""Review service for managing session reviews and optimization.

This service provides comprehensive session review capabilities including
token window tracking, automatic review triggering, and context optimization.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, UTC, timedelta
from uuid import uuid4

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService
from mindflow_backend.services.interfaces.monitoring_interfaces import ReviewServiceInterface


class ReviewService(BaseAbstractService, ReviewServiceInterface):
    """Service for managing session reviews and token window tracking.
    
    This service provides comprehensive review capabilities including
    automatic review triggering, context optimization, and review scheduling.
    """
    
    def __init__(self) -> None:
        """Initialize review service with configuration."""
        super().__init__()
        
        # Review configurations
        self._session_configs: Dict[str, Dict[str, Any]] = {}
        self._review_tasks: Dict[str, List[Dict[str, Any]]] = {}
        self._review_results: Dict[str, List[Dict[str, Any]]] = {}
        
        # Window size configurations
        self._window_sizes = {
            "small": 1000,    # 1k tokens
            "medium": 4000,   # 4k tokens
            "large": 8000,     # 8k tokens
            "xlarge": 16000   # 16k tokens
        }
        
        # Default configurations
        self._default_config = {
            "window_size": "medium",
            "trigger_threshold": 0.8,  # Trigger review at 80% of window
            "auto_optimize": True,
            "review_frequency": "manual",  # manual, hourly, daily
            "max_reviews_per_session": 50
        }
        
        # Lazy load dependencies
        self._memory_service = None
        self._session_service = None
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    def _get_memory_service(self):
        """Get memory service instance (lazy loading)."""
        if self._memory_service is None:
            from mindflow_backend.memory import get_memory_service
            self._memory_service = get_memory_service()
        return self._memory_service
    
    def _get_session_service(self):
        """Get session service instance (lazy loading)."""
        if self._session_service is None:
            from mindflow_backend.services import get_session_service
            self._session_service = get_session_service()
        return self._session_service
    
    async def initialize_session_review(
        self,
        session_id: str,
        window_size: str = "medium",
        custom_tokens: Optional[int] = None,
        trigger_threshold: Optional[int] = None
    ) -> Dict[str, Any]:
        """Initialize session review configuration.
        
        Args:
            session_id: Session identifier
            window_size: Token window size
            custom_tokens: Custom token count
            trigger_threshold: Custom trigger threshold
            
        Returns:
            Dictionary containing initialization result
        """
        self.log_operation(
            "initialize_session_review",
            session_id=session_id,
            window_size=window_size,
            custom_tokens=custom_tokens
        )
        
        try:
            # Validate window size
            if window_size not in self._window_sizes:
                raise ValueError(f"Invalid window size: {window_size}. Available: {list(self._window_sizes.keys())}")
            
            # Get token limit
            token_limit = custom_tokens or self._window_sizes[window_size]
            
            # Create session configuration
            config = {
                **self._default_config,
                "session_id": session_id,
                "window_size": window_size,
                "token_limit": token_limit,
                "trigger_threshold": trigger_threshold or self._default_config["trigger_threshold"],
                "initialized_at": datetime.now(UTC).isoformat(),
                "current_tokens": 0,
                "last_review_at": None,
                "review_count": 0
            }
            
            self._session_configs[session_id] = config
            self._review_tasks[session_id] = []
            self._review_results[session_id] = []
            
            return {
                "session_id": session_id,
                "window_size": window_size,
                "token_limit": token_limit,
                "trigger_threshold": config["trigger_threshold"],
                "status": "initialized",
                "initialized_at": config["initialized_at"]
            }
            
        except Exception as exc:
            self._logger.error(f"Error initializing session review for {session_id}: {str(exc)}")
            raise
    
    async def update_token_count(
        self,
        session_id: str,
        additional_tokens: int
    ) -> Dict[str, Any]:
        """Update token count and check if review should be triggered.
        
        Args:
            session_id: Session identifier
            additional_tokens: Number of additional tokens
            
        Returns:
            Dictionary containing update result and trigger status
        """
        self.log_operation(
            "update_token_count",
            session_id=session_id,
            additional_tokens=additional_tokens
        )
        
        try:
            # Get session configuration
            config = self._session_configs.get(session_id)
            if not config:
                raise ValueError(f"Session review not initialized: {session_id}")
            
            # Update token count
            old_tokens = config["current_tokens"]
            new_tokens = old_tokens + additional_tokens
            config["current_tokens"] = new_tokens
            
            # Check if review should be triggered
            token_ratio = new_tokens / config["token_limit"]
            should_trigger = token_ratio >= config["trigger_threshold"]
            
            result = {
                "session_id": session_id,
                "old_token_count": old_tokens,
                "new_token_count": new_tokens,
                "additional_tokens": additional_tokens,
                "token_limit": config["token_limit"],
                "token_ratio": round(token_ratio, 3),
                "trigger_threshold": config["trigger_threshold"],
                "should_trigger_review": should_trigger,
                "updated_at": datetime.now(UTC).isoformat()
            }
            
            # Auto-trigger review if needed
            if should_trigger and config["auto_optimize"]:
                await self.trigger_review(session_id, "automatic")
                result["auto_triggered"] = True
                result["trigger_type"] = "automatic"
            else:
                result["auto_triggered"] = False
                result["trigger_type"] = None
            
            return result
            
        except Exception as exc:
            self._logger.error(f"Error updating token count for {session_id}: {str(exc)}")
            raise
    
    async def trigger_review(
        self,
        session_id: str,
        review_type: str = "manual"
    ) -> Dict[str, Any]:
        """Trigger a session review.
        
        Args:
            session_id: Session identifier
            review_type: Type of review (manual, automatic, scheduled)
            
        Returns:
            Dictionary containing review trigger result
        """
        self.log_operation(
            "trigger_review",
            session_id=session_id,
            review_type=review_type
        )
        
        try:
            # Get session configuration
            config = self._session_configs.get(session_id)
            if not config:
                raise ValueError(f"Session review not initialized: {session_id}")
            
            # Check review limits
            if config["review_count"] >= config["max_reviews_per_session"]:
                return {
                    "session_id": session_id,
                    "status": "skipped",
                    "reason": "max_reviews_reached",
                    "max_reviews": config["max_reviews_per_session"],
                    "current_reviews": config["review_count"]
                }
            
            # Create review task
            review_task = {
                "id": f"review-{uuid4()}",
                "session_id": session_id,
                "type": review_type,
                "token_count": config["current_tokens"],
                "window_size": config["window_size"],
                "token_limit": config["token_limit"],
                "created_at": datetime.now(UTC).isoformat(),
                "status": "pending"
            }
            
            self._review_tasks[session_id].append(review_task)
            
            # Execute review
            review_result = await self._execute_review(session_id, review_task)
            
            # Update configuration
            config["last_review_at"] = review_result["completed_at"]
            config["review_count"] += 1
            config["current_tokens"] = review_result.get("optimized_token_count", config["current_tokens"])
            
            return {
                "session_id": session_id,
                "review_id": review_task["id"],
                "review_type": review_type,
                "status": "completed",
                "review_result": review_result,
                "triggered_at": review_task["created_at"],
                "completed_at": review_result["completed_at"]
            }
            
        except Exception as exc:
            self._logger.error(f"Error triggering review for {session_id}: {str(exc)}")
            raise
    
    async def get_review_status(self, session_id: str) -> Dict[str, Any]:
        """Get review status for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary containing review status information
        """
        self.log_operation("get_review_status", session_id=session_id)
        
        try:
            # Get session configuration
            config = self._session_configs.get(session_id)
            if not config:
                raise ValueError(f"Session review not initialized: {session_id}")
            
            # Get recent review tasks
            recent_tasks = self._review_tasks.get(session_id, [])[-5:]  # Last 5 tasks
            recent_results = self._review_results.get(session_id, [])[-5:]  # Last 5 results
            
            # Calculate next review threshold
            tokens_until_review = config["token_limit"] - config["current_tokens"]
            tokens_ratio = config["current_tokens"] / config["token_limit"]
            next_review_tokens = int(config["token_limit"] * config["trigger_threshold"]) - config["current_tokens"]
            
            return {
                "session_id": session_id,
                "configuration": {
                    "window_size": config["window_size"],
                    "token_limit": config["token_limit"],
                    "trigger_threshold": config["trigger_threshold"],
                    "auto_optimize": config["auto_optimize"]
                },
                "current_status": {
                    "current_tokens": config["current_tokens"],
                    "token_ratio": round(tokens_ratio, 3),
                    "tokens_until_review": max(0, tokens_until_review),
                    "next_review_tokens": max(0, next_review_tokens),
                    "last_review_at": config["last_review_at"],
                    "total_reviews": config["review_count"]
                },
                "recent_tasks": recent_tasks,
                "recent_results": recent_results,
                "status": "active"
            }
            
        except Exception as exc:
            self._logger.error(f"Error getting review status for {session_id}: {str(exc)}")
            raise
    
    async def get_review_results(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get review results for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of results to return
            
        Returns:
            List of review results
        """
        self.log_operation("get_review_results", session_id=session_id, limit=limit)
        
        try:
            results = self._review_results.get(session_id, [])
            
            # Return most recent results first
            sorted_results = sorted(results, key=lambda x: x.get("completed_at", ""), reverse=True)
            
            return sorted_results[:limit]
            
        except Exception as exc:
            self._logger.error(f"Error getting review results for {session_id}: {str(exc)}")
            raise
    
    async def optimize_session_context(
        self,
        session_id: str,
        optimization_strategy: str = "summary"
    ) -> Dict[str, Any]:
        """Optimize session context based on review results.
        
        Args:
            session_id: Session identifier
            optimization_strategy: Strategy for optimization (summary, compression, pruning)
            
        Returns:
            Dictionary containing optimization result
        """
        self.log_operation(
            "optimize_session_context",
            session_id=session_id,
            optimization_strategy=optimization_strategy
        )
        
        try:
            # Get session configuration
            config = self._session_configs.get(session_id)
            if not config:
                raise ValueError(f"Session review not initialized: {session_id}")
            
            # Get memory service for optimization
            memory_service = self._get_memory_service()
            
            if optimization_strategy == "summary":
                # Create memory summary
                window_start = 0
                window_end = config["current_tokens"]
                
                summary_result = await memory_service.create_memory_summary(
                    agent_id="session",
                    session_id=session_id,
                    window_range=(window_start, window_end)
                )
                
                optimization_result = {
                    "strategy": "summary",
                    "summary_id": summary_result["id"],
                    "window_range": (window_start, window_end),
                    "optimized_tokens": summary_result.get("event_count", 0),
                    "compression_ratio": 0.3  # Estimated
                }
                
            elif optimization_strategy == "compression":
                # Compress older context
                optimization_result = await self._compress_session_context(session_id, config)
                
            elif optimization_strategy == "pruning":
                # Prune less relevant context
                optimization_result = await self._prune_session_context(session_id, config)
                
            else:
                raise ValueError(f"Unsupported optimization strategy: {optimization_strategy}")
            
            # Update configuration with optimized token count
            optimized_tokens = optimization_result.get("optimized_tokens", config["current_tokens"])
            config["current_tokens"] = optimized_tokens
            
            return {
                "session_id": session_id,
                "optimization_strategy": optimization_strategy,
                "optimization_result": optimization_result,
                "previous_tokens": config["current_tokens"] + optimization_result.get("tokens_saved", 0),
                "optimized_tokens": optimized_tokens,
                "tokens_saved": optimization_result.get("tokens_saved", 0),
                "compression_ratio": optimization_result.get("compression_ratio", 0.0),
                "optimized_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error optimizing session context for {session_id}: {str(exc)}")
            raise
    
    async def get_review_statistics(
        self,
        time_range: Optional[Tuple[str, str]] = None
    ) -> Dict[str, Any]:
        """Get review statistics for analysis.
        
        Args:
            time_range: Optional time range filter
            
        Returns:
            Dictionary containing review statistics
        """
        self.log_operation("get_review_statistics", time_range=time_range)
        
        try:
            # Aggregate statistics across all sessions
            all_results = []
            all_configs = []
            
            for session_id, results in self._review_results.items():
                config = self._session_configs.get(session_id, {})
                
                for result in results:
                    if time_range:
                        result_time = datetime.fromisoformat(result.get("completed_at", ""))
                        start_time = datetime.fromisoformat(time_range[0])
                        end_time = datetime.fromisoformat(time_range[1])
                        
                        if not (start_time <= result_time <= end_time):
                            continue
                    
                    result["session_id"] = session_id
                    result["window_size"] = config.get("window_size")
                    all_results.append(result)
                
                if config:
                    config["session_id"] = session_id
                    all_configs.append(config)
            
            # Calculate statistics
            total_reviews = len(all_results)
            if total_reviews == 0:
                return {
                    "total_reviews": 0,
                    "time_range": time_range,
                    "generated_at": datetime.now(UTC).isoformat()
                }
            
            # Review type distribution
            review_types = {}
            for result in all_results:
                review_type = result.get("type", "unknown")
                review_types[review_type] = review_types.get(review_type, 0) + 1
            
            # Window size distribution
            window_sizes = {}
            for config in all_configs:
                window_size = config.get("window_size", "unknown")
                window_sizes[window_size] = window_sizes.get(window_size, 0) + 1
            
            # Average optimization metrics
            optimizations = [r for r in all_results if r.get("optimization_result")]
            avg_compression = 0.0
            if optimizations:
                compressions = [r.get("optimization_result", {}).get("compression_ratio", 0.0) for r in optimizations]
                avg_compression = sum(compressions) / len(compressions)
            
            return {
                "total_reviews": total_reviews,
                "review_types": review_types,
                "window_sizes": window_sizes,
                "total_sessions": len(all_configs),
                "average_compression_ratio": round(avg_compression, 3),
                "total_optimizations": len(optimizations),
                "time_range": time_range,
                "generated_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error getting review statistics: {str(exc)}")
            raise
    
    async def create_review_schedule(
        self,
        schedule_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create automated review schedule.
        
        Args:
            schedule_config: Schedule configuration
            
        Returns:
            Dictionary containing schedule creation result
        """
        self.log_operation("create_review_schedule")
        
        try:
            # Validate schedule configuration
            required_fields = ["name", "frequency", "enabled"]
            for field in required_fields:
                if field not in schedule_config:
                    raise ValueError(f"Missing required field: {field}")
            
            # Generate schedule ID
            schedule_id = f"schedule-{uuid4()}"
            
            # Create schedule
            schedule = {
                "id": schedule_id,
                "name": schedule_config["name"],
                "frequency": schedule_config["frequency"],  # hourly, daily, weekly
                "enabled": schedule_config["enabled"],
                "session_filter": schedule_config.get("session_filter", "all"),
                "window_size": schedule_config.get("window_size", "medium"),
                "optimization_strategy": schedule_config.get("optimization_strategy", "summary"),
                "created_at": datetime.now(UTC).isoformat(),
                "last_run": None,
                "next_run": self._calculate_next_run(schedule_config["frequency"])
            }
            
            # Store schedule (in a real implementation, this would be in database)
            # For now, we'll store in memory
            if not hasattr(self, '_schedules'):
                self._schedules = {}
            
            self._schedules[schedule_id] = schedule
            
            return {
                "schedule_id": schedule_id,
                "name": schedule_config["name"],
                "frequency": schedule_config["frequency"],
                "enabled": schedule_config["enabled"],
                "next_run": schedule["next_run"],
                "status": "created",
                "created_at": schedule["created_at"]
            }
            
        except Exception as exc:
            self._logger.error(f"Error creating review schedule: {str(exc)}")
            raise
    
    # Helper methods
    
    async def _execute_review(self, session_id: str, review_task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a review task."""
        try:
            # Update task status
            review_task["status"] = "executing"
            review_task["started_at"] = datetime.now(UTC).isoformat()
            
            # Get session configuration
            config = self._session_configs[session_id]
            
            # Perform review based on type
            if review_task["type"] == "automatic":
                # Automatic optimization
                optimization_result = await self.optimize_session_context(
                    session_id, 
                    config.get("optimization_strategy", "summary")
                )
            else:
                # Manual review - just analyze current state
                optimization_result = {
                    "strategy": "analysis",
                    "current_tokens": config["current_tokens"],
                    "token_limit": config["token_limit"],
                    "utilization": config["current_tokens"] / config["token_limit"]
                }
            
            # Complete review
            review_task["status"] = "completed"
            review_task["completed_at"] = datetime.now(UTC).isoformat()
            
            result = {
                "review_id": review_task["id"],
                "session_id": session_id,
                "type": review_task["type"],
                "optimization_result": optimization_result,
                "started_at": review_task["started_at"],
                "completed_at": review_task["completed_at"],
                "duration_ms": self._calculate_duration(review_task["started_at"], review_task["completed_at"])
            }
            
            # Store result
            self._review_results[session_id].append(result)
            
            return result
            
        except Exception as exc:
            review_task["status"] = "failed"
            review_task["error"] = str(exc)
            review_task["completed_at"] = datetime.now(UTC).isoformat()
            
            self._logger.error(f"Review execution failed: {str(exc)}")
            raise
    
    async def _compress_session_context(self, session_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Compress session context to save tokens."""
        # Placeholder implementation - would use actual compression algorithms
        return {
            "strategy": "compression",
            "original_tokens": config["current_tokens"],
            "compressed_tokens": int(config["current_tokens"] * 0.7),
            "tokens_saved": int(config["current_tokens"] * 0.3),
            "compression_ratio": 0.3
        }
    
    async def _prune_session_context(self, session_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Prune less relevant context from session."""
        # Placeholder implementation - would use relevance scoring
        return {
            "strategy": "pruning",
            "original_tokens": config["current_tokens"],
            "pruned_tokens": int(config["current_tokens"] * 0.8),
            "tokens_saved": int(config["current_tokens"] * 0.2),
            "compression_ratio": 0.2
        }
    
    def _calculate_next_run(self, frequency: str) -> str:
        """Calculate next run time for schedule."""
        now = datetime.now(UTC)
        
        if frequency == "hourly":
            next_run = now + timedelta(hours=1)
        elif frequency == "daily":
            next_run = now + timedelta(days=1)
        elif frequency == "weekly":
            next_run = now + timedelta(weeks=1)
        else:
            next_run = now + timedelta(hours=1)  # Default to hourly
        
        return next_run.isoformat()
    
    def _calculate_duration(self, start_time: str, end_time: str) -> int:
        """Calculate duration in milliseconds between two timestamps."""
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
        return int((end - start).total_seconds() * 1000)
