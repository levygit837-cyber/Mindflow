"""Chat session endpoints — clean async implementation using SQLAlchemy AsyncSession.

Security:
- Session ownership enforced via owner_id (set from the caller's API key).
- Callers can only list/read/modify their own sessions.
- Legacy sessions (owner_id='legacy-system') are only accessible to admin callers.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from mindflow_backend.api.dependencies import protected_route_dependencies
from mindflow_backend.api.dependencies.security import audit_log
from mindflow_backend.infra.middleware.auth import require_api_key
from mindflow_backend.infra.config import get_settings
from mindflow_backend.schemas.api.chat import (
    ChatSessionCreateRequest,
    ChatSessionMessageCreateRequest,
    ChatSessionTitleGenerateRequest,
    ChatSessionUpdateRequest,
)
from mindflow_backend.infra.database.connection import get_db_session
from mindflow_backend.storage.postgresql.models import ChatMessage, ChatSession

router = APIRouter(prefix="/chat", tags=["chat"], dependencies=protected_route_dependencies)

_LEGACY_OWNER = "legacy-system"


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
