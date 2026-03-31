"""Session manager interface for MindFlow agents.

Defines the contract for session lifecycle management, context
governance, and window analysis based on session_contracts.py schemas.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from mindflow_backend.schemas.session.contracts import (
    ContextControlResult,
    ContextWindowInfo,
    RetrievedContext,
    SessionReview,
    SubSessionReview,
    SummarizationReview,
)


@runtime_checkable
class SessionManagerContract(Protocol):
    """Contract for session management and context governance.
    
    Handles session lifecycle, context window management,
    and context governance operations.
    """

    async def create_session(
        self,
        token_range: tuple[int, int],
        execution_window: tuple[int, int],
        context_window: tuple[int, int],
        mode: str = "normal",
        parent_session_id: UUID | None = None,
    ) -> SessionReview:
        """Create a new session review.
        
        Args:
            token_range: Token range for the session.
            execution_window: Execution token boundaries.
            context_window: Analysis token boundaries.
            mode: Session execution mode.
            parent_session_id: Parent session if this is a sub-session.
            
        Returns:
            Created session review.
        """
        ...

    async def manage_context(
        self,
        session_id: UUID,
        current_position: int,
        window_size: int = 10000,
    ) -> ContextControlResult:
        """Manage context flow and window advancement.
        
        Args:
            session_id: Session identifier.
            current_position: Current position in token stream.
            window_size: Size of context windows.
            
        Returns:
            Context control result with action taken.
        """
        ...

    async def analyze_window(
        self,
        context: ReviewExecutionContext,
        analysis_type: str = "comprehensive",
    ) -> str:
        """Analyze session window and extract insights.
        
        Args:
            context: Execution context for window analysis.
            analysis_type: Type of analysis to perform.
            
        Returns:
            Analysis results with insights and actions.
        """
        ...

    async def retrieve_context(
        self,
        session_id: UUID,
        query: str,
        retrieval_mode: str = "range",
        context_window: tuple[int, int] = (0, 100000),
        max_results: int = 10,
    ) -> RetrievedContext:
        """Retrieve relevant context for analysis.
        
        Args:
            session_id: Session identifier.
            query: Query for semantic retrieval.
            retrieval_mode: Mode of retrieval (range, topic, semantic).
            context_window: Context analysis window.
            max_results: Maximum results to return.
            
        Returns:
            Retrieved context with relevance scores.
        """
        ...

    async def get_context_window_info(
        self,
        session_id: UUID,
        current_position: int,
        window_size: int,
        total_tokens: int,
    ) -> ContextWindowInfo:
        """Get information about current and adjacent context windows.
        
        Args:
            session_id: Session identifier.
            current_position: Current position in token stream.
            window_size: Size of context windows.
            total_tokens: Total tokens in session.
            
        Returns:
            Context window information.
        """
        ...

    async def create_sub_session(
        self,
        parent_session_id: UUID,
        token_sub_range: str,
        execution_window: tuple[int, int],
        relationship_type: str = "sequential",
        dependency_order: int | None = None,
    ) -> SubSessionReview:
        """Create a sub-session within a parent session.
        
        Args:
            parent_session_id: Parent session identifier.
            token_sub_range: Token range within parent.
            execution_window: Execution window for sub-session.
            relationship_type: Type of relationship to parent.
            dependency_order: Order for dependency relationships.
            
        Returns:
            Created sub-session review.
        """
        ...

    async def advance_window(
        self,
        session_id: UUID,
        step_size: int = 10000,
    ) -> ContextControlResult:
        """Advance to the next context window.
        
        Args:
            session_id: Session identifier.
            step_size: Size of advancement step.
            
        Returns:
            Context control result with new window info.
        """
        ...

    async def summarize_context(
        self,
        session_id: UUID,
        context_range: tuple[int, int],
        summary_type: str = "comprehensive",
    ) -> SummarizationReview:
        """Summarize context from a specific range.
        
        Args:
            session_id: Session identifier.
            context_range: Token range to summarize.
            summary_type: Type of summary to generate.
            
        Returns:
            Summarization review with insights.
        """
        ...

    async def should_create_session(
        self,
        current_position: int,
        window_size: int,
        total_tokens: int,
        session_threshold: int = 50000,
    ) -> bool:
        """Determine if a new session should be created.
        
        Args:
            current_position: Current position in token stream.
            window_size: Size of context windows.
            total_tokens: Total tokens processed.
            session_threshold: Threshold for session creation.
            
        Returns:
            True if new session should be created.
        """
        ...

    async def get_session_hierarchy(
        self,
        session_id: UUID,
    ) -> dict[str, Any]:
        """Get hierarchical relationship information for a session.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            Hierarchy information with parent and child relationships.
        """
        ...

    async def update_session_progress(
        self,
        session_id: UUID,
        tokens_processed: int,
        window_position: int,
    ) -> SessionReview:
        """Update session progress information.
        
        Args:
            session_id: Session identifier.
            tokens_processed: Total tokens processed.
            window_position: Current window position.
            
        Returns:
            Updated session review.
        """
        ...

    async def close_session(
        self,
        session_id: UUID,
        final_summary: str = "",
    ) -> SessionReview:
        """Close a session and finalize its state.
        
        Args:
            session_id: Session identifier.
            final_summary: Final summary of session work.
            
        Returns:
            Finalized session review.
        """
        ...

    async def get_session_metrics(
        self,
        session_id: UUID,
    ) -> dict[str, float]:
        """Get performance metrics for a session.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            Session performance metrics.
        """
        ...
