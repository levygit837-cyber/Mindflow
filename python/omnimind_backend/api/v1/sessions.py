from fastapi import APIRouter, HTTPException, Query

from omnimind_backend.api.deps import session_repository
from omnimind_backend.schemas.agent import MessageOut, SessionCreate, SessionOut, SessionRunOut, SessionUpdate, TopicType
from omnimind_backend.storage.db import db_session

router = APIRouter(prefix="/agent/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionOut])
def list_sessions(
    folderPath: str | None = Query(default=None),
    topicType: TopicType | None = Query(default=None),
) -> list[SessionOut]:
    with db_session() as session:
        return session_repository.list(session, folder_path=folderPath, topic_type=topicType)


@router.post("", response_model=SessionOut)
def create_session(payload: SessionCreate) -> SessionOut:
    with db_session() as session:
        return session_repository.create(
            session,
            title=payload.title,
            topic_about=payload.topic_about,
            topic_type=payload.topic_type,
            folder_path=payload.folder_path,
            project_root_session_id=payload.project_root_session_id,
        )


@router.patch("/{session_id}", response_model=SessionOut)
def update_session(session_id: str, payload: SessionUpdate) -> SessionOut:
    with db_session() as session:
        from omnimind_backend.storage.models import Conversation

        conv = session.get(Conversation, session_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="Session not found")

        if payload.title is not None:
            conv.title = payload.title
        if payload.topic_about is not None:
            conv.topic_about = payload.topic_about
        updated = session_repository.get(session, session_id)
        if updated is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return updated


@router.delete("/{session_id}")
def delete_session(session_id: str) -> dict[str, bool]:
    with db_session() as session:
        ok = session_repository.delete(session, session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


@router.get("/{session_id}/messages", response_model=list[MessageOut])
def list_messages(session_id: str, runId: str | None = Query(default=None)) -> list[MessageOut]:
    with db_session() as session:
        return session_repository.list_messages(session, session_id, run_id=runId)


@router.get("/{session_id}/runs", response_model=list[SessionRunOut])
def list_runs(session_id: str) -> list[SessionRunOut]:
    with db_session() as session:
        return session_repository.list_runs(session, session_id)
