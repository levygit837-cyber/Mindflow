"""Unit tests for node utility functions."""

from __future__ import annotations

import pytest

from mindflow_backend.nodes.common.utils import (
    compile_metrics,
    configure_memory_scope,
    format_final_result,
    generate_memory_annotations,
    identify_relevant_files,
    initialize_metrics,
    map_project_structure,
    scan_filesystem,
)
from mindflow_backend.nodes.analysis.utils import (
    analyze_file_structure,
    calculate_confidence_score,
    extract_key_insights,
    merge_annotations,
)


class TestCommonUtils:
    """Test suite for common utility functions."""

    def test_initialize_metrics(self) -> None:
        """Test metrics initialization."""
        metrics = initialize_metrics(max_iterations=100, max_duration_seconds=60.0)

        assert metrics["iteration"] == 0
        assert metrics["confidence"] == 0.0
        assert metrics["max_iterations"] == 100
        assert metrics["max_duration_seconds"] == 60.0
        assert metrics["nodes_executed"] == 0
        assert metrics["nodes_failed"] == 0
        assert metrics["total_tokens_used"] == 0
        assert "started_at" in metrics

    @pytest.mark.asyncio
    async def test_configure_memory_scope(self) -> None:
        """Test memory scope configuration."""
        scope = await configure_memory_scope(
            agent_id="analyst",
            mission_type="analysis",
            session_id="test-session",
        )

        assert scope["agent_id"] == "analyst"
        assert scope["mission_type"] == "analysis"
        assert scope["session_id"] == "test-session"
        assert scope["read_scope"] == "universal"  # Analysis can read universal
        assert scope["write_scope"] == "mission"

    @pytest.mark.asyncio
    async def test_configure_memory_scope_security_audit(self) -> None:
        """Test memory scope for security audit."""
        scope = await configure_memory_scope(
            agent_id="analyst",
            mission_type="security_audit",
            session_id="test-session",
        )

        assert scope["write_scope"] == "universal"  # Security findings go to universal

    @pytest.mark.asyncio
    async def test_scan_filesystem(self) -> None:
        """Test filesystem scanning."""
        result = await scan_filesystem("/home/levybonito/Projetos/MindFlow/python")

        assert "root" in result
        assert "files" in result
        assert "directories" in result
        assert isinstance(result["files"], list)

    @pytest.mark.asyncio
    async def test_map_project_structure(self) -> None:
        """Test project structure mapping."""
        scan_result = {
            "files": [
                {"path": "test.py", "extension": ".py"},
                {"path": "test.ts", "extension": ".ts"},
            ],
            "directories": ["src", "tests"],
        }

        structure = map_project_structure(scan_result)

        assert "project_type" in structure
        assert "by_extension" in structure
        assert "total_files" in structure
        assert structure["project_type"] == "python"  # Has .py files

    @pytest.mark.asyncio
    async def test_identify_relevant_files(self) -> None:
        """Test relevant file identification."""
        structure_map = {
            "by_extension": {
                ".py": ["test.py", "main.py"],
                ".md": ["README.md"],
                ".json": ["config.json"],
            },
            "total_files": 4,
        }

        files = identify_relevant_files(
            structure_map, mission_type="analysis", working_directory="/tmp"
        )

        assert len(files) > 0
        assert any(f.endswith(".py") for f in files)

    @pytest.mark.asyncio
    async def test_format_final_result(self) -> None:
        """Test final result formatting."""
        state = {
            "mission_type": "analysis",
            "iteration": 5,
            "confidence": 0.85,
            "annotations": [{"content": "test"}],
            "analyzed_files": {"test.py": "analyzed"},
        }

        result = format_final_result(state)

        assert result["mission_type"] == "analysis"
        assert result["iterations"] == 5
        assert result["confidence"] == 0.85
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_compile_metrics(self) -> None:
        """Test metrics compilation."""
        state = {
            "started_at": 1234567890.0,
            "metrics": {
                "nodes_executed": 10,
                "nodes_failed": 0,
                "total_tokens_used": 1000,
            },
            "iteration": 5,
            "confidence": 0.85,
        }

        metrics = compile_metrics(state)

        assert metrics["nodes_executed"] == 10
        assert metrics["nodes_failed"] == 0
        assert metrics["total_tokens_used"] == 1000
        assert metrics["iteration"] == 5
        assert metrics["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_generate_memory_annotations(self) -> None:
        """Test memory annotation generation."""
        state = {
            "annotations": [
                {"content": "test", "confidence": 0.8},
                {"content": "low confidence", "confidence": 0.5},
            ],
            "confidence": 0.85,
        }

        annotations = await generate_memory_annotations(
            state, agent_id="analyst", mission_type="analysis", session_id="test"
        )

        assert len(annotations) == 1  # Only high confidence
        assert annotations[0]["agent_id"] == "analyst"
        assert annotations[0]["mission_type"] == "analysis"


class TestAnalysisUtils:
    """Test suite for analysis utility functions."""

    @pytest.mark.asyncio
    async def test_extract_key_insights(self) -> None:
        """Test key insights extraction."""
        findings = {
            "patterns_found": {
                "matches": {
                    "test.py": [
                        {"pattern": "class", "line": 1},
                    ]
                }
            },
            "dependencies": {
                "dependencies": [
                    {"file": "test.py", "imports": []},
                ]
            },
        }

        insights = await extract_key_insights(findings, iteration=1)

        assert len(insights) > 0
        assert all(insight["iteration"] == 1 for insight in insights)

    @pytest.mark.asyncio
    async def test_calculate_confidence_score(self) -> None:
        """Test confidence score calculation."""
        insights = [
            {"confidence": 0.7},
            {"confidence": 0.8},
            {"confidence": 0.9},
        ]

        new_confidence = await calculate_confidence_score(insights, previous_confidence=0.5)

        assert new_confidence > 0.5  # Should increase
        assert new_confidence <= 1.0  # Should not exceed 1.0

    @pytest.mark.asyncio
    async def test_calculate_confidence_score_empty_insights(self) -> None:
        """Test confidence score with empty insights."""
        new_confidence = await calculate_confidence_score([], previous_confidence=0.5)

        assert new_confidence == 0.5  # Should not change

    @pytest.mark.asyncio
    async def test_merge_annotations(self) -> None:
        """Test annotation merging."""
        annotations = [
            {"content": "test1", "type": "pattern_match", "confidence": 0.7},
            {"content": "test2", "type": "dependency", "confidence": 0.8},
            {"content": "test3", "type": "pattern_match", "confidence": 0.9},
        ]

        merged = await merge_annotations(annotations)

        assert "grouped" in merged
        assert "total_count" in merged
        assert merged["total_count"] == 3
        assert "pattern_match" in merged["grouped"]
        assert "dependency" in merged["grouped"]

    @pytest.mark.asyncio
    async def test_analyze_file_structure(self) -> None:
        """Test file structure analysis."""
        files = ["mindflow_backend/nodes/common/initialize_node.py"]

        structure = await analyze_file_structure(files, "/home/levybonito/Projetos/MindFlow/python")

        assert "structure" in structure
        assert isinstance(structure["structure"], dict)
