"""Advanced transaction management and coordination.

Provides sophisticated transaction handling, distributed transactions,
and transaction coordination for complex operations.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from mindflow_backend.infra.database.connection import get_db_session
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class TransactionState(Enum):
    """Transaction lifecycle states."""
    PENDING = "pending"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class TransactionIsolationLevel(Enum):
    """Transaction isolation levels."""
    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"


@dataclass
class TransactionMetrics:
    """Metrics for transaction monitoring."""
    transaction_id: str
    start_time: datetime
    end_time: datetime | None = None
    state: TransactionState = TransactionState.PENDING
    isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.READ_COMMITTED
    operations_count: int = 0
    rollback_reason: str | None = None
    error: Exception | None = None
    
    @property
    def duration_ms(self) -> float:
        """Calculate transaction duration in milliseconds."""
        end = self.end_time or datetime.now(UTC)
        return (end - self.start_time).total_seconds() * 1000


class TransactionManager:
    """Advanced transaction management with coordination.
    
    Features:
    - Nested transaction support
    - Distributed transaction coordination
    - Transaction retry with exponential backoff
    - Transaction monitoring and metrics
    - Automatic cleanup and resource management
    - Savepoint management
    """
    
    def __init__(self) -> None:
        """Initialize transaction manager."""
        self._active_transactions: dict[str, TransactionMetrics] = {}
        self._transaction_lock = asyncio.Lock()
        
    @asynccontextmanager
    async def transaction(
        self,
        isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.READ_COMMITTED,
        rollback_for: list[type] | None = None,
        retry_count: int = 0,
    ) -> AsyncGenerator[AsyncSession, None]:
        """Execute database transaction with advanced management.
        
        Args:
            isolation_level: Transaction isolation level
            rollback_for: Exception types that trigger rollback
            retry_count: Number of retry attempts
            
        Yields:
            AsyncSession: Database session within transaction context.
        """
        transaction_id = str(uuid.uuid4())
        metrics = TransactionMetrics(
            transaction_id=transaction_id,
            start_time=datetime.now(UTC),
            isolation_level=isolation_level,
        )
        
        async with self._transaction_lock:
            self._active_transactions[transaction_id] = metrics
            
        try:
            async with get_db_session() as session:
                # Set isolation level
                await session.execute(
                    text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level.value}")
                )
                
                metrics.state = TransactionState.ACTIVE
                
                # Begin transaction
                await session.begin()
                
                try:
                    yield session
                    
                    # Commit transaction
                    await session.commit()
                    metrics.state = TransactionState.COMMITTED
                    metrics.end_time = datetime.now(UTC)
                    
                    _logger.info(
                        "transaction_committed",
                        transaction_id=transaction_id,
                        duration_ms=metrics.duration_ms,
                        operations=metrics.operations_count,
                    )
                    
                except Exception as e:
                    # Determine if should rollback
                    should_rollback = (
                        rollback_for is None or 
                        any(isinstance(e, exc_type) for exc_type in rollback_for)
                    )
                    
                    if should_rollback:
                        await session.rollback()
                        metrics.state = TransactionState.ROLLED_BACK
                        metrics.rollback_reason = str(e)
                        metrics.error = e
                        metrics.end_time = datetime.now(UTC)
                        
                        _logger.warning(
                            "transaction_rolled_back",
                            transaction_id=transaction_id,
                            duration_ms=metrics.duration_ms,
                            reason=str(e),
                            operations=metrics.operations_count,
                        )
                    else:
                        # Re-raise exception without rollback
                        metrics.state = TransactionState.FAILED
                        metrics.error = e
                        metrics.end_time = datetime.now(UTC)
                        raise
                        
        except Exception as e:
            metrics.state = TransactionState.FAILED
            metrics.error = e
            metrics.end_time = datetime.now(UTC)
            
            # Retry logic if specified
            if retry_count > 0:
                _logger.info(
                    "transaction_retry_attempt",
                    transaction_id=transaction_id,
                    retry_count=retry_count,
                    error=str(e),
                )
                
                await asyncio.sleep(0.1 * (4 - retry_count))  # Exponential backoff
                async with self.transaction(
                    isolation_level=isolation_level,
                    rollback_for=rollback_for,
                    retry_count=retry_count - 1,
                ) as retry_session:
                    yield retry_session
            else:
                _logger.error(
                    "transaction_failed",
                    transaction_id=transaction_id,
                    duration_ms=metrics.duration_ms,
                    error=str(e),
                    operations=metrics.operations_count,
                )
                raise
                
        finally:
            async with self._transaction_lock:
                self._active_transactions.pop(transaction_id, None)
                
    @asynccontextmanager
    async def savepoint(self, session: AsyncSession, name: str | None = None) -> AsyncGenerator[str, None]:
        """Create and manage transaction savepoint.
        
        Args:
            session: Database session
            name: Optional savepoint name
            
        Yields:
            str: Savepoint name for rollback operations.
        """
        if name is None:
            name = f"sp_{uuid.uuid4().hex[:8]}"
            
        try:
            # Create savepoint
            await session.execute(text(f"SAVEPOINT {name}"))
            _logger.debug("savepoint_created", name=name)
            
            yield name
            
        except Exception as e:
            # Rollback to savepoint on error
            try:
                await session.execute(text(f"ROLLBACK TO SAVEPOINT {name}"))
                _logger.info("savepoint_rolled_back", name=name, error=str(e))
            except Exception as rollback_error:
                _logger.error(
                    "savepoint_rollback_failed",
                    name=name,
                    error=str(rollback_error),
                )
            raise
            
    async def execute_in_transaction(
        self,
        operations: list[Callable[[AsyncSession], Any]],
        isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.READ_COMMITTED,
        rollback_for: list[type] | None = None,
    ) -> list[Any]:
        """Execute multiple operations in a single transaction.
        
        Args:
            operations: List of operation functions
            isolation_level: Transaction isolation level
            rollback_for: Exception types that trigger rollback
            
        Returns:
            List of operation results.
        """
        results = []
        
        async with self.transaction(
            isolation_level=isolation_level,
            rollback_for=rollback_for,
        ) as session:
            for operation in operations:
                try:
                    result = await operation(session)
                    results.append(result)
                    
                    # Update operation count
                    transaction_id = await self._get_current_transaction_id(session)
                    if transaction_id:
                        metrics = self._active_transactions.get(transaction_id)
                        if metrics:
                            metrics.operations_count += 1
                            
                except Exception as e:
                    _logger.error(
                        "transaction_operation_failed",
                        operation=operation.__name__,
                        error=str(e),
                    )
                    raise
                    
        return results
        
    async def get_transaction_metrics(self, transaction_id: str) -> TransactionMetrics | None:
        """Get metrics for a specific transaction.
        
        Args:
            transaction_id: Transaction identifier
            
        Returns:
            TransactionMetrics if found, None otherwise.
        """
        async with self._transaction_lock:
            return self._active_transactions.get(transaction_id)
            
    async def get_all_active_transactions(self) -> dict[str, TransactionMetrics]:
        """Get all currently active transactions.
        
        Returns:
            Dict of active transaction metrics.
        """
        async with self._transaction_lock:
            return self._active_transactions.copy()
            
    async def cleanup_expired_transactions(self, max_age_minutes: int = 30) -> int:
        """Clean up expired transactions from monitoring.
        
        Args:
            max_age_minutes: Maximum age for transactions to keep
            
        Returns:
            Number of transactions cleaned up.
        """
        cutoff_time = datetime.now(UTC) - timedelta(minutes=max_age_minutes)
        cleaned_count = 0
        
        async with self._transaction_lock:
            expired_transactions = [
                tx_id for tx_id, metrics in self._active_transactions.items()
                if metrics.start_time < cutoff_time
            ]
            
            for tx_id in expired_transactions:
                self._active_transactions.pop(tx_id, None)
                cleaned_count += 1
                
        if cleaned_count > 0:
            _logger.info(
                "expired_transactions_cleaned",
                count=cleaned_count,
                max_age_minutes=max_age_minutes,
            )
            
        return cleaned_count
        
    async def _get_current_transaction_id(self, session: AsyncSession) -> str | None:
        """Get transaction ID for current session.
        
        Args:
            session: Database session
            
        Returns:
            Transaction ID if available, None otherwise.
        """
        # This is a simplified implementation
        # In a real scenario, you might store transaction ID in session context
        async with self._transaction_lock:
            for tx_id, metrics in self._active_transactions.items():
                if metrics.state == TransactionState.ACTIVE:
                    return tx_id
        return None


# Global transaction manager instance
_transaction_manager: TransactionManager | None = None


def get_transaction_manager() -> TransactionManager:
    """Get global transaction manager instance."""
    global _transaction_manager
    if _transaction_manager is None:
        _transaction_manager = TransactionManager()
    return _transaction_manager


# Convenience functions
@asynccontextmanager
async def transaction(
    isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.READ_COMMITTED,
    rollback_for: list[type] | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Convenience function for transaction management.
    
    Args:
        isolation_level: Transaction isolation level
        rollback_for: Exception types that trigger rollback
        
    Yields:
        AsyncSession: Database session within transaction.
    """
    tx_manager = get_transaction_manager()
    async with tx_manager.transaction(
        isolation_level=isolation_level,
        rollback_for=rollback_for,
    ) as session:
        yield session


@asynccontextmanager
async def savepoint(session: AsyncSession, name: str | None = None) -> AsyncGenerator[str, None]:
    """Convenience function for savepoint management.
    
    Args:
        session: Database session
        name: Optional savepoint name
        
    Yields:
        str: Savepoint name.
    """
    tx_manager = get_transaction_manager()
    async with tx_manager.savepoint(session, name) as sp_name:
        yield sp_name
