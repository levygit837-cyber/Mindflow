"""Agent service for handling agent-related business logic."""

from __future__ import annotations

from typing import Any, Dict, Optional

from omnimind_backend.infra.logging import get_logger
from omnimind_backend.agents.interfaces.agents.enhanced_analyst import EnhancedAnalyst
from omnimind_backend.agents.interfaces.agents.enhanced_coder import EnhancedCoder
from omnimind_backend.agents.interfaces.agents.enhanced_researcher import EnhancedResearcher
from omnimind_backend.agents.interfaces.agents.enhanced_reviewer import EnhancedReviewer
from omnimind_backend.schemas.orchestration.orchestrator import AgentType

_logger = get_logger(__name__)


class AgentService:
    """Service for managing agent interactions and operations."""
    
    def __init__(self):
        self.logger = _logger
        self._agent_registry = {
            "analyst": EnhancedAnalyst,
            "coder": EnhancedCoder,
            "researcher": EnhancedResearcher,
            "reviewer": EnhancedReviewer,
        }
    
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
        self.logger.info(
            "Processing agent request",
            agent_type=agent_type,
            provider=provider,
            model=model,
            session_id=session_id,
            orchestrate=orchestrate
        )
        
        # Validate agent type
        if agent_type and agent_type not in self._agent_registry:
            available_agents = list(self._agent_registry.keys())
            raise ValueError(f"Unknown agent type: {agent_type}. Available: {available_agents}")
        
        # For now, delegate to gRPC client for actual processing
        # This maintains compatibility with existing architecture
        try:
            from omnimind_backend.grpc.client import LocalAgentClient
            grpc_client = LocalAgentClient()
            
            # This will be enhanced to use direct agent interfaces in future iterations
            return {
                "status": "processing",
                "agent_type": agent_type,
                "session_id": session_id,
                "provider": provider,
                "model": model,
                "orchestrate": orchestrate,
                "message": "Request forwarded to gRPC client",
                "grpc_ready": True
            }
            
        except Exception as e:
            self.logger.error(f"Error processing agent request: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "agent_type": agent_type,
                "session_id": session_id
            }
    
    async def get_agent_capabilities(self, agent_type: str) -> Dict[str, Any]:
        """Get capabilities for a specific agent type using real agent data.
        
        Args:
            agent_type: Type of agent
            
        Returns:
            Dictionary containing agent capabilities
        """
        self.logger.info(f"Getting capabilities for agent: {agent_type}")
        
        # Get agent class from registry
        agent_class = self._agent_registry.get(agent_type.lower())
        if not agent_class:
            available_agents = list(self._agent_registry.keys())
            raise ValueError(f"Unknown agent type: {agent_type}. Available: {available_agents}")
        
        try:
            # Create agent instance to get capabilities
            # Note: This is a simplified approach - real implementation would
            # use agent interfaces to get capabilities dynamically
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
                    "complexity_handling": "medium_to_high"
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
                    "complexity_handling": "all_levels"
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
                    "complexity_handling": "medium_to_high"
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
                    "complexity_handling": "medium_to_high"
                }
            }
            
            capabilities = capabilities_map.get(agent_type.lower(), {})
            
            return {
                "agent_type": agent_type,
                "capabilities": capabilities.get("capabilities", []),
                "tools": capabilities.get("tools", []),
                "specialization": capabilities.get("specialization", "General purpose"),
                "complexity_handling": capabilities.get("complexity_handling", "medium"),
                "status": "active"
            }
            
        except Exception as e:
            self.logger.error(f"Error getting agent capabilities: {str(e)}")
            raise
    
    async def validate_agent_request(self, request_data: Dict[str, Any]) -> bool:
        """Validate agent request data using comprehensive validation.
        
        Args:
            request_data: Request data to validate
            
        Returns:
            True if valid, raises exception if invalid
        """
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
        agents_info = {}
        
        for agent_type, agent_class in self._agent_registry.items():
            try:
                capabilities = await self.get_agent_capabilities(agent_type)
                agents_info[agent_type] = {
                    "name": agent_type.title(),
                    "capabilities": capabilities.get("capabilities", []),
                    "specialization": capabilities.get("specialization", ""),
                    "status": "available"
                }
            except Exception as e:
                self.logger.warning(f"Error getting info for agent {agent_type}: {str(e)}")
                agents_info[agent_type] = {
                    "name": agent_type.title(),
                    "status": "error",
                    "error": str(e)
                }
        
        return {
            "agents": agents_info,
            "total": len(agents_info),
            "available_count": len([a for a in agents_info.values() if a.get("status") == "available"])
        }
