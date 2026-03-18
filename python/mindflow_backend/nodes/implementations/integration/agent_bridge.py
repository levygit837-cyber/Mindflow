"""Agent Bridge Node - Integrates Nodes with Agents system.

This node provides a clean interface between the Nodes system and the Agents system,
isolating dependencies and maintaining separation of concerns.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from mindflow_backend.nodes.base.node import BaseNode, NodeType, NodeCategory
from mindflow_backend.nodes.base.stateful import StatefulNode
from mindflow_backend.schemas.orchestration.orchestrator import (
    OrchestratorDecision,
    SandboxMode,
)


class AgentBridge(StatefulNode, BaseNode):
    """Bridge node for integrating with Agents system.
    
    This node isolates the dependency on the Agents system, providing
    a clean interface for node execution while maintaining architectural
    separation between Nodes and Agents.
    """
    
    def __init__(
        self, 
        node_id: str = "agent_bridge",
        agent_type: Optional[str] = None,
        sandbox_mode: SandboxMode = SandboxMode.FULL
    ) -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.PROCESSING,
            category=NodeCategory.INTEGRATION,
            description="Bridge node for agent system integration"
        )
        
        self.agent_type = agent_type
        self.sandbox_mode = sandbox_mode
        
        # Required inputs
        self.config.required_inputs = {"message", "session_id"}
        self.config.outputs = {"response", "metadata", "error"}
        
        # Internal state for agent integration
        self._agent_instance = None
        self._tools_registry = None
        self._sandbox = None
    
    async def initialize(self) -> None:
        """Initialize the agent bridge and its dependencies."""
        await super().initialize()
        
        # Import agent dependencies only when needed
        from mindflow_backend.agents._registry import get_agent
        from mindflow_backend.agents.tools import create_default_registry
        from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
        from mindflow_backend.infra.config import get_settings
        from mindflow_backend.infra.logging import get_logger
        
        self._logger = get_logger(__name__)
        
        try:
            # Get agent instance
            if self.agent_type:
                self._agent_instance = get_agent(self.agent_type)
            else:
                # Dynamic agent selection based on decision
                self._agent_instance = None
            
            # Create tools registry
            self._tools_registry = create_default_registry()
            
            # Create sandbox environment
            settings = get_settings()
            self._sandbox = MindFlowSandbox(
                mode=self.sandbox_mode,
                tools_registry=self._tools_registry,
                max_execution_time=settings.max_agent_execution_time,
                max_memory_usage=settings.max_agent_memory_usage
            )
            
            self._logger.info("agent_bridge_initialized", 
                           agent_type=self.agent_type, 
                           sandbox_mode=self.sandbox_mode.value)
            
        except Exception as e:
            self._logger.error("agent_bridge_initialization_failed", error=str(e))
            raise
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent logic through the bridge interface."""
        if not self._agent_instance and self.agent_type:
            raise RuntimeError("Agent bridge not properly initialized")
        
        try:
            message = state["message"]
            session_id = state.get("session_id", "unknown")
            
            # Dynamic agent selection if not pre-configured
            if not self._agent_instance:
                agent_decision = state.get("decision")
                if agent_decision and hasattr(agent_decision, 'agent'):
                    self._agent_instance = get_agent(agent_decision.agent.value)
                else:
                    # Default to general agent
                    from mindflow_backend.agents._registry import get_agent
                    self._agent_instance = get_agent("general")
            
            # Execute agent with sandbox
            response = await self._execute_agent_with_sandbox(
                message=message,
                session_id=session_id,
                context=state.get("context", {})
            )
            
            return {
                "response": response["content"],
                "metadata": {
                    "agent_type": self._agent_instance.personality.name if self._agent_instance else "unknown",
                    "execution_time": response.get("execution_time", 0),
                    "tokens_used": response.get("tokens_used", 0),
                    "tools_used": response.get("tools_used", []),
                },
                "error": None
            }
            
        except Exception as e:
            self._logger.error("agent_bridge_execution_failed", 
                           message=str(e), 
                           agent_type=self.agent_type)
            
            return {
                "response": None,
                "metadata": {"error_type": type(e).__name__},
                "error": str(e)
            }
    
    async def _execute_agent_with_sandbox(
        self, 
        message: str, 
        session_id: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute agent within sandbox environment."""
        if not self._sandbox:
            raise RuntimeError("Sandbox not initialized")
        
        # Prepare execution context
        execution_context = {
            "message": message,
            "session_id": session_id,
            "context": context,
            "agent": self._agent_instance,
            "tools_registry": self._tools_registry,
        }
        
        # Execute within sandbox
        result = await self._sandbox.execute(
            func=self._agent_execution_func,
            context=execution_context
        )
        
        return result
    
    async def _agent_execution_func(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Actual agent execution function to run in sandbox."""
        agent = context["agent"]
        message = context["message"]
        session_id = context["session_id"]
        tools_registry = context["tools_registry"]
        
        # Get memory context if available
        memory_context = ""
        try:
            from mindflow_backend.memory import get_memory_service
            memory_service = await get_memory_service()
            memory_result = await memory_service.retrieve_context(
                session_id=session_id,
                query=message,
                limit=5
            )
            memory_context = memory_result.context if memory_result else ""
        except Exception:
            # Memory is optional, continue without it
            pass
        
        # Execute agent using the proper execution flow
        response = await self._execute_agent_properly(
            agent=agent,
            message=message,
            session_id=session_id,
            tools_registry=tools_registry,
            memory_context=memory_context
        )
        
        return {
            "content": response.content,
            "execution_time": getattr(response, 'execution_time', 0),
            "tokens_used": getattr(response, 'tokens_used', 0),
            "tools_used": getattr(response, 'tools_used', []),
        }
    
    async def cleanup(self) -> None:
        """Cleanup agent bridge resources."""
        if self._sandbox:
            await self._sandbox.cleanup()
        
        self._agent_instance = None
        self._tools_registry = None
        self._sandbox = None
        
        await super().cleanup()
    
    async def _execute_agent_properly(
        self, 
        agent: Any, 
        message: str, 
        session_id: str, 
        tools_registry: Any, 
        memory_context: str
    ) -> Any:
        """Execute agent using the proper architecture."""
        from mindflow_backend.infra.logging import get_logger
        _logger = get_logger(__name__)
        
        try:
            # Get tools for the agent type
            tools = tools_registry.get_tools_for_agent(agent)
            
            # Create a simple response object for compatibility
            class AgentResponse:
                def __init__(self, content: str):
                    self.content = content
                    self.execution_time = 0
                    self.tokens_used = 0
                    self.tools_used = []
            
            # For now, return a simple response
            # In a full implementation, this would use the LLM with tools
            response_content = f"[{agent.agent_type.value}] Processing: {message}"
            
            if memory_context:
                response_content += f"\n\nContext: {memory_context[:200]}..."
            
            response_content += f"\n\nAvailable tools: {len(tools)} tools loaded"
            
            return AgentResponse(response_content)
            
        except Exception as exc:
            _logger.error("agent_execution_failed", error=str(exc))
            # Return error response
            class AgentResponse:
                def __init__(self, content: str):
                    self.content = content
                    self.execution_time = 0
                    self.tokens_used = 0
                    self.tools_used = []
            
            return AgentResponse(f"Error executing agent: {str(exc)}")
    
    def get_agent_capabilities(self) -> Dict[str, Any]:
        """Get capabilities of the current agent."""
        if not self._agent_instance:
            return {"capabilities": [], "personality": None}
        
        return {
            "capabilities": self._agent_instance.personality.capabilities,
            "personality": self._agent_instance.personality.name,
            "description": self._agent_instance.personality.description,
        }
    
    def update_agent_type(self, agent_type: str) -> None:
        """Dynamically update the agent type."""
        self.agent_type = agent_type
        self._agent_instance = None  # Force re-initialization
