"""Agent system exceptions.

Simplified exception hierarchy for agent operations following best practices
from examples - direct inheritance from MindFlowError with clear context.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.core import MindFlowError


class AgentSystemError(MindFlowError):
    """Base exception for all agent system errors.
    
    Simplified to inherit directly from MindFlowError following best practices.
    """
    
    def __init__(
        self,
        message: str,
        *,
        agent_type: str | None = None,
        task_id: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            component="agents",
            **kwargs
        )
        self.agent_type = agent_type
        self.task_id = task_id


class ContextRetrievalError(AgentSystemError):
    """Raised when context retrieval fails."""
    
    def __init__(
        self,
        message: str,
        *,
        session_id: str | None = None,
        agent_id: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            **kwargs
        )
        self.session_id = session_id
        self.agent_id = agent_id


class AgentVectorStoreError(AgentSystemError):
    """Raised when agent vector store operations fail.
    
    Renamed from VectorStoreError to avoid conflicts with storage module.
    """
    
    def __init__(
        self,
        message: str,
        *,
        operation: str | None = None,
        session_id: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            **kwargs
        )
        self.operation = operation
        self.session_id = session_id


class SpecialistSelectionError(AgentSystemError):
    """Raised when specialist selection fails."""
    
    def __init__(
        self,
        message: str,
        *,
        task_id: str | None = None,
        task_description: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            task_id=task_id,
            **kwargs
        )
        self.task_description = task_description


class RuleEngineError(AgentSystemError):
    """Raised when rule evaluation fails."""
    
    def __init__(
        self,
        message: str,
        *,
        rule_name: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            **kwargs
        )
        self.rule_name = rule_name


class ContentAnalysisError(AgentSystemError):
    """Raised when content analysis fails."""
    
    def __init__(
        self,
        message: str,
        *,
        session_id: str | None = None,
        window_range: tuple[int, int] | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            **kwargs
        )
        self.session_id = session_id
        self.window_range = window_range


class ResultParsingError(AgentSystemError):
    """Raised when result parsing fails."""
    
    def __init__(
        self,
        message: str,
        *,
        content_type: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            **kwargs
        )
        self.content_type = content_type


class AgentCacheError(AgentSystemError):
    """Raised when agent cache operations fail.
    
    Renamed from CacheError to avoid conflicts with storage module.
    """
    
    def __init__(
        self,
        message: str,
        *,
        operation: str | None = None,
        key: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            **kwargs
        )
        self.operation = operation
        self.key = key


class AgentConfigurationError(AgentSystemError):
    """Raised when agent configuration is invalid.
    
    Renamed from ConfigurationError to avoid conflicts.
    """
    
    def __init__(
        self,
        message: str,
        *,
        config_key: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            **kwargs
        )
        self.config_key = config_key


class DependencyInjectionError(AgentSystemError):
    """Raised when dependency injection fails."""
    
    def __init__(
        self,
        message: str,
        *,
        dependency_type: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            **kwargs
        )
        self.dependency_type = dependency_type


class AgentRegistrationError(AgentSystemError):
    """Raised when agent registration fails."""
    
    def __init__(
        self,
        message: str,
        *,
        agent_type: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            agent_type=agent_type,
            **kwargs
        )


class AgentExecutionError(AgentSystemError):
    """Raised when agent execution fails."""
    
    def __init__(
        self,
        message: str,
        *,
        agent_type: str | None = None,
        task_id: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            agent_type=agent_type,
            task_id=task_id,
            **kwargs
        )


class AgentTimeoutError(AgentSystemError):
    """Raised when agent execution times out."""
    
    def __init__(
        self,
        message: str,
        *,
        agent_type: str | None = None,
        timeout_seconds: float | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            agent_type=agent_type,
            **kwargs
        )
        self.timeout_seconds = timeout_seconds


class AgentCommunicationError(AgentSystemError):
    """Raised when agent communication fails."""
    
    def __init__(
        self,
        message: str,
        *,
        source_agent: str | None = None,
        target_agent: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            **kwargs
        )
        self.source_agent = source_agent
        self.target_agent = target_agent


# Factory methods for common cases following examples pattern
class AgentErrors:
    """Factory methods for common agent errors."""
    
    @staticmethod
    def context_failed(session_id: str, agent_id: str | None = None) -> ContextRetrievalError:
        """Create context retrieval failure error."""
        return ContextRetrievalError(
            f"Context retrieval failed for session {session_id}",
            session_id=session_id,
            agent_id=agent_id
        )
    
    @staticmethod
    def vector_store_failed(operation: str, session_id: str | None = None) -> AgentVectorStoreError:
        """Create vector store failure error."""
        return AgentVectorStoreError(
            f"Vector store {operation} operation failed",
            operation=operation,
            session_id=session_id
        )
    
    @staticmethod
    def execution_timeout(agent_type: str, timeout_seconds: float) -> AgentTimeoutError:
        """Create execution timeout error."""
        return AgentTimeoutError(
            f"Agent {agent_type} execution timed out after {timeout_seconds}s",
            agent_type=agent_type,
            timeout_seconds=timeout_seconds
        )
    
    @staticmethod
    def execution_failed(agent_type: str, task_id: str | None = None, error_message: str | None = None) -> AgentExecutionError:
        """Create agent execution failure error."""
        message = f"Agent {agent_type} execution failed"
        if error_message:
            message += f": {error_message}"
        return AgentExecutionError(
            message,
            agent_type=agent_type,
            task_id=task_id
        )
    
    @staticmethod
    def communication_failed(source_agent: str, target_agent: str, error_message: str | None = None) -> AgentCommunicationError:
        """Create agent communication failure error."""
        message = f"Communication failed from {source_agent} to {target_agent}"
        if error_message:
            message += f": {error_message}"
        return AgentCommunicationError(
            message,
            source_agent=source_agent,
            target_agent=target_agent
        )
    
    @staticmethod
    def specialist_selection_failed(task_id: str, task_description: str | None = None) -> SpecialistSelectionError:
        """Create specialist selection failure error."""
        message = f"Specialist selection failed for task {task_id}"
        return SpecialistSelectionError(
            message,
            task_id=task_id,
            task_description=task_description
        )
    
    @staticmethod
    def cache_failed(operation: str, key: str | None = None) -> AgentCacheError:
        """Create cache operation failure error."""
        message = f"Cache {operation} operation failed"
        return AgentCacheError(
            message,
            operation=operation,
            key=key
        )
    
    @staticmethod
    def configuration_invalid(config_key: str, reason: str | None = None) -> AgentConfigurationError:
        """Create configuration error."""
        message = f"Invalid configuration for {config_key}"
        if reason:
            message += f": {reason}"
        return AgentConfigurationError(
            message,
            config_key=config_key
        )


# Backward compatibility aliases with deprecation warnings
import warnings

def _deprecated_alias(new_class, old_name):
    """Create a deprecated alias for backward compatibility."""
    class DeprecatedAlias(new_class):
        def __init__(self, *args, **kwargs):
            warnings.warn(
                f"{old_name} is deprecated. Use {new_class.__name__} instead.",
                DeprecationWarning,
                stacklevel=2
            )
            super().__init__(*args, **kwargs)
    
    DeprecatedAlias.__name__ = old_name
    return DeprecatedAlias

PersonalitySelectionError = _deprecated_alias(SpecialistSelectionError, "PersonalitySelectionError")
