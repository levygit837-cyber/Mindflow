from __future__ import annotations

from pathlib import Path

MIGRATION_PATH = Path(
    "/home/levybonito/Projetos/MindFlow/python/mindflow_backend/storage/postgresql/migrations/versions/20260317_0012_session_blocks_and_embedding_identity.py"
)


def test_session_blocks_migration_exists() -> None:
    assert MIGRATION_PATH.exists()


def test_session_blocks_migration_contains_expected_schema_changes() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260317_0012"' in content
    assert 'down_revision = "20260316_0011"' in content
    assert '"session_blocks"' in content
    assert '"source_message_id"' in content
    assert '"idempotency_key"' in content
    assert "Vector(768)" in content
    assert "uq_session_embedding_message" in content
    assert "uq_session_embedding_idempotency" in content
    assert "ix_session_blocks_embedding" in content
