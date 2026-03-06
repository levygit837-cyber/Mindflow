from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mindflow_backend.storage.postgresql.models import ChatMessage, ChatSession, NeuralDocument


class ChatRepository:
    def get_session(self, db: Session, session_id: str) -> ChatSession | None:
        return db.get(ChatSession, session_id)

    def get_or_create_session(self, db: Session, session_id: str, title: str | None = None) -> ChatSession:
        session = db.get(ChatSession, session_id)
        if not session:
            # Create session if it doesn't exist
            session = ChatSession(id=session_id, title=title or "New Conversation")
            db.add(session)
            db.flush()
        return session

    def list_sessions(self, db: Session, limit: int = 50) -> list[ChatSession]:
        stmt = select(ChatSession).order_by(ChatSession.updated_at.desc()).limit(limit)
        return list(db.scalars(stmt).all())

    def update_session_title(self, db: Session, session_id: str, title: str) -> None:
        session = db.get(ChatSession, session_id)
        if session:
            session.title = title
            db.flush()

    def add_message(
        self,
        db: Session,
        session_id: str,
        role: str,
        content: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> ChatMessage:
        self.get_or_create_session(db, session_id)
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            provider=provider,
            model=model,
        )
        db.add(message)
        
        # Update session timestamp
        session = db.get(ChatSession, session_id)
        if session:
            from datetime import UTC, datetime
            session.updated_at = datetime.now(UTC)
            
        db.flush()
        return message

    def get_messages(self, db: Session, session_id: str) -> list[ChatMessage]:
        stmt = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc())
        return list(db.scalars(stmt).all())


class NeuralRepository:
    def next_sequence(self, session: Session) -> int:
        value = session.scalar(select(func.max(NeuralDocument.sequence)))
        if value is None:
            return 1
        return int(value) + 1

    def create_document(
        self,
        session: Session,
        *,
        folder_path: str | None,
        file_path: str,
        filename: str,
        sequence: int,
        content: str,
    ) -> int:
        row = NeuralDocument(
            folder_path=folder_path,
            file_path=file_path,
            filename=filename,
            sequence=sequence,
            content=content,
        )
        session.add(row)
        session.flush()
        return row.id
