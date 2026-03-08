"""Tests for error handling setup utilities."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI

from mindflow_backend.utils.error_setup import (
    setup_fastapi_error_handling,
    setup_grpc_error_handling,
    setup_comprehensive_error_handling,
    create_error_handling_config,
)


class TestErrorSetup:
    """Test error handling setup utilities."""
    
    def test_create_error_handling_config_default(self):
        """Test creating default error handling configuration."""
        config = create_error_handling_config()
        
        assert config["debug"] is False
        assert config["log_level"] == "INFO"
        assert config["enable_metrics"] is False
        assert config["enable_tracing"] is False
        assert "middleware_config" in config
        assert "logging_config" in config
    
    def test_create_error_handling_config_custom(self):
        """Test creating custom error handling configuration."""
        config = create_error_handling_config(
            debug=True,
            log_level="DEBUG",
            enable_metrics=True,
            enable_tracing=True,
        )
        
        assert config["debug"] is True
        assert config["log_level"] == "DEBUG"
        assert config["enable_metrics"] is True
        assert config["enable_tracing"] is True
        assert config["middleware_config"]["fastapi"]["debug"] is True
        assert config["middleware_config"]["grpc"]["debug"] is True
    
    def test_setup_fastapi_error_handling_basic(self):
        """Test basic FastAPI error handling setup."""
        app = FastAPI()
        
        with patch('mindflow_backend.utils.error_setup.ErrorHandlerMiddleware') as mock_middleware:
            setup_fastapi_error_handling(app, debug=True)
            
            # Verify middleware was added
            mock_middleware.assert_called_once_with(debug=True)
            app.user_middleware.clear()  # Clean up
    
    def test_setup_fastapi_error_handling_with_cors(self):
        """Test FastAPI setup with custom CORS configuration."""
        app = FastAPI()
        
        with patch('mindflow_backend.utils.error_setup.ErrorHandlerMiddleware') as mock_error_middleware, \
             patch('mindflow_backend.utils.error_setup.CORSMiddleware') as mock_cors_middleware:
            
            setup_fastapi_error_handling(
                app,
                debug=False,
                cors_origins=["http://localhost:3000"],
                cors_allow_credentials=False,
                cors_allow_methods=["GET", "POST"],
                cors_allow_headers=["Content-Type"],
            )
            
            # Verify error middleware was added
            mock_error_middleware.assert_called_once_with(debug=False)
            
            # Verify CORS middleware was added with correct parameters
            mock_cors_middleware.assert_called_once_with(
                allow_origins=["http://localhost:3000"],
                allow_credentials=False,
                allow_methods=["GET", "POST"],
                allow_headers=["Content-Type"],
            )
            
            app.user_middleware.clear()  # Clean up
    
    def test_setup_fastapi_error_handling_cors_unavailable(self):
        """Test FastAPI setup when CORS middleware is not available."""
        app = FastAPI()
        
        with patch('mindflow_backend.utils.error_setup.ErrorHandlerMiddleware') as mock_middleware, \
             patch('mindflow_backend.utils.error_setup.CORSMiddleware', side_effect=ImportError):
            
            setup_fastapi_error_handling(app, debug=True)
            
            # Should still add error middleware even if CORS fails
            mock_middleware.assert_called_once_with(debug=True)
            
            app.user_middleware.clear()  # Clean up
    
    def test_setup_grpc_error_handling_basic(self):
        """Test basic gRPC error handling setup."""
        mock_server = MagicMock()
        
        with patch('mindflow_backend.utils.error_setup.ErrorHandlerInterceptor') as mock_interceptor:
            setup_grpc_error_handling(mock_server, debug=True, port=50052, host="0.0.0.0:")
            
            # Verify interceptor was added
            mock_interceptor.assert_called_once_with(debug=True)
            mock_server.add_interceptor.assert_called_once_with(mock_interceptor.return_value)
            
            # Verify port was added
            mock_server.add_insecure_port.assert_called_once_with("0.0.0.0:50052")
    
    def test_setup_grpc_error_handling_defaults(self):
        """Test gRPC setup with default parameters."""
        mock_server = MagicMock()
        
        with patch('mindflow_backend.utils.error_setup.ErrorHandlerInterceptor'):
            setup_grpc_error_handling(mock_server)
            
            # Verify default port was used
            mock_server.add_insecure_port.assert_called_once_with("[::]:50051")
    
    def test_setup_comprehensive_error_handling_both(self):
        """Test comprehensive setup with both FastAPI and gRPC."""
        app = FastAPI()
        mock_server = MagicMock()
        
        with patch('mindflow_backend.utils.error_setup.setup_fastapi_error_handling') as mock_fastapi, \
             patch('mindflow_backend.utils.error_setup.setup_grpc_error_handling') as mock_grpc:
            
            result = setup_comprehensive_error_handling(
                fastapi_app=app,
                grpc_server=mock_server,
                debug=True,
                fastapi_cors_origins=["http://localhost:3000"],
                grpc_port=50052,
                grpc_host="0.0.0.0:",
            )
            
            # Verify both setups were called
            mock_fastapi.assert_called_once_with(
                app,
                debug=True,
                cors_origins=["http://localhost:3000"],
            )
            
            mock_grpc.assert_called_once_with(
                mock_server,
                debug=True,
                port=50052,
                host="0.0.0.0:",
            )
            
            # Verify return status
            assert result["fastapi_setup"] is True
            assert result["grpc_setup"] is True
            assert result["debug_enabled"] is True
            assert result["configuration"]["fastapi_cors_origins"] == ["http://localhost:3000"]
            assert result["configuration"]["grpc_port"] == 50052
            assert result["configuration"]["grpc_host"] == "0.0.0.0:"
    
    def test_setup_comprehensive_error_handling_fastapi_only(self):
        """Test comprehensive setup with only FastAPI."""
        app = FastAPI()
        
        with patch('mindflow_backend.utils.error_setup.setup_fastapi_error_handling') as mock_fastapi:
            result = setup_comprehensive_error_handling(fastapi_app=app)
            
            # Verify only FastAPI setup was called
            mock_fastapi.assert_called_once()
            
            # Verify return status
            assert result["fastapi_setup"] is True
            assert result["grpc_setup"] is False
    
    def test_setup_comprehensive_error_handling_grpc_only(self):
        """Test comprehensive setup with only gRPC."""
        mock_server = MagicMock()
        
        with patch('mindflow_backend.utils.error_setup.setup_grpc_error_handling') as mock_grpc:
            result = setup_comprehensive_error_handling(grpc_server=mock_server)
            
            # Verify only gRPC setup was called
            mock_grpc.assert_called_once()
            
            # Verify return status
            assert result["fastapi_setup"] is False
            assert result["grpc_setup"] is True
    
    def test_setup_comprehensive_error_handling_none(self):
        """Test comprehensive setup with no servers."""
        result = setup_comprehensive_error_handling()
        
        # Verify no setups were called
        assert result["fastapi_setup"] is False
        assert result["grpc_setup"] is False
        assert result["debug_enabled"] is False
        assert result["configuration"]["fastapi_cors_origins"] == ["*"]
        assert result["configuration"]["grpc_port"] == 50051
        assert result["configuration"]["grpc_host"] == "[::]:"


class TestIntegration:
    """Integration tests for error handling setup."""
    
    def test_fastapi_integration(self):
        """Test actual FastAPI integration."""
        app = FastAPI()
        
        # This should not raise an exception
        setup_fastapi_error_handling(app, debug=False)
        
        # Verify middleware was added (indirectly)
        assert len(app.user_middleware) > 0
        
        # Clean up
        app.user_middleware.clear()
    
    @pytest.mark.asyncio
    async def test_fastapi_middleware_functionality(self):
        """Test that FastAPI middleware actually handles errors."""
        from fastapi import HTTPException
        from fastapi.testclient import TestClient
        
        app = FastAPI()
        setup_fastapi_error_handling(app, debug=True)
        
        @app.get("/test-error")
        async def test_error():
            raise HTTPException(status_code=400, detail="Test error")
        
        client = TestClient(app)
        response = client.get("/test-error")
        
        # Should return structured error response
        assert response.status_code == 400
        assert "error" in response.json()
        
        # Clean up
        app.user_middleware.clear()


if __name__ == "__main__":
    pytest.main([__file__])
