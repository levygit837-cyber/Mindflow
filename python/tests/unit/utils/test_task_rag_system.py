"""Tests for the DT RAG system components."""

import pytest
import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from omnimind_backend.orchestrator.decomposition.dt_dependency_resolver import (
    get_dt_dependency_resolver,
    DependencyAnalysis,
    DependencyValidation,
)
from omnimind_backend.orchestrator.decomposition.dt_rag_context_manager import (
    get_dt_rag_context_manager,
)
from omnimind_backend.orchestrator.decomposition.dt_state_orchestrator import (
    get_dt_state_orchestrator,
)
from omnimind_backend.orchestrator.decomposition.component_router import (
    get_rag_aware_router,
)
from omnimind_backend.schemas.orchestration.decomposition.decomposition_v2 import (
    ComponentOwner,
    ComponentStatus,
    SubComponentContract,
    SubComponentState,
    ComponentEvidence,
)


@pytest.fixture
async def dt_rag_system():
    """Fixture to set up the complete DT RAG system for testing."""
    # Initialize all components
    context_manager = await get_dt_rag_context_manager()
    dependency_resolver = await get_dt_dependency_resolver()
    state_orchestrator = await get_dt_state_orchestrator()
    rag_router = await get_rag_aware_router()
    
    yield {
        "context_manager": context_manager,
        "dependency_resolver": dependency_resolver,
        "state_orchestrator": state_orchestrator,
        "rag_router": rag_router,
    }
    
    # Cleanup
    await state_orchestrator.shutdown()


@pytest.fixture
def sample_component():
    """Create a sample component for testing."""
    return SubComponentContract(
        component_id=uuid4(),
        parent_id=uuid4(),
        title="Test Component",
        scope="Implement test functionality",
        dependencies=[uuid4()],  # One dependency
        context_boundary="Test context",
        allowed_inputs=["test_input"],
        forbidden_inputs=["secret_input"],
        expected_artifacts=["test_artifact"],
        owner_agent=ComponentOwner.CODER,
        priority="medium",
    )


@pytest.fixture
def sample_component_state():
    """Create a sample component state for testing."""
    return SubComponentState(
        component_id=uuid4(),
        state=ComponentStatus.IN_PROGRESS,
        progress=0.5,
        evidence=ComponentEvidence(
            tests_passed=3,
            tests_total=5,
            lint_passed=True,
            checks=["check1", "check2"],
            agent_notes="Test notes",
        ),
        last_checkpoint_at=datetime.now(UTC),
        iteration_count=1,
        max_iterations=3,
    )


class TestDTRagContextManager:
    """Test the DT RAG Context Manager."""
    
    @pytest.mark.asyncio
    async def test_register_component(self, dt_rag_system):
        """Test component registration."""
        context_manager = dt_rag_system["context_manager"]
        component_id = str(uuid4())
        
        await context_manager.register_component(component_id, "component")
        
        # Verify component is registered
        context = await context_manager.get_component_context(component_id)
        assert context["component_id"] == component_id
        assert context["component_type"] == "component"
    
    @pytest.mark.asyncio
    async def test_update_component_state(self, dt_rag_system, sample_component_state):
        """Test component state updates."""
        context_manager = dt_rag_system["context_manager"]
        component_id = str(sample_component_state.component_id)
        
        # Register component first
        await context_manager.register_component(component_id, "component")
        
        # Update state
        await context_manager.update_component_state(
            component_id, "component", sample_component_state
        )
        
        # Verify context was updated
        context = await context_manager.get_component_context(component_id)
        assert context["context_ready"] is True  # Should have embedding now


class TestDTDependencyResolver:
    """Test the DT Dependency Resolver."""
    
    @pytest.mark.asyncio
    async def test_validate_component_dependencies(
        self, dt_rag_system, sample_component, sample_component_state
    ):
        """Test dependency validation."""
        dependency_resolver = dt_rag_system["dependency_resolver"]
        
        # Validate dependencies
        analysis = await dependency_resolver.validate_component_dependencies(
            sample_component, sample_component_state
        )
        
        assert isinstance(analysis, DependencyAnalysis)
        assert analysis.component_id == str(sample_component.component_id)
        assert analysis.total_dependencies == len(sample_component.dependencies)
        assert 0 <= analysis.overall_readiness <= 1.0
    
    @pytest.mark.asyncio
    async def test_should_pause_execution(self, dt_rag_system, sample_component_state):
        """Test pause decision logic."""
        dependency_resolver = dt_rag_system["dependency_resolver"]
        component_id = str(sample_component_state.component_id)
        
        # Initially should not pause (no cached analysis)
        should_pause = await dependency_resolver.should_pause_execution(
            component_id, sample_component_state
        )
        assert should_pause is False  # No dependencies to check


class TestDTStateOrchestrator:
    """Test the DT State Orchestrator."""
    
    @pytest.mark.asyncio
    async def test_register_component(
        self, dt_rag_system, sample_component, sample_component_state
    ):
        """Test component registration in orchestrator."""
        orchestrator = dt_rag_system["state_orchestrator"]
        
        await orchestrator.register_component(sample_component, sample_component_state)
        
        # Verify component is registered
        status = await orchestrator.get_component_rag_status(
            str(sample_component.component_id)
        )
        assert status["component_id"] == str(sample_component.component_id)
        assert status["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_update_component_state(
        self, dt_rag_system, sample_component, sample_component_state
    ):
        """Test component state updates in orchestrator."""
        orchestrator = dt_rag_system["state_orchestrator"]
        
        # Register component first
        await orchestrator.register_component(sample_component, sample_component_state)
        
        # Update state
        new_state = SubComponentState(
            component_id=sample_component.component_id,
            state=ComponentStatus.DONE,
            progress=1.0,
        )
        
        result = await orchestrator.update_component_state(
            str(sample_component.component_id), new_state
        )
        
        assert result["component_id"] == str(sample_component.component_id)
        assert result["new_state"] == ComponentStatus.DONE
        assert result["context_triggered"] is True


class TestRAGAwareComponentRouter:
    """Test the RAG-aware component router."""
    
    @pytest.mark.asyncio
    async def test_route_component_with_rag(
        self, dt_rag_system, sample_component, sample_component_state
    ):
        """Test RAG-aware routing."""
        router = dt_rag_system["rag_router"]
        
        routing_decision = await router.route_component_with_rag(
            sample_component, sample_component_state
        )
        
        assert "component_id" in routing_decision
        assert "primary_agent" in routing_decision
        assert "dependency_analysis" in routing_decision
        assert "routing_confidence" in routing_decision
        assert 0 <= routing_decision["routing_confidence"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_get_contextual_agent_suggestions(self, dt_rag_system):
        """Test contextual agent suggestions."""
        router = dt_rag_system["rag_router"]
        component_id = str(uuid4())
        
        suggestions = await router.get_contextual_agent_suggestions(
            component_id, 
            router.ComponentType.CODE_IMPLEMENTATION,
            "Implement user authentication system"
        )
        
        assert isinstance(suggestions, list)
        # Each suggestion should have required fields
        for suggestion in suggestions:
            assert "agent_type" in suggestion
            assert "confidence" in suggestion
            assert "recommendation" in suggestion


class TestIntegration:
    """Integration tests for the complete DT RAG system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(
        self, dt_rag_system, sample_component, sample_component_state
    ):
        """Test end-to-end workflow with all components."""
        orchestrator = dt_rag_system["state_orchestrator"]
        
        # Register component
        await orchestrator.register_component(sample_component, sample_component_state)
        
        # Update state to trigger context generation
        new_state = SubComponentState(
            component_id=sample_component.component_id,
            state=ComponentStatus.DONE,
            progress=1.0,
        )
        
        await orchestrator.update_component_state(
            str(sample_component.component_id), new_state
        )
        
        # Wait a bit for async processing
        await asyncio.sleep(0.1)
        
        # Check final status
        status = await orchestrator.get_component_rag_status(
            str(sample_component.component_id)
        )
        
        assert status["is_active"] is True
        assert status["context_status"]["context_ready"] is True
        assert status["dependency_analysis"] is not None
        assert status["routing_recommendation"] is not None
    
    @pytest.mark.asyncio
    async def test_dependency_coordination(self, dt_rag_system):
        """Test dependency coordination between components."""
        orchestrator = dt_rag_system["state_orchestrator"]
        
        # Create two components with dependency relationship
        dependency_id = uuid4()
        dependent_id = uuid4()
        
        dependency_component = SubComponentContract(
            component_id=dependency_id,
            parent_id=uuid4(),
            title="Dependency Component",
            scope="Provide dependency functionality",
            dependencies=[],
            owner_agent=ComponentOwner.CODER,
        )
        
        dependent_component = SubComponentContract(
            component_id=dependent_id,
            parent_id=uuid4(),
            title="Dependent Component",
            scope="Use dependency functionality",
            dependencies=[dependency_id],
            owner_agent=ComponentOwner.CODER,
        )
        
        # Register both components
        dependency_state = SubComponentState(
            component_id=dependency_id,
            state=ComponentStatus.IN_PROGRESS,
            progress=0.5,
        )
        
        dependent_state = SubComponentState(
            component_id=dependent_id,
            state=ComponentStatus.PENDING,
            progress=0.0,
        )
        
        await orchestrator.register_component(dependency_component, dependency_state)
        await orchestrator.register_component(dependent_component, dependent_state)
        
        # Complete the dependency
        completed_dependency = SubComponentState(
            component_id=dependency_id,
            state=ComponentStatus.DONE,
            progress=1.0,
        )
        
        await orchestrator.update_component_state(
            str(dependency_id), completed_dependency
        )
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Check if dependent can resume
        dependency_resolver = dt_rag_system["dependency_resolver"]
        can_resume = await dependency_resolver.can_resume_execution(str(dependent_id))
        
        # The dependent should be able to resume (dependency is ready)
        assert can_resume is True


if __name__ == "__main__":
    pytest.main([__file__])
