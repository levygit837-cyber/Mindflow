from __future__ import annotations

from pathlib import Path


MIGRATION_PATH = Path(
    "/home/levybonito/Projetos/MindFlow/python/mindflow_backend/storage/postgresql/migrations/versions/20260316_0011_session_embeddings_table.py"
)


def test_session_embeddings_migration_exists() -> None:
    assert MIGRATION_PATH.exists()


def test_session_embeddings_migration_creates_expected_table_and_index() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260316_0011"' in content
    assert 'down_revision = "20260316_0010"' in content
    assert '"session_embeddings"' in content
    assert "Vector(768)" in content
    assert "ix_session_embeddings_embedding" in content
