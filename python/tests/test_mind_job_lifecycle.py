from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from omnimind_backend.storage.models import Base, MindJob
from omnimind_backend.storage.repositories import MindRepository


def _build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return Session(engine)


def test_mind_job_lifecycle_transitions() -> None:
    repository = MindRepository()

    with _build_session() as session:
        job = MindJob(
            id="job-1",
            folder_path="/tmp/project",
            selected_session_ids=["s-1"],
            query="optional query",
            status="queued",
        )
        session.add(job)
        session.commit()

        repository.mark_job_running(session, "job-1")
        session.flush()

        running = session.get(MindJob, "job-1")
        assert running is not None
        assert running.status == "running"
        assert running.started_at is not None

        repository.mark_job_completed(session, "job-1", "done")
        session.flush()

        completed = session.get(MindJob, "job-1")
        assert completed is not None
        assert completed.status == "completed"
        assert completed.result_summary == "done"
        assert completed.completed_at is not None



def test_mind_job_failure_transition() -> None:
    repository = MindRepository()

    with _build_session() as session:
        job = MindJob(
            id="job-2",
            folder_path="/tmp/project",
            selected_session_ids=["s-1"],
            query=None,
            status="queued",
        )
        session.add(job)
        session.commit()

        repository.mark_job_failed(session, "job-2", "boom")
        session.flush()

        failed = session.get(MindJob, "job-2")
        assert failed is not None
        assert failed.status == "failed"
        assert failed.error_message == "boom"
        assert failed.completed_at is not None
