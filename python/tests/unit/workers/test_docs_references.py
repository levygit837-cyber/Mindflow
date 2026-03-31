from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
README_PATH = REPO_ROOT / "README.md"
ARCH_BACKEND_PATH = REPO_ROOT / "docs" / "architecture" / "python-backend.md"
ENGINEERING_STANDARDS_PATH = REPO_ROOT / "docs" / "architecture" / "python-engineering-standards.md"
COMPOSE_PATH = REPO_ROOT / "python" / "docker-compose.backend.yml"
ENV_EXAMPLE_PATH = REPO_ROOT / "python" / ".env.example"
LEGACY_README_PATH = (
    REPO_ROOT
    / "python"
    / "mindflow_backend"
    / "workers"
    / "archive"
    / "legacy_rq_workers_20260305_163354"
    / "README.md"
)


def test_primary_docs_promote_rabbitmq_and_aio_pika_instead_of_rq() -> None:
    readme = README_PATH.read_text(encoding="utf-8").lower()
    backend_doc = ARCH_BACKEND_PATH.read_text(encoding="utf-8").lower()
    standards_doc = ENGINEERING_STANDARDS_PATH.read_text(encoding="utf-8").lower()

    assert "rabbitmq" in readme
    assert "rabbitmq" in backend_doc
    assert "rabbitmq" in standards_doc
    assert "aio-pika" in backend_doc
    assert "aio-pika" in standards_doc

    forbidden_active_refs = [
        "redis+rq",
        "rq + redis",
        "execução assíncrona (rq)",
        "rq background worker",
    ]
    for forbidden in forbidden_active_refs:
        assert forbidden not in readme
        assert forbidden not in backend_doc
        assert forbidden not in standards_doc


def test_docs_describe_worker_contract_tree_and_rollout_flags() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    backend_doc = ARCH_BACKEND_PATH.read_text(encoding="utf-8")
    standards_doc = ENGINEERING_STANDARDS_PATH.read_text(encoding="utf-8")

    assert "workers/contracts" in backend_doc
    assert "workers/contracts" in standards_doc
    assert "schemas" in backend_doc
    assert "interfaces" in backend_doc
    assert "ENABLE_RABBITMQ" in readme
    assert "QUEUE_MEMORY_PIPELINE" in readme
    assert "QUEUE_SESSION_REVIEW" in readme
    assert "QUEUE_RESEARCH_PIPELINE" in readme


def test_compose_and_env_example_share_rabbitmq_defaults() -> None:
    compose = COMPOSE_PATH.read_text(encoding="utf-8")
    env_example = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")

    assert "RABBITMQ_PORT=5673" in env_example
    assert 'container_name: ${RABBITMQ_CONTAINER_NAME:-mindflow-rabbitmq-v1}' in compose
    assert '- "${RABBITMQ_PORT:-5673}:5672"' in compose
    assert "RABBITMQ_URL=amqp://guest:guest@127.0.0.1:5673/" in env_example


def test_legacy_archive_readme_marks_rq_as_archived_only() -> None:
    legacy_readme = LEGACY_README_PATH.read_text(encoding="utf-8").lower()

    assert "legacy rq workers archive" in legacy_readme
    assert "archived" in legacy_readme
    assert "rabbitmq" in legacy_readme
    assert "official" in legacy_readme
