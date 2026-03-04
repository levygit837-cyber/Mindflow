"""Custom exceptions for the agent system.

Provides specific exception types for better error handling
and debugging in the agent ecosystem.
"""

from __future__ import annotations


class AgentSystemError(Exception):
    """Base exception for all agent system errors."""
    pass


class ContextRetrievalError(AgentSystemError):
    """Raised when context retrieval fails."""
    
    def __init__(self, message: str, session_id: str | None = None, agent_id: str | None = None):
        super().__init__(message)
        self.session_id = session_id
        self.agent_id = agent_id


class VectorStoreError(AgentSystemError):
    """Raised when vector store operations fail."""
    
    def __init__(self, message: str, operation: str | None = None, session_id: str | None = None):
        super().__init__(message)
        self.operation = operation
        self.session_id = session_id


class PersonalitySelectionError(AgentSystemError):
    """Raised when personality selection fails."""
    
    def __init__(self, message: str, task_id: str | None = None, task_description: str | None = None):
        super().__init__(message)
        self.task_id = task_id
        self.task_description = task_description


class RuleEngineError(AgentSystemError):
    """Raised when rule evaluation fails."""
    
    def __init__(self, message: str, rule_name: str | None = None):
        super().__init__(message)
        self.rule_name = rule_name


class ContentAnalysisError(AgentSystemError):
    """Raised when content analysis fails."""
    
    def __init__(self, message: str, session_id: str | None = None, window_range: tuple[int, int] | None = None):
        super().__init__(message)
        self.session_id = session_id
        self.window_range = window_range


class ResultParsingError(AgentSystemError):
    """Raised when result parsing fails."""
    
    def __init__(self, message: str, content_type: str | None = None):
        super().__init__(message)
        self.content_type = content_type


class CacheError(AgentSystemError):
    """Raised when cache operations fail."""
    
    def __init__(self, message: str, operation: str | None = None, key: str | None = None):
        super().__init__(message)
        self.operation = operation
        self.key = key


class ConfigurationError(AgentSystemError):
    """Raised when configuration is invalid."""
    
    def __init__(self, message: str, config_key: str | None = None):
        super().__init__(message)
        self.config_key = config_key


class DependencyInjectionError(AgentSystemError):
    """Raised when dependency injection fails."""
    
    def __init__(self, message: str, dependency_type: str | None = None):
        super().__init__(message)
        self.dependency_type = dependency_type


class SessionReviewError(AgentSystemError):
    """Raised when session review operations fail."""
    
    def __init__(self, message: str, session_id: str | None = None, task_id: str | None = None):
        super().__init__(message)
        self.session_id = session_id
        self.task_id = task_id


class AgentRegistrationError(AgentSystemError):
    """Raised when agent registration fails."""
    
    def __init__(self, message: str, agent_type: str | None = None):
        super().__init__(message)
        self.agent_type = agent_type
