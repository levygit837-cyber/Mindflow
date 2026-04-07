"""
Memory command - manage memory system (stats, clear, search, export).
"""

from mindflow_backend.commands.types import (
    CommandCategory,
    CommandContext,
    CommandMetadata,
    CommandResult,
)


class MemoryCommand:
    """
    Manage memory system.

    Usage:
        /memory stats                - Show memory statistics
        /memory clear <session_id>   - Clear session memory
        /memory search <query>       - Search memory
        /memory export <session_id>  - Export session memory
    """

    metadata = CommandMetadata(
        name="memory",
        description="Manage memory system",
        category=CommandCategory.MEMORY,
        aliases=("mem",),
        examples=(
            "/memory stats",
            "/memory clear session-123",
            "/memory search authentication",
            "/memory export session-123",
        ),
    )

    async def execute(self, context: CommandContext) -> CommandResult:
        """Execute memory command."""
        if not context.args:
            return CommandResult(
                success=False,
                message="Missing subcommand. Usage: /memory <stats|clear|search|export>",
                error="MISSING_SUBCOMMAND",
            )

        subcommand = context.args[0].lower()

        if subcommand == "stats":
            return await self._memory_stats()
        elif subcommand == "clear":
            if len(context.args) < 2:
                return CommandResult(
                    success=False,
                    message="Missing session ID. Usage: /memory clear <session_id>",
                    error="MISSING_SESSION_ID",
                )
            session_id = context.args[1]
            return await self._clear_memory(session_id)
        elif subcommand == "search":
            if len(context.args) < 2:
                return CommandResult(
                    success=False,
                    message="Missing search query. Usage: /memory search <query>",
                    error="MISSING_QUERY",
                )
            query = " ".join(context.args[1:])
            return await self._search_memory(query, context)
        elif subcommand == "export":
            if len(context.args) < 2:
                return CommandResult(
                    success=False,
                    message="Missing session ID. Usage: /memory export <session_id>",
                    error="MISSING_SESSION_ID",
                )
            session_id = context.args[1]
            return await self._export_memory(session_id)
        else:
            return CommandResult(
                success=False,
                message=f"Unknown subcommand '{subcommand}'. Valid: stats, clear, search, export",
                error="INVALID_SUBCOMMAND",
            )

    async def _memory_stats(self) -> CommandResult:
        """Show memory statistics using actual memory service."""
        try:
            from mindflow_backend.services.memory import get_memory_facade_service
            from mindflow_backend.infra.database.connection import get_db_session
            
            memory_service = get_memory_facade_service()
            
            async with get_db_session() as session:
                # Get memory statistics
                stats = await memory_service.get_memory_stats(session)
                
                total_entries = stats.get("total_entries", 0)
                sessions = stats.get("sessions", 0)
                cache_size_mb = stats.get("cache_size_mb", 0)
                
                message = (
                    f"Memory Statistics:\n"
                    f"  Total entries: {total_entries}\n"
                    f"  Sessions: {sessions}\n"
                    f"  Cache size: {cache_size_mb:.2f} MB"
                )
                
                return CommandResult(
                    success=True,
                    message=message,
                    data=stats,
                )
                
        except Exception as exc:
            _logger.warning("memory_stats_failed", error=str(exc))
            # Return fallback stats
            return CommandResult(
                success=True,
                message="Memory Statistics:\n  Total entries: 0\n  Sessions: 0\n  Cache size: 0 MB",
                data={
                    "total_entries": 0,
                    "sessions": 0,
                    "cache_size_mb": 0,
                    "error": str(exc),
                },
            )

    async def _clear_memory(self, session_id: str) -> CommandResult:
        """Clear session memory using actual memory service."""
        try:
            from mindflow_backend.services.memory import get_memory_facade_service
            from mindflow_backend.infra.database.connection import get_db_session
            
            memory_service = get_memory_facade_service()
            
            async with get_db_session() as session:
                # Clear memory for the session
                cleared = await memory_service.clear_session_memory(session, session_id)
                
                if cleared:
                    return CommandResult(
                        success=True,
                        message=f"Memory cleared for session: {session_id}",
                        data={"session_id": session_id, "cleared": True},
                    )
                else:
                    return CommandResult(
                        success=False,
                        message=f"No memory found for session: {session_id}",
                        error="NO_MEMORY_FOUND",
                        data={"session_id": session_id},
                    )
                
        except Exception as exc:
            _logger.error("memory_clear_failed", session_id=session_id, error=str(exc))
            return CommandResult(
                success=False,
                message=f"Failed to clear memory for session {session_id}: {exc}",
                error="CLEAR_FAILED",
                data={"session_id": session_id, "error": str(exc)},
            )

    async def _search_memory(
        self, query: str, context: CommandContext
    ) -> CommandResult:
        """Search memory using actual memory service."""
        try:
            from mindflow_backend.services.memory import get_memory_facade_service
            from mindflow_backend.infra.database.connection import get_db_session
            
            memory_service = get_memory_facade_service()
            session_id = context.session_id
            
            async with get_db_session() as session:
                # Search memory with the query
                results = await memory_service.search_memory(
                    session,
                    query=query,
                    session_id=session_id,
                    limit=10,
                )
                
                if results:
                    result_count = len(results)
                    message = f"Found {result_count} memory entries for query: '{query}'"
                    
                    # Format results for display
                    formatted_results = []
                    for r in results:
                        formatted_results.append({
                            "id": str(r.get("id", "unknown")),
                            "content": r.get("content", "")[:100] + "...",
                            "relevance": r.get("relevance_score", 0),
                        })
                    
                    return CommandResult(
                        success=True,
                        message=message,
                        data={
                            "query": query,
                            "session_id": session_id,
                            "results_count": result_count,
                            "results": formatted_results,
                        },
                    )
                else:
                    return CommandResult(
                        success=True,
                        message=f"No memory found for query: '{query}'",
                        data={"query": query, "session_id": session_id, "results": []},
                    )
                
        except Exception as exc:
            _logger.error("memory_search_failed", query=query, error=str(exc))
            return CommandResult(
                success=False,
                message=f"Memory search failed for query '{query}': {exc}",
                error="SEARCH_FAILED",
                data={"query": query, "error": str(exc)},
            )

    async def _export_memory(self, session_id: str) -> CommandResult:
        """Export session memory using actual memory service."""
        try:
            from mindflow_backend.services.memory import get_memory_facade_service
            from mindflow_backend.infra.database.connection import get_db_session
            import json
            
            memory_service = get_memory_facade_service()
            
            async with get_db_session() as session:
                # Export memory for the session
                memory_data = await memory_service.export_session_memory(session, session_id)
                
                if memory_data:
                    # Convert to JSON for export
                    export_json = json.dumps(memory_data, indent=2, default=str)
                    
                    return CommandResult(
                        success=True,
                        message=f"Memory exported for session: {session_id}",
                        data={
                            "session_id": session_id,
                            "export": memory_data,
                            "export_json": export_json,
                            "entry_count": len(memory_data.get("entries", [])),
                        },
                    )
                else:
                    return CommandResult(
                        success=False,
                        message=f"No memory to export for session: {session_id}",
                        error="NO_MEMORY_FOUND",
                        data={"session_id": session_id},
                    )
                
        except Exception as exc:
            _logger.error("memory_export_failed", session_id=session_id, error=str(exc))
            return CommandResult(
                success=False,
                message=f"Failed to export memory for session {session_id}: {exc}",
                error="EXPORT_FAILED",
                data={"session_id": session_id, "error": str(exc)},
            )
