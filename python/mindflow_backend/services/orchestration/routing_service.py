"""Routing service for intelligent agent selection and message routing.

This service provides comprehensive routing capabilities including
agent selection, message analysis, and performance optimization.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService
from mindflow_backend.services.interfaces.orchestration_interfaces import RoutingServiceInterface


class RoutingService(BaseAbstractService, RoutingServiceInterface):
    """Service for intelligent routing and agent selection.
    
    This service provides comprehensive routing capabilities including
    message analysis, agent selection, and performance optimization.
    """
    
    def __init__(self) -> None:
        """Initialize routing service with configuration and analytics."""
        super().__init__()
        
        # Routing configuration
        self._routing_rules: dict[str, dict[str, Any]] = {}
        self._agent_capabilities: dict[str, dict[str, Any]] = {}
        self._performance_metrics: dict[str, dict[str, Any]] = defaultdict(dict)
        
        # Routing history for learning
        self._routing_history: list[dict[str, Any]] = []
        self._max_history_size = 10000
        
        # Agent selection weights
        self._selection_weights = {
            "capability_match": 0.4,
            "performance": 0.3,
            "availability": 0.2,
            "load_balance": 0.1
        }
        
        # Lazy load dependencies
        self._agent_service = None
        self._provider_service = None
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    def _get_agent_service(self):
        """Get agent service instance (lazy loading)."""
        if self._agent_service is None:
            from mindflow_backend.services import get_agent_service
            self._agent_service = get_agent_service()
        return self._agent_service
    
    def _get_provider_service(self):
        """Get provider service instance (lazy loading)."""
        if self._provider_service is None:
            from mindflow_backend.services import get_provider_service
            self._provider_service = get_provider_service()
        return self._provider_service
    
    async def route_message(
        self,
        message: str,
        session_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Route message to appropriate agent.
        
        Args:
            message: Message to route
            session_context: Optional session context
            
        Returns:
            Dictionary containing routing decision
        """
        self.log_operation(
            "route_message",
            message_length=len(message),
            has_context=session_context is not None
        )
        
        try:
            # Analyze message intent
            intent_analysis = await self.analyze_message_intent(message)
            
            # Get available agents
            agent_service = self._get_agent_service()
            available_agents = await agent_service.list_available_agents()
            agent_list = list(available_agents["agents"].keys())
            
            # Select optimal agent
            selection_result = await self.select_agent_for_task(
                task_description=message,
                task_complexity=intent_analysis.get("complexity", "medium"),
                available_agents=agent_list
            )
            
            # Apply routing rules
            routing_decision = await self._apply_routing_rules(
                message, intent_analysis, selection_result, session_context
            )
            
            # Record routing decision
            routing_record = {
                "message": message[:100],  # Truncate for storage
                "intent_analysis": intent_analysis,
                "selected_agent": routing_decision.get("selected_agent"),
                "routing_rules_applied": routing_decision.get("rules_applied", []),
                "confidence": routing_decision.get("confidence", 0.5),
                "timestamp": datetime.now(UTC).isoformat()
            }
            
            self._routing_history.append(routing_record)
            
            # Update performance metrics
            await self._update_routing_metrics(routing_decision)
            
            return {
                "message_id": routing_record.get("id"),
                "selected_agent": routing_decision.get("selected_agent"),
                "agent_type": routing_decision.get("agent_type"),
                "confidence": routing_decision.get("confidence", 0.5),
                "reasoning": routing_decision.get("reasoning", ""),
                "intent_analysis": intent_analysis,
                "routing_rules_applied": routing_decision.get("rules_applied", []),
                "alternatives": routing_decision.get("alternatives", []),
                "session_context": session_context,
                "routed_at": routing_record["timestamp"]
            }
            
        except Exception as exc:
            self._logger.error(f"Error routing message: {str(exc)}")
            raise
    
    async def select_agent_for_task(
        self,
        task_description: str,
        task_complexity: str,
        available_agents: list[str]
    ) -> dict[str, Any]:
        """Select optimal agent for a specific task.
        
        Args:
            task_description: Description of the task
            task_complexity: Complexity level of the task
            available_agents: List of available agent types
            
        Returns:
            Dictionary containing agent selection result
        """
        self.log_operation(
            "select_agent_for_task",
            task_description=task_description[:100],
            task_complexity=task_complexity,
            available_agents=available_agents
        )
        
        try:
            # Get agent capabilities
            agent_service = self._get_agent_service()
            agent_scores = {}
            
            for agent_type in available_agents:
                # Get agent capabilities
                try:
                    capabilities = await agent_service.get_agent_capabilities(agent_type)
                except Exception:
                    continue
                
                # Calculate capability match score
                capability_score = await self._calculate_capability_match(
                    task_description, task_complexity, capabilities
                )
                
                # Calculate performance score
                performance_score = self._get_agent_performance_score(agent_type)
                
                # Calculate availability score
                availability_score = await self._get_agent_availability_score(agent_type)
                
                # Calculate load balance score
                load_balance_score = self._get_load_balance_score(agent_type)
                
                # Calculate weighted total score
                total_score = (
                    capability_score * self._selection_weights["capability_match"] +
                    performance_score * self._selection_weights["performance"] +
                    availability_score * self._selection_weights["availability"] +
                    load_balance_score * self._selection_weights["load_balance"]
                )
                
                agent_scores[agent_type] = {
                    "agent_type": agent_type,
                    "capability_score": capability_score,
                    "performance_score": performance_score,
                    "availability_score": availability_score,
                    "load_balance_score": load_balance_score,
                    "total_score": total_score,
                    "capabilities": capabilities
                }
            
            # Sort agents by score
            sorted_agents = sorted(
                agent_scores.values(),
                key=lambda x: x["total_score"],
                reverse=True
            )
            
            if not sorted_agents:
                raise ValueError("No suitable agents found")
            
            # Get top selection and alternatives
            selected_agent = sorted_agents[0]
            alternatives = sorted_agents[1:4]  # Top 4 alternatives
            
            return {
                "selected_agent": selected_agent["agent_type"],
                "agent_type": selected_agent.get("capabilities", {}).get("specialization", "Unknown"),
                "confidence": min(selected_agent["total_score"], 1.0),
                "reasoning": self._generate_selection_reasoning(selected_agent, task_description),
                "score_breakdown": {
                    "capability_match": selected_agent["capability_score"],
                    "performance": selected_agent["performance_score"],
                    "availability": selected_agent["availability_score"],
                    "load_balance": selected_agent["load_balance_score"],
                    "total": selected_agent["total_score"]
                },
                "alternatives": [
                    {
                        "agent_type": alt["agent_type"],
                        "confidence": min(alt["total_score"], 1.0),
                        "reasoning": self._generate_selection_reasoning(alt, task_description)
                    }
                    for alt in alternatives
                ],
                "all_candidates": agent_scores
            }
            
        except Exception as exc:
            self._logger.error(f"Error selecting agent for task: {str(exc)}")
            raise
    
    async def get_routing_rules(self) -> list[dict[str, Any]]:
        """Get current routing rules.
        
        Returns:
            List of routing rule configurations
        """
        self.log_operation("get_routing_rules")
        
        try:
            rules = []
            
            for rule_id, rule in self._routing_rules.items():
                rules.append({
                    "rule_id": rule_id,
                    "name": rule.get("name", "Unnamed Rule"),
                    "description": rule.get("description", ""),
                    "conditions": rule.get("conditions", {}),
                    "actions": rule.get("actions", {}),
                    "priority": rule.get("priority", 0),
                    "enabled": rule.get("enabled", True),
                    "created_at": rule.get("created_at"),
                    "match_count": rule.get("match_count", 0)
                })
            
            # Sort by priority (highest first)
            rules.sort(key=lambda x: x["priority"], reverse=True)
            
            return rules
            
        except Exception as exc:
            self._logger.error(f"Error getting routing rules: {str(exc)}")
            raise
    
    async def update_routing_rule(
        self,
        rule_id: str,
        rule_definition: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a routing rule.
        
        Args:
            rule_id: Rule identifier
            rule_definition: New rule definition
            
        Returns:
            Dictionary containing update result
        """
        self.log_operation("update_routing_rule", rule_id=rule_id)
        
        try:
            # Validate rule definition
            required_fields = ["name", "conditions", "actions"]
            for field in required_fields:
                if field not in rule_definition:
                    raise ValueError(f"Missing required field: {field}")
            
            # Update rule
            if rule_id not in self._routing_rules:
                self._routing_rules[rule_id] = {}
            
            self._routing_rules[rule_id].update(rule_definition)
            self._routing_rules[rule_id]["updated_at"] = datetime.now(UTC).isoformat()
            
            return {
                "rule_id": rule_id,
                "name": rule_definition["name"],
                "status": "updated",
                "updated_at": self._routing_rules[rule_id]["updated_at"]
            }
            
        except Exception as exc:
            self._logger.error(f"Error updating routing rule {rule_id}: {str(exc)}")
            raise
    
    async def analyze_message_intent(self, message: str) -> dict[str, Any]:
        """Analyze message intent for routing decisions.
        
        Args:
            message: Message to analyze
            
        Returns:
            Dictionary containing intent analysis
        """
        self.log_operation("analyze_message_intent", message_length=len(message))
        
        try:
            message_lower = message.lower()
            
            # Analyze intent patterns
            intent_patterns = {
                "coding": [
                    "code", "program", "implement", "function", "class", "debug", "fix bug",
                    "write code", "develop", "algorithm", "script"
                ],
                "analysis": [
                    "analyze", "review", "check", "examine", "investigate", "audit",
                    "evaluate", "assess", "diagnose"
                ],
                "research": [
                    "research", "find", "search", "look up", "investigate", "explore",
                    "gather information", "learn about", "find data"
                ],
                "review": [
                    "review", "check quality", "validate", "verify", "test", "inspect",
                    "quality check", "audit code", "evaluate"
                ],
                "general": [
                    "help", "explain", "describe", "tell me", "what is", "how to"
                ]
            }
            
            # Calculate intent scores
            intent_scores = {}
            for intent, keywords in intent_patterns.items():
                score = sum(1 for keyword in keywords if keyword in message_lower)
                intent_scores[intent] = score
            
            # Determine primary intent
            if not any(intent_scores.values()):
                primary_intent = "general"
                confidence = 0.3
            else:
                primary_intent = max(intent_scores, key=intent_scores.get)
                max_score = intent_scores[primary_intent]
                confidence = min(max_score / 5.0, 1.0)  # Normalize to 0-1
            
            # Determine complexity
            complexity_indicators = {
                "simple": ["simple", "basic", "easy", "quick"],
                "complex": ["complex", "difficult", "advanced", "detailed", "comprehensive"],
                "multiple": ["multiple", "several", "various", "and", "also", "additionally"]
            }
            
            complexity_score = 0
            for level, indicators in complexity_indicators.items():
                if any(indicator in message_lower for indicator in indicators):
                    if level == "simple":
                        complexity_score -= 1
                    elif level == "complex":
                        complexity_score += 2
                    elif level == "multiple":
                        complexity_score += 1
            
            # Determine complexity level
            if complexity_score <= -1:
                complexity = "simple"
            elif complexity_score >= 2:
                complexity = "complex"
            else:
                complexity = "medium"
            
            return {
                "message": message[:200],  # Truncate for storage
                "primary_intent": primary_intent,
                "intent_scores": intent_scores,
                "confidence": round(confidence, 3),
                "complexity": complexity,
                "complexity_score": complexity_score,
                "keywords_found": self._extract_keywords(message_lower, intent_patterns[primary_intent]),
                "analyzed_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error analyzing message intent: {str(exc)}")
            raise
    
    async def get_routing_performance_metrics(self) -> dict[str, Any]:
        """Get routing performance metrics and statistics.
        
        Returns:
            Dictionary containing routing performance metrics
        """
        self.log_operation("get_routing_performance_metrics")
        
        try:
            # Calculate metrics from history
            if not self._routing_history:
                return {
                    "total_routings": 0,
                    "success_rate": 0.0,
                    "avg_confidence": 0.0,
                    "generated_at": datetime.now(UTC).isoformat()
                }
            
            total_routings = len(self._routing_history)
            successful_routings = len([
                r for r in self._routing_history
                if r.get("confidence", 0) > 0.5
            ])
            
            # Calculate confidence statistics
            confidences = [r.get("confidence", 0) for r in self._routing_history]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Agent usage statistics
            agent_usage = defaultdict(int)
            for routing in self._routing_history:
                agent = routing.get("selected_agent")
                if agent:
                    agent_usage[agent] += 1
            
            # Most used agents
            most_used_agents = sorted(
                agent_usage.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            return {
                "total_routings": total_routings,
                "successful_routings": successful_routings,
                "success_rate": round(successful_routings / total_routings, 3) if total_routings > 0 else 0.0,
                "avg_confidence": round(avg_confidence, 3),
                "agent_usage": dict(agent_usage),
                "most_used_agents": [
                    {"agent_type": agent, "usage_count": count}
                    for agent, count in most_used_agents
                ],
                "routing_rules_count": len(self._routing_rules),
                "performance_metrics": dict(self._performance_metrics),
                "generated_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error getting routing performance metrics: {str(exc)}")
            raise
    
    async def optimize_routing_strategy(self) -> dict[str, Any]:
        """Optimize routing strategy based on performance data.
        
        Returns:
            Dictionary containing optimization recommendations
        """
        self.log_operation("optimize_routing_strategy")
        
        try:
            # Analyze current performance
            performance_metrics = await self.get_routing_performance_metrics()
            
            # Generate optimization recommendations
            recommendations = []
            
            # Analyze agent performance
            agent_performance = performance_metrics.get("performance_metrics", {})
            for agent_type, metrics in agent_performance.items():
                avg_response_time = metrics.get("avg_response_time_ms", 0)
                success_rate = metrics.get("success_rate", 1.0)
                
                if avg_response_time > 5000:  # 5 seconds
                    recommendations.append({
                        "type": "agent_performance",
                        "agent_type": agent_type,
                        "issue": "slow_response_time",
                        "recommendation": "Consider optimizing agent implementation or using faster provider",
                        "current_avg_response_time_ms": avg_response_time
                    })
                
                if success_rate < 0.8:
                    recommendations.append({
                        "type": "agent_reliability",
                        "agent_type": agent_type,
                        "issue": "low_success_rate",
                        "recommendation": "Investigate agent failures and improve error handling",
                        "current_success_rate": success_rate
                    })
            
            # Analyze routing rules effectiveness
            rule_usage = performance_metrics.get("rule_usage", {})
            for rule_id, usage in rule_usage.items():
                if usage.get("success_rate", 1.0) < 0.7:
                    recommendations.append({
                        "type": "rule_optimization",
                        "rule_id": rule_id,
                        "issue": "low_effectiveness",
                        "recommendation": "Review and update rule conditions or priority",
                        "current_success_rate": usage.get("success_rate", 0.0)
                    })
            
            # Suggest selection weight adjustments
            success_rate = performance_metrics.get("success_rate", 1.0)
            if success_rate < 0.8:
                recommendations.append({
                    "type": "weight_adjustment",
                    "issue": "low_overall_success_rate",
                    "recommendation": "Increase weight for performance metrics in agent selection",
                    "current_weights": self._selection_weights,
                    "suggested_weights": {
                        "capability_match": 0.5,
                        "performance": 0.4,
                        "availability": 0.1,
                        "load_balance": 0.0
                    }
                })
            
            return {
                "current_performance": performance_metrics,
                "recommendations": recommendations,
                "optimization_priority": "high" if len(recommendations) > 3 else "medium" if len(recommendations) > 0 else "low",
                "optimized_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error optimizing routing strategy: {str(exc)}")
            raise
    
    # Helper methods
    
    async def _calculate_capability_match(
        self,
        task_description: str,
        task_complexity: str,
        capabilities: dict[str, Any]
    ) -> float:
        """Calculate capability match score between task and agent."""
        try:
            agent_capabilities = capabilities.get("capabilities", [])
            agent_specialization = capabilities.get("specialization", "").lower()
            
            # Keyword matching
            task_lower = task_description.lower()
            match_score = 0.0
            
            for capability in agent_capabilities:
                if capability.lower() in task_lower:
                    match_score += 0.3
            
            # Specialization matching
            specialization_keywords = {
                "technical analysis": ["analyze", "technical", "code analysis", "debug"],
                "software development": ["code", "program", "implement", "develop", "software"],
                "research and information gathering": ["research", "find", "search", "investigate", "information"],
                "code quality and security review": ["review", "quality", "security", "test", "validate"]
            }
            
            for specialization, keywords in specialization_keywords.items():
                if specialization.lower() == agent_specialization:
                    for keyword in keywords:
                        if keyword in task_lower:
                            match_score += 0.2
                            break
            
            # Complexity matching
            if task_complexity == "simple" and "simple" in agent_specialization or task_complexity == "complex" and "complex" in agent_specialization:
                match_score += 0.1
            
            return min(match_score, 1.0)
            
        except Exception:
            return 0.0
    
    def _get_agent_performance_score(self, agent_type: str) -> float:
        """Get performance score for an agent."""
        metrics = self._performance_metrics.get(agent_type, {})
        
        avg_response_time = metrics.get("avg_response_time_ms", 1000)
        success_rate = metrics.get("success_rate", 1.0)
        
        # Normalize response time (lower is better)
        response_score = max(0, 1.0 - (avg_response_time - 1000) / 10000)
        
        # Combine scores
        return (response_score + success_rate) / 2
    
    async def _get_agent_availability_score(self, agent_type: str) -> float:
        """Get availability score for an agent."""
        try:
            agent_service = self._get_agent_service()
            status = await agent_service.get_agent_status(agent_type)
            
            if status.get("status") == "active":
                return 1.0
            elif status.get("status") == "degraded":
                return 0.5
            else:
                return 0.0
                
        except Exception:
            return 0.5  # Default to medium if unknown
    
    def _get_load_balance_score(self, agent_type: str) -> float:
        """Get load balance score for an agent."""
        # In a real implementation, this would track current load
        # For now, return a balanced score
        return 0.8
    
    async def _apply_routing_rules(
        self,
        message: str,
        intent_analysis: dict[str, Any],
        selection_result: dict[str, Any],
        session_context: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Apply routing rules to modify selection."""
        rules_applied = []
        modified_selection = selection_result.copy()
        
        # Sort rules by priority
        sorted_rules = sorted(
            self._routing_rules.items(),
            key=lambda x: x[1].get("priority", 0),
            reverse=True
        )
        
        for rule_id, rule in sorted_rules:
            if not rule.get("enabled", True):
                continue
            
            # Check if rule conditions match
            if await self._evaluate_rule_conditions(rule.get("conditions", {}), message, intent_analysis, session_context):
                # Apply rule actions
                actions = rule.get("actions", {})
                
                if "override_agent" in actions:
                    modified_selection["selected_agent"] = actions["override_agent"]
                    modified_selection["reasoning"] = f"Overridden by rule: {rule.get('name')}"
                
                if "adjust_confidence" in actions:
                    modified_selection["confidence"] = actions["adjust_confidence"]
                
                rules_applied.append(rule_id)
                
                # Update rule match count
                rule["match_count"] = rule.get("match_count", 0) + 1
                
                break  # Apply first matching rule
        
        modified_selection["rules_applied"] = rules_applied
        
        return modified_selection
    
    async def _evaluate_rule_conditions(
        self,
        conditions: dict[str, Any],
        message: str,
        intent_analysis: dict[str, Any],
        session_context: dict[str, Any] | None
    ) -> bool:
        """Evaluate if routing rule conditions match."""
        try:
            # Check intent conditions
            if "intent" in conditions:
                required_intent = conditions["intent"]
                if intent_analysis.get("primary_intent") != required_intent:
                    return False
            
            # Check complexity conditions
            if "complexity" in conditions:
                required_complexity = conditions["complexity"]
                if intent_analysis.get("complexity") != required_complexity:
                    return False
            
            # Check session conditions
            if "session_has_context" in conditions:
                has_context = session_context is not None and len(session_context) > 0
                if conditions["session_has_context"] != has_context:
                    return False
            
            # Check message length conditions
            if "message_length" in conditions:
                length_condition = conditions["message_length"]
                message_length = len(message)
                
                if isinstance(length_condition, dict):
                    min_len = length_condition.get("min", 0)
                    max_len = length_condition.get("max", float('inf'))
                    
                    if not (min_len <= message_length <= max_len):
                        return False
                elif isinstance(length_condition, (int, float)):
                    if message_length != length_condition:
                        return False
            
            return True
            
        except Exception:
            return False
    
    def _generate_selection_reasoning(self, agent_score: dict[str, Any], task_description: str) -> str:
        """Generate reasoning for agent selection."""
        agent_type = agent_score.get("agent_type", "unknown")
        capability_score = agent_score.get("capability_score", 0)
        performance_score = agent_score.get("performance_score", 0)
        
        reasoning_parts = []
        
        if capability_score > 0.5:
            reasoning_parts.append(f"Strong capability match for {agent_type}")
        
        if performance_score > 0.7:
            reasoning_parts.append(f"Good historical performance for {agent_type}")
        
        if not reasoning_parts:
            reasoning_parts.append(f"Selected {agent_type} as best available option")
        
        return " | ".join(reasoning_parts)
    
    def _extract_keywords(self, message: str, intent_keywords: list[str]) -> list[str]:
        """Extract keywords found in message."""
        found_keywords = []
        message_lower = message.lower()
        
        for keyword in intent_keywords:
            if keyword in message_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    async def _update_routing_metrics(self, routing_decision: dict[str, Any]) -> None:
        """Update routing performance metrics."""
        agent_type = routing_decision.get("selected_agent")
        confidence = routing_decision.get("confidence", 0.5)
        
        if agent_type not in self._performance_metrics:
            self._performance_metrics[agent_type] = {
                "total_routings": 0,
                "successful_routings": 0,
                "avg_response_time_ms": 0,
                "success_rate": 1.0
            }
        
        metrics = self._performance_metrics[agent_type]
        metrics["total_routings"] += 1
        
        if confidence > 0.5:
            metrics["successful_routings"] += 1
        
        # Update success rate
        metrics["success_rate"] = metrics["successful_routings"] / metrics["total_routings"]
