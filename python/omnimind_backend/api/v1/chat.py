from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from omnimind_backend.schemas.chat.agent import ChatMessageSchema, ChatSessionSchema
from omnimind_backend.storage.db import db_session
from omnimind_backend.storage.repositories import ChatRepository
from omnimind_backend.api.controllers.session_controller import SessionController
from omnimind_backend.api.schemas.requests import SessionCreateRequest, SessionUpdateRequest
from omnimind_backend.api.schemas.common import PaginationParams

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize controller
session_controller = SessionController()


def get_db():
    with db_session() as db:
        yield db


# New controller-based endpoints
@router.post("/sessions")
async def create_session(request: SessionCreateRequest, db: Session = Depends(get_db)):
    """Create a new session using controller."""
    return await session_controller.create_session(request, db)


@router.get("/sessions")
async def list_sessions(
    pagination: PaginationParams = PaginationParams(),
    db: Session = Depends(get_db)
):
    """List sessions using controller."""
    return await session_controller.list_sessions(pagination, db)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, db: Session = Depends(get_db)):
    """Get session using controller."""
    return await session_controller.get_session(session_id, db)


@router.put("/sessions/{session_id}")
async def update_session(
    session_id: str, 
    request: SessionUpdateRequest, 
    db: Session = Depends(get_db)
):
    """Update session using controller."""
    return await session_controller.update_session(session_id, request, db)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete session using controller."""
    return await session_controller.delete_session(session_id, db)


@router.post("/sessions/{session_id}/messages")
async def add_message(
    session_id: str,
    role: str,
    content: str,
    provider: str = None,
    model: str = None,
    db: Session = Depends(get_db)
):
    """Add message to session using controller."""
    return await session_controller.add_message(
        session_id, role, content, provider, model, db
    )


# Legacy endpoints - maintained for backward compatibility
@router.get("/sessions", response_model=list[ChatSessionSchema])
async def list_sessions_legacy(db: Session = Depends(get_db)):
    """Legacy session listing - maintained for compatibility."""
    repo = ChatRepository()
    sessions = repo.list_sessions(db)
    return [
        ChatSessionSchema(
            id=s.id,
            title=s.title,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=ChatSessionSchema)
async def get_session_history_legacy(session_id: str, db: Session = Depends(get_db)):
    """Legacy session history - maintained for compatibility."""
    repo = ChatRepository()
    session = repo.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = repo.get_messages(db, session_id)
    return ChatSessionSchema(
        id=session.id,
        title=session.title,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
        messages=[
            ChatMessageSchema(
                id=m.id,
                role=m.role,
                content=m.content,
                provider=m.provider,
                model=m.model,
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ],
    )
