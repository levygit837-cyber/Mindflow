"""Proposal Collector — Collects agent proposals via CommunicationBus.

Broadcasts user messages to all registered agents and collects
their proposals within a timeout window.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.proposal import (
    AgentProposal,
    ProposalRequest,
    ProposalResponse,
)

_logger = get_logger(__name__)


class ProposalCollector:
    """Collects proposals from agents via CommunicationBus.

    When a user message arrives, this collector:
    1. Creates a ProposalRequest
    2. Broadcasts it to all agents via CommunicationBus
    3. Waits for proposals within timeout
    4. Returns collected proposals
    """

    def __init__(self) -> None:
        self._pending_requests: dict[UUID, asyncio.Future] = {}

    async def collect(
        self,
        message: str,
        session_id: str = "",
        folder_path: str | None = None,
        context_summary: str = "",
        timeout: float = 5.0,
        exclude_agents: list[str] | None = None,
        target_agents: list[str] | None = None,
    ) -> list[AgentProposal]:
        """Collect proposals from agents (broadcast or targeted multicast).

        Args:
            message: User message to evaluate
            session_id: Current session ID
            folder_path: Working directory context
            context_summary: Brief context for agents
            timeout: Max seconds to wait for proposals
            exclude_agents: Agents to skip (applied on top of target_agents)
            target_agents: If provided, only these agents are consulted (multicast).
                If None, all registered agents receive the request (broadcast).

        Returns:
            List of AgentProposal from responding agents
        """
        request = ProposalRequest(
            message=message,
            session_id=session_id,
            folder_path=folder_path,
            context_summary=context_summary,
            timeout_seconds=timeout,
            exclude_agents=exclude_agents or [],
        )

        _logger.info(
            "proposal_collection_started",
            request_id=str(request.request_id),
            message_preview=message[:100],
            timeout=timeout,
            targeted=bool(target_agents),
            target_count=len(target_agents) if target_agents else None,
        )

        # Create future for this request
        future: asyncio.Future[list[AgentProposal]] = asyncio.get_event_loop().create_future()
        self._pending_requests[request.request_id] = future

        try:
            # Broadcast (or multicast) to agents via CommunicationBus
            await self._broadcast_request(request, target_agents=target_agents)

            # Wait for proposals with timeout
            proposals = await asyncio.wait_for(future, timeout=timeout)

            _logger.info(
                "proposal_collection_completed",
                request_id=str(request.request_id),
                proposals_count=len(proposals),
            )
            return proposals

        except asyncio.TimeoutError:
            # Collect whatever we have
            proposals = self._collect_partial(request.request_id)
            _logger.warning(
                "proposal_collection_timeout",
                request_id=str(request.request_id),
                partial_count=len(proposals),
            )
            return proposals

        finally:
            self._pending_requests.pop(request.request_id, None)

    async def _broadcast_request(
        self,
        request: ProposalRequest,
        target_agents: list[str] | None = None,
    ) -> None:
        """Send proposal request to agents (broadcast or targeted multicast).

        Args:
            request: The proposal request to send.
            target_agents: If provided, only send to these specific agents.
                           If None, send to all registered agents (broadcast).
        """
        try:
            from mindflow_backend.communication.bus import get_communication_bus

            bus = get_communication_bus()

            # Determine candidate set: targeted multicast or full broadcast
            all_registered = bus.get_registered_agents()
            candidates = (
                [a for a in target_agents if a in all_registered]
                if target_agents
                else list(all_registered)
            )

            _logger.debug(
                "proposal_broadcast_candidates",
                total_registered=len(all_registered),
                candidates=len(candidates),
                mode="multicast" if target_agents else "broadcast",
            )

            for agent_id in candidates:
                if agent_id in request.exclude_agents:
                    continue
                await bus.send(
                    sender_id="proposal_collector",
                    recipient_id=agent_id,
                    message={
                        "type": "proposal_request",
                        "request_id": str(request.request_id),
                        "message": request.message,
                        "session_id": request.session_id,
                        "folder_path": request.folder_path,
                        "context_summary": request.context_summary,
                    },
                )
                _logger.debug("proposal_request_sent", agent=agent_id)

        except Exception as exc:
            _logger.error("proposal_broadcast_failed", error=str(exc))

    async def submit_proposal(self, response: ProposalResponse) -> None:
        """Called by agents to submit their proposals."""
        request_id = response.request_id
        future = self._pending_requests.get(request_id)

        if future is None or future.done():
            return

        if response.proposal is not None:
            # Collect all proposals for this request
            if not hasattr(self, "_collected"):
                self._collected = {}
            if request_id not in self._collected:
                self._collected[request_id] = []
            self._collected[request_id].append(response.proposal)

            _logger.debug(
                "proposal_received",
                request_id=str(request_id),
                agent=response.agent_id,
                confidence=response.proposal.confidence,
            )

    def _collect_partial(self, request_id: UUID) -> list[AgentProposal]:
        """Collect partial proposals that arrived before timeout."""
        collected = getattr(self, "_collected", {}).pop(request_id, [])
        return collected


# Singleton instance
_collector: ProposalCollector | None = None


def get_proposal_collector() -> ProposalCollector:
    """Get or create the global proposal collector."""
    global _collector
    if _collector is None:
        _collector = ProposalCollector()
    return _collector