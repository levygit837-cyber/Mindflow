"""Conditional Workflow Graph - Defines conditional execution workflows.

This graph implements workflow patterns where execution paths are determined
by dynamic conditions with support for complex decision trees and rule-based routing.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Union
import asyncio

from mindflow_backend.graphs.base.graph import BaseGraph, GraphType, GraphState
from mindflow_backend.nodes.base.node import BaseNode
from mindflow_backend.nodes.base.stateful import StatefulNode


class ConditionalWorkflowGraph(BaseGraph):
    """Graph that implements conditional workflow patterns.
    
    This graph supports:
    - Rule-based routing with priority
    - Multi-level decision trees
    - Dynamic path selection
    - Conditional branching with complex logic
    - Pattern matching and rule evaluation
    """
    
    def __init__(
        self,
        graph_id: str = "conditional_workflow",
        rules: List[Dict[str, Any]] = None,
        default_path: Optional[str] = None,
        decision_mode: str = "priority",  # priority, weighted, first_match, custom
        condition_evaluator: Optional[Callable[[Dict[str, Any]], bool]] = None,
        description: str = ""
    ) -> None:
        super().__init__(
            graph_id=graph_id,
            graph_type=GraphType.CONDITIONAL,
            description=description or "Conditional workflow execution"
        )
        
        self.rules = rules or []
        self.default_path = default_path
        self.decision_mode = decision_mode.lower()
        self.condition_evaluator = condition_evaluator
        
        # Internal state
        self._workflow_state = {}
        self._execution_history = []
        self._rule_cache = {}
    
    def add_rule(
        self,
        rule_id: str,
        condition: Dict[str, Any],
        target_path: str,
        priority: int = 0,
        weight: float = 1.0,
        description: str = ""
    ) -> None:
        """Add a conditional rule to the workflow."""
        rule = {
            "rule_id": rule_id,
            "condition": condition,
            "target_path": target_path,
            "priority": priority,
            "weight": weight,
            "description": description
        }
        
        self.rules.append(rule)
    
    def add_pattern_rule(
        self,
        rule_id: str,
        pattern: str,
        target_path: str,
        priority: int = 0,
        description: str = ""
    ) -> None:
        """Add a pattern-based rule to the workflow."""
        rule = {
            "rule_id": rule_id,
            "condition": {"pattern": pattern},
            "target_path": target_path,
            "priority": priority,
            "weight": 1.0,
            "description": description
        }
        
        self.rules.append(rule)
    
    def add_custom_rule(
        self,
        rule_id: str,
        condition_evaluator: Callable[[Dict[str, Any]], bool],
        target_path: str,
        priority: int = 0,
        description: str = ""
    ) -> None:
        """Add a custom rule with evaluator function."""
        rule = {
            "rule_id": rule_id,
            "condition": {"custom_evaluator": condition_evaluator},
            "target_path": target_path,
            "priority": priority,
            "weight": 1.0,
            "description": description
        }
        
        self.rules.append(rule)
    
    async def execute(self, initial_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the conditional workflow."""
        workflow_state = initial_state or {}
        workflow_state.update(self._workflow_state)
        
        self._execution_history = []
        
        try:
            # Phase 1: Evaluate all rules
            matched_rules = await self._evaluate_rules(workflow_state)
            
            if not matched_rules:
                # No rules matched, use default path
                final_result = await self._execute_default_path(workflow_state)
            else:
                # Phase 2: Select best rule based on decision mode
                selected_rule = self._select_rule(matched_rules, workflow_state)
                
                # Phase 3: Execute the selected rule's target path
                execution_result = await self._execute_rule_path(selected_rule, workflow_state)
                final_result = execution_result.get("result")
            
            return {
                "workflow_state": workflow_state,
                "execution_history": self._execution_history,
                "final_state": "completed",
                "matched_rules": len(matched_rules),
                "selected_rule": selected_rule.get("rule_id") if matched_rules else None,
                "final_result": final_result,
                "execution_path": selected_rule.get("target_path", self.default_path)
            }
            
        except Exception as e:
            from mindflow_backend.infra.logging import get_logger
            logger = get_logger(__name__)
            logger.error("conditional_workflow_execution_failed", error=str(e))
            
            return {
                "workflow_state": workflow_state,
                "execution_history": self._execution_history,
                "final_state": "failed",
                "error": str(e),
                "matched_rules": 0,
                "selected_rule": None,
                "final_result": None,
                "execution_path": self.default_path
            }
    
    async def _evaluate_rules(self, workflow_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate all rules against the current state."""
        matched_rules = []
        
        for rule in self.rules:
            if await self._evaluate_rule_condition(rule, workflow_state):
                matched_rules.append(rule)
        
        return matched_rules
    
    async def _evaluate_rule_condition(self, rule: Dict[str, Any], workflow_state: Dict[str, Any]) -> bool:
        """Evaluate a single rule condition."""
        condition = rule.get("condition", {})
        
        if "pattern" in condition:
            return await self._evaluate_pattern_condition(condition["pattern"], workflow_state)
        elif "custom_evaluator" in condition:
            return condition["custom_evaluator"](workflow_state)
        else:
            return self._evaluate_simple_condition(condition, workflow_state)
    
    async def _evaluate_pattern_condition(self, pattern: str, workflow_state: Dict[str, Any]) -> bool:
        """Evaluate a pattern-based condition."""
        import re
        
        try:
            # Compile regex pattern
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            
            # Convert workflow state to string for pattern matching
            state_string = str(workflow_state)
            
            # Check if pattern matches
            return bool(compiled_pattern.search(state_string))
            
        except re.error:
            return False
    
    def _evaluate_simple_condition(self, condition: Dict[str, Any], workflow_state: Dict[str, Any]) -> bool:
        """Evaluate a simple condition."""
        for field, expected_value in condition.items():
            if field.startswith("state."):
                # Check workflow state
                state_field = field[6:]  # Remove "state." prefix
                actual_value = workflow_state.get(state_field)
            else:
                # Check other fields
                actual_value = workflow_state.get(field)
            
            if actual_value != expected_value:
                return False
        
        return True
    
    def _select_rule(self, matched_rules: List[Dict[str, Any]], workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Select the best rule based on decision mode."""
        if not matched_rules:
            return {}
        
        if self.decision_mode == "priority":
            return self._select_by_priority(matched_rules)
        elif self.decision_mode == "weighted":
            return self._select_by_weight(matched_rules)
        elif self.decision_mode == "first_match":
            return matched_rules[0]  # First rule in list
        elif self.decision_mode == "custom":
            return self._select_by_custom_evaluator(matched_rules, workflow_state)
        else:
            # Default to priority
            return self._select_by_priority(matched_rules)
    
    def _select_by_priority(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select rule with highest priority (lowest number)."""
        if not rules:
            return {}
        
        # Sort by priority (lower number = higher priority)
        sorted_rules = sorted(rules, key=lambda x: x.get("priority", 999))
        return sorted_rules[0]
    
    def _select_by_weight(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select rule with highest weight."""
        if not rules:
            return {}
        
        # Sort by weight (higher number = higher priority)
        sorted_rules = sorted(rules, key=lambda x: x.get("weight", 0.0))
        return sorted_rules[-1]
    
    def _select_by_custom_evaluator(self, rules: List[Dict[str, Any]], workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Select rule using custom evaluator function."""
        if not self.condition_evaluator:
            return self._select_by_priority(rules)
        
        best_rule = None
        best_score = -1
        
        for rule in rules:
            # Use the custom evaluator to score this rule
            try:
                score = self.condition_evaluator(workflow_state)
                if score > best_score:
                    best_score = score
                    best_rule = rule
            except Exception:
                # Evaluator failed, skip this rule
                continue
        
        return best_rule or {}
    
    async def _execute_default_path(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the default path when no rules match."""
        if not self.default_path:
            return {
                "status": "no_default_path",
                "error": "No default path configured"
            }
        
        # Resolve default path (could be a node ID or sub-workflow)
        if self.default_path.startswith("node:"):
            node_id = self.default_path[5:]  # Remove "node:" prefix
            from mindflow_backend.graphs.factory import get_graph_factory
            factory = get_graph_factory()
            node_instance = factory.get_node(node_id)
            
            if not node_instance:
                return {
                    "status": "node_not_found",
                    "error": f"Default path node not found: {node_id}"
                }
            
            result = await node_instance.execute(workflow_state)
            return {
                "status": "completed",
                "result": result,
                "execution_path": self.default_path
            }
        
        elif self.default_path.startswith("workflow:"):
            # Execute sub-workflow
            workflow_id = self.default_path[9:]  # Remove "workflow:" prefix
            from mindflow_backend.graphs.factory import get_graph_factory
            factory = get_graph_factory()
            workflow_instance = factory.get_graph(workflow_id)
            
            if not workflow_instance:
                return {
                    "status": "workflow_not_found",
                    "error": f"Default path workflow not found: {workflow_id}"
                }
            
            result = await workflow_instance.execute(workflow_state)
            return {
                "status": "completed",
                "result": result,
                "execution_path": self.default_path
            }
        
        else:
            return {
                "status": "invalid_default_path",
                "error": f"Invalid default path format: {self.default_path}"
            }
    
    async def _execute_rule_path(self, rule: Dict[str, Any], workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the target path specified by a rule."""
        target_path = rule.get("target_path")
        
        if not target_path:
            return {
                "status": "no_target_path",
                "error": "Rule has no target path"
            }
        
        # Prepare rule-specific state
        rule_state = {
            "rule_id": rule.get("rule_id"),
            "workflow_state": workflow_state,
            "rule_config": rule
        }
        
        if target_path.startswith("node:"):
            node_id = target_path[5:]  # Remove "node:" prefix
            from mindflow_backend.graphs.factory import get_graph_factory
            factory = get_graph_factory()
            node_instance = factory.get_node(node_id)
            
            if not node_instance:
                return {
                    "status": "node_not_found",
                    "error": f"Target path node not found: {node_id}"
                }
            
            result = await node_instance.execute(rule_state)
            return {
                "status": "completed",
                "result": result,
                "execution_path": target_path,
                "rule_id": rule.get("rule_id")
            }
        
        elif target_path.startswith("workflow:"):
            workflow_id = target_path[9:]  # Remove "workflow:" prefix
            from mindflow_backend.graphs.factory import get_graph_factory
            factory = get_graph_factory()
            workflow_instance = factory.get_graph(workflow_id)
            
            if not workflow_instance:
                return {
                    "status": "workflow_not_found",
                    "error": f"Target path workflow not found: {workflow_id}"
                }
            
            result = await workflow_instance.execute(rule_state)
            return {
                "status": "completed",
                "result": result,
                "execution_path": target_path,
                "rule_id": rule.get("rule_id")
            }
        
        elif target_path.startswith("function:"):
            # Execute custom function
            function_name = target_path[9:]  # Remove "function:" prefix
            function = self._get_custom_function(function_name)
            
            if not function:
                return {
                    "status": "function_not_found",
                    "error": f"Target path function not found: {function_name}"
                }
            
            try:
                result = await function(workflow_state)
                return {
                    "status": "completed",
                    "result": result,
                    "execution_path": target_path,
                    "rule_id": rule.get("rule_id")
                }
            except Exception as e:
                return {
                    "status": "function_failed",
                    "error": str(e),
                    "execution_path": target_path,
                    "rule_id": rule.get("rule_id")
                }
        
        else:
            return {
                "status": "invalid_target_path",
                "error": f"Invalid target path format: {target_path}"
            }
    
    def _get_custom_function(self, function_name: str) -> Optional[Callable]:
        """Get a custom function by name (would be from a registry)."""
        # This would integrate with a function registry
        # For now, return None
        return None
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Get information about the workflow configuration."""
        return {
            "graph_id": self.graph_id,
            "total_rules": len(self.rules),
            "decision_mode": self.decision_mode,
            "default_path": self.default_path,
            "has_custom_evaluator": self.condition_evaluator is not None,
            "rule_cache_size": len(self._rule_cache),
            "execution_history_count": len(self._execution_history)
        }
