import threading
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import asc, select

from omnimind_backend.storage.db import db_session
from omnimind_backend.storage.models import Conversation, Message, MindJob
from omnimind_backend.storage.repositories import MindRepository


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truncate(text: str, limit: int = 240) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else f"{text[: limit - 3]}..."


class SessionSupervisor:
    """Basic v1 Supervisor for cross-session context analysis jobs.

    This implementation is intentionally conservative: deterministic context synthesis,
    async execution via background thread, and persisted snapshots for later deep analysis.
    """

    def __init__(self) -> None:
        self._mind_repository = MindRepository()

    def dispatch(self, job_id: str) -> None:
        thread = threading.Thread(target=self._run_job, args=(job_id,), daemon=True)
        thread.start()

    def run_now(self, job_id: str) -> None:
        self._run_job(job_id)

    def _run_job(self, job_id: str) -> None:
        try:
            with db_session() as session:
                row = session.get(MindJob, job_id)
                if row is None:
                    return
                self._mind_repository.mark_job_running(session, job_id)

            with db_session() as session:
                row = session.get(MindJob, job_id)
                if row is None:
                    return

                selected = row.selected_session_ids or []
                query = row.query

                snapshots: list[dict[str, Any]] = []
                summary_lines: list[str] = []

                for session_id in selected:
                    conv = session.get(Conversation, session_id)
                    if conv is None:
                        continue
                    messages = session.scalars(
                        select(Message)
                        .where(Message.conversation_id == session_id)
                        .order_by(asc(Message.created_at))
                    ).all()

                    msg_preview = [
                        {
                            "role": m.role,
                            "content": _truncate(m.content, 400),
                            "runId": m.run_id,
                            "createdAt": m.created_at.isoformat(),
                        }
                        for m in messages[-12:]
                    ]

                    snapshots.append(
                        {
                            "sessionId": conv.id,
                            "title": conv.title,
                            "topicAbout": conv.topic_about,
                            "topicType": conv.topic_type.value,
                            "folderPath": conv.folder_path,
                            "messages": msg_preview,
                        }
                    )

                    summary_lines.append(
                        f"- Session '{conv.title}' ({conv.id}) | type={conv.topic_type.value} | messages={len(messages)}"
                    )

                if query:
                    header = f"Query: {query}\n\n"
                else:
                    header = "Query: <none> (automatic context synthesis)\n\n"

                result_summary = (
                    header
                    + "Supervisor synthesis (v1 basic):\n"
                    + "\n".join(summary_lines or ["- No sessions available for synthesis."])
                    + "\n\nGenerated at: "
                    + _utcnow_iso()
                )

                self._mind_repository.add_snapshot(
                    session,
                    job_id=job_id,
                    payload={
                        "query": query,
                        "selectedSessionIds": selected,
                        "sessions": snapshots,
                    },
                )
                self._mind_repository.mark_job_completed(session, job_id, result_summary=result_summary)
        except Exception as exc:
            with db_session() as session:
                self._mind_repository.mark_job_failed(session, job_id, error_message=str(exc))


session_supervisor = SessionSupervisor()
