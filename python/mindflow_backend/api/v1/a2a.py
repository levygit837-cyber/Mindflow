from fastapi import APIRouter
from mindflow_backend.schemas.a2a.task import A2AMessage
from mindflow_backend.api.controllers.a2a_controller import A2AController

router = APIRouter(tags=["A2A Protocol Extension"])

@router.get("/.well-known/agent.json", summary="Discover MindFlow A2A Agents", response_model=None)
async def get_agent_discovery():
    """
    Returns the AgentCards according to A2A standard representing the internal MindFlow capabilities.
    """
    cards = A2AController.get_agent_cards()
    return {"agents": [card.model_dump() for card in cards]}

@router.post("/a2a/tasks/send", summary="Create Synchronous A2A Task")
async def send_task(message: A2AMessage):
    """
    Triggers an execution flow mapping standard A2A input to the Internal Delegation System,
    returning a structured Artifact when finished.
    """
    return await A2AController.process_task(message)

@router.post("/a2a/tasks/sendSubscribe", summary="Create Streaming A2A Task")
async def send_subscribe_task(message: A2AMessage):
    """
    Triggers execution similar to `tasks/send` but responds with a Server-Sent Events (SSE)
    connection following the A2A streaming event protocol.
    """
    return await A2AController.stream_task_processing(message)
