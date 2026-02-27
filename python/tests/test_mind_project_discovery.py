from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from omnimind_backend.storage.models import AllowedPath, Base, Conversation, TopicType
from omnimind_backend.storage.repositories import MindRepository


def _build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return Session(engine)


def test_project_list_includes_auto_discovered_git_projects(tmp_path: Path) -> None:
    allow_root = (tmp_path / "workspace").resolve()
    allow_root.mkdir(parents=True)

    auto_project = (allow_root / "auto-project").resolve()
    auto_project.mkdir()
    (auto_project / ".git").mkdir()

    with _build_session() as session:
        session.add(AllowedPath(path=str(allow_root), source="test"))
        session.commit()

        projects = MindRepository().list_projects(session)

    paths = {item.folderPath for item in projects}
    assert str(allow_root) in paths
    assert str(auto_project) in paths



def test_project_list_deduplicates_manual_and_auto_entries(tmp_path: Path) -> None:
    allow_root = (tmp_path / "workspace").resolve()
    allow_root.mkdir(parents=True)

    manual_project = (allow_root / "manual-project").resolve()
    manual_project.mkdir()
    (manual_project / ".git").mkdir()

    with _build_session() as session:
        session.add(AllowedPath(path=str(allow_root), source="test"))

        root_session = Conversation(
            title="Manual Root",
            topic_type=TopicType.PROJECT_MAIN,
            folder_path=str(manual_project),
        )
        session.add(root_session)
        session.flush()

        topic_session = Conversation(
            title="Topic",
            topic_type=TopicType.PROJECT_TOPIC,
            folder_path=str(manual_project),
            project_root_session_id=root_session.id,
        )
        session.add(topic_session)
        session.commit()

        projects = MindRepository().list_projects(session)

    same_path = [item for item in projects if item.folderPath == str(manual_project)]
    assert len(same_path) == 1

    project = same_path[0]
    assert project.projectSessionId == root_session.id
    assert project.hasSessions is True
    assert project.sessionsCount == 1
