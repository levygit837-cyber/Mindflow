from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from omnimind_backend.schemas.agent import (
    AllowlistPathOut,
    MindJobOut,
    MindSessionLinkOut,
    ProjectOut,
    SessionOut,
    SessionRunOut,
    TopicType,
    MessageOut,
)
from omnimind_backend.storage.models import (
    AllowedPath,
    Conversation,
    Message,
    MindJob,
    MindJobSnapshot,
    MindSessionLink,
    NeuralDocument,
    SessionRun,
    TopicType as TopicTypeModel,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_topic_type(value: TopicType | str) -> TopicTypeModel:
    return TopicTypeModel(value)


def _path_mtime_iso(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        return None


def _session_out(row: Conversation) -> SessionOut:
    return SessionOut(
        id=row.id,
        title=row.title,
        topic_about=row.topic_about,
        topic_type=row.topic_type.value,
        folder_path=row.folder_path,
        project_root_session_id=row.project_root_session_id,
        createdAt=row.created_at.isoformat(),
        updatedAt=row.updated_at.isoformat(),
    )


class SessionRepository:
    def list(
        self,
        session: Session,
        *,
        folder_path: str | None = None,
        topic_type: TopicType | None = None,
    ) -> list[SessionOut]:
        stmt = select(Conversation)
        if folder_path is not None:
            stmt = stmt.where(Conversation.folder_path == folder_path)
        if topic_type is not None:
            stmt = stmt.where(Conversation.topic_type == _to_topic_type(topic_type))

        rows = session.scalars(stmt.order_by(desc(Conversation.updated_at))).all()
        return [_session_out(r) for r in rows]

    def list_by_ids(self, session: Session, session_ids: list[str]) -> list[SessionOut]:
        if not session_ids:
            return []
        rows = session.scalars(
            select(Conversation).where(Conversation.id.in_(session_ids)).order_by(desc(Conversation.updated_at))
        ).all()
        return [_session_out(r) for r in rows]

    def get(self, session: Session, session_id: str) -> SessionOut | None:
        row = session.get(Conversation, session_id)
        if row is None:
            return None
        return _session_out(row)

    def create(
        self,
        session: Session,
        *,
        title: str | None = None,
        topic_about: str | None = None,
        topic_type: TopicType = "standalone",
        folder_path: str | None = None,
        project_root_session_id: str | None = None,
    ) -> SessionOut:
        row = Conversation(
            title=title or "New Session",
            topic_about=topic_about,
            topic_type=_to_topic_type(topic_type),
            folder_path=folder_path,
            project_root_session_id=project_root_session_id,
        )
        session.add(row)
        session.flush()
        return _session_out(row)

    def delete(self, session: Session, session_id: str) -> bool:
        row = session.get(Conversation, session_id)
        if not row:
            return False
        session.delete(row)
        return True

    def list_messages(
        self,
        session: Session,
        session_id: str,
        *,
        run_id: str | None = None,
    ) -> list[MessageOut]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == session_id)
            .order_by(asc(Message.created_at))
        )
        if run_id:
            stmt = stmt.where(Message.run_id == run_id)

        rows = session.scalars(stmt).all()
        return [
            MessageOut(
                id=r.id,
                sessionId=r.conversation_id,
                role=r.role,
                content=r.content,
                thoughts=r.thoughts,
                toolCalls=r.tool_calls,
                runId=r.run_id,
                createdAt=r.created_at.isoformat(),
            )
            for r in rows
        ]

    def save_message(
        self,
        session: Session,
        *,
        session_id: str,
        role: str,
        content: str,
        thoughts: str | None = None,
        tool_calls: list[dict] | None = None,
        run_id: str | None = None,
    ) -> str:
        conv = session.get(Conversation, session_id)
        if conv is None:
            conv = Conversation(
                id=session_id,
                title="New Session",
                topic_type=TopicTypeModel.STANDALONE,
            )
            session.add(conv)
            session.flush()

        row = Message(
            conversation_id=session_id,
            role=role,
            content=content,
            thoughts=thoughts,
            tool_calls=tool_calls,
            run_id=run_id,
        )
        conv.updated_at = _utcnow()
        session.add(row)
        session.flush()
        return row.id

    def register_run(
        self,
        session: Session,
        *,
        session_id: str,
        run_id: str,
        label: str | None = None,
        metadata: dict | None = None,
    ) -> SessionRunOut:
        row = session.scalar(
            select(SessionRun).where(
                SessionRun.conversation_id == session_id,
                SessionRun.run_id == run_id,
            )
        )
        if row is None:
            row = SessionRun(
                conversation_id=session_id,
                run_id=run_id,
                label=label,
                metadata_json=metadata or {},
            )
            session.add(row)
        else:
            if label:
                row.label = label
            if metadata:
                row.metadata_json = metadata
        session.flush()
        return SessionRunOut(
            id=row.id,
            sessionId=row.conversation_id,
            runId=row.run_id,
            label=row.label,
            metadata=row.metadata_json,
            createdAt=row.created_at.isoformat(),
        )

    def list_runs(self, session: Session, session_id: str) -> list[SessionRunOut]:
        rows = session.scalars(
            select(SessionRun)
            .where(SessionRun.conversation_id == session_id)
            .order_by(desc(SessionRun.created_at))
        ).all()
        return [
            SessionRunOut(
                id=r.id,
                sessionId=r.conversation_id,
                runId=r.run_id,
                label=r.label,
                metadata=r.metadata_json,
                createdAt=r.created_at.isoformat(),
            )
            for r in rows
        ]


class MindRepository:
    _AUTO_DISCOVERY_LIMIT = 200

    def list_projects(self, session: Session) -> list[ProjectOut]:
        rows = session.scalars(
            select(Conversation)
            .where(Conversation.folder_path.is_not(None))
            .order_by(desc(Conversation.updated_at))
        ).all()

        by_path: dict[str, list[Conversation]] = {}
        for row in rows:
            if not row.folder_path:
                continue
            by_path.setdefault(row.folder_path, []).append(row)

        projects_by_path: dict[str, ProjectOut] = {}
        for folder_path, items in by_path.items():
            project_main = next((x for x in items if x.topic_type == TopicTypeModel.PROJECT_MAIN), None)
            sessions_count = sum(1 for x in items if x.topic_type != TopicTypeModel.PROJECT_MAIN)
            latest = max(items, key=lambda x: x.updated_at)

            projects_by_path[folder_path] = ProjectOut(
                folderPath=folder_path,
                projectSessionId=project_main.id if project_main else None,
                title=project_main.title if project_main else Path(folder_path).name,
                hasSessions=sessions_count > 0,
                sessionsCount=sessions_count,
                updatedAt=latest.updated_at.isoformat(),
            )

        # Automatic discovery from allowlist roots: include roots and likely
        # project directories (subfolders with a .git marker).
        for folder_path in self._discover_auto_projects(session):
            if folder_path in projects_by_path:
                continue
            path = Path(folder_path)
            projects_by_path[folder_path] = ProjectOut(
                folderPath=folder_path,
                projectSessionId=None,
                title=path.name or folder_path,
                hasSessions=False,
                sessionsCount=0,
                updatedAt=_path_mtime_iso(path),
            )

        return sorted(projects_by_path.values(), key=lambda p: p.updatedAt or "", reverse=True)

    def _discover_auto_projects(self, session: Session) -> set[str]:
        discovered: set[str] = set()

        allowlist_rows = session.scalars(select(AllowedPath).order_by(asc(AllowedPath.path))).all()
        for allow_row in allowlist_rows:
            root = Path(allow_row.path).expanduser().resolve()
            if not root.exists() or not root.is_dir():
                continue

            discovered.add(str(root))
            if len(discovered) >= self._AUTO_DISCOVERY_LIMIT:
                break

            try:
                children = sorted(root.iterdir(), key=lambda p: p.name.lower())
            except OSError:
                continue

            for child in children:
                if len(discovered) >= self._AUTO_DISCOVERY_LIMIT:
                    break
                if not child.is_dir():
                    continue
                if (child / ".git").exists():
                    discovered.add(str(child.resolve()))

        return discovered

    def get_or_create_project_main(
        self,
        session: Session,
        *,
        folder_path: str,
        title: str | None = None,
        topic_about: str | None = None,
    ) -> SessionOut:
        row = session.scalar(
            select(Conversation)
            .where(
                Conversation.folder_path == folder_path,
                Conversation.topic_type == TopicTypeModel.PROJECT_MAIN,
            )
            .order_by(asc(Conversation.created_at))
        )
        if row is None:
            row = Conversation(
                title=title or Path(folder_path).name,
                topic_about=topic_about,
                topic_type=TopicTypeModel.PROJECT_MAIN,
                folder_path=folder_path,
            )
            session.add(row)
            session.flush()
        else:
            if title:
                row.title = title
            if topic_about:
                row.topic_about = topic_about
            row.updated_at = _utcnow()
        session.flush()
        return _session_out(row)

    def list_sessions_for_folder(self, session: Session, folder_path: str) -> list[SessionOut]:
        rows = session.scalars(
            select(Conversation)
            .where(Conversation.folder_path == folder_path)
            .order_by(desc(Conversation.updated_at))
        ).all()
        return [_session_out(r) for r in rows]

    def create_link(
        self,
        session: Session,
        *,
        folder_path: str,
        source_session_id: str,
        target_session_id: str,
        label: str | None = None,
    ) -> MindSessionLinkOut:
        row = MindSessionLink(
            folder_path=folder_path,
            source_session_id=source_session_id,
            target_session_id=target_session_id,
            label=label,
        )
        session.add(row)
        session.flush()
        return MindSessionLinkOut(
            id=row.id,
            folderPath=row.folder_path,
            sourceSessionId=row.source_session_id,
            targetSessionId=row.target_session_id,
            label=row.label,
            createdAt=row.created_at.isoformat(),
        )

    def delete_link(self, session: Session, link_id: int) -> bool:
        row = session.get(MindSessionLink, link_id)
        if not row:
            return False
        session.delete(row)
        return True

    def list_links(self, session: Session, folder_path: str) -> list[MindSessionLinkOut]:
        rows = session.scalars(
            select(MindSessionLink)
            .where(MindSessionLink.folder_path == folder_path)
            .order_by(desc(MindSessionLink.created_at))
        ).all()
        return [
            MindSessionLinkOut(
                id=r.id,
                folderPath=r.folder_path,
                sourceSessionId=r.source_session_id,
                targetSessionId=r.target_session_id,
                label=r.label,
                createdAt=r.created_at.isoformat(),
            )
            for r in rows
        ]

    def create_job(
        self,
        session: Session,
        *,
        folder_path: str,
        session_ids: list[str],
        query: str | None,
        source_session_id: str | None,
    ) -> MindJobOut:
        row = MindJob(
            id=str(uuid.uuid4()),
            folder_path=folder_path,
            selected_session_ids=session_ids,
            query=query,
            requested_by_session_id=source_session_id,
            status="queued",
        )
        session.add(row)
        session.flush()
        return self._to_job_out(row)

    def get_job(self, session: Session, job_id: str) -> MindJobOut | None:
        row = session.get(MindJob, job_id)
        if row is None:
            return None
        return self._to_job_out(row)

    def mark_job_running(self, session: Session, job_id: str) -> None:
        row = session.get(MindJob, job_id)
        if row is None:
            return
        row.status = "running"
        row.started_at = _utcnow()

    def mark_job_failed(self, session: Session, job_id: str, error_message: str) -> None:
        row = session.get(MindJob, job_id)
        if row is None:
            return
        row.status = "failed"
        row.error_message = error_message
        row.completed_at = _utcnow()

    def mark_job_completed(self, session: Session, job_id: str, result_summary: str) -> None:
        row = session.get(MindJob, job_id)
        if row is None:
            return
        row.status = "completed"
        row.result_summary = result_summary
        row.completed_at = _utcnow()

    def add_snapshot(self, session: Session, *, job_id: str, payload: dict) -> None:
        current_max = session.scalar(
            select(func.max(MindJobSnapshot.snapshot_index)).where(MindJobSnapshot.job_id == job_id)
        )
        next_index = (int(current_max) + 1) if current_max is not None else 0
        row = MindJobSnapshot(job_id=job_id, snapshot_index=next_index, payload=payload)
        session.add(row)

    def _to_job_out(self, row: MindJob) -> MindJobOut:
        return MindJobOut(
            id=row.id,
            folderPath=row.folder_path,
            sessionIds=row.selected_session_ids,
            query=row.query,
            status=row.status,
            resultSummary=row.result_summary,
            errorMessage=row.error_message,
            createdAt=row.created_at.isoformat(),
            startedAt=row.started_at.isoformat() if row.started_at else None,
            completedAt=row.completed_at.isoformat() if row.completed_at else None,
        )


class AllowlistRepository:
    def list(self, session: Session) -> list[AllowlistPathOut]:
        rows = session.scalars(select(AllowedPath).order_by(asc(AllowedPath.path))).all()
        return [AllowlistPathOut(path=r.path) for r in rows]

    def is_allowed(self, session: Session, folder_path: str) -> bool:
        candidate = Path(folder_path).resolve()
        rows = session.scalars(select(AllowedPath)).all()
        if not rows:
            return False
        for row in rows:
            allowed = Path(row.path).resolve()
            try:
                common = os.path.commonpath([str(candidate), str(allowed)])
            except ValueError:
                continue
            if common == str(allowed):
                return True
        return False

    def bootstrap_from_env(self, session: Session, raw_paths: str | None) -> int:
        if not raw_paths:
            return 0

        normalized: list[str] = []
        for chunk in raw_paths.replace("\n", ",").split(","):
            value = chunk.strip()
            if not value:
                continue
            normalized.append(str(Path(value).expanduser().resolve()))

        inserted = 0
        for path in sorted(set(normalized)):
            existing = session.get(AllowedPath, path)
            if existing is None:
                session.add(AllowedPath(path=path, source="env_bootstrap"))
                inserted += 1
        return inserted


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
        session_id: str | None,
        folder_path: str | None,
        file_path: str,
        filename: str,
        sequence: int,
        content: str,
    ) -> int:
        row = NeuralDocument(
            session_id=session_id,
            folder_path=folder_path,
            file_path=file_path,
            filename=filename,
            sequence=sequence,
            content=content,
        )
        session.add(row)
        session.flush()
        return row.id
