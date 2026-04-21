import json
import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Type
import httpx
from pydantic import Field

from langchain_core.callbacks.manager import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatCompletionChunk, ChatResult

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

class WindsurfChatModel(BaseChatModel):
    """LangChain-compatible model backed by the wind-gateway."""

    gateway_url: str
    session_id: str
    workspace_path: Optional[str] = None
    model_uid: str
    
    @property
    def _llm_type(self) -> str:
        return "windsurf"

    def _convert_messages_to_prompt(self, messages: List[BaseMessage]) -> str:
        """Convert a list of LangChain messages into a single prompt string."""
        prompt = ""
        for message in messages:
            if isinstance(message, SystemMessage):
                prompt += f"System: {message.content}\n\n"
            elif isinstance(message, HumanMessage):
                prompt += f"{message.content}\n\n"
            elif isinstance(message, AIMessage):
                if message.content:
                    prompt += f"Assistant: {message.content}\n\n"
        return prompt.strip()

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]: # Type hints may need checking based on langchain version
        from langchain_core.outputs import ChatGenerationChunk
        
        prompt = self._convert_messages_to_prompt(messages)
        
        if not prompt:
             return

        async with httpx.AsyncClient() as client:
            request_data = {
                "message": prompt,
                "model": self.model_uid
            }
            
            try:
                async with client.stream(
                    "POST",
                    f"{self.gateway_url}/chat/session/{self.session_id}/message?stream=true",
                    json=request_data,
                    timeout=300.0 # Long timeout for streaming
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                            
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                            
                        try:
                            event = json.loads(data_str)
                            event_type = event.get("type")
                            
                            if event_type == "chunk":
                                text = event.get("text", "")
                                chunk = ChatGenerationChunk(message=AIMessageChunk(content=text))
                                if run_manager:
                                    await run_manager.on_llm_new_token(text, chunk=chunk)
                                yield chunk
                            elif event_type == "thinking":
                                text = event.get("text", "")
                                if text:
                                   chunk = ChatGenerationChunk(
                                       message=AIMessageChunk(content="", additional_kwargs={"thinking": text})
                                   )
                                   # We might not want to call on_llm_new_token for thinking chunks directly depending on handler
                                   yield chunk
                            elif event_type == "error":
                                _logger.error("windsurf_stream_error", error=event.get("error"))
                                raise RuntimeError(f"Windsurf stream error: {event.get('error')}")
                            # Other event types (complete, thinking_complete, tool_*) exist but are handled by UI/windsurf natively right now in bypass mode
                            
                        except json.JSONDecodeError:
                            _logger.warning("windsurf_stream_invalid_json", data=data_str)
                            
            except Exception as e:
                 _logger.error("windsurf_stream_failed", error=str(e))
                 raise


    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Sync generation. Since this is primarily a streaming model, we can buffer."""
        # For simplicity in this integration, we will buffer the stream.
        # A more robust sync implementation might use an async runner.
        loop = asyncio.get_event_loop()
        if loop.is_running():
            raise RuntimeError("Cannot _generate synchronously in a running event loop. Use agenerate.")
        
        return loop.run_until_complete(self._agenerate(messages, stop, **kwargs))
        
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
         
         content = ""
         additional_kwargs = {}
         thinking_content = ""
         
         async for chunk in self._astream(messages, stop, run_manager, **kwargs):
             if chunk.message.content:
                 content += chunk.message.content
             if chunk.message.additional_kwargs.get("thinking"):
                 thinking_content += chunk.message.additional_kwargs["thinking"]
                 
         if thinking_content:
             additional_kwargs["thinking"] = thinking_content
                 
         return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content, additional_kwargs=additional_kwargs))])
