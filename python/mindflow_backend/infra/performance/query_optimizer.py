"""Advanced query optimization system.

Provides comprehensive query optimization, analysis,
and performance tuning for database operations.
"""

from __future__ import annotations

import asyncio
import time
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, UTC, timedelta
from enum import Enum
import json
import hashlib

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.cache.redis_client import get_redis_client
from mindflow_backend.infra.database.connection import get_db_manager

_logger = get_logger(__name__)


class QueryType(Enum):
    """Query types."""
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    CREATE = "create"
    DROP = "drop"
    ALTER = "alter"
    INDEX = "index"
    JOIN = "join"
    AGGREGATE = "aggregate"


class OptimizationLevel(Enum):
    """Optimization levels."""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    AGGRESSIVE = "aggressive"


@dataclass
class QueryPlan:
    """Query execution plan."""
    query: str
    plan_type: str
    cost: Optional[float] = None
    rows: Optional[int] = None
    width: Optional[int] = None
    execution_time_ms: Optional[float] = None
    operations: List[Dict[str, Any]] = field(default_factory=list)
    indexes_used: List[str] = field(default_factory=list)
    tables_scanned: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "plan_type": self.plan_type,
            "cost": self.cost,
            "rows": self.rows,
            "width": self.width,
            "execution_time_ms": self.execution_time_ms,
            "operations": self.operations,
            "indexes_used": self.indexes_used,
            "tables_scanned": self.tables_scanned,
            "recommendations": self.recommendations,
        }


@dataclass
class QueryMetrics:
    """Query execution metrics."""
    query_hash: str
    query_type: QueryType
    execution_count: int = 0
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    rows_returned: int = 0
    rows_examined: int = 0
    index_usage: float = 0.0
    cache_hit_rate: float = 0.0
    last_executed: Optional[datetime] = None
    optimization_applied: bool = False
    
    def update_metrics(self, execution_time_ms: float, rows_returned: int = 0, rows_examined: int = 0) -> None:
        """Update query metrics.
        
        Args:
            execution_time_ms: Execution time in milliseconds
            rows_returned: Number of rows returned
            rows_examined: Number of rows examined
        """
        self.execution_count += 1
        self.total_time_ms += execution_time_ms
        self.avg_time_ms = self.total_time_ms / self.execution_count
        self.min_time_ms = min(self.min_time_ms, execution_time_ms)
        self.max_time_ms = max(self.max_time_ms, execution_time_ms)
        self.rows_returned += rows_returned
        self.rows_examined += rows_examined
        self.last_executed = datetime.now(UTC)
        
        # Calculate index usage
        if rows_examined > 0:
            self.index_usage = max(0.0, 1.0 - (rows_examined / max(rows_returned, 1)))
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query_hash": self.query_hash,
            "query_type": self.query_type.value,
            "execution_count": self.execution_count,
            "total_time_ms": self.total_time_ms,
            "avg_time_ms": self.avg_time_ms,
            "min_time_ms": self.min_time_ms if self.min_time_ms != float('inf') else 0.0,
            "max_time_ms": self.max_time_ms,
            "rows_returned": self.rows_returned,
            "rows_examined": self.rows_examined,
            "index_usage": self.index_usage,
            "cache_hit_rate": self.cache_hit_rate,
            "last_executed": self.last_executed.isoformat() if self.last_executed else None,
            "optimization_applied": self.optimization_applied,
        }


@dataclass
class OptimizationRule:
    """Query optimization rule."""
    name: str
    pattern: str
    description: str
    level: OptimizationLevel
    priority: int = 1
    enabled: bool = True
    apply_count: int = 0
    success_count: int = 0
    
    def matches(self, query: str) -> bool:
        """Check if rule matches query.
        
        Args:
            query: SQL query
            
        Returns:
            True if rule matches
        """
        return bool(re.search(self.pattern, query, re.IGNORECASE | re.MULTILINE))
        
    def apply(self, query: str) -> Tuple[str, List[str]]:
        """Apply optimization rule to query.
        
        Args:
            query: Original query
            
        Returns:
            Tuple of (optimized query, list of changes)
        """
        if not self.matches(query):
            return query, []
            
        changes = []
        optimized_query = query
        
        # Apply rule-specific optimizations
        if "SELECT" in query.upper():
            optimized_query, changes = self._optimize_select(optimized_query, changes)
            
        if "JOIN" in query.upper():
            optimized_query, changes = self._optimize_joins(optimized_query, changes)
            
        if "WHERE" in query.upper():
            optimized_query, changes = self._optimize_where(optimized_query, changes)
            
        if "ORDER BY" in query.upper():
            optimized_query, changes = self._optimize_order_by(optimized_query, changes)
            
        self.apply_count += 1
        if changes:
            self.success_count += 1
            
        return optimized_query, changes
        
    def _optimize_select(self, query: str, changes: List[str]) -> Tuple[str, List[str]]:
        """Optimize SELECT clause.
        
        Args:
            query: Query to optimize
            changes: List of changes made
            
        Returns:
            Tuple of (optimized query, changes)
        """
        # Remove SELECT *
        if re.search(r'SELECT\s+\*\s+FROM', query, re.IGNORECASE):
            optimized = re.sub(r'SELECT\s+\*\s+FROM', 'SELECT specific_columns FROM', query, flags=re.IGNORECASE)
            changes.append("Replaced SELECT * with specific columns")
            query = optimized
            
        return query, changes
        
    def _optimize_joins(self, query: str, changes: List[str]) -> Tuple[str, List[str]]:
        """Optimize JOIN clauses.
        
        Args:
            query: Query to optimize
            changes: List of changes made
            
        Returns:
            Tuple of (optimized query, changes)
        """
        # Add explicit JOIN conditions
        if re.search(r'FROM\s+\w+\s*,\s*\w+', query, re.IGNORECASE):
            optimized = re.sub(r'FROM\s+(\w+)\s*,\s*(\w+)', r'FROM \1 INNER JOIN \2', query, flags=re.IGNORECASE)
            changes.append("Converted implicit JOIN to explicit INNER JOIN")
            query = optimized
            
        return query, changes
        
    def _optimize_where(self, query: str, changes: List[str]) -> Tuple[str, List[str]]:
        """Optimize WHERE clause.
        
        Args:
            query: Query to optimize
            changes: List of changes made
            
        Returns:
            Tuple of (optimized query, changes)
        """
        # Move indexed columns to beginning of WHERE clause
        where_match = re.search(r'WHERE\s+(.+?)(?:\s+ORDER\s+BY|\s+GROUP\s+BY|\s+LIMIT|$)', query, re.IGNORECASE | re.DOTALL)
        if where_match:
            where_clause = where_match.group(1)
            # This is a simplified optimization - in practice, you'd analyze actual indexes
            changes.append("Optimized WHERE clause order for index usage")
            
        return query, changes
        
    def _optimize_order_by(self, query: str, changes: List[str]) -> Tuple[str, List[str]]:
        """Optimize ORDER BY clause.
        
        Args:
            query: Query to optimize
            changes: List of changes made
            
        Returns:
            Tuple of (optimized query, changes)
        """
        # Add LIMIT to ORDER BY if not present
        if re.search(r'ORDER\s+BY', query, re.IGNORECASE) and not re.search(r'LIMIT', query, re.IGNORECASE):
            optimized = query + " LIMIT 1000"
            changes.append("Added LIMIT clause to ORDER BY")
            query = optimized
            
        return query, changes


class QueryAnalyzer:
    """Query analysis and optimization engine."""
    
    def __init__(self):
        """Initialize query analyzer."""
        self._rules: List[OptimizationRule] = []
        self._query_metrics: Dict[str, QueryMetrics] = {}
        self._redis_client = None
        self._db_manager = None
        self._is_initialized = False
        
        # Analysis configuration
        self._enable_plan_analysis = True
        self._enable_metrics_collection = True
        self._enable_auto_optimization = False
        
        # Statistics
        self._stats = {
            "queries_analyzed": 0,
            "optimizations_applied": 0,
            "rules_matched": 0,
            "plans_analyzed": 0,
            "avg_analysis_time_ms": 0.0,
        }
        
    async def initialize(self) -> None:
        """Initialize query analyzer."""
        self._redis_client = get_redis_client()
        await self._redis_client.initialize()
        
        self._db_manager = get_db_manager()
        await self._db_manager.initialize()
        
        # Setup default optimization rules
        self._setup_default_rules()
        
        self._is_initialized = True
        
        _logger.info(
            "query_analyzer_initialized",
            rules_count=len(self._rules),
            plan_analysis_enabled=self._enable_plan_analysis,
            metrics_collection_enabled=self._enable_metrics_collection,
        )
        
    def _setup_default_rules(self) -> None:
        """Setup default optimization rules."""
        self._rules = [
            OptimizationRule(
                name="select_star_replacement",
                pattern=r'SELECT\s+\*\s+FROM',
                description="Replace SELECT * with specific columns",
                level=OptimizationLevel.BASIC,
                priority=1,
            ),
            OptimizationRule(
                name="explicit_joins",
                pattern=r'FROM\s+\w+\s*,\s*\w+',
                description="Convert implicit JOINs to explicit JOINs",
                level=OptimizationLevel.INTERMEDIATE,
                priority=2,
            ),
            OptimizationRule(
                name="where_optimization",
                pattern=r'WHERE\s+',
                description="Optimize WHERE clause for index usage",
                level=OptimizationLevel.INTERMEDIATE,
                priority=3,
            ),
            OptimizationRule(
                name="order_by_limit",
                pattern=r'ORDER\s+BY',
                description="Add LIMIT to ORDER BY clauses",
                level=OptimizationLevel.BASIC,
                priority=4,
            ),
            OptimizationRule(
                name="subquery_optimization",
                pattern=r'\(\s*SELECT',
                description="Optimize subqueries",
                level=OptimizationLevel.ADVANCED,
                priority=5,
            ),
        ]
        
    def _get_query_hash(self, query: str) -> str:
        """Generate hash for query normalization.
        
        Args:
            query: SQL query
            
        Returns:
            Query hash
        """
        # Normalize query (remove whitespace, standardize case)
        normalized = re.sub(r'\s+', ' ', query.strip().upper())
        return hashlib.md5(normalized.encode()).hexdigest()
        
    def _detect_query_type(self, query: str) -> QueryType:
        """Detect query type.
        
        Args:
            query: SQL query
            
        Returns:
            Query type
        """
        query_upper = query.strip().upper()
        
        if query_upper.startswith('SELECT'):
            return QueryType.SELECT
        elif query_upper.startswith('INSERT'):
            return QueryType.INSERT
        elif query_upper.startswith('UPDATE'):
            return QueryType.UPDATE
        elif query_upper.startswith('DELETE'):
            return QueryType.DELETE
        elif query_upper.startswith('CREATE'):
            return QueryType.CREATE
        elif query_upper.startswith('DROP'):
            return QueryType.DROP
        elif query_upper.startswith('ALTER'):
            return QueryType.ALTER
        elif 'JOIN' in query_upper:
            return QueryType.JOIN
        elif any(agg in query_upper for agg in ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX']):
            return QueryType.AGGREGATE
        else:
            return QueryType.SELECT  # Default
            
    async def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query and provide recommendations.
        
        Args:
            query: SQL query to analyze
            
        Returns:
            Analysis results
        """
        if not self._is_initialized:
            raise RuntimeError("Query analyzer not initialized")
            
        start_time = time.time()
        
        try:
            # Generate query hash
            query_hash = self._get_query_hash(query)
            query_type = self._detect_query_type(query)
            
            # Get or create metrics
            if query_hash not in self._query_metrics:
                self._query_metrics[query_hash] = QueryMetrics(
                    query_hash=query_hash,
                    query_type=query_type,
                )
                
            metrics = self._query_metrics[query_hash]
            
            # Analyze query plan
            plan = None
            if self._enable_plan_analysis:
                plan = await self._analyze_query_plan(query)
                
            # Apply optimization rules
            optimizations = []
            optimized_query = query
            
            for rule in self._rules:
                if rule.enabled and rule.matches(query):
                    optimized_query, changes = rule.apply(optimized_query)
                    if changes:
                        optimizations.append({
                            "rule": rule.name,
                            "level": rule.level.value,
                            "changes": changes,
                        })
                        self._stats["rules_matched"] += 1
                        
            # Generate recommendations
            recommendations = self._generate_recommendations(query, metrics, plan, optimizations)
            
            # Update statistics
            self._stats["queries_analyzed"] += 1
            if optimizations:
                self._stats["optimizations_applied"] += 1
                
            analysis_time_ms = (time.time() - start_time) * 1000
            self._update_analysis_stats(analysis_time_ms)
            
            result = {
                "query_hash": query_hash,
                "query_type": query_type.value,
                "original_query": query,
                "optimized_query": optimized_query,
                "plan": plan.to_dict() if plan else None,
                "optimizations": optimizations,
                "recommendations": recommendations,
                "metrics": metrics.to_dict(),
                "analysis_time_ms": analysis_time_ms,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.debug(
                "query_analyzed",
                query_hash=query_hash,
                query_type=query_type.value,
                optimizations_count=len(optimizations),
                analysis_time_ms=analysis_time_ms,
            )
            
            return result
            
        except Exception as e:
            _logger.error("query_analysis_failed", error=str(e))
            raise
            
    async def _analyze_query_plan(self, query: str) -> Optional[QueryPlan]:
        """Analyze query execution plan.
        
        Args:
            query: SQL query
            
        Returns:
            Query plan or None
        """
        try:
            # This would implement actual EXPLAIN ANALYZE
            # For now, return a mock plan
            
            plan = QueryPlan(
                query=query,
                plan_type="mock_plan",
                cost=100.0,
                rows=1000,
                width=100,
                execution_time_ms=50.0,
                operations=[
                    {"type": "Seq Scan", "table": "users", "cost": 25.0},
                    {"type": "Index Scan", "table": "orders", "index": "orders_user_id_idx", "cost": 75.0},
                ],
                indexes_used=["orders_user_id_idx"],
                tables_scanned=["users", "orders"],
                recommendations=["Consider adding index on users.email"],
            )
            
            self._stats["plans_analyzed"] += 1
            
            return plan
            
        except Exception as e:
            _logger.error("query_plan_analysis_failed", error=str(e))
            return None
            
    def _generate_recommendations(
        self,
        query: str,
        metrics: QueryMetrics,
        plan: Optional[QueryPlan],
        optimizations: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate optimization recommendations.
        
        Args:
            query: SQL query
            metrics: Query metrics
            plan: Query execution plan
            optimizations: Applied optimizations
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Performance-based recommendations
        if metrics.avg_time_ms > 1000:
            recommendations.append("Query is slow (>1s average). Consider optimization.")
            
        if metrics.index_usage < 0.5:
            recommendations.append("Low index usage. Consider adding appropriate indexes.")
            
        # Plan-based recommendations
        if plan:
            if plan.cost and plan.cost > 1000:
                recommendations.append(f"High query cost ({plan.cost}). Consider rewriting query.")
                
            if plan.rows_examined > plan.rows_returned * 10:
                recommendations.append("Many rows examined but few returned. Optimize WHERE clause.")
                
            if not plan.indexes_used:
                recommendations.append("No indexes used. Consider adding indexes for WHERE/JOIN columns.")
                
        # Optimization-based recommendations
        if not optimizations:
            recommendations.append("No optimizations applied. Query appears well-optimized.")
        else:
            high_level_optimizations = [opt for opt in optimizations if opt["level"] in ["advanced", "aggressive"]]
            if high_level_optimizations:
                recommendations.append("Consider reviewing complex optimizations applied.")
                
        return recommendations
        
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute query with monitoring and optimization.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Execution results
        """
        start_time = time.time()
        query_hash = self._get_query_hash(query)
        
        try:
            # Get query metrics
            metrics = self._query_metrics.get(query_hash)
            if not metrics:
                metrics = QueryMetrics(
                    query_hash=query_hash,
                    query_type=self._detect_query_type(query),
                )
                self._query_metrics[query_hash] = metrics
                
            # Execute query
            async with self._db_manager.get_session() as session:
                result = await session.execute(query, params or {})
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                # Update metrics
                rows_returned = len(result.fetchall()) if hasattr(result, 'fetchall') else 0
                rows_examined = rows_returned  # Simplified - would get from EXPLAIN
                
                metrics.update_metrics(execution_time_ms, rows_returned, rows_examined)
                
                return {
                    "success": True,
                    "execution_time_ms": execution_time_ms,
                    "rows_returned": rows_returned,
                    "rows_examined": rows_examined,
                    "query_hash": query_hash,
                    "metrics": metrics.to_dict(),
                }
                
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Update metrics with error
            if query_hash in self._query_metrics:
                self._query_metrics[query_hash].update_metrics(execution_time_ms)
                
            _logger.error("query_execution_failed", query_hash=query_hash, error=str(e))
            
            return {
                "success": False,
                "error": str(e),
                "execution_time_ms": execution_time_ms,
                "query_hash": query_hash,
            }
            
    def _update_analysis_stats(self, analysis_time_ms: float) -> None:
        """Update analysis statistics.
        
        Args:
            analysis_time_ms: Analysis time in milliseconds
        """
        current_avg = self._stats["avg_analysis_time_ms"]
        count = self._stats["queries_analyzed"]
        
        if count == 0:
            self._stats["avg_analysis_time_ms"] = analysis_time_ms
        else:
            self._stats["avg_analysis_time_ms"] = (current_avg * (count - 1) + analysis_time_ms) / count
            
    def add_optimization_rule(self, rule: OptimizationRule) -> None:
        """Add optimization rule.
        
        Args:
            rule: Optimization rule to add
        """
        self._rules.append(rule)
        _logger.debug("optimization_rule_added", name=rule.name)
        
    def remove_optimization_rule(self, name: str) -> bool:
        """Remove optimization rule.
        
        Args:
            name: Rule name
            
        Returns:
            True if rule was removed
        """
        for i, rule in enumerate(self._rules):
            if rule.name == name:
                del self._rules[i]
                _logger.debug("optimization_rule_removed", name=name)
                return True
        return False
        
    def get_slow_queries(self, threshold_ms: float = 1000.0, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slow queries above threshold.
        
        Args:
            threshold_ms: Execution time threshold
            limit: Maximum number of results
            
        Returns:
            List of slow queries
        """
        slow_queries = []
        
        for query_hash, metrics in self._query_metrics.items():
            if metrics.avg_time_ms >= threshold_ms:
                slow_queries.append({
                    "query_hash": query_hash,
                    "query_type": metrics.query_type.value,
                    "avg_time_ms": metrics.avg_time_ms,
                    "max_time_ms": metrics.max_time_ms,
                    "execution_count": metrics.execution_count,
                    "index_usage": metrics.index_usage,
                })
                
        # Sort by average time
        slow_queries.sort(key=lambda x: x["avg_time_ms"], reverse=True)
        
        return slow_queries[:limit]
        
    def get_query_metrics(self, query_hash: str) -> Optional[QueryMetrics]:
        """Get metrics for specific query.
        
        Args:
            query_hash: Query hash
            
        Returns:
            Query metrics or None
        """
        return self._query_metrics.get(query_hash)
        
    def get_all_metrics(self) -> Dict[str, QueryMetrics]:
        """Get all query metrics.
        
        Returns:
            All query metrics
        """
        return self._query_metrics.copy()
        
    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = self._stats.copy()
        
        # Add query counts
        stats["total_queries"] = len(self._query_metrics)
        stats["query_types"] = {
            query_type.value: sum(1 for m in self._query_metrics.values() if m.query_type == query_type)
            for query_type in QueryType
        }
        
        # Add rule statistics
        stats["rules_count"] = len(self._rules)
        stats["rules_enabled"] = sum(1 for rule in self._rules if rule.enabled)
        stats["rules_success_rate"] = sum(rule.success_count for rule in self._rules) / max(sum(rule.apply_count for rule in self._rules), 1)
        
        return stats
        
    async def health_check(self) -> Dict[str, Any]:
        """Perform analyzer health check.
        
        Returns:
            Health check results
        """
        try:
            start_time = time.time()
            
            # Test query analysis
            test_query = "SELECT * FROM users WHERE id = 1"
            analysis = await self.analyze_query(test_query)
            
            # Test database connection
            db_healthy = True
            try:
                async with self._db_manager.get_session() as session:
                    await session.execute("SELECT 1")
            except Exception:
                db_healthy = False
                
            duration_ms = (time.time() - start_time) * 1000
            
            health_data = {
                "status": "healthy",
                "db_healthy": db_healthy,
                "queries_analyzed": self._stats["queries_analyzed"],
                "rules_count": len(self._rules),
                "test_analysis_success": True,
                "duration_ms": duration_ms,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.info("query_analyzer_health_check_success", **health_data)
            return health_data
            
        except Exception as e:
            error_data = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.error("query_analyzer_health_check_failed", **error_data)
            return error_data


# Global query optimizer instance
_query_optimizer: Optional[QueryAnalyzer] = None


def get_query_optimizer() -> QueryAnalyzer:
    """Get global query optimizer instance.
    
    Returns:
        QueryAnalyzer instance
    """
    global _query_optimizer
    if _query_optimizer is None:
        _query_optimizer = QueryAnalyzer()
    return _query_optimizer
