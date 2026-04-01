"""Tests for MIND.md memory system — MemoryType, MemoryFileLoader, MemoryFileLayer."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from mindflow_backend.agents.prompts.layers.memory_loader import MemoryFile, MemoryFileLoader
from mindflow_backend.agents.prompts.layers.memory_types import (
    DEFAULT_SEARCH_PATHS,
    MEMORY_TYPE_HEADERS,
    MEMORY_TYPE_PRIORITY,
    MemoryType,
)


# ─── MemoryType Tests ────────────────────────────────────────────────


class TestMemoryType:
    """Tests for MemoryType enum."""

    def test_all_four_types_exist(self):
        assert len(MemoryType) == 4
        assert MemoryType.USER == "user"
        assert MemoryType.PROJECT == "project"
        assert MemoryType.LOCAL == "local"
        assert MemoryType.MANAGED == "managed"

    def test_priority_order(self):
        """Managed should have highest priority, local lowest."""
        assert MEMORY_TYPE_PRIORITY[MemoryType.MANAGED] > MEMORY_TYPE_PRIORITY[MemoryType.USER]
        assert MEMORY_TYPE_PRIORITY[MemoryType.USER] > MEMORY_TYPE_PRIORITY[MemoryType.PROJECT]
        assert MEMORY_TYPE_PRIORITY[MemoryType.PROJECT] > MEMORY_TYPE_PRIORITY[MemoryType.LOCAL]

    def test_headers_defined(self):
        for mt in MemoryType:
            assert mt in MEMORY_TYPE_HEADERS
            assert MEMORY_TYPE_HEADERS[mt].startswith("##")

    def test_search_paths_defined(self):
        for mt in MemoryType:
            assert mt in DEFAULT_SEARCH_PATHS
            assert len(DEFAULT_SEARCH_PATHS[mt]) > 0


# ─── MemoryFile Tests ────────────────────────────────────────────────


class TestMemoryFile:
    """Tests for MemoryFile dataclass."""

    def test_token_estimation(self):
        mf = MemoryFile(
            content="A" * 400,
            source=MemoryType.USER,
            path="/fake/path",
        )
        assert mf.token_estimate == 100  # 400 / 4

    def test_header_property(self):
        mf = MemoryFile(
            content="test",
            source=MemoryType.MANAGED,
            path="/fake",
        )
        assert mf.header == "## Managed Memory (Enterprise)"

    def test_minimum_tokens(self):
        mf = MemoryFile(
            content="",
            source=MemoryType.USER,
            path="/fake",
        )
        assert mf.token_estimate == 1  # min 1 token


# ─── MemoryFileLoader Tests ──────────────────────────────────────────


class TestMemoryFileLoader:
    """Tests for MemoryFileLoader."""

    @pytest.fixture
    def temp_project(self, tmp_path: Path) -> Path:
        """Create a temp project with MIND.md files."""
        # Create .mindflow directory
        mindflow_dir = tmp_path / ".mindflow"
        mindflow_dir.mkdir()

        # Project memory
        (mindflow_dir / "MIND.md").write_text("# Project Rules\nAlways use type hints.")

        # Local memory (gitignored)
        (mindflow_dir / "MIND.local.md").write_text("# Local Prefs\nUse vim as editor.")

        return tmp_path

    @pytest.fixture
    def temp_home(self, tmp_path: Path) -> Path:
        """Create a temp home directory with user and managed memory."""
        # User memory
        mindflow_dir = tmp_path / ".mindflow"
        mindflow_dir.mkdir()
        (mindflow_dir / "MIND.md").write_text("# User Prefs\nSpeak in Portuguese.")

        # Managed memory
        managed_dir = mindflow_dir / "managed"
        managed_dir.mkdir()
        (managed_dir / "MIND.md").write_text("# Enterprise Policy\nNo external APIs.")

        return tmp_path

    @pytest.mark.asyncio
    async def test_load_all_four_types(self, tmp_path: Path):
        """Should load all 4 memory types when all files exist in same dir."""
        # Create all 4 files in the same directory (no home patching needed)
        mindflow_dir = tmp_path / ".mindflow"
        mindflow_dir.mkdir()
        (mindflow_dir / "MIND.md").write_text("# Project Rules")
        (mindflow_dir / "MIND.local.md").write_text("# Local Prefs")
        user_dir = mindflow_dir / "user"
        user_dir.mkdir()
        (user_dir / "MIND.md").write_text("# User Prefs")
        managed_dir = mindflow_dir / "managed"
        managed_dir.mkdir()
        (managed_dir / "MIND.md").write_text("# Enterprise Policy")

        loader = MemoryFileLoader()
        loader._search_paths = {
            MemoryType.USER: [str(user_dir / "MIND.md")],
            MemoryType.PROJECT: [".mindflow/MIND.md"],
            MemoryType.LOCAL: [".mindflow/MIND.local.md"],
            MemoryType.MANAGED: [str(managed_dir / "MIND.md")],
        }

        files = await loader.load_all(str(tmp_path))

        assert len(files) == 4
        loaded_types = {f.source for f in files}
        assert loaded_types == {MemoryType.USER, MemoryType.PROJECT, MemoryType.LOCAL, MemoryType.MANAGED}

    @pytest.mark.asyncio
    async def test_load_only_project(self, temp_project: Path):
        """Should load only project memory when others don't exist."""
        loader = MemoryFileLoader()
        loader._search_paths = {
            MemoryType.PROJECT: [".mindflow/MIND.md"],
        }

        files = await loader.load_all(str(temp_project), types=[MemoryType.PROJECT])

        assert len(files) == 1
        assert files[0].source == MemoryType.PROJECT
        assert "type hints" in files[0].content

    @pytest.mark.asyncio
    async def test_missing_files_returns_empty(self, tmp_path: Path):
        """Should return empty list when no MIND.md files exist."""
        loader = MemoryFileLoader()
        files = await loader.load_all(str(tmp_path))
        assert files == []

    @pytest.mark.asyncio
    async def test_priority_sorting(self, tmp_path: Path):
        """Files should be sorted by priority (managed > user > project > local)."""
        mindflow_dir = tmp_path / ".mindflow"
        mindflow_dir.mkdir()
        (mindflow_dir / "MIND.md").write_text("# Project")
        (mindflow_dir / "MIND.local.md").write_text("# Local")
        user_dir = mindflow_dir / "user"
        user_dir.mkdir()
        (user_dir / "MIND.md").write_text("# User")
        managed_dir = mindflow_dir / "managed"
        managed_dir.mkdir()
        (managed_dir / "MIND.md").write_text("# Managed")

        loader = MemoryFileLoader()
        loader._search_paths = {
            MemoryType.USER: [str(user_dir / "MIND.md")],
            MemoryType.PROJECT: [".mindflow/MIND.md"],
            MemoryType.LOCAL: [".mindflow/MIND.local.md"],
            MemoryType.MANAGED: [str(managed_dir / "MIND.md")],
        }

        files = await loader.load_all(str(tmp_path))

        # First should be managed (highest priority)
        assert files[0].source == MemoryType.MANAGED
        # Last should be local (lowest priority)
        assert files[-1].source == MemoryType.LOCAL

    @pytest.mark.asyncio
    async def test_oversized_file_skipped(self, tmp_path: Path):
        """Files exceeding max size should be skipped."""
        big_file = tmp_path / "HUGE.md"
        big_file.write_text("X" * 100_000)  # 100KB

        loader = MemoryFileLoader(max_file_size_kb=1)  # 1KB limit
        loader._search_paths = {
            MemoryType.PROJECT: [str(big_file)],
        }

        files = await loader.load_all(str(tmp_path))
        assert files == []

    @pytest.mark.asyncio
    async def test_empty_file_skipped(self, tmp_path: Path):
        """Empty files should be skipped."""
        empty_file = tmp_path / "EMPTY.md"
        empty_file.write_text("")

        loader = MemoryFileLoader()
        loader._search_paths = {
            MemoryType.PROJECT: [str(empty_file)],
        }

        files = await loader.load_all(str(tmp_path))
        assert files == []

    def test_estimate_total_tokens(self):
        files = [
            MemoryFile(content="A" * 400, source=MemoryType.USER, path="/a"),
            MemoryFile(content="B" * 200, source=MemoryType.PROJECT, path="/b"),
        ]
        assert MemoryFileLoader.estimate_total_tokens(files) == 100 + 50


# ─── MemoryFileLayer Tests ───────────────────────────────────────────
# NOTE: MemoryFileLayer tests require full MindFlow runtime (redis, etc.)
# These tests validate the loader integration independently.


class TestMemoryFileLoaderIntegration:
    """Integration tests for MemoryFileLoader with real file system."""

    @pytest.mark.asyncio
    async def test_load_from_real_directory(self, tmp_path: Path):
        """Should load MIND.md from a real directory structure."""
        mindflow_dir = tmp_path / ".mindflow"
        mindflow_dir.mkdir()
        (mindflow_dir / "MIND.md").write_text("# Project: Use Python 3.12+")
        (mindflow_dir / "MIND.local.md").write_text("# Local: Debug mode on")

        loader = MemoryFileLoader()
        files = await loader.load_all(str(tmp_path))

        # Should find project and local memory
        loaded_types = {f.source for f in files}
        assert MemoryType.PROJECT in loaded_types
        assert MemoryType.LOCAL in loaded_types

        # Check content
        project_file = next(f for f in files if f.source == MemoryType.PROJECT)
        assert "Python 3.12" in project_file.content

        local_file = next(f for f in files if f.source == MemoryType.LOCAL)
        assert "Debug mode" in local_file.content

    @pytest.mark.asyncio
    async def test_token_estimate_accurate(self):
        """Token estimation should be reasonable."""
        content = "This is a test message with some content." * 10
        mf = MemoryFile(content=content, source=MemoryType.USER, path="/test")
        # ~400 chars / 4 = ~100 tokens
        assert 80 <= mf.token_estimate <= 120

    @pytest.mark.asyncio
    async def test_memory_file_dataclass_fields(self):
        """MemoryFile should have all required fields."""
        from datetime import datetime

        mf = MemoryFile(
            content="test content",
            source=MemoryType.PROJECT,
            path="/some/path/MIND.md",
        )
        assert mf.content == "test content"
        assert mf.source == MemoryType.PROJECT
        assert mf.path == "/some/path/MIND.md"
        assert isinstance(mf.loaded_at, datetime)
        assert mf.token_estimate > 0
        assert mf.header == "## Project Memory"
