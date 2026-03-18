from __future__ import annotations

from pathlib import Path


MIGRATION_PATH = Path(
    "/home/levybonito/Projetos/MindFlow/python/mindflow_backend/storage/postgresql/migrations/versions/20260317_0014_session_memory_indexing_metadata.py"
)


def test_session_memory_indexing_migration_exists() -> None:
    assert MIGRATION_PATH.exists()


def test_session_memory_indexing_migration_contains_expected_columns() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260317_0014"' in content
    assert 'down_revision = "20260317_0013"' in content
    for token in (
        '"indexable"',
        '"content_kind"',
        '"quality_flags"',
        '"source_status"',
        '"derived_from_recall"',
        '"session_embeddings"',
        '"session_blocks"',
    ):
        assert token in content
