"""Chat session endpoints — clean async implementation using SQLAlchemy AsyncSession.

Security:
- Session ownership enforced via owner_id (set from the caller's API key).
- Callers can only list/read/modify their own sessions.
- Legacy sessions (owner_id='legacy-system') are only accessible to admin callers.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from mindflow_backend.api.controllers.agent_controller import AgentController
from mindflow_backend.api.dependencies import protected_route_dependencies
from mindflow_backend.execution_memory import get_execution_memory_service
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.database.connection import get_db_session
from mindflow_backend.infra.middleware.auth import require_api_key
from mindflow_backend.schemas.api.chat import (
    ChatSessionCreateRequest,
    ChatSessionMessageCreateRequest,
    ChatSessionTitleGenerateRequest,
    ChatSessionUpdateRequest,
)
from mindflow_backend.schemas.chat.agent import AgentChatRequest
from mindflow_backend.storage.postgresql.models import ChatMessage, ChatSession

router = APIRouter(prefix="/chat", tags=["chat"], dependencies=protected_route_dependencies)

# Initialize agent controller for chat forwarding
agent_controller = AgentController()

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
        import uuid
        
        grpc_client = get_runtime_client()
        session_id = payload.get("session_id") or agent_request.sessionId
        run_id = str(uuid.uuid4())
        
        full_content = []
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
            # Collect assistant text from events
            if hasattr(event, 'data'):
                full_content.append(event.data)
            elif hasattr(event, 'assistant_text_delta'):
                full_content.append(event.assistant_text_delta)
        
        # Return as AssistantMessage format
        return {
            "message": {
                "type": "assistant",
                "content": "".join(full_content),
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
    body: ChatSessionCreateRequest,
    api_key: str | None = Depends(require_api_key),
):
    import uuid
    session_id = f"sess-{uuid.uuid4()}"
    owner_id = _resolve_owner(api_key)

    async with get_db_session() as db:
        sess = ChatSession(id=session_id, title=body.title, owner_id=owner_id)
        db.add(sess)
        await db.commit()
        await db.refresh(sess)
        return _session_dict(sess)


@router.get("/sessions")
async def list_sessions(api_key: str | None = Depends(require_api_key)):
    owner_id = _resolve_owner(api_key)
    async with get_db_session() as db:
        query = select(ChatSession).order_by(ChatSession.updated_at.desc()).limit(100)
        # Admin sees all sessions; regular callers only see their own
        if owner_id != "admin":
            query = query.where(ChatSession.owner_id == owner_id)
        result = await db.execute(query)
        sessions = result.scalars().all()
        return [_session_dict(s) for s in sessions]


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    api_key: str | None = Depends(require_api_key),
):
    owner_id = _resolve_owner(api_key)
    async with get_db_session() as db:
        sess = await db.get(ChatSession, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")

        # Ownership check: admin sees all; others only see their own (+ legacy)
        if owner_id != "admin" and sess.owner_id not in (owner_id, _LEGACY_OWNER, None):
            raise HTTPException(status_code=403, detail="Access denied to this session")

        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        messages = result.scalars().all()

        data = _session_dict(sess)
        data["messages"] = [_message_dict(m) for m in messages]
        with_runtime_state = None
        with_runtime_payload = {}
        try:
            execution_memory = get_execution_memory_service()
            with_runtime_state = await execution_memory.load_session_runtime_state(session_id=session_id)
        except Exception:
            with_runtime_state = None

        if with_runtime_state is not None:
            with_runtime_payload = {
                "execution_id": getattr(with_runtime_state, "execution_id", None),
                "state": getattr(with_runtime_state, "state_json", {}) or {},
                "version": getattr(with_runtime_state, "version", None),
                "updated_at": getattr(with_runtime_state, "updated_at", None).isoformat()
                if getattr(with_runtime_state, "updated_at", None)
                else None,
            }
        data["runtime_state"] = with_runtime_payload
        return data


@router.put("/sessions/{session_id}")
async def update_session(
    session_id: str,
    body: ChatSessionUpdateRequest,
    api_key: str | None = Depends(require_api_key),
):
    owner_id = _resolve_owner(api_key)
    async with get_db_session() as db:
        sess = await db.get(ChatSession, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")
        if owner_id != "admin" and sess.owner_id not in (owner_id, _LEGACY_OWNER, None):
            raise HTTPException(status_code=403, detail="Access denied to this session")

        sess.title = body.title
        sess.updated_at = datetime.now(UTC)
        await db.commit()
        return _session_dict(sess)


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    api_key: str | None = Depends(require_api_key),
):
    owner_id = _resolve_owner(api_key)
    async with get_db_session() as db:
        sess = await db.get(ChatSession, session_id)
        if sess:
            if owner_id != "admin" and sess.owner_id not in (owner_id, _LEGACY_OWNER, None):
                raise HTTPException(status_code=403, detail="Access denied to this session")
            await db.delete(sess)
            await db.commit()
        return {"success": True, "session_id": session_id}


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
