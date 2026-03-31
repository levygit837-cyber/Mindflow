"""Integration tests for enhanced researcher components.

Tests the integration between port management, health monitoring,
query planning, source trust evaluation, and result synthesis.
"""

from __future__ import annotations

import pytest

from mindflow_backend.agents.research.enhanced_query_planner import get_enhanced_query_planner
from mindflow_backend.agents.research.result_synthesizer import get_result_synthesizer
from mindflow_backend.agents.research.source_trust_engine import get_source_trust_engine
from mindflow_backend.agents.research.utils.health_checker import get_health_checker
from mindflow_backend.agents.research.utils.port_manager import get_port_manager
from mindflow_backend.schemas.research import (
    ConfidenceLevel,
    QuestionType,
    ResearchFinding,
    SourceClassification,
    SourceType,
)


class TestPortManager:
    """Test port management functionality."""
    
    @pytest.mark.asyncio
    async def test_port_allocation_and_release(self) -> None:
        """Test basic port allocation and release."""
        port_manager = get_port_manager()
        
        # Allocate a port
        port = await port_manager.allocate_port()
        assert port >= 9867 and port <= 9967
        assert port in port_manager.get_allocated_ports()
        
        # Release the port
        await port_manager.release_port(port)
        assert port not in port_manager.get_allocated_ports()
        
    @pytest.mark.asyncio
    async def test_port_conflict_prevention(self) -> None:
        """Test that port conflicts are prevented."""
        port_manager = get_port_manager()
        
        # Allocate first port
        port1 = await port_manager.allocate_port()
        
        # Try to allocate same port (should fail)
        with pytest.raises(RuntimeError):
            await port_manager.allocate_port(preferred_port=port1)
            
        # Clean up
        await port_manager.release_port(port1)
        
    @pytest.mark.asyncio
    async def test_port_status_tracking(self) -> None:
        """Test port status tracking."""
        port_manager = get_port_manager()
        
        initial_status = port_manager.get_status()
        assert initial_status["allocated_ports"] == 0
        assert initial_status["available_ports"] > 0
        
        # Allocate some ports
        ports = []
        for _ in range(3):
            port = await port_manager.allocate_port()
            ports.append(port)
            
        updated_status = port_manager.get_status()
        assert updated_status["allocated_ports"] == 3
        assert updated_status["available_ports"] == initial_status["available_ports"] - 3
        
        # Clean up
        for port in ports:
            await port_manager.release_port(port)


class TestHealthChecker:
    """Test health checking functionality."""
    
    @pytest.mark.asyncio
    async def test_process_registration_and_health(self) -> None:
        """Test process registration and health checking."""
        health_checker = get_health_checker()
        
        # Register a process
        await health_checker.register_process("test_process", 9867, 12345)
        
        # Update health metrics
        await health_checker.update_process_health(
            "test_process", "running", cpu_percent=25.0, memory_mb=512.0
        )
        
        # Check health
        is_healthy = await health_checker.is_healthy("test_process")
        assert is_healthy is True
        
        # Get status summary
        status = health_checker.get_status_summary()
        assert status["total_processes"] == 1
        assert status["healthy_processes"] == 1
        
    @pytest.mark.asyncio
    async def test_unhealthy_process_detection(self) -> None:
        """Test detection of unhealthy processes."""
        health_checker = get_health_checker()
        
        # Register a process
        await health_checker.register_process("unhealthy_process", 9868, 12346)
        
        # Mark as unhealthy (high CPU)
        await health_checker.update_process_health(
            "unhealthy_process", "running", cpu_percent=95.0, is_error=True
        )
        
        # Check health
        is_healthy = await health_checker.is_healthy("unhealthy_process")
        assert is_healthy is False
        
        # Get unhealthy processes
        unhealthy = await health_checker.get_unhealthy_processes()
        assert "unhealthy_process" in unhealthy


class TestEnhancedQueryPlanner:
    """Test enhanced query planning functionality."""
    
    @pytest.mark.asyncio
    async def test_intent_analysis(self) -> None:
        """Test query intent analysis."""
        planner = get_enhanced_query_planner()
        
        # Test definition query
        intent = planner.analyze_intent("What is microservice architecture?")
        assert intent.question_type == QuestionType.DEFINITION
        assert intent.complexity_level in ["simple", "moderate"]
        
        # Test comparison query
        intent = planner.analyze_intent("React vs Vue performance comparison")
        assert intent.question_type == QuestionType.COMPARISON
        assert intent.browser_count >= 2
        
        # Test debug query
        intent = planner.analyze_intent("Why does my application crash on startup?")
        assert intent.question_type == QuestionType.DEBUG
        assert intent.complexity_level in ["complex", "deep"]
        
    @pytest.mark.asyncio
    async def test_query_expansion(self) -> None:
        """Test query expansion capabilities."""
        planner = get_enhanced_query_planner()
        
        # Test expansion for definition
        intent = planner.analyze_intent("Docker containers")
        query_plan = planner.plan_queries(intent, "Docker containers")
        
        # Should have multiple query variants
        assert len(query_plan.queries) >= 2
        assert "Docker containers" in query_plan.queries  # Original query preserved
        
        # Test expansion for comparison
        intent = planner.analyze_intent("Python vs JavaScript")
        query_plan = planner.plan_queries(intent, "Python vs JavaScript")
        
        # Should have comparison-specific expansions
        comparison_terms = any("vs" in q or "versus" in q or "compared" in q for q in query_plan.queries)
        assert comparison_terms is True
        
    @pytest.mark.asyncio
    async def test_search_engine_selection(self) -> None:
        """Test intelligent search engine selection."""
        planner = get_enhanced_query_planner()
        
        # Test programming query
        intent = planner.analyze_intent("Python async programming")
        query_plan = planner.plan_queries(intent, "Python async programming")
        
        # Should include programming-specific engines
        engines_str = " ".join(query_plan.search_engines)
        assert any(engine in engines_str for engine in ["github.com", "stackoverflow.com"])
        
        # Test academic query
        intent = planner.analyze_intent("machine learning research papers")
        query_plan = planner.plan_queries(intent, "machine learning research papers")
        
        # Should include academic engines
        engines_str = " ".join(query_plan.search_engines)
        assert any(engine in engines_str for engine in ["scholar.google.com", "arxiv.org"])


class TestSourceTrustEngine:
    """Test source trust evaluation functionality."""
    
    @pytest.mark.asyncio
    async def test_domain_authority_calculation(self) -> None:
        """Test domain authority calculation."""
        engine = get_source_trust_engine()
        
        # Test official documentation
        classification = engine.evaluate_source(
            url="https://docs.python.org/3/library/",
            content="Python 3.12 documentation with official information",
        )
        
        assert classification.source_type == SourceType.OFFICIAL
        assert classification.domain_authority >= 0.9
        assert classification.trust_level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]
        
        # Test unknown blog
        classification = engine.evaluate_source(
            url="https://random-blog.xyz/post",
            content="Some random content from unknown source",
        )
        
        assert classification.source_type == SourceType.UNKNOWN_BLOG
        assert classification.domain_authority <= 0.5
        
    @pytest.mark.asyncio
    async def test_bias_detection(self) -> None:
        """Test bias detection in content."""
        engine = get_source_trust_engine()
        
        # Test promotional content
        promotional_content = "Buy now! Limited time offer! Best price guaranteed!"
        classification = engine.evaluate_source(
            url="https://example.com/product",
            content=promotional_content,
        )
        
        # Should detect promotional bias
        assert classification.domain_authority < 0.7  # Reduced due to bias
        
        # Test objective content
        objective_content = "The API supports authentication via OAuth 2.0"
        classification = engine.evaluate_source(
            url="https://docs.example.com/api",
            content=objective_content,
        )
        
        # Should maintain higher authority
        assert classification.domain_authority > 0.8
        
    @pytest.mark.asyncio
    async def test_cross_reference_validation(self) -> None:
        """Test cross-reference validation."""
        engine = get_source_trust_engine()
        
        # Add consistent facts from multiple sources
        engine.cross_validator.add_source_facts(
            "https://docs.example.com",
            ["Python supports async/await", "Python 3.12 was released in 2024"]
        )
        engine.cross_validator.add_source_facts(
            "https://tutorial.example.com",
            ["Python supports async/await", "Async programming is recommended"]
        )
        
        # Should find high cross-reference score
        score = engine.cross_validator.calculate_cross_reference_score("https://docs.example.com")
        assert score > 0.7  # High corroboration
        
        # Test conflicting facts
        engine.cross_validator.add_source_facts(
            "https://conflicting.example.com",
            ["Python does not support async/await"]  # Contradiction
        )
        
        conflicts = engine.cross_validator.find_conflicts("https://conflicting.example.com")
        assert len(conflicts) > 0


class TestResultSynthesizer:
    """Test result synthesis functionality."""
    
    @pytest.mark.asyncio
    async def test_conflict_detection(self) -> None:
        """Test conflict detection between sources."""
        synthesizer = get_result_synthesizer()
        
        # Create conflicting findings
        findings = [
            ResearchFinding(
                source_url="https://source1.com",
                source_classification=SourceClassification(
                    url="https://source1.com",
                    source_type=SourceType.OFFICIAL,
                    trust_level=ConfidenceLevel.HIGH,
                    domain_authority=0.9,
                ),
                content_summary="Version 2.0 was released in 2024",
                key_points=["Version 2.0", "2024 release"],
                confidence_score=0.9,
            ),
            ResearchFinding(
                source_url="https://source2.com",
                source_classification=SourceClassification(
                    url="https://source2.com",
                    source_type=SourceType.TECH_PUBLICATION,
                    trust_level=ConfidenceLevel.MEDIUM,
                    domain_authority=0.7,
                ),
                content_summary="Version 2.0 was released in 2023",  # Contradiction
                key_points=["Version 2.0", "2023 release"],
                confidence_score=0.7,
            ),
        ]
        
        # Synthesize results
        results = synthesizer.synthesize_results(findings, "Version 2.0 release date")
        
        # Should detect conflicts
        assert len(results["conflicts"]) > 0
        assert "contradiction" in " ".join(str(c) for c in results["conflicts"]).lower()
        
    @pytest.mark.asyncio
    async def test_confidence_weighted_synthesis(self) -> None:
        """Test confidence-weighted synthesis."""
        synthesizer = get_result_synthesizer()
        
        # Create findings with different confidence levels
        findings = [
            ResearchFinding(
                source_url="https://official.com",
                source_classification=SourceClassification(
                    url="https://official.com",
                    source_type=SourceType.OFFICIAL,
                    trust_level=ConfidenceLevel.HIGH,
                    domain_authority=0.95,
                ),
                content_summary="Official documentation states X is true",
                key_points=["X is true", "Official source"],
                confidence_score=0.95,
            ),
            ResearchFinding(
                source_url="https://blog.com",
                source_classification=SourceClassification(
                    url="https://blog.com",
                    source_type=SourceType.UNKNOWN_BLOG,
                    trust_level=ConfidenceLevel.LOW,
                    domain_authority=0.3,
                ),
                content_summary="Blog post says Y is true",
                key_points=["Y is true", "Blog source"],
                confidence_score=0.4,
            ),
        ]
        
        # Synthesize results
        results = synthesizer.synthesize_results(findings, "Test query")
        
        # Should prioritize high-confidence sources
        assert "official.com" in results["summary"]
        assert results["confidence_level"] in ["high", "medium"]
        
        # Should include confidence breakdown
        assert "confidence_breakdown" in results
        assert "official" in results["confidence_breakdown"]
        
    @pytest.mark.asyncio
    async def test_citation_formatting(self) -> None:
        """Test automatic citation formatting."""
        synthesizer = get_result_synthesizer()
        
        # Create test findings
        findings = [
            ResearchFinding(
                source_url="https://docs.python.org",
                source_classification=SourceClassification(
                    url="https://docs.python.org",
                    source_type=SourceType.OFFICIAL,
                    trust_level=ConfidenceLevel.HIGH,
                    domain_authority=0.95,
                ),
                content_summary="Python documentation",
                key_points=["Python", "Documentation"],
                confidence_score=0.9,
            ),
            ResearchFinding(
                source_url="https://stackoverflow.com",
                source_classification=SourceClassification(
                    url="https://stackoverflow.com",
                    source_type=SourceType.REPUTABLE_COMMUNITY,
                    trust_level=ConfidenceLevel.MEDIUM,
                    domain_authority=0.8,
                ),
                content_summary="Community answer",
                key_points=["Community", "Answer"],
                confidence_score=0.7,
            ),
        ]
        
        # Synthesize results
        results = synthesizer.synthesize_results(findings, "Test query")
        
        # Should format citations properly
        citations = results["citations"]
        assert len(citations) == 2
        
        # Check official source citation
        official_citation = next(c for c in citations if "docs.python.org" in c)
        assert "Official Documentation" in official_citation
        assert "High Confidence" in official_citation
        
        # Check community source citation
        community_citation = next(c for c in citations if "stackoverflow.com" in c)
        assert "Community Source" in community_citation
        assert "0.7" in community_citation


class TestIntegration:
    """Test end-to-end integration."""
    
    @pytest.mark.asyncio
    async def test_full_research_pipeline(self) -> None:
        """Test complete research pipeline integration."""
        # This would require mocking the browser tool and other dependencies
        # For now, test that components can be instantiated together
        port_manager = get_port_manager()
        health_checker = get_health_checker()
        planner = get_enhanced_query_planner()
        trust_engine = get_source_trust_engine()
        synthesizer = get_result_synthesizer()
        
        # All components should be available
        assert port_manager is not None
        assert health_checker is not None
        assert planner is not None
        assert trust_engine is not None
        assert synthesizer is not None
        
        # Test basic workflow
        intent = planner.analyze_intent("What is REST API?")
        assert intent.question_type == QuestionType.DEFINITION
        
        # Test source evaluation
        classification = trust_engine.evaluate_source(
            url="https://restfulapi.net/",
            content="REST API is an architectural style",
        )
        assert classification.source_type is not None
        
        # Test synthesis
        findings = [ResearchFinding(
            source_url="https://restfulapi.net/",
            source_classification=classification,
            content_summary="REST API is an architectural style",
            key_points=["REST", "API", "Architecture"],
            confidence_score=0.8,
        )]
        
        results = synthesizer.synthesize_results(findings, "What is REST API?")
        assert results["summary"] is not None
        assert len(results["citations"]) > 0
