"""Enhanced Orchestrator - Chain Integration.

This module provides the Orchestrator with complete control over chain execution,
including dynamic chain selection, configuration, lifecycle management, and
monitoring.

The Orchestrator can:
1. Select chains based on task analysis
2. Configure chains dynamically  
3. Monitor chain execution in real-time
4. Chain multiple workflows together
5. Handle failures and fallbacks
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import asyncio
import time

from mindflow_backend.chains.factory import (
    get_chain_factory,
    ChainRequest,
    ChainMetadata,
    ChainCapability,
    ChainComplexity,
)
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.orchestrator import (
    ExecutionStrategy,
    AgentType,
    ChainType,
    OrchestratorDecision,
)
from mindflow_backend.schemas.orchestration.workflow import WorkflowPlan, WorkflowRouteDecision

_logger = get_logger(__name__)


@dataclass
class ChainSelectionCriteria:
    """Criteria for selecting appropriate chains."""
    
    task_type: str
    complexity_threshold: float = 0.5
    required_capabilities: Optional[List[ChainCapability]] = None
    exclude_chains: Optional[List[str]] = None
    max_execution_time: Optional[float] = None
    preferred_agents: Optional[List[AgentType]] = None


@dataclass
class ChainExecutionPlan:
    """Plan for chain execution with fallback options."""
    
    primary_chain: str
    primary_config: Dict[str, Any]
    fallback_chains: List[tuple[str, Dict[str, Any]]]  # (chain_id, config)
    execution_order: List[str]  # For chained executions
    timeout: float
    retry_attempts: int


class ChainOrchestrator:
    """Enhanced orchestrator integration for chain management."""
    
    def __init__(self) -> None:
        self.factory = get_chain_factory()
        self._execution_history: Dict[str, List[Dict[str, Any]]] = {}
        self._active_plans: Dict[str, ChainExecutionPlan] = {}
    
    async def select_chain_for_task(
        self,
        message: str,
        complexity_score: float,
        session_context: Optional[Dict[str, Any]] = None,
        criteria: Optional[ChainSelectionCriteria] = None,
    ) -> ChainExecutionPlan:
        """Select the most appropriate chain for a task."""
        
        # Analyze task requirements
        task_analysis = self._analyze_task_requirements(message, complexity_score)
        
        # Build selection criteria
        selection_criteria = criteria or ChainSelectionCriteria(
            task_type=task_analysis["task_type"],
            complexity_threshold=complexity_score,
        )
        
        # Find suitable chains
        suitable_chains = self._find_suitable_chains(selection_criteria, task_analysis)
        
        if not suitable_chains:
            raise ValueError("No suitable chains found for task")
        
        # Select primary chain
        primary_chain = suitable_chains[0]
        
        # Build execution plan with fallbacks
        plan = self._build_execution_plan(
            primary_chain=primary_chain,
            fallback_chains=suitable_chains[1:3],  # Top 2 fallbacks
            task_analysis=task_analysis,
            session_context=session_context or {},
        )
        
        _logger.info("chain_selected",
                    primary_chain=primary_chain.chain_id,
                    complexity=complexity_score,
                    fallback_count=len(plan.fallback_chains))
        
        return plan
    
    def _analyze_task_requirements(self, message: str, complexity_score: float) -> Dict[str, Any]:
        """Build task analysis from complexity score only — no keyword matching.

        The routing decision (which chain to use) was already made by the LLM
        in IntelligentRouter. This method only derives structural properties
        from the complexity score to configure chain execution parameters.
        """
        is_complex = complexity_score > 0.7

        return {
            "task_type": "coding",  # CHAIN strategy is only triggered for coding_task
            "requires_code": True,
            "requires_analysis": True,
            "requires_research": False,
            "requires_validation": is_complex,
            "is_multi_step": is_complex,
            "estimated_time": 120.0 if is_complex else 90.0,
        }
    
    def _find_suitable_chains(
        self,
        criteria: ChainSelectionCriteria,
        task_analysis: Dict[str, Any],
    ) -> List[ChainMetadata]:
        """Find chains that match the criteria."""
        
        # Determine required capabilities
        required_caps = []
        
        if task_analysis["requires_code"]:
            required_caps.append(ChainCapability.CODING)
        
        if task_analysis["requires_analysis"]:
            required_caps.append(ChainCapability.ANALYSIS)
        
        if task_analysis["requires_research"]:
            required_caps.append(ChainCapability.RESEARCH)
        
        if task_analysis["requires_validation"]:
            required_caps.append(ChainCapability.VALIDATION)
        
        if task_analysis["is_multi_step"]:
            required_caps.append(ChainCapability.MULTI_AGENT)
        
        if criteria.required_capabilities:
            required_caps.extend(criteria.required_capabilities)
        
        # Determine complexity
        if criteria.complexity_threshold > 0.8:
            complexity = ChainComplexity.EXTREME
        elif criteria.complexity_threshold > 0.6:
            complexity = ChainComplexity.HIGH
        elif criteria.complexity_threshold > 0.3:
            complexity = ChainComplexity.MEDIUM
        else:
            complexity = ChainComplexity.LOW
        
        # Find suitable chains
        suitable_chains = self.factory.registry.find_chains_for_task(
            task_type=criteria.task_type,
            complexity=complexity,
            required_capabilities=required_caps,
        )
        
        # Filter by exclusions
        if criteria.exclude_chains:
            suitable_chains = [
                chain for chain in suitable_chains
                if chain.chain_id not in criteria.exclude_chains
            ]
        
        # Filter by time constraints
        if criteria.max_execution_time:
            suitable_chains = [
                chain for chain in suitable_chains
                if chain.estimated_execution_time <= criteria.max_execution_time
            ]
        
        # Filter by preferred agents
        if criteria.preferred_agents:
            suitable_chains = [
                chain for chain in suitable_chains
                if any(agent in chain.required_agents for agent in criteria.preferred_agents)
            ]
        
        return suitable_chains
    
    def _build_execution_plan(
        self,
        primary_chain: ChainMetadata,
        fallback_chains: List[ChainMetadata],
        task_analysis: Dict[str, Any],
        session_context: Dict[str, Any],
    ) -> ChainExecutionPlan:
        """Build an execution plan with primary and fallback options."""
        
        # Build dynamic configuration
        primary_config = self._build_chain_config(primary_chain, task_analysis, session_context)
        fallback_configs = []
        
        for chain in fallback_chains:
            config = self._build_chain_config(chain, task_analysis, session_context)
            fallback_configs.append((chain.chain_id, config))
        
        # Determine timeout based on task complexity
        base_timeout = primary_chain.estimated_execution_time
        if task_analysis["is_multi_step"]:
            base_timeout *= 1.5
        
        timeout = min(base_timeout, primary_chain.timeout)
        
        return ChainExecutionPlan(
            primary_chain=primary_chain.chain_id,
            primary_config=primary_config,
            fallback_chains=fallback_configs,
            execution_order=[primary_chain.chain_id] + [c[0] for c in fallback_configs],
            timeout=timeout,
            retry_attempts=primary_chain.retry_attempts,
        )
    
    def _build_chain_config(
        self,
        chain: ChainMetadata,
        task_analysis: Dict[str, Any],
        session_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build dynamic configuration for a chain."""
        
        config = dict(chain.default_config)
        
        # Adjust based on task analysis
        if task_analysis["requires_analysis"] and "enable_deep_analysis" in config:
            config["enable_deep_analysis"] = True
        
        if task_analysis["is_multi_step"] and "enable_parallel_paths" in config:
            config["enable_parallel_paths"] = True
        
        # Adjust based on session context
        if "max_context_chars" in config and session_context.get("large_context"):
            config["max_context_chars"] = min(config["max_context_chars"], 4000)
        
        # Adjust confidence thresholds based on task criticality
        if session_context.get("high_priority"):
            config["confidence_threshold"] = config.get("confidence_threshold", 0.7) + 0.1
        
        return config
    
    async def execute_chain_plan(
        self,
        plan: ChainExecutionPlan,
        context: Dict[str, Any],
        execution_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a chain plan with fallback handling."""
        
        execution_id = execution_id or f"plan_exec_{int(time.time())}"
        start_time = time.time()
        
        _logger.info("chain_plan_execution_started",
                    execution_id=execution_id,
                    primary_chain=plan.primary_chain,
                    fallback_count=len(plan.fallback_chains))
        
        # Try primary chain first
        try:
            result = await self._execute_single_chain(
                chain_id=plan.primary_chain,
                config=plan.primary_config,
                context=context,
                timeout=plan.timeout,
                execution_id=f"{execution_id}_primary",
            )
            
            if not result.get("error"):
                self._record_execution_success(execution_id, plan, result, time.time() - start_time)
                return result
            
            _logger.warning("primary_chain_failed", 
                          execution_id=execution_id,
                          error=result.get("error"))
            
        except Exception as e:
            _logger.error("primary_chain_exception",
                         execution_id=execution_id,
                         error=str(e))
        
        # Try fallback chains
        for i, (fallback_chain_id, fallback_config) in enumerate(plan.fallback_chains):
            try:
                _logger.info("trying_fallback_chain",
                           execution_id=execution_id,
                           fallback_index=i + 1,
                           fallback_chain=fallback_chain_id)
                
                result = await self._execute_single_chain(
                    chain_id=fallback_chain_id,
                    config=fallback_config,
                    context=context,
                    timeout=plan.timeout * 0.8,  # Reduce timeout for fallbacks
                    execution_id=f"{execution_id}_fallback_{i + 1}",
                )
                
                if not result.get("error"):
                    self._record_execution_success(execution_id, plan, result, time.time() - start_time, fallback_used=i + 1)
                    return result
                
            except Exception as e:
                _logger.error("fallback_chain_failed",
                             execution_id=execution_id,
                             fallback_chain=fallback_chain_id,
                             error=str(e))
                continue
        
        # All chains failed
        execution_time = time.time() - start_time
        self._record_execution_failure(execution_id, plan, execution_time)
        
        return {
            "response": "",
            "error": f"All chains failed. Tried: {plan.execution_order}",
            "execution_metadata": {
                "execution_id": execution_id,
                "execution_time": execution_time,
                "chains_attempted": plan.execution_order,
                "all_failed": True,
            }
        }
    
    async def _execute_single_chain(
        self,
        chain_id: str,
        config: Dict[str, Any],
        context: Dict[str, Any],
        timeout: float,
        execution_id: str,
    ) -> Dict[str, Any]:
        """Execute a single chain with timeout."""
        
        request = ChainRequest(
            chain_id=chain_id,
            config=config,
            execution_context=context,
            request_id=execution_id,
        )
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self.factory.execute_chain(request, context),
                timeout=timeout
            )
            
            return result
            
        except asyncio.TimeoutError:
            return {
                "response": "",
                "error": f"Chain execution timed out after {timeout}s",
                "execution_metadata": {"timeout": True, "timeout_limit": timeout},
            }
    
    def _record_execution_success(
        self,
        execution_id: str,
        plan: ChainExecutionPlan,
        result: Dict[str, Any],
        execution_time: float,
        fallback_used: Optional[int] = None,
    ) -> None:
        """Record successful execution."""
        
        execution_record = {
            "execution_id": execution_id,
            "plan": plan,
            "result": result,
            "execution_time": execution_time,
            "fallback_used": fallback_used,
            "timestamp": time.time(),
            "success": True,
        }
        
        session_id = result.get("execution_metadata", {}).get("session_id", "unknown")
        if session_id not in self._execution_history:
            self._execution_history[session_id] = []
        
        self._execution_history[session_id].append(execution_record)
        
        _logger.info("chain_plan_execution_success",
                    execution_id=execution_id,
                    execution_time=execution_time,
                    fallback_used=fallback_used)
    
    def _record_execution_failure(
        self,
        execution_id: str,
        plan: ChainExecutionPlan,
        execution_time: float,
    ) -> None:
        """Record failed execution."""
        
        execution_record = {
            "execution_id": execution_id,
            "plan": plan,
            "execution_time": execution_time,
            "timestamp": time.time(),
            "success": False,
            "chains_attempted": plan.execution_order,
        }
        
        session_id = "unknown"
        if session_id not in self._execution_history:
            self._execution_history[session_id] = []
        
        self._execution_history[session_id].append(execution_record)
        
        _logger.error("chain_plan_execution_failure",
                      execution_id=execution_id,
                      execution_time=execution_time)
    
    def get_execution_history(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get execution history for analysis."""
        
        if session_id:
            return {"session_id": session_id, "executions": self._execution_history.get(session_id, [])}
        
        return {"sessions": dict(self._execution_history)}
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for chain executions."""
        
        all_executions = []
        for session_executions in self._execution_history.values():
            all_executions.extend(session_executions)
        
        if not all_executions:
            return {"total_executions": 0}
        
        successful_executions = [e for e in all_executions if e["success"]]
        failed_executions = [e for e in all_executions if not e["success"]]
        
        stats = {
            "total_executions": len(all_executions),
            "successful_executions": len(successful_executions),
            "failed_executions": len(failed_executions),
            "success_rate": len(successful_executions) / len(all_executions),
            "average_execution_time": sum(e["execution_time"] for e in all_executions) / len(all_executions),
            "fallback_usage_rate": sum(1 for e in successful_executions if e.get("fallback_used")) / len(successful_executions) if successful_executions else 0,
        }
        
        # Chain-specific stats
        chain_stats = {}
        for execution in all_executions:
            chain_id = execution["plan"].primary_chain
            if chain_id not in chain_stats:
                chain_stats[chain_id] = {"total": 0, "successful": 0, "failed": 0}
            
            chain_stats[chain_id]["total"] += 1
            if execution["success"]:
                chain_stats[chain_id]["successful"] += 1
            else:
                chain_stats[chain_id]["failed"] += 1
        
        stats["chain_performance"] = chain_stats
        
        return stats


# Global chain orchestrator instance
_chain_orchestrator = ChainOrchestrator()


def get_chain_orchestrator() -> ChainOrchestrator:
    """Get the global chain orchestrator instance."""
    return _chain_orchestrator


def build_workflow_plan(
    *,
    message: str,
    route: WorkflowRouteDecision,
    folder_path: str | None = None,
) -> WorkflowPlan:
    """Resolve router output into the final executor plan.

    The planner is the single authoritative place where chain variants are
    selected. Executors consume the returned plan without re-routing.
    """
    plan = WorkflowPlan(route=route, tools=list(route.tools))

    if route.execution_strategy != ExecutionStrategy.CHAIN:
        return plan

    if folder_path and route.agent_role == AgentType.ANALYST:
        plan.chain_id = "file_analysis"
        plan.chain_type = ChainType.FILE_ANALYSIS
        plan.planner_rule = "workspace_analysis"
        return plan

    if route.agent_role == AgentType.CODER:
        plan.chain_id = "coding_task"
        plan.chain_type = ChainType.CODING_TASK
        plan.planner_rule = "implementation_pipeline"
        return plan

    plan.chain_id = "analysis_task"
    plan.chain_type = ChainType.ANALYSIS_TASK
    plan.planner_rule = "analysis_pipeline"
    return plan


def plan_orchestrator_execution(
    *,
    message: str,
    route: WorkflowRouteDecision,
    folder_path: str | None = None,
) -> OrchestratorDecision:
    """Compatibility adapter returning the executor-facing decision payload."""
    return build_workflow_plan(
        message=message,
        route=route,
        folder_path=folder_path,
    ).to_decision()


# Integration function for orchestrator graph
def _resolve_chain_id(chain_id: Optional[str], complexity_score: float) -> str:
    """Resolve the final chain_id to execute, including automatic variant selection.

    For `file_analysis`, automatically upgrades to a more capable variant based
    on complexity_score — the LLM only needs to say "file_analysis" and the
    system picks the right implementation:

      complexity < 0.45  → file_analysis            (sequential, simple)
      complexity < 0.65  → conditional_file_analysis (iterative, asks for more files)
      complexity >= 0.65 → parallel_file_analysis    (parallel scopes, large codebases)

    All other chain_ids are passed through unchanged.
    """
    if chain_id == "file_analysis":
        if complexity_score >= 0.65:
            _logger.info("chain_variant_selected", variant="parallel_file_analysis", score=complexity_score)
            return "parallel_file_analysis"
        if complexity_score >= 0.45:
            _logger.info("chain_variant_selected", variant="conditional_file_analysis", score=complexity_score)
            return "conditional_file_analysis"
        _logger.info("chain_variant_selected", variant="file_analysis", score=complexity_score)
        return "file_analysis"

    return chain_id or "coding_task"


async def execute_chain_with_intelligence(
    message: str,
    complexity_score: float,
    context: Dict[str, Any],
    session_id: Optional[str] = None,
    chain_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a chain using the LLM-decided chain_id (no keyword selection).

    The chain_id is decided upstream by IntelligentRouter's LLM call.
    For file_analysis chains, the specific variant is chosen automatically
    from complexity_score so the LLM doesn't need to know about variants.
    """
    resolved_id = _resolve_chain_id(chain_id, complexity_score)

    orchestrator = get_chain_orchestrator()
    criteria = ChainSelectionCriteria(
        task_type=resolved_id,
        complexity_threshold=complexity_score,
    )

    plan = await orchestrator.select_chain_for_task(
        message=message,
        complexity_score=complexity_score,
        session_context={"session_id": session_id} if session_id else None,
        criteria=criteria,
    )

    result = await orchestrator.execute_chain_plan(
        plan=plan,
        context=context,
        execution_id=f"orchestrator_{session_id}_{int(time.time())}" if session_id else None,
    )

    return result
