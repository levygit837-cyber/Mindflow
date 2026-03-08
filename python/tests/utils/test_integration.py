"""Integration tests for utils restructure.

Tests that verify the migration from old utils locations to new centralized structure.
"""

import pytest
from mindflow_backend.utils.core import estimate_token_count
from mindflow_backend.utils.formatting import format_sse, extract_json_from_response
from mindflow_backend.utils.validation import validate_memory_data, validate_search_query
from mindflow_backend.utils.network import retry_on_error, get_port_manager
from mindflow_backend.utils.monitoring import HealthStatus, health_check_database


class TestUtilsIntegration:
    """Test that all migrated utilities work correctly."""

    def test_memory_utils_migration(self):
        """Test memory utils migrated to core."""
        # Test estimate_token_count (from memory.utils.tokenization)
        result = estimate_token_count("Hello world, this is a test")
        assert result > 0
        assert isinstance(result, int)

    def test_format_sse_migration(self):
        """Test SSE formatting migrated from api.sse."""
        data = {"message": "Hello", "type": "event"}
        result = format_sse(data)
        assert "data:" in result
        assert "Hello" in result
        assert "event" in result

    def test_extract_json_migration(self):
        """Test JSON extraction migrated from decomposition.utils."""
        content = '```json\n{"key": "value"}\n```'
        result = extract_json_from_response(content)
        assert result == '{"key": "value"}'

    def test_validation_migration(self):
        """Test validation migrated from memory.utils."""
        # Test memory data validation
        data = {
            "session_id": "test_session",
            "agent_id": "test_agent",
            "content": "Test content"
        }
        errors = validate_memory_data(data)
        assert len(errors) == 0

        # Test search query validation
        errors = validate_search_query("test query")
        assert len(errors) == 0

    def test_retry_migration(self):
        """Test retry migrated from utils.error_handling."""
        call_count = 0
        
        @retry_on_error(max_attempts=2, delay=0.01)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Retry once")
            return "success"
        
        result = test_function()
        assert result == "success"
        assert call_count == 2

    def test_port_manager_migration(self):
        """Test port manager migrated from agents.research.utils."""
        pm = get_port_manager()
        assert pm is not None
        
        stats = pm.get_stats()
        assert "port_range" in stats
        assert "total_ports" in stats

    def test_health_check_migration(self):
        """Test health checks migrated from agents.research.utils."""
        status = health_check_database("sqlite:///memory")
        assert isinstance(status, HealthStatus)
        assert status.name == "database"

    def test_import_consistency(self):
        """Test that all imports work consistently."""
        # Test that we can import from all new locations
        from mindflow_backend.utils.core import (
            format_datetime_iso, 
            slugify, 
            generate_uuid4,
            estimate_token_count
        )
        
        from mindflow_backend.utils.validation import (
            validate_email,
            validate_url,
            sanitize_string
        )
        
        from mindflow_backend.utils.formatting import (
            format_sse,
            extract_json_from_response
        )
        
        from mindflow_backend.utils.network import (
            retry_on_error,
            get_port_manager,
            parse_url
        )
        
        from mindflow_backend.utils.monitoring import (
            HealthStatus,
            health_check_database
        )
        
        # All imports should work without errors
        assert callable(format_datetime_iso)
        assert callable(slugify)
        assert callable(generate_uuid4)
        assert callable(estimate_token_count)
        assert callable(validate_email)
        assert callable(validate_url)
        assert callable(sanitize_string)
        assert callable(format_sse)
        assert callable(extract_json_from_response)
        assert callable(retry_on_error)
        assert callable(get_port_manager)
        assert callable(parse_url)
        assert HealthStatus is not None
        assert callable(health_check_database)

    def test_backward_compatibility(self):
        """Test that memory module still exports estimate_token_count."""
        from mindflow_backend import estimate_token_count as memory_token_count
        from mindflow_backend.utils.core import estimate_token_count as utils_token_count
        
        text = "Test backward compatibility"
        memory_result = memory_token_count(text)
        utils_result = utils_token_count(text)
        
        assert memory_result == utils_result

    def test_no_old_imports(self):
        """Test that old import paths no longer work."""
        # These imports should fail
        with pytest.raises(ImportError):
            from mindflow_backend.memory.utils.validation import validate_memory_data
        
        with pytest.raises(ImportError):
            from mindflow_backend.agents.research.utils.port_manager import get_port_manager
        
        with pytest.raises(ImportError):
            from mindflow_backend.api.sse import format_sse
        
        with pytest.raises(ImportError):
            from mindflow_backend.decomposition.utils import extract_json_from_response
