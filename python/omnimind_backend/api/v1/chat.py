from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from omnimind_backend.schemas.agent import ChatMessageSchema, ChatSessionSchema
from omnimind_backend.storage.db import db_session
from omnimind_backend.storage.repositories import ChatRepository

router = APIRouter(prefix="/chat", tags=["chat"])


def get_db():
    with db_session() as db:
        yield db


@router.get("/sessions", response_model=list[ChatSessionSchema])
async def list_sessions(db: Session = Depends(get_db)):
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
async def get_session_history(session_id: str, db: Session = Depends(get_db)):
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
