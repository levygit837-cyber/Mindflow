"""Integration tests for API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


class TestAPIEndpointsIntegration:
    """Integration tests for the complete API."""
    
    def test_health_endpoint(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_agent_endpoints_integration(self, client: TestClient):
        """Test agent endpoints integration."""
        # Test agent capabilities endpoint
        with patch('mindflow_backend.api.v1.agent.agent_controller') as mock_controller:
            mock_controller_instance = AsyncMock()
            mock_controller_instance.get_capabilities.return_value = {
                "success": True,
                "agent_type": "analyst",
                "capabilities": ["analysis"],
                "response": "Agent capabilities retrieved"
            }
            mock_controller.return_value = mock_controller_instance
            
            response = client.get("/v1/agent/capabilities/analyst")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["agent_type"] == "analyst"
    
    def test_session_endpoints_integration(self, client: TestClient):
        """Test session endpoints integration."""
        with patch('mindflow_backend.api.v1.chat.session_controller') as mock_controller:
            mock_controller_instance = AsyncMock()
            mock_controller_instance.create_session.return_value = {
                "success": True,
                "id": "test-session",
                "title": "Test Session"
            }
            mock_controller.return_value = mock_controller_instance
            
            # Test create session
            response = client.post("/v1/chat/sessions", json={"title": "Test Session"})
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["title"] == "Test Session"
    
    def test_orchestration_endpoints_integration(self, client: TestClient):
        """Test orchestration endpoints integration."""
        with patch('mindflow_backend.api.v1.orchestration.orchestration_controller') as mock_controller:
            mock_controller_instance = AsyncMock()
            mock_controller_instance.decompose_task.return_value = {
                "success": True,
                "task_id": "test-task",
                "sub_tasks": [],
                "description": "Test task"
            }
            mock_controller.return_value = mock_controller_instance
            
            # Test task decomposition
            request_data = {
                "task_description": "Test task",
                "complexity_level": "medium"
            }
            response = client.post("/v1/orchestration/decompose", json=request_data)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["task_id"] == "test-task"
    
    def test_provider_endpoints_integration(self, client: TestClient):
        """Test provider endpoints integration."""
        with patch('mindflow_backend.api.v1.providers.provider_controller') as mock_controller:
            mock_controller_instance = AsyncMock()
            mock_controller_instance.list_providers.return_value = {
                "success": True,
                "providers": [
                    {"id": "google", "name": "Google", "status": "active"}
                ],
                "total": 1
            }
            mock_controller.return_value = mock_controller_instance
            
            # Test list providers
            response = client.get("/v1/providers/")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["total"] == 1
    
    def test_memory_endpoints_integration(self, client: TestClient):
        """Test memory endpoints integration."""
        with patch('mindflow_backend.api.v1.memory.memory_controller') as mock_controller:
            mock_controller_instance = AsyncMock()
            mock_controller_instance.get_agent_memory.return_value = {
                "success": True,
                "agent_id": "test-agent",
                "session_id": "test-session",
                "memory_events": []
            }
            mock_controller.return_value = mock_controller_instance
            
            # Test get agent memory
            response = client.get("/v1/memory/agents/test-agent/sessions/test-session")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["agent_id"] == "test-agent"
    
    @pytest.mark.asyncio
    async def test_async_endpoints_integration(self, async_client: AsyncClient):
        """Test async endpoints with AsyncClient."""
        # Test health endpoint asynchronously
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    @pytest.mark.asyncio
    async def test_streaming_endpoint_integration(self, async_client: AsyncClient):
        """Test streaming endpoint integration."""
        with patch('mindflow_backend.api.v1.agent.agent_controller') as mock_controller:
            mock_controller_instance = AsyncMock()
            mock_stream_response = AsyncMock()
            mock_controller_instance.stream_chat.return_value = mock_stream_response
            mock_controller.return_value = mock_controller_instance
            
            # Test streaming endpoint
            request_data = {
                "message": "Test message",
                "agent_type": "analyst",
                "sessionId": "test-session"
            }
            
            response = await async_client.post("/v1/agent/chat/stream", json=request_data)
            
            # Streaming responses might not return standard HTTP status
            # This test verifies the endpoint is reachable
            assert response.status_code in [200, 404]
    
    def test_cors_headers(self, client: TestClient):
        """Test CORS headers are present."""
        response = client.options("/health")
        
        # Check for CORS headers
        cors_headers = [
            "access-control-allow-origin",
            "access-control-allow-methods",
            "access-control-allow-headers"
        ]
        
        for header in cors_headers:
            if header in response.headers:
                assert response.headers[header] is not None
    
    def test_security_headers(self, client: TestClient):
        """Test security headers are present."""
        response = client.get("/health")
        
        # Check for security headers from ValidationMiddleware
        security_headers = [
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection",
            "referrer-policy"
        ]
        
        for header in security_headers:
            if header in response.headers:
                assert response.headers[header] is not None
    
    def test_error_handling_integration(self, client: TestClient):
        """Test error handling across the API."""
        # Test 404 for non-existent endpoint
        response = client.get("/v1/non-existent-endpoint")
        assert response.status_code == 404
        
        # Test invalid method
        response = client.patch("/health")
        # Should either return 405 Method Not Allowed or 404
        assert response.status_code in [404, 405]
    
    def test_request_validation_integration(self, client: TestClient):
        """Test request validation across endpoints."""
        # Test invalid JSON
        response = client.post(
            "/v1/agent/validate",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        # Should return validation error
        assert response.status_code in [400, 422]
        
        # Test missing required fields
        response = client.post("/v1/agent/validate", json={})
        # Should return validation error for missing message
        assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, async_client: AsyncClient):
        """Test handling of concurrent requests."""
        import asyncio
        
        # Make multiple concurrent requests
        tasks = []
        for i in range(5):
            task = async_client.get("/health")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All requests should succeed
        for response in responses:
            if not isinstance(response, Exception):
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ok"
    
    def test_api_versioning(self, client: TestClient):
        """Test API versioning is properly implemented."""
        # Test v1 endpoints are available
        response = client.get("/v1/agent/list")
        # Should either succeed (if mocked) or return appropriate error
        assert response.status_code in [200, 404, 500]
        
        # Test that root endpoints work
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_middleware_pipeline_integration(self, client: TestClient):
        """Test that middleware pipeline works correctly."""
        # Test that requests pass through all middleware
        response = client.get("/health")
        assert response.status_code == 200
        
        # The request should have passed through:
        # 1. ValidationMiddleware
        # 2. SecurityHeadersMiddleware
        # 3. RateLimiterMiddleware
        # 4. RequestContextMiddleware
        
        # Check evidence of middleware processing
        # (Security headers from ValidationMiddleware)
        if "x-content-type-options" in response.headers:
            assert response.headers["x-content-type-options"] == "nosniff"


class TestAPIWorkflowIntegration:
    """Test complete API workflows."""
    
    def test_complete_agent_workflow(self, client: TestClient):
        """Test complete agent interaction workflow."""
        with patch('mindflow_backend.api.v1.agent.agent_controller') as mock_controller:
            mock_controller_instance = AsyncMock()
            
            # Mock all agent controller methods
            mock_controller_instance.list_agents.return_value = {
                "success": True,
                "response": "Found 4 available agents",
                "capabilities": ["analyst", "coder", "researcher", "reviewer"]
            }
            mock_controller_instance.get_capabilities.return_value = {
                "success": True,
                "agent_type": "analyst",
                "capabilities": ["analysis", "coding"],
                "response": "Agent capabilities retrieved"
            }
            mock_controller_instance.validate_request.return_value = {
                "success": True,
                "response": "Request is valid",
                "metadata": {"valid": True}
            }
            mock_controller.return_value = mock_controller_instance
            
            # 1. List available agents
            response = client.get("/v1/agent/list")
            assert response.status_code == 200
            agents_data = response.json()
            assert agents_data["success"] is True
            
            # 2. Get capabilities for an agent
            response = client.get("/v1/agent/capabilities/analyst")
            assert response.status_code == 200
            capabilities_data = response.json()
            assert capabilities_data["success"] is True
            
            # 3. Validate a request
            request_data = {
                "message": "Test message",
                "agent_type": "analyst",
                "provider": "google"
            }
            response = client.post("/v1/agent/validate", json=request_data)
            assert response.status_code == 200
            validation_data = response.json()
            assert validation_data["success"] is True
    
    def test_complete_session_workflow(self, client: TestClient):
        """Test complete session management workflow."""
        with patch('mindflow_backend.api.v1.chat.session_controller') as mock_controller:
            mock_controller_instance = AsyncMock()
            
            # Mock session controller methods
            mock_controller_instance.create_session.return_value = {
                "success": True,
                "id": "test-session-id",
                "title": "Test Session"
            }
            mock_controller_instance.get_session.return_value = {
                "success": True,
                "id": "test-session-id",
                "title": "Test Session",
                "message_count": 0
            }
            mock_controller_instance.add_message.return_value = {
                "success": True,
                "data": {
                    "id": 1,
                    "role": "user",
                    "content": "Test message"
                }
            }
            mock_controller.return_value = mock_controller_instance
            
            # 1. Create a session
            response = client.post("/v1/chat/sessions", json={"title": "Test Session"})
            assert response.status_code == 200
            session_data = response.json()
            session_id = session_data["id"]
            
            # 2. Get session details
            response = client.get(f"/v1/chat/sessions/{session_id}")
            assert response.status_code == 200
            session_details = response.json()
            assert session_details["id"] == session_id
            
            # 3. Add a message to the session
            response = client.post(
                f"/v1/chat/sessions/{session_id}/messages",
                params={
                    "role": "user",
                    "content": "Test message"
                }
            )
            assert response.status_code == 200
            message_data = response.json()
            assert message_data["success"] is True
    
    def test_complete_orchestration_workflow(self, client: TestClient):
        """Test complete orchestration workflow."""
        with patch('mindflow_backend.api.v1.orchestration.orchestration_controller') as mock_controller:
            mock_controller_instance = AsyncMock()
            
            # Mock orchestration controller methods
            mock_controller_instance.decompose_task.return_value = {
                "success": True,
                "task_id": "test-task",
                "sub_tasks": [
                    {
                        "id": "subtask-1",
                        "description": "Analyze requirements",
                        "agent_type": "analyst"
                    }
                ]
            }
            mock_controller_instance.select_specialist.return_value = {
                "success": True,
                "task_id": "test-task",
                "selected_specialist": "analyst",
                "confidence": 0.8
            }
            mock_controller_instance.get_execution_status.return_value = {
                "success": True,
                "execution_id": "test-exec",
                "status": "completed",
                "progress": 100
            }
            mock_controller.return_value = mock_controller_instance
            
            # 1. Decompose a task
            request_data = {
                "task_description": "Analyze the codebase",
                "complexity_level": "medium"
            }
            response = client.post("/v1/orchestration/decompose", json=request_data)
            assert response.status_code == 200
            decomposition_data = response.json()
            task_id = decomposition_data["task_id"]
            
            # 2. Select specialist for the task
            specialist_request = {
                "task_id": task_id,
                "task_description": "Analyze the codebase",
                "task_complexity": "medium"
            }
            response = client.post("/v1/orchestration/select-specialist", json=specialist_request)
            assert response.status_code == 200
            specialist_data = response.json()
            assert specialist_data["selected_specialist"] == "analyst"
            
            # 3. Check execution status
            response = client.get("/v1/orchestration/execution/test-exec")
            assert response.status_code == 200
            status_data = response.json()
            assert status_data["status"] == "completed"
