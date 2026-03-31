"""Test cases for network utilities."""


import pytest

from mindflow_backend.utils.network import (
    add_query_params,
    build_url,
    find_free_port,
    get_port_manager,
    is_port_open,
    parse_url,
    retry_on_error,
)


class TestNetworkUtilities:
    """Test network utility functions."""

    def test_retry_on_error_success(self):
        """Test retry decorator with successful function."""
        call_count = 0
        
        @retry_on_error(max_attempts=3, delay=0.01)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "success"
        
        result = failing_function()
        assert result == "success"
        assert call_count == 2

    def test_retry_on_error_failure(self):
        """Test retry decorator with persistent failure."""
        @retry_on_error(max_attempts=2, delay=0.01)
        def always_failing_function():
            raise ValueError("Persistent failure")
        
        with pytest.raises(ValueError):
            always_failing_function()

    def test_get_port_manager(self):
        """Test port manager singleton."""
        pm1 = get_port_manager()
        pm2 = get_port_manager()
        assert pm1 is pm2

    @pytest.mark.asyncio
    async def test_port_allocation(self):
        """Test port allocation."""
        pm = get_port_manager()
        
        # Test port allocation
        port = await pm.allocate_port()
        assert isinstance(port, int)
        assert 8000 <= port <= 9000  # Default range
        
        # Test port release
        await pm.release_port(port)
        
        # Test preferred port
        preferred_port = 8888
        allocated = await pm.allocate_port(preferred_port)
        assert allocated == preferred_port
        await pm.release_port(allocated)

    def test_is_port_open(self):
        """Test port availability check."""
        # Test with a port that's likely closed
        assert is_port_open(65432) is False
        
        # Test with localhost port 80 (may or may not be open)
        result = is_port_open(80)
        assert isinstance(result, bool)

    def test_find_free_port(self):
        """Test free port finding."""
        port = find_free_port(8000, 8100)
        assert isinstance(port, int)
        assert 8000 <= port <= 8100

    def test_parse_url(self):
        """Test URL parsing."""
        url = "https://www.example.com:8080/path?query=value#fragment"
        result = parse_url(url)
        
        assert result.scheme == "https"
        assert result.netloc == "www.example.com:8080"
        assert result.path == "/path"
        assert "query=value" in result.query

    def test_build_url(self):
        """Test URL building."""
        base = "https://www.example.com"
        path = "/api/v1"
        params = {"key": "value", "limit": 10}
        
        result = build_url(base, path, params)
        assert "https://www.example.com/api/v1" in result
        assert "key=value" in result
        assert "limit=10" in result

    def test_add_query_params(self):
        """Test query parameter addition."""
        url = "https://example.com/path"
        params = {"param1": "value1", "param2": "value2"}
        
        result = add_query_params(url, params)
        assert "param1=value1" in result
        assert "param2=value2" in result

    def test_retry_on_error_with_custom_exception(self):
        """Test retry with specific exception type."""
        call_count = 0
        
        @retry_on_error(max_attempts=3, exceptions=(ValueError,))
        def function_with_value_error():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry me")
            return "success"
        
        result = function_with_value_error()
        assert result == "success"

    def test_retry_on_error_wrong_exception(self):
        """Test retry doesn't catch wrong exception type."""
        @retry_on_error(max_attempts=3, exceptions=(ValueError,))
        def function_with_type_error():
            raise TypeError("Don't retry me")
        
        with pytest.raises(TypeError):
            function_with_type_error()

    @pytest.mark.asyncio
    async def test_port_manager_stats(self):
        """Test port manager statistics."""
        pm = get_port_manager()
        stats = pm.get_stats()
        
        assert "port_range" in stats
        assert "total_ports" in stats
        assert "allocated_ports" in stats
        assert "available_ports" in stats
        assert "utilization" in stats
