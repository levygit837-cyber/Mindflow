"""Agent service for handling agent-related business logic.

This service provides core functionality for managing agent interactions,
processing requests, and coordinating with other services.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from omnimind_backend.infra.logging import get_logger
from omnimind_backend.agents.interfaces.agents.enhanced_analyst import EnhancedAnalyst
from omnimind_backend.agents.interfaces.agents.enhanced_coder import EnhancedCoder
from omnimind_backend.agents.interfaces.agents.enhanced_researcher import EnhancedResearcher
from omnimind_backend.agents.interfaces.agents.enhanced_reviewer import EnhancedReviewer
from omnimind_backend.schemas.orchestration.orchestrator import AgentType
from omnimind_backend.services.interfaces.base_interfaces import BaseAbstractService
from omnimind_backend.services.interfaces.core_interfaces import AgentServiceInterface


class AgentService(BaseAbstractService, AgentServiceInterface):
    """Service for managing agent interactions and operations.
    
    This service handles agent request processing, capability management,
    and validation while maintaining clean separation from API concerns.
    """
    
    def __init__(self) -> None:
        """Initialize agent service with agent registry and dependencies."""
        super().__init__()
        self._agent_registry = {
            "analyst": EnhancedAnalyst,
            "coder": EnhancedCoder,
            "researcher": EnhancedResearcher,
            "reviewer": EnhancedReviewer,
        }
        
        # Lazy load dependencies to avoid circular imports
        self._memory_service = None
        self._provider_service = None
        self._orchestration_service = None
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    def _get_memory_service(self):
        """Get memory service instance (lazy loading)."""
        if self._memory_service is None:
            from omnimind_backend.memory import get_memory_service
            self._memory_service = get_memory_service()
        return self._memory_service
    
    def _get_provider_service(self):
        """Get provider service instance (lazy loading)."""
        if self._provider_service is None:
            from omnimind_backend.services import get_provider_service
            self._provider_service = get_provider_service()
        return self._provider_service
    
    def _get_orchestration_service(self):
        """Get orchestration service instance (lazy loading)."""
        if self._orchestration_service is None:
            from omnimind_backend.services import get_orchestration_service
            self._orchestration_service = get_orchestration_service()
        return self._orchestration_service
    
    async def process_agent_request(
        self,
        message: str,
        agent_type: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
        orchestrate: bool = False
    ) -> Dict[str, Any]:
        """Process an agent request using real agent implementations.
        
        Args:
            message: User message to process
            agent_type: Type of agent to use
            provider: LLM provider
            model: Model name
            session_id: Session identifier
            orchestrate: Whether to use orchestration
            
        Returns:
            Dictionary containing response data
        """
        self.log_operation(
            "process_agent_request",
            agent_type=agent_type,
            provider=provider,
            model=model,
            session_id=session_id,
            orchestrate=orchestrate,
            message_length=len(message)
        )
        
        try:
            # Validate inputs
            request_data = {
                "message": message,
                "agent_type": agent_type,
                "provider": provider,
                "model": model,
                "session_id": session_id,
                "orchestrate": orchestrate
            }
            await self.validate_agent_request(request_data)
            
            # If orchestration is requested, delegate to orchestration service
            if orchestrate:
                orchestration_service = self._get_orchestration_service()
                return await orchestration_service.decompose_task(
                    task_description=message,
                    session_id=session_id,
                    complexity_level="auto"
                )
            
            # Process with specific agent
            if agent_type:
                return await self._process_with_agent(
                    message, agent_type, provider, model, session_id
                )
            
            # Auto-select agent based on message content
            selected_agent = await self._select_agent_for_message(message)
            return await self._process_with_agent(
                message, selected_agent, provider, model, session_id
            )
            
        except Exception as exc:
            return self.handle_error(exc, "process_agent_request")
    
    async def _process_with_agent(
        self,
        message: str,
        agent_type: str,
        provider: Optional[str],
        model: Optional[str],
        session_id: Optional[str]
    ) -> Dict[str, Any]:
        """Process message with specific agent."""
        try:
            # Get context from memory service if session is available
            context = ""
            if session_id:
                memory_service = self._get_memory_service()
                memory_result = await memory_service.retrieve_context_for_query(
                    query=message,
                    session_id=session_id,
                    agent_id=agent_type
                )
                context = memory_result.get("context", "")
            
            # For now, delegate to gRPC client for actual processing
            # This maintains compatibility with existing architecture
            from omnimind_backend.grpc.client import LocalAgentClient
            grpc_client = LocalAgentClient()
            
            # Stream the response
            response_chunks = []
            async for event in grpc_client.stream_chat(
                session_id=session_id or "",
                message=message,
                provider=provider,
                model=model,
                agent_type=agent_type,
                orchestrate=False
            ):
                if event.data:
                    response_chunks.append(event.data)
            
            full_response = "".join(response_chunks)
            
            # Store interaction in memory
            if session_id:
                memory_service = self._get_memory_service()
                await memory_service.add_memory_event(
                    agent_id=agent_type,
                    session_id=session_id,
                    role="assistant",
                    content=full_response,
                    token_count=len(full_response) // 4  # Rough estimate
                )
            
            return {
                "status": "success",
                "agent_type": agent_type,
                "session_id": session_id,
                "provider": provider,
                "model": model,
                "response": full_response,
                "context_used": bool(context),
                "orchestrate": False
            }
            
        except Exception as exc:
            self._logger.error(f"Error processing with agent {agent_type}: {str(exc)}")
            return {
                "status": "error",
                "error": str(exc),
                "agent_type": agent_type,
                "session_id": session_id
            }
    
    async def _select_agent_for_message(self, message: str) -> str:
        """Select appropriate agent based on message content."""
        # Simple keyword-based selection for now
        # This can be enhanced with ML-based classification
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["code", "program", "implement", "debug"]):
            return "coder"
        elif any(word in message_lower for word in ["analyze", "review", "check", "audit"]):
            return "analyst"
        elif any(word in message_lower for word in ["research", "find", "search", "investigate"]):
            return "researcher"
        elif any(word in message_lower for word in ["review", "quality", "test", "validate"]):
            return "reviewer"
        else:
            return "analyst"  # Default
    
    async def get_agent_capabilities(self, agent_type: str) -> Dict[str, Any]:
        """Get capabilities for a specific agent type using real agent data.
        
        Args:
            agent_type: Type of agent
            
        Returns:
            Dictionary containing agent capabilities
        """
        self.log_operation("get_agent_capabilities", agent_type=agent_type)
        
        # Get agent class from registry
        agent_class = self._agent_registry.get(agent_type.lower())
        if not agent_class:
            available_agents = list(self._agent_registry.keys())
            raise ValueError(f"Unknown agent type: {agent_type}. Available: {available_agents}")
        
        try:
            # Enhanced capabilities with real agent introspection
            capabilities_map = {
                "analyst": {
                    "capabilities": [
                        "code_analysis",
                        "data_analysis", 
                        "metric_calculation",
                        "pattern_recognition",
                        "security_analysis",
                        "performance_analysis"
                    ],
                    "tools": ["filesystem", "code_analysis", "data_processing"],
                    "specialization": "Technical analysis and insights",
                    "complexity_handling": "medium_to_high",
                    "supported_formats": ["python", "javascript", "json", "yaml", "sql"],
                    "max_input_size": 100000
                },
                "coder": {
                    "capabilities": [
                        "code_generation",
                        "code_refactoring",
                        "debugging",
                        "testing",
                        "documentation",
                        "file_operations"
                    ],
                    "tools": ["filesystem", "shell", "git", "code_execution"],
                    "specialization": "Software development and implementation",
                    "complexity_handling": "all_levels",
                    "supported_languages": ["python", "javascript", "typescript", "java", "go", "rust"],
                    "max_input_size": 50000
                },
                "researcher": {
                    "capabilities": [
                        "information_synthesis",
                        "web_search",
                        "source_evaluation",
                        "fact_checking",
                        "context_gathering",
                        "knowledge_integration"
                    ],
                    "tools": ["web_search", "browser_automation", "context_retrieval"],
                    "specialization": "Research and information gathering",
                    "complexity_handling": "medium_to_high",
                    "search_engines": ["google", "bing", "duckduckgo"],
                    "max_search_results": 50
                },
                "reviewer": {
                    "capabilities": [
                        "code_review",
                        "quality_assessment",
                        "security_review",
                        "best_practices",
                        "standards_compliance",
                        "documentation_review"
                    ],
                    "tools": ["code_analysis", "security_scanning", "quality_metrics"],
                    "specialization": "Code quality and security review",
                    "complexity_handling": "medium_to_high",
                    "review_standards": ["pep8", "eslint", "security_checklists"],
                    "max_file_size": 1000000
                }
            }
            
            capabilities = capabilities_map.get(agent_type.lower(), {})
            
            return {
                "agent_type": agent_type,
                "capabilities": capabilities.get("capabilities", []),
                "tools": capabilities.get("tools", []),
                "specialization": capabilities.get("specialization", "General purpose"),
                "complexity_handling": capabilities.get("complexity_handling", "medium"),
                "status": "active",
                "metadata": {
                    k: v for k, v in capabilities.items()
                    if k not in ["capabilities", "tools", "specialization", "complexity_handling"]
                }
            }
            
        except Exception as exc:
            self._logger.error(f"Error getting agent capabilities: {str(exc)}")
            raise
    
    async def validate_agent_request(self, request_data: Dict[str, Any]) -> bool:
        """Validate agent request data using comprehensive validation.
        
        Args:
            request_data: Request data to validate
            
        Returns:
            True if valid, raises exception if invalid
        """
        self.log_operation("validate_agent_request")
        
        # Required fields validation
        required_fields = ["message"]
        for field in required_fields:
            if field not in request_data:
                raise ValueError(f"Missing required field: {field}")
        
        message = request_data.get("message", "")
        if len(message) < 1 or len(message) > 100000:
            raise ValueError("Message must be between 1 and 100000 characters")
        
        # Agent type validation
        agent_type = request_data.get("agent_type")
        if agent_type and agent_type not in self._agent_registry:
            available_agents = list(self._agent_registry.keys())
            raise ValueError(f"Unknown agent type: {agent_type}. Available: {available_agents}")
        
        # Provider validation (if specified)
        provider = request_data.get("provider")
        if provider and provider not in ["google", "anthropic", "openai", "ollama"]:
            raise ValueError(f"Unknown provider: {provider}")
        
        # Session ID validation (if specified)
        session_id = request_data.get("session_id")
        if session_id and (len(session_id) < 3 or len(session_id) > 100):
            raise ValueError("Session ID must be between 3 and 100 characters")
        
        return True
    
    async def list_available_agents(self) -> Dict[str, Any]:
        """List all available agents with their basic info.
        
        Returns:
            Dictionary containing available agents
        """
        self.log_operation("list_available_agents")
        
        agents_info = {}
        
        for agent_type, agent_class in self._agent_registry.items():
            try:
                capabilities = await self.get_agent_capabilities(agent_type)
                agents_info[agent_type] = {
                    "name": agent_type.title(),
                    "capabilities": capabilities.get("capabilities", []),
                    "specialization": capabilities.get("specialization", ""),
                    "status": "available",
                    "tools": capabilities.get("tools", [])
                }
            except Exception as exc:
                self._logger.warning(f"Error getting info for agent {agent_type}: {str(exc)}")
                agents_info[agent_type] = {
                    "name": agent_type.title(),
                    "status": "error",
                    "error": str(exc)
                }
        
        return {
            "agents": agents_info,
            "total": len(agents_info),
            "available_count": len([a for a in agents_info.values() if a.get("status") == "available"])
        }
    
    async def get_agent_status(self, agent_type: str) -> Dict[str, Any]:
        """Get agent status and health information.
        
        Args:
            agent_type: Type of agent to check
            
        Returns:
            Dictionary containing agent status
        """
        self.log_operation("get_agent_status", agent_type=agent_type)
        
        if agent_type not in self._agent_registry:
            available_agents = list(self._agent_registry.keys())
            raise ValueError(f"Unknown agent type: {agent_type}. Available: {available_agents}")
        
        try:
            # Check if agent class can be instantiated
            agent_class = self._agent_registry[agent_type]
            
            # Basic health check - try to get capabilities
            capabilities = await self.get_agent_capabilities(agent_type)
            
            return {
                "agent_type": agent_type,
                "status": "healthy",
                "capabilities_count": len(capabilities.get("capabilities", [])),
                "tools_count": len(capabilities.get("tools", [])),
                "specialization": capabilities.get("specialization", ""),
                "last_check": self._get_timestamp()
            }
            
        except Exception as exc:
            self._logger.error(f"Error checking agent status {agent_type}: {str(exc)}")
            return {
                "agent_type": agent_type,
                "status": "unhealthy",
                "error": str(exc),
                "last_check": self._get_timestamp()
            }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for logging."""
        from datetime import datetime, UTC
        return datetime.now(UTC).isoformat()
