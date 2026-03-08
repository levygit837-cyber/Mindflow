"""Chain Manager - Central management for chain instances.

This manager provides a centralized way to create, manage, and execute
chains of different types with proper lifecycle management.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, Union
from datetime import datetime
import asyncio

from mindflow_backend.chains.base.chain import BaseChain, ChainType, ChainStatus
from mindflow_backend.chains.builders.sequential_builder import SequentialChainBuilder
from mindflow_backend.chains.builders.conditional_builder import ConditionalChainBuilder
from mindflow_backend.chains.templates.research_chain import ResearchChain
from mindflow_backend.chains.templates.coding_chain import CodingChain
from mindflow_backend.chains.base.types import ChainConfig, ExecutionContext


class ChainManager:
    """Central manager for chain instances and lifecycle."""
    
    def __init__(self) -> None:
        self._chains: Dict[str, BaseChain] = {}
        self._chain_templates: Dict[str, Type] = {}
        self._chain_history: List[Dict[str, Any]] = []
        self._execution_stats: Dict[str, Dict[str, Any]] = {}
        
        # Register built-in templates
        self._register_builtin_templates()
    
    def _register_builtin_templates(self) -> None:
        """Register built-in chain templates."""
        self._chain_templates.update({
            "research": ResearchChain,
            "coding": CodingChain,
        })
    
    def create_chain(
        self,
        chain_id: str,
        chain_type: ChainType,
        config: Optional[ChainConfig] = None,
        **kwargs
    ) -> BaseChain:
        """Create a new chain instance.
        
        Args:
            chain_id: Unique identifier for the chain
            chain_type: Type of chain to create
            config: Optional chain configuration
            **kwargs: Additional parameters for chain creation
            
        Returns:
            Created chain instance
            
        Raises:
            ValueError: If chain_id already exists or chain_type unsupported
        """
        if chain_id in self._chains:
            raise ValueError(f"Chain with ID '{chain_id}' already exists")
        
        # Create chain based on type
        if chain_type == ChainType.SEQUENTIAL:
            builder = SequentialChainBuilder(chain_id)
            # Apply configuration
            if config:
                builder = builder.with_config(**config.dict())
            chain = builder.build()
            
        elif chain_type == ChainType.CONDITIONAL:
            builder = ConditionalChainBuilder(chain_id)
            if config:
                builder = builder.with_config(**config.dict())
            chain = builder.build()
            
        elif chain_type == ChainType.PARALLEL:
            # TODO: Implement ParallelChainBuilder
            raise NotImplementedError("Parallel chains not yet implemented")
            
        elif chain_type == ChainType.LOOPING:
            # TODO: Implement LoopingChainBuilder
            raise NotImplementedError("Looping chains not yet implemented")
            
        else:
            raise ValueError(f"Unsupported chain type: {chain_type}")
        
        # Store chain
        self._chains[chain_id] = chain
        
        # Initialize stats
        self._execution_stats[chain_id] = {
            "created_at": datetime.now(),
            "executions": 0,
            "successes": 0,
            "failures": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0
        }
        
        return chain
    
    def create_template_chain(
        self,
        chain_id: str,
        template_name: str,
        **template_kwargs
    ) -> BaseChain:
        """Create a chain from a predefined template.
        
        Args:
            chain_id: Unique identifier for the chain
            template_name: Name of the template to use
            **template_kwargs: Template-specific parameters
            
        Returns:
            Created chain instance
            
        Raises:
            ValueError: If template not found or chain_id already exists
        """
        if chain_id in self._chains:
            raise ValueError(f"Chain with ID '{chain_id}' already exists")
        
        if template_name not in self._chain_templates:
            raise ValueError(f"Template '{template_name}' not found. Available: {list(self._chain_templates.keys())}")
        
        # Create chain from template
        template_class = self._chain_templates[template_name]
        template_instance = template_class(chain_id=chain_id, **template_kwargs)
        chain = template_instance.build()
        
        # Store chain
        self._chains[chain_id] = chain
        
        # Initialize stats
        self._execution_stats[chain_id] = {
            "created_at": datetime.now(),
            "template_used": template_name,
            "template_params": template_kwargs,
            "executions": 0,
            "successes": 0,
            "failures": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0
        }
        
        return chain
    
    def get_chain(self, chain_id: str) -> Optional[BaseChain]:
        """Get a chain instance by ID.
        
        Args:
            chain_id: ID of the chain to retrieve
            
        Returns:
            Chain instance or None if not found
        """
        return self._chains.get(chain_id)
    
    def list_chains(self) -> List[Dict[str, Any]]:
        """List all registered chains with their metadata.
        
        Returns:
            List of chain information
        """
        chains_info = []
        
        for chain_id, chain in self._chains.items():
            stats = self._execution_stats.get(chain_id, {})
            
            chains_info.append({
                "chain_id": chain_id,
                "chain_type": chain.config.chain_type.value,
                "status": chain.status.value,
                "created_at": stats.get("created_at"),
                "executions": stats.get("executions", 0),
                "success_rate": self._calculate_success_rate(stats),
                "average_execution_time": stats.get("average_execution_time", 0.0),
                "template_used": stats.get("template_used"),
            })
        
        return chains_info
    
    async def execute_chain(
        self,
        chain_id: str,
        initial_context: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Execute a chain by ID.
        
        Args:
            chain_id: ID of the chain to execute
            initial_context: Initial context for execution
            timeout: Optional timeout for execution
            
        Returns:
            Execution result context
            
        Raises:
            ValueError: If chain not found
            TimeoutError: If execution times out
        """
        chain = self.get_chain(chain_id)
        if not chain:
            raise ValueError(f"Chain '{chain_id}' not found")
        
        # Update stats
        stats = self._execution_stats[chain_id]
        stats["executions"] += 1
        stats["last_execution"] = datetime.now()
        
        # Execute chain with timeout
        start_time = datetime.now()
        
        try:
            if timeout:
                result = await asyncio.wait_for(
                    chain.execute(initial_context),
                    timeout=timeout
                )
            else:
                result = await chain.execute(initial_context)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Update success stats
            stats["successes"] += 1
            stats["total_execution_time"] += execution_time
            stats["average_execution_time"] = stats["total_execution_time"] / stats["executions"]
            
            # Record in history
            self._record_execution(chain_id, True, execution_time, result)
            
            return result
            
        except asyncio.TimeoutError:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Update failure stats
            stats["failures"] += 1
            stats["total_execution_time"] += execution_time
            stats["average_execution_time"] = stats["total_execution_time"] / stats["executions"]
            
            # Record in history
            self._record_execution(chain_id, False, execution_time, {"error": "timeout"})
            
            raise TimeoutError(f"Chain '{chain_id}' execution timed out after {timeout}s")
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Update failure stats
            stats["failures"] += 1
            stats["total_execution_time"] += execution_time
            stats["average_execution_time"] = stats["total_execution_time"] / stats["executions"]
            
            # Record in history
            self._record_execution(chain_id, False, execution_time, {"error": str(e)})
            
            raise
    
    def delete_chain(self, chain_id: str) -> bool:
        """Delete a chain by ID.
        
        Args:
            chain_id: ID of the chain to delete
            
        Returns:
            True if chain was deleted, False if not found
        """
        if chain_id in self._chains:
            del self._chains[chain_id]
            if chain_id in self._execution_stats:
                del self._execution_stats[chain_id]
            return True
        
        return False
    
    def get_chain_history(self, chain_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution history for a specific chain.
        
        Args:
            chain_id: ID of the chain
            limit: Maximum number of history entries to return
            
        Returns:
            List of execution history entries
        """
        chain_history = [
            entry for entry in self._chain_history
            if entry["chain_id"] == chain_id
        ]
        
        return chain_history[-limit:] if len(chain_history) > limit else chain_history
    
    def get_execution_stats(self, chain_id: Optional[str] = None) -> Dict[str, Any]:
        """Get execution statistics.
        
        Args:
            chain_id: Specific chain ID or None for all chains
            
        Returns:
            Execution statistics
        """
        if chain_id:
            return self._execution_stats.get(chain_id, {})
        
        # Return stats for all chains
        return {
            "total_chains": len(self._chains),
            "total_executions": sum(
                stats.get("executions", 0) 
                for stats in self._execution_stats.values()
            ),
            "total_successes": sum(
                stats.get("successes", 0) 
                for stats in self._execution_stats.values()
            ),
            "total_failures": sum(
                stats.get("failures", 0) 
                for stats in self._execution_stats.values()
            ),
            "overall_success_rate": self._calculate_overall_success_rate(),
            "chain_stats": dict(self._execution_stats)
        }
    
    def register_template(self, template_name: str, template_class: Type) -> None:
        """Register a custom chain template.
        
        Args:
            template_name: Name for the template
            template_class: Template class that implements build() method
        """
        self._chain_templates[template_name] = template_class
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates.
        
        Returns:
            List of template information
        """
        templates_info = []
        
        for name, template_class in self._chain_templates.items():
            templates_info.append({
                "name": name,
                "class": template_class.__name__,
                "module": template_class.__module__,
                "description": getattr(template_class, "__doc__", "No description available")
            })
        
        return templates_info
    
    def validate_chain(self, chain_id: str) -> List[str]:
        """Validate a chain configuration.
        
        Args:
            chain_id: ID of the chain to validate
            
        Returns:
            List of validation issues
        """
        chain = self.get_chain(chain_id)
        if not chain:
            return [f"Chain '{chain_id}' not found"]
        
        return chain.validate()
    
    def cleanup_completed_chains(self) -> int:
        """Clean up chains that have completed execution.
        
        Returns:
            Number of chains cleaned up
        """
        cleaned_count = 0
        
        for chain_id, chain in list(self._chains.items()):
            if chain.status in [ChainStatus.COMPLETED, ChainStatus.FAILED]:
                # Don't delete, just reset status
                chain.status = ChainStatus.PENDING
                cleaned_count += 1
        
        return cleaned_count
    
    def _calculate_success_rate(self, stats: Dict[str, Any]) -> float:
        """Calculate success rate for a chain."""
        executions = stats.get("executions", 0)
        successes = stats.get("successes", 0)
        
        if executions == 0:
            return 0.0
        
        return (successes / executions) * 100.0
    
    def _calculate_overall_success_rate(self) -> float:
        """Calculate overall success rate across all chains."""
        total_executions = sum(
            stats.get("executions", 0) 
            for stats in self._execution_stats.values()
        )
        total_successes = sum(
            stats.get("successes", 0) 
            for stats in self._execution_stats.values()
        )
        
        if total_executions == 0:
            return 0.0
        
        return (total_successes / total_executions) * 100.0
    
    def _record_execution(
        self,
        chain_id: str,
        success: bool,
        execution_time: float,
        result: Dict[str, Any]
    ) -> None:
        """Record execution in history."""
        history_entry = {
            "chain_id": chain_id,
            "timestamp": datetime.now(),
            "success": success,
            "execution_time": execution_time,
            "result_summary": {
                "steps_completed": len(result.get("step_results", {})),
                "final_status": result.get("metadata", {}).get("chain_status", "unknown")
            }
        }
        
        self._chain_history.append(history_entry)
        
        # Keep history size manageable
        if len(self._chain_history) > 1000:
            self._chain_history = self._chain_history[-500:]


# Global chain manager instance
_chain_manager: Optional[ChainManager] = None


def get_chain_manager() -> ChainManager:
    """Get the global chain manager instance.
    
    Returns:
        ChainManager singleton instance
    """
    global _chain_manager
    
    if _chain_manager is None:
        _chain_manager = ChainManager()
    
    return _chain_manager


def reset_chain_manager() -> None:
    """Reset the global chain manager instance.
    
    Useful for testing or reinitialization.
    """
    global _chain_manager
    _chain_manager = None
