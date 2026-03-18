"""Verify that memory storage models and postgresql models are aligned.

Canonical rule: both AgentMemoryEmbedding.vector and SessionEmbedding.embedding
must use Vector(768). SessionEmbedding primary key must be int, session_id must
be String. EMBEDDING_DIMS=768 is the single source of truth.
"""
from __future__ import annotations

import pytest
from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, String

from mindflow_backend.memory.storage import models as mem_models
from mindflow_backend.storage.postgresql import models as pg_models


# ---------------------------------------------------------------------------
# AgentMemoryEmbedding alignment
# ---------------------------------------------------------------------------

def test_agent_memory_embedding_vector_is_pgvector_in_memory_models() -> None:
    col = mem_models.AgentMemoryEmbedding.__table__.c["vector"]
    assert isinstance(col.type, Vector), f"Expected Vector, got {type(col.type)}"


def test_agent_memory_embedding_vector_is_pgvector_in_pg_models() -> None:
    col = pg_models.AgentMemoryEmbedding.__table__.c["vector"]
    assert isinstance(col.type, Vector), f"Expected Vector, got {type(col.type)}"


def test_agent_memory_embedding_vector_dims_768_in_memory_models() -> None:
    col = mem_models.AgentMemoryEmbedding.__table__.c["vector"]
    assert col.type.dim == 768


def test_agent_memory_embedding_vector_dims_768_in_pg_models() -> None:
    col = pg_models.AgentMemoryEmbedding.__table__.c["vector"]
    assert col.type.dim == 768


# ---------------------------------------------------------------------------
# SessionEmbedding alignment
# ---------------------------------------------------------------------------

def test_session_embedding_id_is_integer_in_memory_models() -> None:
    col = mem_models.SessionEmbedding.__table__.c["id"]
    assert isinstance(col.type, Integer), f"Expected Integer, got {type(col.type)}"


def test_session_embedding_id_is_integer_in_pg_models() -> None:
    col = pg_models.SessionEmbedding.__table__.c["id"]
    assert isinstance(col.type, Integer), f"Expected Integer, got {type(col.type)}"


def test_session_embedding_session_id_is_string_in_memory_models() -> None:
    col = mem_models.SessionEmbedding.__table__.c["session_id"]
    assert isinstance(col.type, String), f"Expected String, got {type(col.type)}"


def test_session_embedding_session_id_is_string_in_pg_models() -> None:
    col = pg_models.SessionEmbedding.__table__.c["session_id"]
    assert isinstance(col.type, String), f"Expected String, got {type(col.type)}"


def test_session_embedding_embedding_is_pgvector_in_memory_models() -> None:
    col = mem_models.SessionEmbedding.__table__.c["embedding"]
    assert isinstance(col.type, Vector), f"Expected Vector, got {type(col.type)}"


def test_session_embedding_embedding_is_pgvector_in_pg_models() -> None:
    col = pg_models.SessionEmbedding.__table__.c["embedding"]
    assert isinstance(col.type, Vector), f"Expected Vector, got {type(col.type)}"


def test_session_embedding_embedding_dims_768_in_memory_models() -> None:
    col = mem_models.SessionEmbedding.__table__.c["embedding"]
    assert col.type.dim == 768


def test_session_embedding_embedding_dims_768_in_pg_models() -> None:
    col = pg_models.SessionEmbedding.__table__.c["embedding"]
    assert col.type.dim == 768


def test_agent_memory_cursor_has_no_chunk_columns_in_memory_models() -> None:
    cols = set(mem_models.AgentMemoryCursor.__table__.c.keys())
    assert "tokens_since_chunk" not in cols
    assert "last_chunked_event_id" not in cols
    assert "chunk_sequence" not in cols


def test_agent_memory_cursor_has_no_chunk_columns_in_pg_models() -> None:
    cols = set(pg_models.AgentMemoryCursor.__table__.c.keys())
    assert "tokens_since_chunk" not in cols
    assert "last_chunked_event_id" not in cols
    assert "chunk_sequence" not in cols


def test_session_block_embedding_is_pgvector_in_memory_models() -> None:
    col = mem_models.SessionBlock.__table__.c["embedding"]
    assert isinstance(col.type, Vector), f"Expected Vector, got {type(col.type)}"


def test_session_block_embedding_is_pgvector_in_pg_models() -> None:
    col = pg_models.SessionBlock.__table__.c["embedding"]
    assert isinstance(col.type, Vector), f"Expected Vector, got {type(col.type)}"


def test_session_block_embedding_dims_768_in_memory_models() -> None:
    col = mem_models.SessionBlock.__table__.c["embedding"]
    assert col.type.dim == 768


def test_session_block_embedding_dims_768_in_pg_models() -> None:
    col = pg_models.SessionBlock.__table__.c["embedding"]
    assert col.type.dim == 768


def test_session_embedding_metadata_columns_exist_in_memory_models() -> None:
    cols = set(mem_models.SessionEmbedding.__table__.c.keys())
    assert {"indexable", "content_kind", "quality_flags", "source_status", "derived_from_recall"} <= cols


def test_session_embedding_metadata_columns_exist_in_pg_models() -> None:
    cols = set(pg_models.SessionEmbedding.__table__.c.keys())
    assert {"indexable", "content_kind", "quality_flags", "source_status", "derived_from_recall"} <= cols


def test_session_block_metadata_columns_exist_in_memory_models() -> None:
    cols = set(mem_models.SessionBlock.__table__.c.keys())
    assert {"indexable", "content_kind", "quality_flags", "source_status", "derived_from_recall"} <= cols


def test_session_block_metadata_columns_exist_in_pg_models() -> None:
    cols = set(pg_models.SessionBlock.__table__.c.keys())
    assert {"indexable", "content_kind", "quality_flags", "source_status", "derived_from_recall"} <= cols


# ---------------------------------------------------------------------------
# Settings canonical dims
# ---------------------------------------------------------------------------

def test_settings_canonical_embedding_dims_is_768() -> None:
    from mindflow_backend.infra.config.settings import Settings
    s = Settings()
    assert s.embedding_dims == 768


def test_settings_deprecated_memory_embedding_dims_default_is_768() -> None:
    from mindflow_backend.infra.config.settings import Settings
    s = Settings()
    assert s.memory_embedding_dims == 768


def test_settings_deprecated_vector_db_dimensions_default_is_768() -> None:
    from mindflow_backend.infra.config.settings import Settings
    s = Settings()
    assert s.vector_db_dimensions == 768


def test_settings_canonical_embedding_dims_property() -> None:
    from mindflow_backend.infra.config.settings import Settings
    s = Settings()
    assert s.canonical_embedding_dims == 768
