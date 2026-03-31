"""Tests for SessionController."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from mindflow_backend.api.controllers.session_controller import SessionController
from mindflow_backend.api.schemas.responses import SessionListResponse, SessionResponse


class TestSessionController:
    """Test suite for SessionController."""
    
    def test_session_controller_initialization(self):
        """Test SessionController initialization."""
        controller = SessionController()
        assert controller.session_service is not None
        assert controller.logger is not None
    
    @pytest.mark.asyncio
    async def test_create_session_success(self, mock_session_service):
        """Test creating a session successfully."""
        controller = SessionController()
        controller.session_service = mock_session_service
        
        request = AsyncMock()
        request.title = "Test Session"
        request.user_id = "test-user"
        
        result = await controller.create_session(request)
        
        assert isinstance(result, SessionResponse)
        assert result.success is True
        assert result.id == "test-session-id"
        assert result.title == "Test Session"
        mock_session_service.create_session.assert_called_once_with(
            title="Test Session",
            user_id="test-user"
        )
    
    @pytest.mark.asyncio
    async def test_get_session_success(self, mock_session_service):
        """Test getting a session successfully."""
        controller = SessionController()
        controller.session_service = mock_session_service
        
        result = await controller.get_session("test-session-id")
        
        assert isinstance(result, SessionResponse)
        assert result.success is True
        assert result.id == "test-session-id"
        assert result.message_count == 0
        mock_session_service.get_session.assert_called_once_with("test-session-id")
    
    @pytest.mark.asyncio
    async def test_get_session_not_found(self, mock_session_service):
        """Test getting a non-existent session."""
        controller = SessionController()
        controller.session_service = mock_session_service
        mock_session_service.get_session.side_effect = ValueError("Session not found")
        
        with pytest.raises(Exception):
            await controller.get_session("non-existent-session")
    
    @pytest.mark.asyncio
    async def test_list_sessions_success(self, mock_session_service):
        """Test listing sessions successfully."""
        controller = SessionController()
        controller.session_service = mock_session_service
        
        pagination = AsyncMock()
        pagination.limit = 10
        pagination.offset = 0
        
        result = await controller.list_sessions(pagination)
        
        assert isinstance(result, SessionListResponse)
        assert result.success is True
        assert result.limit == 10
        assert result.offset == 0
        mock_session_service.list_sessions.assert_called_once_with(limit=10, offset=0)
    
    @pytest.mark.asyncio
    async def test_update_session_success(self, mock_session_service):
        """Test updating a session successfully."""
        controller = SessionController()
        controller.session_service = mock_session_service
        
        request = AsyncMock()
        request.title = "Updated Session"
        
        result = await controller.update_session("test-session-id", request)
        
        assert isinstance(result, SessionResponse)
        assert result.success is True
        assert result.title == "Updated Session"
        mock_session_service.update_session.assert_called_once_with(
            session_id="test-session-id",
            title="Updated Session"
        )
    
    @pytest.mark.asyncio
    async def test_delete_session_success(self, mock_session_service):
        """Test deleting a session successfully."""
        controller = SessionController()
        controller.session_service = mock_session_service
        
        result = await controller.delete_session("test-session-id")
        
        assert result["success"] is True
        assert result["session_id"] == "test-session-id"
        mock_session_service.delete_session.assert_called_once_with("test-session-id")
    
    @pytest.mark.asyncio
    async def test_add_message_success(self, mock_session_service):
        """Test adding a message to a session successfully."""
        controller = SessionController()
        controller.session_service = mock_session_service
        
        result = await controller.add_message(
            session_id="test-session-id",
            role="user",
            content="Test message",
            provider="google",
            model="gemini-3.1-flash-lite-preview"
        )
        
        assert result["success"] is True
        assert result["data"]["role"] == "user"
        assert result["data"]["content"] == "Test message"
        mock_session_service.add_message.assert_called_once_with(
            session_id="test-session-id",
            role="user",
            content="Test message",
            provider="google",
            model="gemini-3.1-flash-lite-preview"
        )
    
    @pytest.mark.asyncio
    async def test_add_message_sanitization(self, mock_session_service):
        """Test that message content is sanitized."""
        controller = SessionController()
        controller.session_service = mock_session_service
        
        with patch.object(controller, 'sanitize_input') as mock_sanitize:
            mock_sanitize.return_value = "Sanitized message"
            
            result = await controller.add_message(
                session_id="test-session-id",
                role="user",
                content="Original message",
                provider="google",
                model="gemini-3.1-flash-lite-preview"
            )
            
            mock_sanitize.assert_called_once_with("Original message")
            assert result["data"]["content"] == "Sanitized message"


class TestSessionControllerIntegration:
    """Integration tests for SessionController endpoints."""
    
    def test_create_session_endpoint(self, client: TestClient, mock_session_service):
        """Test POST /chat/sessions endpoint."""
        with patch('mindflow_backend.api.v1.chat.session_controller') as mock_controller:
            mock_controller_instance = AsyncMock()
            mock_controller_instance.create_session.return_value = SessionResponse(
                success=True,
                id="test-session-id",
                title="Test Session"
            )
            mock_controller.return_value = mock_controller_instance
            
            request_data = {
                "title": "Test Session",
                "user_id": "test-user"
            }
            
            response = client.post("/v1/chat/sessions", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["id"] == "test-session-id"
    
    def test_get_session_endpoint(self, client: TestClient, mock_session_service):
        """Test GET /chat/sessions/{session_id} endpoint."""
        with patch('mindflow_backend.api.v1.chat.session_controller') as mock_controller:
            mock_controller_instance = AsyncMock()
            mock_controller_instance.get_session.return_value = SessionResponse(
                success=True,
                id="test-session-id",
                title="Test Session"
            )
            mock_controller.return_value = mock_controller_instance
            
            response = client.get("/v1/chat/sessions/test-session-id")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["id"] == "test-session-id"
    
    def test_list_sessions_endpoint(self, client: TestClient, mock_session_service):
        """Test GET /chat/sessions endpoint."""
        with patch('mindflow_backend.api.v1.chat.session_controller') as mock_controller:
            mock_controller_instance = AsyncMock()
            mock_controller_instance.list_sessions.return_value = SessionListResponse(
                success=True,
                items=[],
                total=0,
                limit=50,
                offset=0,
                has_next=False,
                has_prev=False
            )
            mock_controller.return_value = mock_controller_instance
            
            response = client.get("/v1/chat/sessions")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["total"] == 0
    
    def test_update_session_endpoint(self, client: TestClient, mock_session_service):
        """Test PUT /chat/sessions/{session_id} endpoint."""
        with patch('mindflow_backend.api.v1.chat.session_controller') as mock_controller:
            mock_controller_instance = AsyncMock()
            mock_controller_instance.update_session.return_value = SessionResponse(
                success=True,
                id="test-session-id",
                title="Updated Session"
            )
            mock_controller.return_value = mock_controller_instance
            
            request_data = {"title": "Updated Session"}
            
            response = client.put("/v1/chat/sessions/test-session-id", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["title"] == "Updated Session"
    
    def test_delete_session_endpoint(self, client: TestClient, mock_session_service):
        """Test DELETE /chat/sessions/{session_id} endpoint."""
        with patch('mindflow_backend.api.v1.chat.session_controller') as mock_controller:
            mock_controller_instance = AsyncMock()
            mock_controller_instance.delete_session.return_value = {
                "success": True,
                "session_id": "test-session-id"
            }
            mock_controller.return_value = mock_controller_instance
            
            response = client.delete("/v1/chat/sessions/test-session-id")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["session_id"] == "test-session-id"
    
    def test_add_message_endpoint(self, client: TestClient, mock_session_service):
        """Test POST /chat/sessions/{session_id}/messages endpoint."""
        with patch('mindflow_backend.api.v1.chat.session_controller') as mock_controller:
            mock_controller_instance = AsyncMock()
            mock_controller_instance.add_message.return_value = {
                "success": True,
                "data": {
                    "id": 1,
                    "role": "user",
                    "content": "Test message"
                }
            }
            mock_controller.return_value = mock_controller_instance
            
            response = client.post(
                "/v1/chat/sessions/test-session-id/messages",
                params={
                    "role": "user",
                    "content": "Test message",
                    "provider": "google",
                    "model": "gemini-3.1-flash-lite-preview"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["role"] == "user"


class TestSessionControllerErrorHandling:
    """Test error handling in SessionController."""
    
    @pytest.mark.asyncio
    async def test_create_session_error(self, mock_session_service):
        """Test error handling when creating session fails."""
        controller = SessionController()
        controller.session_service = mock_session_service
        mock_session_service.create_session.side_effect = Exception("Database error")
        
        request = AsyncMock()
        request.title = "Test Session"
        
        with pytest.raises(Exception):
            await controller.create_session(request)
    
    @pytest.mark.asyncio
    async def test_get_session_not_found_error(self, mock_session_service):
        """Test error handling when session not found."""
        controller = SessionController()
        controller.session_service = mock_session_service
        mock_session_service.get_session.side_effect = ValueError("Session not found")
        
        with pytest.raises(Exception):
            await controller.get_session("non-existent")
    
    @pytest.mark.asyncio
    async def test_add_message_invalid_role(self, mock_session_service):
        """Test error handling for invalid message role."""
        controller = SessionController()
        controller.session_service = mock_session_service
        mock_session_service.add_message.side_effect = ValueError("Invalid role")
        
        with pytest.raises(Exception):
            await controller.add_message(
                session_id="test-session",
                role="invalid_role",
                content="Test message"
            )
    
    @pytest.mark.asyncio
    async def test_delete_session_error(self, mock_session_service):
        """Test error handling when deleting session fails."""
        controller = SessionController()
        controller.session_service = mock_session_service
        mock_session_service.delete_session.side_effect = Exception("Delete failed")
        
        with pytest.raises(Exception):
            await controller.delete_session("test-session")
    
    @pytest.mark.asyncio
    async def test_update_session_not_found(self, mock_session_service):
        """Test error when updating non-existent session."""
        controller = SessionController()
        controller.session_service = mock_session_service
        mock_session_service.update_session.side_effect = ValueError("Session not found")
        
        request = AsyncMock()
        request.title = "Updated Title"
        
        with pytest.raises(Exception):
            await controller.update_session("non-existent", request)
