"""Tests for AgentService."""

from __future__ import annotations

import pytest
from unittest.mock import patch, AsyncMock

from mindflow_backend.api.services.agent_service import AgentService


class TestAgentService:
    """Test suite for AgentService."""
    
    def test_agent_service_initialization(self):
        """Test AgentService initialization."""
        service = AgentService()
        assert service.logger is not None
        assert "analyst" in service._agent_registry
        assert "coder" in service._agent_registry
        assert "researcher" in service._agent_registry
        assert "reviewer" in service._agent_registry
    
    @pytest.mark.asyncio
    async def test_process_agent_request_success(self):
        """Test processing agent request successfully."""
        service = AgentService()
        
        with patch('mindflow_backend.api.services.agent_service.LocalAgentClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value = mock_client_instance
            
            result = await service.process_agent_request(
                message="Test message",
                agent_type="analyst",
                provider="google",
                model="gemini-pro",
                session_id="test-session",
                orchestrate=False
            )
            
            assert result["status"] == "processing"
            assert result["agent_type"] == "analyst"
            assert result["session_id"] == "test-session"
            assert result["grpc_ready"] is True
    
    @pytest.mark.asyncio
    async def test_process_agent_request_invalid_agent(self):
        """Test processing request with invalid agent type."""
        service = AgentService()
        
        with pytest.raises(ValueError, match="Unknown agent type"):
            await service.process_agent_request(
                message="Test message",
                agent_type="invalid_agent"
            )
    
    @pytest.mark.asyncio
    async def test_process_agent_request_grpc_error(self):
        """Test processing request when gRPC client fails."""
        service = AgentService()
        
        with patch('mindflow_backend.api.services.agent_service.LocalAgentClient') as mock_client:
            mock_client.side_effect = Exception("gRPC error")
            
            result = await service.process_agent_request(
                message="Test message",
                agent_type="analyst"
            )
            
            assert result["status"] == "error"
            assert "gRPC error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_agent_capabilities_analyst(self):
        """Test getting capabilities for analyst agent."""
        service = AgentService()
        
        result = await service.get_agent_capabilities("analyst")
        
        assert result["agent_type"] == "analyst"
        assert result["status"] == "active"
        assert "code_analysis" in result["capabilities"]
        assert "data_analysis" in result["capabilities"]
        assert "filesystem" in result["tools"]
        assert result["specialization"] == "Technical analysis and insights"
    
    @pytest.mark.asyncio
    async def test_get_agent_capabilities_coder(self):
        """Test getting capabilities for coder agent."""
        service = AgentService()
        
        result = await service.get_agent_capabilities("coder")
        
        assert result["agent_type"] == "coder"
        assert result["status"] == "active"
        assert "code_generation" in result["capabilities"]
        assert "debugging" in result["capabilities"]
        assert "shell" in result["tools"]
        assert result["specialization"] == "Software development and implementation"
    
    @pytest.mark.asyncio
    async def test_get_agent_capabilities_invalid_agent(self):
        """Test getting capabilities for invalid agent type."""
        service = AgentService()
        
        with pytest.raises(ValueError, match="Unknown agent type"):
            await service.get_agent_capabilities("invalid_agent")
    
    @pytest.mark.asyncio
    async def test_validate_agent_request_success(self):
        """Test validating valid agent request."""
        service = AgentService()
        
        request_data = {
            "message": "Test message",
            "agent_type": "analyst",
            "provider": "google",
            "session_id": "test-session"
        }
        
        result = await service.validate_agent_request(request_data)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_agent_request_missing_message(self):
        """Test validating request with missing message."""
        service = AgentService()
        
        request_data = {
            "agent_type": "analyst"
        }
        
        with pytest.raises(ValueError, match="Missing required field: message"):
            await service.validate_agent_request(request_data)
    
    @pytest.mark.asyncio
    async def test_validate_agent_request_message_too_short(self):
        """Test validating request with message too short."""
        service = AgentService()
        
        request_data = {
            "message": "",
            "agent_type": "analyst"
        }
        
        with pytest.raises(ValueError, match="Message must be between 1 and 100000 characters"):
            await service.validate_agent_request(request_data)
    
    @pytest.mark.asyncio
    async def test_validate_agent_request_message_too_long(self):
        """Test validating request with message too long."""
        service = AgentService()
        
        request_data = {
            "message": "x" * 100001,  # Over limit
            "agent_type": "analyst"
        }
        
        with pytest.raises(ValueError, match="Message must be between 1 and 100000 characters"):
            await service.validate_agent_request(request_data)
    
    @pytest.mark.asyncio
    async def test_validate_agent_request_invalid_agent_type(self):
        """Test validating request with invalid agent type."""
        service = AgentService()
        
        request_data = {
            "message": "Test message",
            "agent_type": "invalid_agent"
        }
        
        with pytest.raises(ValueError, match="Unknown agent type"):
            await service.validate_agent_request(request_data)
    
    @pytest.mark.asyncio
    async def test_validate_agent_request_invalid_provider(self):
        """Test validating request with invalid provider."""
        service = AgentService()
        
        request_data = {
            "message": "Test message",
            "agent_type": "analyst",
            "provider": "invalid_provider"
        }
        
        with pytest.raises(ValueError, match="Unknown provider"):
            await service.validate_agent_request(request_data)
    
    @pytest.mark.asyncio
    async def test_validate_agent_request_invalid_session_id(self):
        """Test validating request with invalid session ID."""
        service = AgentService()
        
        request_data = {
            "message": "Test message",
            "agent_type": "analyst",
            "session_id": "ab"  # Too short
        }
        
        with pytest.raises(ValueError, match="Session ID must be between 3 and 100 characters"):
            await service.validate_agent_request(request_data)
    
    @pytest.mark.asyncio
    async def test_list_available_agents_success(self):
        """Test listing available agents successfully."""
        service = AgentService()
        
        result = await service.list_available_agents()
        
        assert "agents" in result
        assert "total" in result
        assert "available_count" in result
        assert result["total"] == 4  # analyst, coder, researcher, reviewer
        assert result["available_count"] == 4
        assert "analyst" in result["agents"]
        assert "coder" in result["agents"]
        assert "researcher" in result["agents"]
        assert "reviewer" in result["agents"]
    
    @pytest.mark.asyncio
    async def test_list_available_agents_with_error(self):
        """Test listing agents when one fails."""
        service = AgentService()
        
        with patch.object(service, 'get_agent_capabilities') as mock_capabilities:
            # Make analyst fail
            mock_capabilities.side_effect = lambda agent_type: (
                {"agent_type": agent_type, "capabilities": [], "status": "active"}
                if agent_type != "analyst"
                else Exception("Agent error")
            )
            
            result = await service.list_available_agents()
            
            assert result["total"] == 4
            assert result["available_count"] == 3  # analyst failed
            assert result["agents"]["analyst"]["status"] == "error"
            assert result["agents"]["coder"]["status"] == "available"


class TestAgentServiceIntegration:
    """Integration tests for AgentService."""
    
    @pytest.mark.asyncio
    async def test_full_agent_workflow(self):
        """Test complete agent workflow."""
        service = AgentService()
        
        # 1. List available agents
        agents = await service.list_available_agents()
        assert agents["available_count"] > 0
        
        # 2. Get capabilities for an agent
        agent_type = list(agents["agents"].keys())[0]
        capabilities = await service.get_agent_capabilities(agent_type)
        assert capabilities["agent_type"] == agent_type
        assert len(capabilities["capabilities"]) > 0
        
        # 3. Validate a request
        request_data = {
            "message": "Test message for workflow",
            "agent_type": agent_type,
            "provider": "google"
        }
        is_valid = await service.validate_agent_request(request_data)
        assert is_valid is True
        
        # 4. Process the request (with mocked gRPC)
        with patch('mindflow_backend.api.services.agent_service.LocalAgentClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value = mock_client_instance
            
            result = await service.process_agent_request(**request_data)
            assert result["status"] == "processing"
            assert result["agent_type"] == agent_type
    
    @pytest.mark.asyncio
    async def test_agent_registry_consistency(self):
        """Test that agent registry is consistent across operations."""
        service = AgentService()
        
        # Get all agents from registry
        registry_agents = set(service._agent_registry.keys())
        
        # Get agents from list operation
        listed_agents = await service.list_available_agents()
        listed_agent_types = set(listed_agents["agents"].keys())
        
        # They should match
        assert registry_agents == listed_agent_types
        
        # All should have valid capabilities
        for agent_type in registry_agents:
            capabilities = await service.get_agent_capabilities(agent_type)
            assert capabilities["agent_type"] == agent_type
            assert len(capabilities["capabilities"]) > 0
            assert "tools" in capabilities
            assert "specialization" in capabilities
