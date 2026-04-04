from typing import AsyncGenerator
from mindflow_backend.schemas.chat.agent import StreamEvent
from mindflow_backend.schemas.a2a.task import TaskStatusUpdateEvent, TaskArtifactUpdateEvent, A2AArtifact, TextPart

class A2AStreamAdapter:
    """Adapts native Mindflow StreamEvent schema into A2A SSE Event format."""
    
    @staticmethod
    async def adapt_stream(agent_stream_generator: AsyncGenerator[StreamEvent, None]) -> AsyncGenerator[str, None]:
        """
        Takes the StreamEvent objects from the MindFlow runtime,
        and re-emits them using A2A TaskStatusUpdateEvent and TaskArtifactUpdateEvent.
        """
        async for event in agent_stream_generator:
            try:
                evt_type = event.type
                
                if evt_type == "agent_step":
                    out_event = TaskStatusUpdateEvent(
                        status="working", 
                        message=str(event.data if isinstance(event.data, str) else "Processing task...")
                    )
                    yield f"event: TaskStatusUpdateEvent\ndata: {out_event.model_dump_json()}\n\n"
                    
                elif evt_type in ["thought", "tool_call", "thinking"]:
                    out_event = TaskStatusUpdateEvent(status="working", message="Analyzing or using tools...")
                    yield f"event: TaskStatusUpdateEvent\ndata: {out_event.model_dump_json()}\n\n"
                    
                elif evt_type == "response":
                    # Chunk of text response
                    chunk_text = str(event.data)
                    artifact = A2AArtifact(parts=[TextPart(text=chunk_text)])
                    out_event = TaskArtifactUpdateEvent(artifact=artifact, append=True)
                    yield f"event: TaskArtifactUpdateEvent\ndata: {out_event.model_dump_json()}\n\n"

                elif evt_type == "done":
                    out_event = TaskStatusUpdateEvent(status="completed")
                    yield f"event: TaskStatusUpdateEvent\ndata: {out_event.model_dump_json()}\n\n"
                    
                elif evt_type == "error":
                    # Extract error data
                    error_msg = str(event.data) if event.data else "Unknown error encountered"
                    out_event = TaskStatusUpdateEvent(status="failed", error=error_msg)
                    yield f"event: TaskStatusUpdateEvent\ndata: {out_event.model_dump_json()}\n\n"
            
            except Exception:
                # Basic safety to avoid breaking the stream
                continue

