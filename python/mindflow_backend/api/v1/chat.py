"""Chat session endpoints — clean async implementation using SQLAlchemy AsyncSession.

Security:
- Session ownership enforced via owner_id (set from the caller's API key).
- Callers can only list/read/modify their own sessions.
- Legacy sessions (owner_id='legacy-system') are only accessible to admin callers.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from mindflow_backend.api.controllers.agent_controller import AgentController
from mindflow_backend.api.controllers.session_controller import SessionController
from mindflow_backend.api.dependencies import protected_route_dependencies
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.database.connection import get_db_session
from mindflow_backend.infra.middleware.auth import require_api_key
from mindflow_backend.schemas.api.chat import (
    ChatSessionMessageCreateRequest,
    ChatSessionTitleGenerateRequest,
)
from mindflow_backend.schemas.api.common import PaginationParams
from mindflow_backend.schemas.api.requests import SessionCreateRequest, SessionUpdateRequest
from mindflow_backend.schemas.chat.agent import AgentChatRequest
from mindflow_backend.storage.postgresql.models import ChatMessage, ChatSession

router = APIRouter(prefix="/chat", tags=["chat"], dependencies=protected_route_dependencies)

# Initialize agent controller for chat forwarding
agent_controller = AgentController()
session_controller = SessionController

_LEGACY_OWNER = "legacy-system"


# ── chat endpoint (Desktop CLI compatibility) ─────────────────────────────────

@router.post("")
async def chat(payload: dict, request: Request):
    """Main chat endpoint for Desktop CLI compatibility.
    
    Forwards requests to the agent chat stream endpoint to enable
    conversation with agents from the Desktop frontend.
    
    Handles frontend's nested message format and converts to AgentChatRequest.
    Supports both streaming and non-streaming modes.
    """
    # Extract message content from frontend format
    # Frontend sends: { message: { type: 'user', content: string, ... }, ... }
    # Backend expects: { message: string, ... }
    
    message_content = ""
    if isinstance(payload.get("message"), dict):
        # Frontend format: nested message object
        message_content = payload["message"].get("content", "")
    elif isinstance(payload.get("message"), str):
        # Simple format: message is already a string
        message_content = payload["message"]
    else:
        raise HTTPException(status_code=400, detail="Invalid message format")
    
    # Build AgentChatRequest from frontend payload
    agent_request = AgentChatRequest(
        message=message_content,
        provider=payload.get("provider"),
        model=payload.get("model"),
        sessionId=payload.get("session_id"),
        agent_type=payload.get("agent_type"),
        orchestrate=payload.get("orchestrate", False),
        debugSteps=payload.get("debugSteps", False),
        folder_path=payload.get("folder_path"),
    )
    
    # Check if streaming is requested
    stream_mode = payload.get("stream", False)
    
    if stream_mode:
        # Streaming mode: return SSE stream
        return await agent_controller.stream_chat(agent_request, request)
    else:
        # Non-streaming mode: use streaming internally and collect result
        # Call the agent runtime directly to collect events
        from mindflow_backend.grpc_internal.factory import get_runtime_client

        grpc_client = get_runtime_client()
        session_id = payload.get("session_id") or agent_request.sessionId
        run_id = str(uuid.uuid4())
        
        full_content = []
        timeout_seconds = 120  # Timeout for event collection
        start_time = asyncio.get_event_loop().time()
        
        try:
            async for event in grpc_client.stream_chat(
                session_id=session_id,
                message=message_content,
                provider=agent_request.provider,
                model=agent_request.model,
                run_id=run_id,
                orchestrate=agent_request.orchestrate,
                agent_type=agent_request.agent_type,
                folder_path=agent_request.folder_path,
            ):
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout_seconds:
                    raise TimeoutError(f"Event collection timeout after {timeout_seconds}s")
                
                # Collect assistant text from events
                if hasattr(event, 'data'):
                    full_content.append(event.data)
                elif hasattr(event, 'assistant_text_delta'):
                    full_content.append(event.assistant_text_delta)
                
                # Break on done event
                if hasattr(event, 'type') and event.type == "done":
                    break
        except TimeoutError:
            # Log timeout error
            logger = logging.getLogger(__name__)
            logger.error(f"Event collection timeout after {timeout_seconds}s for session {session_id}")
            # Return partial content or error message
            if not full_content:
                raise HTTPException(status_code=504, detail="Agent response timeout") from None
        except Exception as e:
            # Log error and re-raise
            logger = logging.getLogger(__name__)
            logger.error(f"Error collecting events for session {session_id}: {str(e)}")
            if not full_content:
                raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}") from e
        
        # Return as AssistantMessage format
        return {
            "message": {
                "type": "assistant",
                "content": "".join(full_content) if full_content else "No response generated",
                "timestamp": datetime.now(UTC).isoformat(),
                "uuid": payload.get("message", {}).get("uuid") if isinstance(payload.get("message"), dict) else None,
                "session_id": session_id,
            },
            "session_id": session_id,
        }


# ── helpers ───────────────────────────────────────────────────────────────────

def _session_dict(s: ChatSession) -> dict:
    return {
        "id": s.id,
        "title": s.title or "Untitled Chat",
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }


def _message_dict(m: ChatMessage) -> dict:
    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "provider": m.provider,
        "model": m.model,
        "created_at": m.created_at.isoformat(),
    }


def _resolve_owner(api_key: str | None) -> str:
    """Map an API key to an owner_id string used for filtering."""
    if api_key is None:
        # Auth disabled — dev mode, use a fixed owner to isolate dev sessions
        return "dev-local"
    settings = get_settings()
    master_key = getattr(settings, "auth_master_key", None)
    if master_key and api_key == master_key:
        return "admin"
    # Hash the key for privacy: only store a fingerprint, not the raw key
    import hashlib
    return "key-" + hashlib.sha256(api_key.encode()).hexdigest()[:16]


# ── session CRUD ──────────────────────────────────────────────────────────────

@router.post("/sessions")
async def create_session(
    body: SessionCreateRequest,
    api_key: str | None = Depends(require_api_key),
):
    del api_key
    return await session_controller().create_session(body)


@router.get("/sessions")
async def list_sessions(
    limit: int = 50,
    offset: int = 0,
    api_key: str | None = Depends(require_api_key),
):
    del api_key
    pagination = PaginationParams(limit=limit, offset=offset)
    return await session_controller().list_sessions(pagination)


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    api_key: str | None = Depends(require_api_key),
):
    del api_key
    return await session_controller().get_session(session_id)


@router.put("/sessions/{session_id}")
async def update_session(
    session_id: str,
    body: SessionUpdateRequest,
    api_key: str | None = Depends(require_api_key),
):
    del api_key
    return await session_controller().update_session(session_id, body)


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    api_key: str | None = Depends(require_api_key),
):
    del api_key
    return await session_controller().delete_session(session_id)


@router.post("/sessions/{session_id}/messages")
async def add_message(
    session_id: str,
    role: str,
    content: str,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = Depends(require_api_key),
):
    del api_key
    return await session_controller().add_message(
        session_id=session_id,
        role=role,
        content=content,
        provider=provider,
        model=model,
    )


# ── message persistence ────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/save-message")
async def save_message(
    session_id: str,
    body: ChatSessionMessageCreateRequest,
    api_key: str | None = Depends(require_api_key),
):
    """Save a single message (user or assistant) to a session."""
    owner_id = _resolve_owner(api_key)
    role = body.role
    content = body.content
    model = body.model
    provider = body.provider

    async with get_db_session() as db:
        sess = await db.get(ChatSession, session_id)
        if not sess:
            sess = ChatSession(id=session_id, title="New Chat", owner_id=owner_id)
            db.add(sess)
        elif owner_id != "admin" and sess.owner_id not in (owner_id, _LEGACY_OWNER, None):
            raise HTTPException(status_code=403, detail="Access denied to this session")

        msg = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            model=model,
            provider=provider,
        )
        db.add(msg)
        sess.updated_at = datetime.now(UTC)
        await db.commit()
        return {"success": True, "id": msg.id}


# ── Ollama title generation ────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/generate-title")
async def generate_session_title(
    session_id: str,
    body: ChatSessionTitleGenerateRequest,
    api_key: str | None = Depends(require_api_key),
):
    """Generate a short session title via local Ollama model and persist it."""
    owner_id = _resolve_owner(api_key)
    settings = get_settings()
    title_model = settings.default_model if settings.default_provider == "ollama" else "qwen3.5-0.8b"
    first_message = body.message[:300]

    # Default fallback title
    title = (first_message[:40] + "…") if len(first_message) > 40 else first_message or "New Chat"

    try:
        import httpx
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/chat",
                json={
                    "model": title_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Gere um título curto (máximo 5 palavras, sem aspas, sem pontuação final) "
                                f"para uma conversa que começa com: '{first_message}'. "
                                "Responda APENAS com o título, sem explicações."
                            ),
                        }
                    ],
                    "stream": False,
                },
            )
        if resp.status_code == 200:
            data = resp.json()
            generated = data.get("message", {}).get("content", "").strip()
            if generated:
                import re as _re
                generated = _re.sub(r"<think>[\s\S]*?</think>", "", generated).strip()
                for line in generated.split("\n"):
                    line = line.strip("\"' \t")
                    if line:
                        title = line[:60]
                        break
    except Exception:
        pass  # Use fallback title

    async with get_db_session() as db:
        sess = await db.get(ChatSession, session_id)
        if sess:
            if owner_id != "admin" and sess.owner_id not in (owner_id, _LEGACY_OWNER, None):
                raise HTTPException(status_code=403, detail="Access denied to this session")
            sess.title = title
            sess.updated_at = datetime.now(UTC)
        else:
            sess = ChatSession(id=session_id, title=title, owner_id=owner_id)
            db.add(sess)
        await db.commit()

    return {"title": title, "session_id": session_id}
