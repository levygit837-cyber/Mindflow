"""Shared test fixtures."""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

from omnimind_backend.main import app
from omnimind_backend.storage.postgresql.connection import async_session_factory
from omnimind_backend.storage.postgresql.models import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Set up test database."""
    # This would set up a test database
    # For now, we'll use in-memory SQLite or mock
    yield
    # Cleanup would go here


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_agent_service():
    """Mock agent service."""
    service = AsyncMock()
    service.process_agent_request.return_value = {
        "status": "processing",
        "agent_type": "analyst",
        "session_id": "test-session"
    }
    service.get_agent_capabilities.return_value = {
        "agent_type": "analyst",
        "capabilities": ["analysis", "coding"],
        "status": "active"
    }
    service.validate_agent_request.return_value = True
    service.list_available_agents.return_value = {
        "agents": {"analyst": {"status": "available"}},
        "total": 1,
        "available_count": 1
    }
    return service


@pytest.fixture
def mock_session_service():
    """Mock session service."""
    service = AsyncMock()
    service.create_session.return_value = {
        "id": "test-session-id",
        "title": "Test Session",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "message_count": 0,
        "status": "created"
    }
    service.get_session.return_value = {
        "id": "test-session-id",
        "title": "Test Session",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "messages": [],
        "message_count": 0,
        "status": "retrieved"
    }
    service.list_sessions.return_value = []
    service.update_session.return_value = {
        "id": "test-session-id",
        "title": "Updated Session",
        "updated_at": "2024-01-01T00:00:00Z",
        "status": "updated"
    }
    service.delete_session.return_value = True
    service.add_message.return_value = {
        "id": 1,
        "session_id": "test-session-id",
        "role": "user",
        "content": "Test message",
        "created_at": "2024-01-01T00:00:00Z",
        "status": "added"
    }
    return service


@pytest.fixture
def mock_orchestration_service():
    """Mock orchestration service."""
    service = AsyncMock()
    service.decompose_task.return_value = {
        "task_id": "test-task-id",
        "description": "Test task",
        "sub_tasks": [
            {
                "id": "subtask-1",
                "description": "Analyze requirements",
                "agent_type": "analyst",
                "priority": "high",
                "status": "pending"
            }
        ],
        "complexity_level": "medium",
        "dependencies": [],
        "estimated_duration": "10m",
        "status": "decomposed"
    }
    service.select_personality.return_value = {
        "task_id": "test-task-id",
        "selected_personality": "analyst",
        "rationale": "Task requires analysis",
        "confidence": 0.8,
        "alternatives": ["coder"],
        "switch_required": False
    }
    service.execute_dag.return_value = {
        "dag_id": "test-dag-id",
        "execution_id": "test-exec-id",
        "status": "running",
        "tasks_completed": 0,
        "total_tasks": 1,
        "results": [],
        "started_at": "2024-01-01T00:00:00Z"
    }
    service.get_execution_status.return_value = {
        "execution_id": "test-exec-id",
        "status": "completed",
        "progress": 100,
        "tasks_completed": 1,
        "total_tasks": 1,
        "started_at": "2024-01-01T00:00:00Z",
        "completed_at": "2024-01-01T00:05:00Z"
    }
    return service


@pytest.fixture
def mock_provider_service():
    """Mock provider service."""
    service = AsyncMock()
    service.list_providers.return_value = [
        {
            "id": "google",
            "name": "Google/VertexAI",
            "status": "active",
            "models": ["gemini-pro", "gemini-pro-vision"]
        },
        {
            "id": "anthropic",
            "name": "Anthropic",
            "status": "active",
            "models": ["claude-3-sonnet", "claude-3-opus"]
        }
    ]
    service.get_provider_models.return_value = [
        {"name": "gemini-pro", "status": "available"},
        {"name": "gemini-pro-vision", "status": "available"}
    ]
    service.test_provider_connection.return_value = {
        "provider_id": "google",
        "status": "success",
        "latency_ms": 150,
        "tested_at": "2024-01-01T00:00:00Z"
    }
    service.get_provider_config.return_value = {
        "provider_id": "google",
        "config": {
            "api_endpoint": "https://api.google.com",
            "timeout": 30,
            "max_tokens": 4096
        }
    }
    service.get_fallback_chain.return_value = ["google", "anthropic", "openai"]
    return service


@pytest.fixture
def mock_memory_service():
    """Mock memory service."""
    service = AsyncMock()
    service.get_agent_memory.return_value = {
        "agent_id": "test-agent",
        "session_id": "test-session",
        "memory_events": [],
        "token_count": 0,
        "window_index": 0
    }
    service.search_semantic_context.return_value = [
        {
            "content": "Relevant context",
            "score": 0.8,
            "source": "memory"
        }
    ]
    service.add_memory_event.return_value = {
        "id": 1,
        "agent_id": "test-agent",
        "session_id": "test-session",
        "role": "user",
        "content": "Test memory event",
        "created_at": "2024-01-01T00:00:00Z"
    }
    service.get_context_window.return_value = {
        "session_id": "test-session",
        "window_start": 0,
        "window_end": 1000,
        "content": "Context window content",
        "token_count": 500
    }
    service.create_memory_summary.return_value = {
        "agent_id": "test-agent",
        "session_id": "test-session",
        "window_range": (0, 1000),
        "summary": "Test summary",
        "key_points": ["Point 1", "Point 2"],
        "coverage_ratio": 0.8,
        "created_at": "2024-01-01T00:00:00Z"
    }
    return service


@pytest.fixture
def sample_agent_request():
    """Sample agent chat request."""
    return {
        "message": "Test message",
        "agent_type": "analyst",
        "provider": "google",
        "model": "gemini-pro",
        "session_id": "test-session",
        "orchestrate": False
    }


@pytest.fixture
def sample_session_request():
    """Sample session creation request."""
    return {
        "title": "Test Session",
        "user_id": "test-user",
        "metadata": {"key": "value"}
    }


@pytest.fixture
def sample_orchestration_request():
    """Sample orchestration request."""
    return {
        "task_description": "Analyze the codebase",
        "complexity_level": "medium",
        "agent_sequence": ["analyst", "coder"],
        "session_id": "test-session"
    }


@pytest.fixture
def sample_memory_request():
    """Sample memory search request."""
    return {
        "query": "Test search query",
        "session_id": "test-session",
        "agent_id": "test-agent",
        "search_type": "semantic",
        "top_k": 5,
        "min_score": 0.3
    }
