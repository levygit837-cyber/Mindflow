"""Integration tests for ResearchGraph with LightPanda."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from mindflow_backend.graphs.implementations.research.research_graph import ResearchGraph
from mindflow_backend.graphs.base.state import GraphState


class TestResearchGraphIntegration:
    """Integration tests for ResearchGraph execution."""

    @pytest.fixture
    def research_graph(self):
        return ResearchGraph()

    @pytest.mark.asyncio
    async def test_research_graph_full_flow_success(self, research_graph):
        """Test complete ResearchGraph execution flow."""
        state = GraphState({
            "query": "test query",
            "search_engine": "google",
            "num_results": 3,
            "language": "en",
            "max_searches": 2,
            "scraping_config": {
                "scroll_depth": 5,
                "extract_links": True,
                "max_content_length": 10000,
            },
            "root_dir": "/tmp",
            "sandbox_mode": False,
        })

        # Mock BrowserSearchCallable
        with patch(
            "mindflow_backend.nodes.implementations.research.BrowserSearchCallable"
        ) as mock_search:
            mock_search_result = MagicMock()
            mock_search_result.success = True
            mock_search_result.data = {
                "results": [
                    {"title": "Test 1", "url": "http://example.com/1", "snippet": "Snippet 1"},
                    {"title": "Test 2", "url": "http://example.com/2", "snippet": "Snippet 2"},
                ],
            }
            mock_search.call_fn = AsyncMock(return_value=mock_search_result)

            # Mock DeepPageScraperCallable
            with patch(
                "mindflow_backend.nodes.implementations.research.DeepPageScraperCallable"
            ) as mock_scrape:
                mock_scrape_result = MagicMock()
                mock_scrape_result.success = True
                mock_scrape_result.data = {
                    "title": "Test",
                    "content": "Test content",
                    "word_count": 100,
                    "reading_time_minutes": 0.5,
                    "scroll_iterations": 3,
                    "content_depth": "medium",
                    "links": {"total": 10},
                    "metadata": {},
                }
                mock_scrape.call_fn = AsyncMock(return_value=mock_scrape_result)

                result = await research_graph.execute(state)

                assert result["current_phase"] == "completed"
                assert result["metrics"]["nodes_executed"] > 0
                assert result["metrics"]["nodes_failed"] == 0
                assert "findings" in result
                assert "synthesis" in result
                assert "citations" in result
                assert "result" in result

    @pytest.mark.asyncio
    async def test_research_graph_search_loop_stops_at_max_searches(self, research_graph):
        """Test that search loop stops at max_searches."""
        state = GraphState({
            "query": "test query",
            "max_searches": 2,
            "search_engine": "google",
            "num_results": 3,
            "language": "en",
            "scraping_config": {},
            "root_dir": "/tmp",
            "sandbox_mode": False,
        })

        with patch(
            "mindflow_backend.nodes.implementations.research.BrowserSearchCallable"
        ) as mock_search:
            mock_search_result = MagicMock()
            mock_search_result.success = True
            mock_search_result.data = {"results": []}
            mock_search.call_fn = AsyncMock(return_value=mock_search_result)

            with patch(
                "mindflow_backend.nodes.implementations.research.DeepPageScraperCallable"
            ) as mock_scrape:
                mock_scrape_result = MagicMock()
                mock_scrape_result.success = True
                mock_scrape_result.data = {
                    "title": "Test",
                    "content": "Content",
                    "word_count": 100,
                    "reading_time_minutes": 0.5,
                    "scroll_iterations": 3,
                    "content_depth": "medium",
                    "links": {"total": 10},
                    "metadata": {},
                }
                mock_scrape.call_fn = AsyncMock(return_value=mock_scrape_result)

                result = await research_graph.execute(state)

                # Should execute search twice (iteration 1 and 2)
                assert mock_search.call_fn.call_count >= 2
                assert result["iteration"] == 2

    @pytest.mark.asyncio
    async def test_research_graph_stops_at_min_findings_threshold(self, research_graph):
        """Test that search loop stops when minimum findings threshold is reached."""
        state = GraphState({
            "query": "test query",
            "max_searches": 10,  # High max to test threshold
            "search_engine": "google",
            "num_results": 10,  # Get many results
            "language": "en",
            "scraping_config": {},
            "root_dir": "/tmp",
            "sandbox_mode": False,
        })

        with patch(
            "mindflow_backend.nodes.implementations.research.BrowserSearchCallable"
        ) as mock_search:
            # Return enough results to trigger threshold
            mock_search_result = MagicMock()
            mock_search_result.success = True
            mock_search_result.data = {
                "results": [
                    {"title": f"Test {i}", "url": f"http://example.com/{i}", "snippet": f"Snippet {i}"}
                    for i in range(20)  # More than MIN_FINDINGS_THRESHOLD (15)
                ]
            }
            mock_search.call_fn = AsyncMock(return_value=mock_search_result)

            with patch(
                "mindflow_backend.nodes.implementations.research.DeepPageScraperCallable"
            ) as mock_scrape:
                mock_scrape_result = MagicMock()
                mock_scrape_result.success = True
                mock_scrape_result.data = {
                    "title": "Test",
                    "content": "Content",
                    "word_count": 100,
                    "reading_time_minutes": 0.5,
                    "scroll_iterations": 3,
                    "content_depth": "medium",
                    "links": {"total": 10},
                    "metadata": {},
                }
                mock_scrape.call_fn = AsyncMock(return_value=mock_scrape_result)

                result = await research_graph.execute(state)

                # Should stop after first iteration due to threshold
                assert result["iteration"] == 1

    @pytest.mark.asyncio
    async def test_research_graph_node_timeout(self, research_graph):
        """Test that node timeout is handled correctly."""
        state = GraphState({
            "query": "test query",
            "max_searches": 1,
            "search_engine": "google",
            "num_results": 3,
            "language": "en",
            "scraping_config": {},
            "root_dir": "/tmp",
            "sandbox_mode": False,
        })

        with patch(
            "mindflow_backend.nodes.implementations.research.BrowserSearchCallable"
        ) as mock_search:
            # Simulate timeout
            mock_search.call_fn = AsyncMock(
                side_effect=asyncio.TimeoutError("Node timeout")
            )

            result = await research_graph.execute(state)

            assert result["error"] is not None
            assert "timeout" in result["error"].lower()
            assert result["metrics"]["node_timeouts"] > 0

    @pytest.mark.asyncio
    async def test_research_graph_query_refinement(self, research_graph):
        """Test that query is refined between iterations."""
        state = GraphState({
            "query": "machine learning",
            "max_searches": 3,
            "search_engine": "google",
            "num_results": 3,
            "language": "en",
            "scraping_config": {},
            "root_dir": "/tmp",
            "sandbox_mode": False,
        })

        with patch(
            "mindflow_backend.nodes.implementations.research.BrowserSearchCallable"
        ) as mock_search:
            mock_search_result = MagicMock()
            mock_search_result.success = True
            mock_search_result.data = {"results": []}
            mock_search.call_fn = AsyncMock(return_value=mock_search_result)

            with patch(
                "mindflow_backend.nodes.implementations.research.DeepPageScraperCallable"
            ) as mock_scrape:
                mock_scrape_result = MagicMock()
                mock_scrape_result.success = True
                mock_scrape_result.data = {
                    "title": "Test",
                    "content": "Content",
                    "word_count": 100,
                    "reading_time_minutes": 0.5,
                    "scroll_iterations": 3,
                    "content_depth": "medium",
                    "links": {"total": 10},
                    "metadata": {},
                }
                mock_scrape.call_fn = AsyncMock(return_value=mock_scrape_result)

                result = await research_graph.execute(state)

                # Check that query was refined
                # First call: "machine learning"
                # Second call: "machine learning tutorial"
                # Third call: "machine learning guide"
                assert mock_search.call_fn.call_count >= 2
                calls = mock_search.call_fn.call_args_list
                # Verify query refinement happened
                if len(calls) > 1:
                    first_query = calls[0][0][0].query
                    second_query = calls[1][0][0].query
                    assert first_query != second_query

    @pytest.mark.asyncio
    async def test_research_graph_deduplication_integration(self, research_graph):
        """Test that deduplication works in the full graph."""
        state = GraphState({
            "query": "test query",
            "max_searches": 1,
            "search_engine": "google",
            "num_results": 5,
            "language": "en",
            "scraping_config": {},
            "root_dir": "/tmp",
            "sandbox_mode": False,
        })

        with patch(
            "mindflow_backend.nodes.implementations.research.BrowserSearchCallable"
        ) as mock_search:
            # Return duplicate URLs
            mock_search_result = MagicMock()
            mock_search_result.success = True
            mock_search_result.data = {
                "results": [
                    {"title": "Test 1", "url": "http://example.com/1", "snippet": "Snippet 1"},
                    {"title": "Test 2", "url": "http://example.com/1", "snippet": "Snippet 2"},  # Duplicate URL
                    {"title": "Test 3", "url": "http://example.com/2", "snippet": "Snippet 3"},
                ]
            }
            mock_search.call_fn = AsyncMock(return_value=mock_search_result)

            with patch(
                "mindflow_backend.nodes.implementations.research.DeepPageScraperCallable"
            ) as mock_scrape:
                mock_scrape_result = MagicMock()
                mock_scrape_result.success = True
                mock_scrape_result.data = {
                    "title": "Test",
                    "content": "Test content",
                    "word_count": 100,
                    "reading_time_minutes": 0.5,
                    "scroll_iterations": 3,
                    "content_depth": "medium",
                    "links": {"total": 10},
                    "metadata": {},
                }
                mock_scrape.call_fn = AsyncMock(return_value=mock_scrape_result)

                result = await research_graph.execute(state)

                # Verify deduplication happened
                assert "deduplication_details" in result
                assert result["deduplication_details"]["duplicates_by_url"] >= 1

    @pytest.mark.asyncio
    async def test_research_graph_metrics_collection(self, research_graph):
        """Test that comprehensive metrics are collected."""
        state = GraphState({
            "query": "test query",
            "max_searches": 1,
            "search_engine": "google",
            "num_results": 3,
            "language": "en",
            "scraping_config": {},
            "root_dir": "/tmp",
            "sandbox_mode": False,
        })

        with patch(
            "mindflow_backend.nodes.implementations.research.BrowserSearchCallable"
        ) as mock_search:
            mock_search_result = MagicMock()
            mock_search_result.success = True
            mock_search_result.data = {"results": []}
            mock_search.call_fn = AsyncMock(return_value=mock_search_result)

            with patch(
                "mindflow_backend.nodes.implementations.research.DeepPageScraperCallable"
            ) as mock_scrape:
                mock_scrape_result = MagicMock()
                mock_scrape_result.success = True
                mock_scrape_result.data = {
                    "title": "Test",
                    "content": "Content",
                    "word_count": 100,
                    "reading_time_minutes": 0.5,
                    "scroll_iterations": 3,
                    "content_depth": "medium",
                    "links": {"total": 10},
                    "metadata": {},
                }
                mock_scrape.call_fn = AsyncMock(return_value=mock_scrape_result)

                result = await research_graph.execute(state)

                # Verify metrics
                assert "metrics" in result
                assert result["metrics"]["duration_seconds"] >= 0
                assert result["metrics"]["nodes_executed"] > 0
                assert "scraping_metrics" in result["metrics"]
                assert "deduplication_metrics" in result["metrics"]

    @pytest.mark.asyncio
    async def test_research_graph_error_handling(self, research_graph):
        """Test error handling in the graph."""
        state = GraphState({
            "query": "test query",
            "max_searches": 1,
            "search_engine": "google",
            "num_results": 3,
            "language": "en",
            "scraping_config": {},
            "root_dir": "/tmp",
            "sandbox_mode": False,
        })

        with patch(
            "mindflow_backend.nodes.implementations.research.BrowserSearchCallable"
        ) as mock_search:
            # Simulate exception
            mock_search.call_fn = AsyncMock(side_effect=Exception("Test error"))

            result = await research_graph.execute(state)

            assert "error" in result
            assert result["metrics"]["nodes_failed"] == 1
            assert result["metrics"]["error_details"] == ["Test error"]
