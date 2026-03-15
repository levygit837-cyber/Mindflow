"""Chat session endpoints — clean async implementation using SQLAlchemy AsyncSession."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from mindflow_backend.infra.database.connection import get_db_session
from mindflow_backend.storage.postgresql.models import ChatMessage, ChatSession

router = APIRouter(prefix="/chat", tags=["chat"])


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


# ── session CRUD ──────────────────────────────────────────────────────────────

@router.post("/sessions")
async def create_session(body: dict = {}):
    import uuid
    session_id = f"sess-{uuid.uuid4()}"
    title = body.get("title", "New Chat") if body else "New Chat"

    async with get_db_session() as db:
        sess = ChatSession(id=session_id, title=title)
        db.add(sess)
        await db.commit()
        await db.refresh(sess)
        return _session_dict(sess)


@router.get("/sessions")
async def list_sessions():
    async with get_db_session() as db:
        result = await db.execute(
            select(ChatSession).order_by(ChatSession.updated_at.desc()).limit(100)
        )
        sessions = result.scalars().all()
        return [_session_dict(s) for s in sessions]


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    async with get_db_session() as db:
        sess = await db.get(ChatSession, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")

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
async def update_session(session_id: str, body: dict):
    async with get_db_session() as db:
        sess = await db.get(ChatSession, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")

        if "title" in body:
            sess.title = body["title"]
        sess.updated_at = datetime.now(UTC)
        await db.commit()
        return _session_dict(sess)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    async with get_db_session() as db:
        sess = await db.get(ChatSession, session_id)
        if sess:
            await db.delete(sess)
            await db.commit()
        return {"success": True, "session_id": session_id}


# ── message persistence ────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/save-message")
async def save_message(session_id: str, body: dict):
    """Save a single message (user or assistant) to a session."""
    role = body.get("role", "user")
    content = body.get("content", "")
    model = body.get("model")
    provider = body.get("provider")

    if not content:
        raise HTTPException(status_code=400, detail="content is required")

    async with get_db_session() as db:
        # Ensure session exists
        sess = await db.get(ChatSession, session_id)
        if not sess:
            sess = ChatSession(id=session_id, title="New Chat")
            db.add(sess)

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
async def generate_session_title(session_id: str, body: dict):
    """Generate a short session title via local Ollama model and persist it."""
    first_message = (body.get("message") or "")[:300]

    # Default fallback title
    title = (first_message[:40] + "…") if len(first_message) > 40 else first_message or "New Chat"

    try:
        import httpx
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "Qwen36:latest",
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
                # Strip <think>...</think> blocks (chain-of-thought models)
                import re as _re
                generated = _re.sub(r"<think>[\s\S]*?</think>", "", generated).strip()
                # Remove surrounding quotes, take first non-empty line only
                for line in generated.split("\n"):
                    line = line.strip("\"' \t")
                    if line:
                        title = line[:60]
                        break
    except Exception:
        pass  # Use fallback title

    # Persist title to DB
    async with get_db_session() as db:
        sess = await db.get(ChatSession, session_id)
        if sess:
            sess.title = title
            sess.updated_at = datetime.now(UTC)
        else:
            sess = ChatSession(id=session_id, title=title)
            db.add(sess)
        await db.commit()

    return {"title": title, "session_id": session_id}
