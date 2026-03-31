"""gRPC metrics interceptor for automatic metrics collection.

Intercepts gRPC calls to automatically collect request metrics,
latency data, and error rates without requiring manual instrumentation.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import Any

import grpc
from grpc import HandlerCallDetails, ServicerContext
from mindflow_backend.grpc.monitoring.metrics import GrpcMetricsCollector
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class MetricsInterceptor(grpc.ServerInterceptor):
    """gRPC server interceptor for automatic metrics collection."""
    
    def __init__(self, metrics_collector: GrpcMetricsCollector, collect_business_metrics: bool = True):
        self.metrics = metrics_collector
        self.collect_business_metrics = collect_business_metrics
    
    def intercept_service(
        self,
        continuation: Callable[[Any, ServicerContext], Any],
        handler_call_details: HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        """Intercept service calls and collect metrics."""
        
        def intercepted_handler(request: Any, context: ServicerContext) -> Any:
            # Generate unique request ID for tracking
            request_id = str(uuid.uuid4())
            method_name = handler_call_details.method.split('/')[-1]  # Extract method name
            
            # Extract metadata for business metrics
            user_id = None
            session_id = None
            if context and hasattr(context, 'invocation_metadata') and context.invocation_metadata:
                metadata = dict(context.invocation_metadata)
                user_id = metadata.get('user-id')
                session_id = metadata.get('session-id')
            
            # Record request start
            start_time = self.metrics.record_request_start(method_name, request_id)
            
            # Log request start
            _logger.info(
                "grpc_request_started",
                method=method_name,
                request_id=request_id,
                user_id=user_id,
                session_id=session_id,
            )
            
            try:
                # Execute the actual service method
                response = continuation(request, context)
                
                # For streaming responses, we need to wrap the generator
                if hasattr(response, '__aiter__'):
                    return self._wrap_streaming_response(
                        response, method_name, request_id, start_time, user_id, session_id
                    )
                else:
                    # For unary responses, record completion immediately
                    self._record_request_completion(
                        method_name, request_id, start_time, 'OK', user_id, session_id
                    )
                    return response
                    
            except Exception as exc:
                # Record error
                status = self._get_error_status(exc)
                self._record_request_completion(
                    method_name, request_id, start_time, status, user_id, session_id
                )
                
                # Log error
                _logger.error(
                    "grpc_request_error",
                    method=method_name,
                    request_id=request_id,
                    error=str(exc),
                    status=status,
                    user_id=user_id,
                    session_id=session_id,
                )
                
                raise
        
        return intercepted_handler
    
    async def _wrap_streaming_response(
        self,
        response_generator,
        method_name: str,
        request_id: str,
        start_time: float,
        user_id: str | None = None,
        session_id: str | None = None,
    ):
        """Wrap streaming response to collect metrics when stream completes."""
        message_count = 0
        first_message_time = None
        
        try:
            async for message in response_generator:
                if first_message_time is None:
                    first_message_time = time.time()
                
                message_count += 1
                yield message
            
            # Record successful completion
            self._record_request_completion(
                method_name, request_id, start_time, 'OK', user_id, session_id,
                message_count=message_count,
                first_message_time=first_message_time
            )
            
        except Exception as exc:
            # Record error
            status = self._get_error_status(exc)
            self._record_request_completion(
                method_name, request_id, start_time, status, user_id, session_id,
                message_count=message_count,
                first_message_time=first_message_time
            )
            raise
    
    def _record_request_completion(
        self,
        method_name: str,
        request_id: str,
        start_time: float,
        status: str,
        user_id: str | None = None,
        session_id: str | None = None,
        message_count: int = 0,
        first_message_time: float | None = None,
    ):
        """Record request completion metrics."""
        # Record basic request metrics
        self.metrics.record_request_complete(method_name, request_id, start_time, status)
        
        # Record business metrics if enabled
        if self.collect_business_metrics:
            self._record_business_metrics(
                method_name, status, user_id, session_id, message_count, first_message_time
            )
        
        # Log completion
        duration = time.time() - start_time
        _logger.info(
            "grpc_request_completed",
            method=method_name,
            request_id=request_id,
            status=status,
            duration=duration,
            user_id=user_id,
            session_id=session_id,
            message_count=message_count,
        )
    
    def _record_business_metrics(
        self,
        method_name: str,
        status: str,
        user_id: str | None = None,
        session_id: str | None = None,
        message_count: int = 0,
        first_message_time: float | None = None,
    ):
        """Record business-specific metrics."""
        # Record chat requests
        if method_name == 'StreamChat' and status == 'OK':
            self.metrics.record_chat_request()
            
            # Record session duration if we have session info
            if session_id and first_message_time:
                session_duration = time.time() - first_message_time
                self.metrics.record_session_duration(session_duration)
        
        # Could add more business metrics here based on method and metadata
        # For example: agent type, operation type, etc.
    
    def _get_error_status(self, exc: Exception) -> str:
        """Convert exception to gRPC status string."""
        if isinstance(exc, grpc.RpcError):
            return exc.code().name
        elif isinstance(exc, ValueError):
            return 'INVALID_ARGUMENT'
        elif isinstance(exc, KeyError):
            return 'NOT_FOUND'
        elif isinstance(exc, PermissionError):
            return 'PERMISSION_DENIED'
        elif isinstance(exc, TimeoutError):
            return 'DEADLINE_EXCEEDED'
        elif isinstance(exc, ConnectionError):
            return 'UNAVAILABLE'
        else:
            return 'INTERNAL'


class ClientMetricsInterceptor:
    """Client-side interceptor for collecting client metrics."""
    
    def __init__(self, metrics_collector: GrpcMetricsCollector):
        self.metrics = metrics_collector
    
    def intercept_unary_unary(self, continuation, client_call_details, request):
        """Intercept unary-unary calls."""
        start_time = time.time()
        method_name = client_call_details.method.split('/')[-1]
        
        try:
            response = continuation(client_call_details, request)
            duration = time.time() - start_time
            self.metrics.record_request_complete(method_name, "client_call", start_time, 'OK')
            return response
        except Exception as exc:
            duration = time.time() - start_time
            status = self._get_error_status(exc)
            self.metrics.record_request_complete(method_name, "client_call", start_time, status)
            raise
    
    def intercept_unary_stream(self, continuation, client_call_details, request):
        """Intercept unary-stream calls."""
        start_time = time.time()
        method_name = client_call_details.method.split('/')[-1]
        
        try:
            response_iterator = continuation(client_call_details, request)
            return self._wrap_client_stream(
                response_iterator, method_name, start_time
            )
        except Exception as exc:
            status = self._get_error_status(exc)
            self.metrics.record_request_complete(method_name, "client_call", start_time, status)
            raise
    
    async def _wrap_client_stream(self, response_iterator, method_name: str, start_time: float):
        """Wrap client streaming response."""
        try:
            async for response in response_iterator:
                yield response
            
            # Record successful completion
            self.metrics.record_request_complete(method_name, "client_call", start_time, 'OK')
            
        except Exception as exc:
            status = self._get_error_status(exc)
            self.metrics.record_request_complete(method_name, "client_call", start_time, status)
            raise
    
    def _get_error_status(self, exc: Exception) -> str:
        """Convert exception to status string."""
        if isinstance(exc, grpc.RpcError):
            return exc.code().name
        else:
            return 'CLIENT_ERROR'
