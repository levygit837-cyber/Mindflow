from fastapi import APIRouter, HTTPException, Query

from omnimind_backend.api.deps import allowlist_repository, mind_repository, session_repository
from omnimind_backend.mind.path_guard import PathValidationError, normalize_and_validate_folder_path
from omnimind_backend.mind.sandbox import MindSandboxService
from omnimind_backend.mind.supervisor import session_supervisor
from omnimind_backend.schemas.agent import (
    AllowlistPathOut,
    MindJobCreate,
    MindJobOut,
    MindSandboxQueryRequest,
    MindSandboxQueryResponse,
    MindSessionLinkCreate,
    MindSessionLinkOut,
    ProjectCreate,
    ProjectOut,
    SessionOut,
)
from omnimind_backend.storage.db import db_session

router = APIRouter(prefix="/agent/mind", tags=["mind"])
sandbox_service = MindSandboxService()


@router.get("/allowlist", response_model=list[AllowlistPathOut])
def list_allowlist() -> list[AllowlistPathOut]:
    with db_session() as session:
        return allowlist_repository.list(session)


@router.get("/projects", response_model=list[ProjectOut])
def list_projects() -> list[ProjectOut]:
    with db_session() as session:
        return mind_repository.list_projects(session)


@router.post("/projects", response_model=SessionOut)
def create_project(payload: ProjectCreate) -> SessionOut:
    with db_session() as session:
        try:
            normalized = normalize_and_validate_folder_path(
                folder_path=payload.folderPath,
                session=session,
                allowlist_repository=allowlist_repository,
            )
        except PathValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return mind_repository.get_or_create_project_main(
            session,
            folder_path=normalized,
            title=payload.title,
            topic_about=payload.topicAbout,
        )


@router.get("/sessions", response_model=list[SessionOut])
def list_project_sessions(folderPath: str = Query(..., min_length=1)) -> list[SessionOut]:
    with db_session() as session:
        try:
            normalized = normalize_and_validate_folder_path(
                folder_path=folderPath,
                session=session,
                allowlist_repository=allowlist_repository,
            )
        except PathValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return mind_repository.list_sessions_for_folder(session, normalized)


@router.get("/links", response_model=list[MindSessionLinkOut])
def list_links(folderPath: str = Query(..., min_length=1)) -> list[MindSessionLinkOut]:
    with db_session() as session:
        try:
            normalized = normalize_and_validate_folder_path(
                folder_path=folderPath,
                session=session,
                allowlist_repository=allowlist_repository,
            )
        except PathValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return mind_repository.list_links(session, normalized)


@router.post("/links", response_model=MindSessionLinkOut)
def create_link(payload: MindSessionLinkCreate) -> MindSessionLinkOut:
    with db_session() as session:
        try:
            normalized = normalize_and_validate_folder_path(
                folder_path=payload.folderPath,
                session=session,
                allowlist_repository=allowlist_repository,
            )
        except PathValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        src = session_repository.get(session, payload.sourceSessionId)
        tgt = session_repository.get(session, payload.targetSessionId)
        if src is None or tgt is None:
            raise HTTPException(status_code=404, detail="Source or target session not found")

        return mind_repository.create_link(
            session,
            folder_path=normalized,
            source_session_id=payload.sourceSessionId,
            target_session_id=payload.targetSessionId,
            label=payload.label,
        )


@router.delete("/links/{link_id}")
def delete_link(link_id: int) -> dict[str, bool]:
    with db_session() as session:
        ok = mind_repository.delete_link(session, link_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"ok": True}


@router.post("/jobs", response_model=MindJobOut)
def create_job(payload: MindJobCreate) -> MindJobOut:
    with db_session() as session:
        try:
            normalized = normalize_and_validate_folder_path(
                folder_path=payload.folderPath,
                session=session,
                allowlist_repository=allowlist_repository,
            )
        except PathValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        sessions = session_repository.list_by_ids(session, payload.sessionIds)
        if len(sessions) != len(payload.sessionIds):
            raise HTTPException(status_code=404, detail="One or more sessions not found")

        created = mind_repository.create_job(
            session,
            folder_path=normalized,
            session_ids=payload.sessionIds,
            query=payload.query,
            source_session_id=payload.sourceSessionId,
        )

    session_supervisor.dispatch(created.id)
    return created


@router.get("/jobs/{job_id}", response_model=MindJobOut)
def get_job(job_id: str) -> MindJobOut:
    with db_session() as session:
        job = mind_repository.get_job(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/sandbox/query", response_model=MindSandboxQueryResponse)
def sandbox_query(payload: MindSandboxQueryRequest) -> MindSandboxQueryResponse:
    with db_session() as session:
        if payload.folderPath:
            try:
                normalized = normalize_and_validate_folder_path(
                    folder_path=payload.folderPath,
                    session=session,
                    allowlist_repository=allowlist_repository,
                )
                payload.folderPath = normalized
            except PathValidationError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        sessions = session_repository.list_by_ids(session, payload.sessionIds)
        if len(sessions) != len(payload.sessionIds):
            raise HTTPException(status_code=404, detail="One or more sessions not found")

        return sandbox_service.execute(session, payload)
