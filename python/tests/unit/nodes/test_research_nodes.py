"""Unit tests for ResearchGraph nodes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from mindflow_backend.nodes.implementations.research import (
    SearchNode,
    CollectNode,
    DeduplicateNode,
    ResearchSynthesizeNode,
    CiteNode,
    ResearchReportNode,
)


class TestSearchNode:
    """Tests for SearchNode."""

    @pytest.fixture
    def search_node(self):
        return SearchNode()

    @pytest.mark.asyncio
    async def test_search_node_success(self, search_node):
        """Test successful search execution."""
        state = {
            "query": "test query",
            "search_engine": "google",
            "num_results": 5,
            "language": "en",
            "root_dir": "/tmp",
            "sandbox_mode": False,
        }

        with patch(
            "mindflow_backend.nodes.implementations.research.BrowserSearchCallable"
        ) as mock_callable:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = {
                "results": [
                    {"title": "Test 1", "url": "http://example.com/1", "snippet": "Snippet 1"},
                    {"title": "Test 2", "url": "http://example.com/2", "snippet": "Snippet 2"},
                ],
                "total_results": 2,
            }
            mock_callable.call_fn = AsyncMock(return_value=mock_result)

            result = await search_node.execute(state)

            assert result["iteration"] == 1
            assert result["current_phase"] == "searching"
            assert len(result["search_results"]) == 2
            assert result["search_results"][0]["title"] == "Test 1"

    @pytest.mark.asyncio
    async def test_search_node_failure(self, search_node):
        """Test search node failure handling."""
        state = {
            "query": "test query",
            "search_engine": "google",
            "num_results": 5,
            "language": "en",
            "root_dir": "/tmp",
            "sandbox_mode": False,
        }

        with patch(
            "mindflow_backend.nodes.implementations.research.BrowserSearchCallable"
        ) as mock_callable:
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.error = "Search failed"
            mock_callable.call_fn = AsyncMock(return_value=mock_result)

            result = await search_node.execute(state)

            assert result["iteration"] == 1
            assert result["current_phase"] == "searching"
            assert result["search_results"] == []
            assert result["error"] == "Search failed"

    @pytest.mark.asyncio
    async def test_search_node_exception(self, search_node):
        """Test search node exception handling."""
        state = {
            "query": "test query",
            "search_engine": "google",
            "num_results": 5,
            "language": "en",
            "root_dir": "/tmp",
            "sandbox_mode": False,
        }

        with patch(
            "mindflow_backend.nodes.implementations.research.BrowserSearchCallable"
        ) as mock_callable:
            mock_callable.call_fn = AsyncMock(side_effect=Exception("Test exception"))

            result = await search_node.execute(state)

            assert result["iteration"] == 1
            assert result["current_phase"] == "searching"
            assert result["search_results"] == []
            assert "Test exception" in result["error"]


class TestCollectNode:
    """Tests for CollectNode."""

    @pytest.fixture
    def collect_node(self):
        return CollectNode()

    @pytest.mark.asyncio
    async def test_collect_node_success(self, collect_node):
        """Test successful collect execution."""
        search_results = [
            {"title": "Test 1", "url": "http://example.com/1", "snippet": "Snippet 1"},
            {"title": "Test 2", "url": "http://example.com/2", "snippet": "Snippet 2"},
        ]

        state = {
            "search_results": search_results,
            "scraping_config": {
                "scroll_depth": 5,
                "extract_links": True,
                "max_content_length": 10000,
            },
            "root_dir": "/tmp",
            "sandbox_mode": False,
        }

        with patch(
            "mindflow_backend.nodes.implementations.research.DeepPageScraperCallable"
        ) as mock_callable:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = {
                "title": "Test 1",
                "content": "Test content",
                "word_count": 100,
                "reading_time_minutes": 0.5,
                "scroll_iterations": 3,
                "content_depth": "medium",
                "links": {"total": 10, "internal": 5, "external": 5},
                "metadata": {"description": "Test desc"},
            }
            mock_callable.call_fn = AsyncMock(return_value=mock_result)

            result = await collect_node.execute(state)

            assert result["current_phase"] == "collected"
            assert len(result["findings"]) == 2
            assert result["scraping_metrics"]["successful_scrapes"] == 2
            assert result["scraping_metrics"]["failed_scrapes"] == 0

    @pytest.mark.asyncio
    async def test_collect_node_partial_failure(self, collect_node):
        """Test collect node with partial failures."""
        search_results = [
            {"title": "Test 1", "url": "http://example.com/1", "snippet": "Snippet 1"},
            {"title": "Test 2", "url": "http://example.com/2", "snippet": "Snippet 2"},
        ]

        state = {
            "search_results": search_results,
            "scraping_config": {
                "scroll_depth": 5,
                "extract_links": True,
                "max_content_length": 10000,
            },
            "root_dir": "/tmp",
            "sandbox_mode": False,
        }

        with patch(
            "mindflow_backend.nodes.implementations.research.DeepPageScraperCallable"
        ) as mock_callable:
            # First success, second failure
            mock_result_success = MagicMock()
            mock_result_success.success = True
            mock_result_success.data = {
                "title": "Test 1",
                "content": "Test content",
                "word_count": 100,
                "reading_time_minutes": 0.5,
                "scroll_iterations": 3,
                "content_depth": "medium",
                "links": {"total": 10},
                "metadata": {},
            }

            mock_result_failure = MagicMock()
            mock_result_failure.success = False
            mock_result_failure.error = "Scrape failed"

            mock_callable.call_fn = AsyncMock(
                side_effect=[mock_result_success, mock_result_failure]
            )

            result = await collect_node.execute(state)

            assert result["current_phase"] == "collected"
            assert len(result["findings"]) == 1
            assert result["scraping_metrics"]["successful_scrapes"] == 1
            assert result["scraping_metrics"]["failed_scrapes"] == 1


class TestDeduplicateNode:
    """Tests for DeduplicateNode."""

    @pytest.fixture
    def deduplicate_node(self):
        return DeduplicateNode()

    @pytest.mark.asyncio
    async def test_deduplicate_node_url_deduplication(self, deduplicate_node):
        """Test URL deduplication."""
        findings = [
            {
                "url": "http://example.com/1",
                "title": "Test 1",
                "content": "Content 1",
            },
            {
                "url": "http://example.com/1",  # Duplicate URL
                "title": "Test 1 Duplicate",
                "content": "Content 1 Duplicate",
            },
            {
                "url": "http://example.com/2",
                "title": "Test 2",
                "content": "Content 2",
            },
        ]

        state = {"findings": findings}

        result = await deduplicate_node.execute(state)

        assert result["current_phase"] == "deduplicated"
        assert result["unique_count"] == 2
        assert result["duplicates_removed"] == 1
        assert result["deduplication_details"]["duplicates_by_url"] == 1
        assert len(result["findings"]) == 2

    @pytest.mark.asyncio
    async def test_deduplicate_node_content_similarity(self, deduplicate_node):
        """Test content similarity deduplication."""
        findings = [
            {
                "url": "http://example.com/1",
                "title": "Test 1",
                "content": "This is very similar content that should be detected as duplicate",
            },
            {
                "url": "http://example.com/2",
                "title": "Test 2",
                "content": "This is very similar content that should be detected as duplicate",  # Similar content
            },
            {
                "url": "http://example.com/3",
                "title": "Test 3",
                "content": "Completely different content here",
            },
        ]

        state = {"findings": findings}

        result = await deduplicate_node.execute(state)

        assert result["current_phase"] == "deduplicated"
        assert result["unique_count"] == 2
        assert result["duplicates_removed"] == 1
        assert result["deduplication_details"]["duplicates_by_content"] == 1

    @pytest.mark.asyncio
    async def test_deduplicate_node_no_duplicates(self, deduplicate_node):
        """Test deduplication with no duplicates."""
        findings = [
            {
                "url": "http://example.com/1",
                "title": "Test 1",
                "content": "Content 1",
            },
            {
                "url": "http://example.com/2",
                "title": "Test 2",
                "content": "Content 2",
            },
            {
                "url": "http://example.com/3",
                "title": "Test 3",
                "content": "Content 3",
            },
        ]

        state = {"findings": findings}

        result = await deduplicate_node.execute(state)

        assert result["current_phase"] == "deduplicated"
        assert result["unique_count"] == 3
        assert result["duplicates_removed"] == 0
        assert len(result["findings"]) == 3


class TestResearchSynthesizeNode:
    """Tests for ResearchSynthesizeNode."""

    @pytest.fixture
    def synthesize_node(self):
        return ResearchSynthesizeNode()

    @pytest.mark.asyncio
    async def test_synthesize_node_success(self, synthesize_node):
        """Test successful synthesis."""
        findings = [
            {
                "url": "http://example.com/1",
                "title": "Test Tutorial",
                "content": "Content about tutorials",
            },
            {
                "url": "http://example.com/2",
                "title": "Test Guide",
                "content": "Content about guides",
            },
        ]

        state = {"findings": findings}

        result = await synthesize_node.execute(state)

        assert result["current_phase"] == "synthesized"
        assert result["synthesis"]["sources_count"] == 2
        assert len(result["synthesis"]["key_themes"]) > 0
        assert result["synthesis"]["confidence_score"] > 0.5
        assert len(result["synthesis"]["main_findings"]) > 0

    @pytest.mark.asyncio
    async def test_synthesize_node_empty_findings(self, synthesize_node):
        """Test synthesis with empty findings."""
        state = {"findings": []}

        result = await synthesize_node.execute(state)

        assert result["current_phase"] == "synthesized"
        assert result["synthesis"]["sources_count"] == 0
        assert result["synthesis"]["confidence_score"] == 0.5


class TestCiteNode:
    """Tests for CiteNode."""

    @pytest.fixture
    def cite_node(self):
        return CiteNode()

    @pytest.mark.asyncio
    async def test_cite_node_success(self, cite_node):
        """Test successful citation formatting."""
        findings = [
            {
                "url": "http://example.com/1",
                "title": "Test 1",
                "content": "Content 1",
                "extracted_at": "2024-01-01T00:00:00",
            },
            {
                "url": "http://example.com/2",
                "title": "Test 2",
                "content": "Content 2",
                "extracted_at": "2024-01-01T00:00:00",
            },
        ]

        synthesis = {
            "key_themes": ["theme1", "theme2"],
            "confidence_score": 0.85,
        }

        state = {"findings": findings, "synthesis": synthesis}

        result = await cite_node.execute(state)

        assert result["current_phase"] == "cited"
        assert len(result["citations"]) == 2
        assert result["citations"][0]["text"] == "[1] Test 1"
        assert "Research Report" in result["formatted_text"]
        assert "## Citations" in result["formatted_text"]

    @pytest.mark.asyncio
    async def test_cite_node_empty_findings(self, cite_node):
        """Test citation with empty findings."""
        state = {"findings": [], "synthesis": {}}

        result = await cite_node.execute(state)

        assert result["current_phase"] == "cited"
        assert len(result["citations"]) == 0
        assert "Sources: 0" in result["formatted_text"]


class TestResearchReportNode:
    """Tests for ResearchReportNode."""

    @pytest.fixture
    def report_node(self):
        return ResearchReportNode()

    @pytest.mark.asyncio
    async def test_report_node_success(self, report_node):
        """Test successful report generation."""
        findings = [
            {
                "url": "http://example.com/1",
                "title": "Test 1",
                "content": "Content 1",
                "word_count": 100,
            },
        ]

        synthesis = {
            "key_themes": ["theme1"],
            "confidence_score": 0.85,
        }

        citations = [
            {
                "text": "[1] Test 1",
                "source": {"url": "http://example.com/1", "title": "Test 1"},
            }
        ]

        state = {
            "findings": findings,
            "synthesis": synthesis,
            "citations": citations,
            "iteration": 2,
            "scraping_metrics": {
                "total_content_chars": 1000,
                "successful_scrapes": 1,
            },
            "deduplication_details": {
                "original_count": 2,
                "duplicates_by_url": 1,
                "duplicates_by_content": 0,
                "unique_count": 1,
            },
        }

        result = await report_node.execute(state)

        assert result["current_phase"] == "completed"
        assert result["result"]["iterations"] == 2
        assert result["result"]["findings_count"] == 1
        assert result["result"]["citations_count"] == 1
        assert result["metrics"]["nodes_executed"] == 7
        assert result["metrics"]["duration_seconds"] >= 0
        assert "generated_at" in result["result"]

    @pytest.mark.asyncio
    async def test_report_node_with_start_time(self, report_node):
        """Test report generation with start time for duration calculation."""
        import time

        state = {
            "findings": [],
            "synthesis": {},
            "citations": [],
            "iteration": 1,
            "start_time": time.time() - 10,  # 10 seconds ago
            "scraping_metrics": {},
            "deduplication_details": {},
        }

        result = await report_node.execute(state)

        assert result["current_phase"] == "completed"
        assert result["metrics"]["duration_seconds"] >= 9  # Should be close to 10
