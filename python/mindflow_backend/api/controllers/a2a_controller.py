from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
from mindflow_backend.schemas.a2a.agent_card import AgentCard
from mindflow_backend.schemas.a2a.task import A2AMessage, A2AArtifact
from mindflow_backend.communication.a2a.agent_card_registry import AgentCardRegistry
from mindflow_backend.communication.a2a.task_adapter import TaskAdapter
from mindflow_backend.communication.a2a.stream_adapter import A2AStreamAdapter
from mindflow_backend.query.budget.token_counter import TokenBudget
from mindflow_backend.query.engine import QueryEngine
from mindflow_backend.schemas.orchestration.delegation import OrchestratorSession

class A2AController:
    """Controller for A2A Gateway operations."""
    
    @staticmethod
    def get_agent_cards() -> list[AgentCard]:
        """Fetch all dynamically mapped AgentCards."""
        return AgentCardRegistry.get_agent_cards()

    @staticmethod
    async def process_task(message: A2AMessage) -> A2AArtifact:
        """Processes an A2A task synchronously and returns an artifact."""
        delegation_task = TaskAdapter.a2a_task_to_delegation_task(message)
        session = OrchestratorSession(user_intent=delegation_task.objective)

        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=200_000),
            session_id=message.context_id,
            use_file_cache=False,
        )
        result = await engine.delegate_task(
            task=delegation_task,
            session=session,
            session_id=message.context_id
        )
        return TaskAdapter.delegation_result_to_a2a_artifact(result)

    @staticmethod
    async def stream_task_processing(message: A2AMessage) -> StreamingResponse:
        """Processes an A2A task returning a standardized Server-Sent Events stream."""
        from mindflow_backend.runtime.streaming.stream import AgentRuntime
        from mindflow_backend.schemas.chat.agent import AgentChatRequest

        # 1. Map A2A message to AgentChatRequest
        objective = ""
        for part in message.parts:
            if part.type == "text":
                objective += getattr(part, 'text', '') + "\n"
        
        target_agent = message.target_agent or "orchestrator"
        # Extract agent type (e.g., 'coder' from 'coder:frontend')
        agent_type = target_agent.split(":")[0]
        
        payload = AgentChatRequest(
            message=objective.strip(),
            agent_type=agent_type,
            orchestrate=(agent_type == "orchestrator"),
            session_id=message.context_id or "a2a-stream-session"
        )
        
        # 2. Initialize runtime and start stream
        runtime = AgentRuntime()
        raw_stream = runtime.stream_chat(payload, session_id=payload.sessionId)
        
        # 3. Adapt to A2A SSE format
        adapted_stream = A2AStreamAdapter.adapt_stream(raw_stream)
        
        return StreamingResponse(adapted_stream, media_type="text/event-stream")
