"""Semantic Context System - Usage Examples and Documentation.

This module provides examples and documentation for using the enhanced
orchestration system with semantic context and multilingual embeddings.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

from mindflow_backend.orchestrator.semantic_context_manager import (
    get_semantic_context_manager,
    ContextMatch,
)
from mindflow_backend.services.multilingual_embeddings import (
    get_multilingual_embedding_service,
)
from mindflow_backend.orchestrator.decomposition.context_aware_resolver import (
    ContextAwareResolver,
)
from mindflow_backend.orchestrator.decomposition.tasker_v2 import (
    TaskerV2,
)


async def example_basic_semantic_search():
    """Example: Basic semantic search between tasks."""
    print("=== Basic Semantic Search Example ===")
    
    # Initialize services
    context_manager = await get_semantic_context_manager()
    embedding_service = await get_multilingual_embedding_service()
    
    session_id = str(uuid4())
    
    # Store context from an Analyst task
    analyst_context = """
    The codebase uses FastAPI with PostgreSQL backend.
    Authentication is handled via JWT tokens.
    The main API endpoints are in /api/v1/ directory.
    Database models are defined in models.py.
    """
    
    await context_manager.store_task_context(
        task_id="analyst_001",
        agent_type="analyst",
        content=analyst_context,
        metadata={"session_id": session_id, "analysis_type": "codebase_overview"},
    )
    
    # Store context from a Coder task
    coder_context = """
    Fixed authentication bug in login endpoint.
    Updated JWT token validation logic.
    Added proper error handling for expired tokens.
    """
    
    await context_manager.store_task_context(
        task_id="coder_001", 
        agent_type="coder",
        content=coder_context,
        metadata={"session_id": session_id, "fix_type": "authentication"},
    )
    
    # Search for relevant context for a new task
    matches = await context_manager.find_relevant_context(
        task_id="new_task_001",
        query="fix authentication issues in the API",
        session_id=session_id,
        limit=5,
    )
    
    print(f"Found {len(matches)} relevant context matches:")
    for i, match in enumerate(matches, 1):
        print(f"{i}. {match.agent_type} task {match.task_id} "
              f"(similarity: {match.similarity:.2f})")
        print(f"   Content: {match.content[:100]}...")
        print()


async def example_dependency_resolution():
    """Example: Task dependency resolution with context waiting."""
    print("=== Dependency Resolution Example ===")
    
    context_manager = await get_semantic_context_manager()
    session_id = str(uuid4())
    
    # Task 1: Analyst needs to understand codebase
    await context_manager.store_task_context(
        task_id="task_001",
        agent_type="analyst",
        content="Codebase analysis: FastAPI + PostgreSQL + JWT auth",
        metadata={"session_id": session_id},
    )
    
    # Mark task as completed
    await context_manager.update_task_status(
        task_id="task_001",
        status="completed",
        session_id=session_id,
    )
    
    # Task 2: Coder needs to fix bug (depends on Task 1)
    # Wait for dependency context
    wait_result = await context_manager.wait_for_context(
        task_id="task_002",
        required_context_ids=["task_001"],
        session_id=session_id,
        timeout=10,
    )
    
    print(f"Wait result: {wait_result['status']}")
    if wait_result['status'] == 'ready':
        print("Dependencies are ready!")
        for ctx in wait_result['contexts']:
            print(f"  - {ctx['agent_type']}: {ctx['content'][:50]}...")
    else:
        print(f"Timeout or error: {wait_result}")


async def example_multilingual_embeddings():
    """Example: Multilingual embedding generation and similarity."""
    print("=== Multilingual Embeddings Example ===")
    
    embedding_service = await get_multilingual_embedding_service()
    
    # Texts in different languages
    texts = [
        "Fix authentication bug in the login system",
        "Corrigir bug de autenticação no sistema de login",
        "Arreglar bug de autenticación en el sistema de login",
    ]
    
    # Generate embeddings
    embeddings = await embedding_service.generate_batch_embeddings(texts)
    
    print(f"Generated {len(embeddings)} embeddings")
    print(f"Embedding dimension: {embedding_service.get_embedding_dimension()}")
    
    # Calculate similarities
    for i in range(1, len(embeddings)):
        similarity = await embedding_service.calculate_similarity(
            embeddings[0], embeddings[i]
        )
        language = await embedding_service.detect_language(texts[i])
        print(f"Similarity with {language}: {similarity:.3f}")


async def example_enhanced_task_decomposition():
    """Example: Enhanced task decomposition with semantic context."""
    print("=== Enhanced Task Decomposition Example ===")
    
    tasker = TaskerV2()
    session_id = str(uuid4())
    
    # Complex request that should be decomposed
    message = """
    Fix the authentication bug in the login system and add comprehensive tests.
    The bug occurs when users try to login with expired JWT tokens.
    Need to analyze the current codebase first, then implement the fix,
    and finally add unit tests and integration tests.
    """
    
    # Decompose with semantic analysis
    main_contract, sub_tasks = await tasker.decompose(
        message=message,
        session_id=session_id,
        complexity_score=0.8,
        provider="vertexai",
        model="gemini-3-flash-preview",
        memory_context="Previous issues with JWT token validation",
    )
    
    print(f"Main goal: {main_contract.goal}")
    print(f"Decomposed into {len(sub_tasks)} sub-tasks:")
    
    for i, task in enumerate(sub_tasks, 1):
        print(f"{i}. {task.title}")
        print(f"   Agent: {task.owner_agent.value}")
        print(f"   Dependencies: {len(task.dependencies)}")
        print(f"   Priority: {task.priority}")
        print()


async def example_context_aware_resolution():
    """Example: Context-aware task resolution."""
    print("=== Context-Aware Resolution Example ===")
    
    from mindflow_backend.schemas.orchestration.decomposition.decomposition_v2 import (
        SubTaskContract,
        ComponentOwner,
    )
    from uuid import UUID
    
    resolver = ContextAwareResolver()
    session_id = str(uuid4())
    
    # Create a sample sub-task contract
    contract = SubTaskContract(
        task_id=UUID(),
        parent_id=UUID(),
        title="Fix Authentication Bug",
        scope="Fix JWT token validation in login endpoint",
        dependencies=[],  # Would normally have dependencies
        context_boundary="Authentication and security modules",
        expected_artifacts=["Fixed login endpoint", "Updated JWT validation"],
        owner_agent=ComponentOwner.CODER,
        priority="high",
    )
    
    # Mock prior results
    prior_results = {
        "analyst_task": "Codebase uses FastAPI with JWT authentication",
    }
    
    # Resolve with context awareness
    result = await resolver.resolve(
        contract=contract,
        prior_results=prior_results,
        provider="vertexai",
        model="gemini-3-flash-preview",
        memory_context="User reported login issues with expired tokens",
        session_id=session_id,
    )
    
    print("Resolution result:")
    print(f"  Task ID: {result['task_id']}")
    print(f"  Title: {result['title']}")
    print(f"  Dependencies resolved: {result['dependencies_resolved']}")
    print(f"  Context used: {result['context_used']}")
    print(f"  Result length: {len(result['result'])} characters")


async def main():
    """Run all examples."""
    print("🚀 Semantic Context System Examples\n")
    
    try:
        await example_basic_semantic_search()
        print("\n" + "="*50 + "\n")
        
        await example_dependency_resolution()
        print("\n" + "="*50 + "\n")
        
        await example_multilingual_embeddings()
        print("\n" + "="*50 + "\n")
        
        await example_enhanced_task_decomposition()
        print("\n" + "="*50 + "\n")
        
        await example_context_aware_resolution()
        
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
