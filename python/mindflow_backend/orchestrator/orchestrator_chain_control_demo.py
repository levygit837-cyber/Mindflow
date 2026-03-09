"""Demo: Orchestrator Chain Control.

This file demonstrates how the Orchestrator has complete control over chains:
1. Dynamic chain selection based on task analysis
2. Runtime configuration adjustment
3. Multi-chain orchestration
4. Fallback and error handling
5. Performance monitoring and optimization
"""

from __future__ import annotations

import asyncio
from typing import Dict, Any

from mindflow_backend.orchestrator.chain_integration import (
    get_chain_orchestrator,
    ChainSelectionCriteria,
    ChainCapability,
    ChainComplexity,
)
from mindflow_backend.chains.factory import get_available_chains
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


async def demo_orchestrator_chain_control():
    """Demonstrate orchestrator's complete control over chains."""
    
    print("🎯 Demo: Orchestrator Chain Control")
    print("=" * 50)
    
    orchestrator = get_chain_orchestrator()
    
    # 1. Show available chains
    print("\n📋 Available Chains:")
    chains = get_available_chains()
    for chain in chains:
        print(f"  • {chain['chain_id']}: {chain['name']} ({chain['complexity']})")
        print(f"    Capabilities: {', '.join(chain['capabilities'])}")
    
    # 2. Dynamic chain selection examples
    print("\n🔍 Dynamic Chain Selection Examples:")
    
    examples = [
        {
            "message": "Implement a new feature for user authentication",
            "complexity": 0.6,
            "expected": "coding_task",
        },
        {
            "message": "Analyze the market trends for Q4 2024",
            "complexity": 0.4,
            "expected": "analysis_task",
        },
        {
            "message": "Create a complex multi-step workflow with parallel processing",
            "complexity": 0.9,
            "expected": "conditional_workflow",
        },
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n  Example {i}: {example['message'][:50]}...")
        print(f"  Complexity: {example['complexity']}")
        
        # Select chain
        plan = await orchestrator.select_chain_for_task(
            message=example["message"],
            complexity_score=example["complexity"],
        )
        
        print(f"  ✅ Selected: {plan.primary_chain}")
        print(f"  🔄 Fallbacks: {[f[0] for f in plan.fallback_chains]}")
        print(f"  ⏱️  Timeout: {plan.timeout}s")
        
        # Verify expectation
        assert plan.primary_chain == example["expected"], f"Expected {example['expected']}, got {plan.primary_chain}"
        print(f"  ✅ Selection correct!")
    
    # 3. Advanced chain selection with custom criteria
    print("\n🎛️  Advanced Chain Selection:")
    
    custom_criteria = ChainSelectionCriteria(
        task_type="coding",
        complexity_threshold=0.7,
        required_capabilities=[ChainCapability.CODING, ChainCapability.VALIDATION],
        max_execution_time=120.0,
        preferred_agents=None,
    )
    
    plan = await orchestrator.select_chain_for_task(
        message="Build a secure API with comprehensive testing",
        complexity_score=0.8,
        criteria=custom_criteria,
    )
    
    print(f"  Task: Complex secure API development")
    print(f"  ✅ Selected: {plan.primary_chain}")
    print(f"  🔧 Config: {plan.primary_config}")
    
    # 4. Chain execution with monitoring
    print("\n⚡ Chain Execution with Monitoring:")
    
    test_context = {
        "message": "Create a simple data analysis script",
        "session_id": "demo_session",
        "provider": "openai",
        "model": "gpt-4",
    }
    
    # Execute with fallback handling
    result = await orchestrator.execute_chain_plan(
        plan=plan,
        context=test_context,
        execution_id="demo_execution",
    )
    
    print(f"  📊 Execution Result:")
    print(f"    Success: {result.get('error') is None}")
    print(f"    Response length: {len(result.get('response', ''))}")
    
    if "execution_metadata" in result:
        metadata = result["execution_metadata"]
        print(f"    Chain used: {metadata.get('chain_id', 'unknown')}")
        print(f"    Execution time: {metadata.get('execution_time', 0):.2f}s")
    
    # 5. Performance statistics
    print("\n📈 Performance Statistics:")
    
    stats = orchestrator.get_performance_stats()
    print(f"  Total executions: {stats['total_executions']}")
    print(f"  Success rate: {stats['success_rate']:.1%}")
    print(f"  Average time: {stats['average_execution_time']:.2f}s")
    print(f"  Fallback usage: {stats['fallback_usage_rate']:.1%}")
    
    if 'chain_performance' in stats:
        print(f"  Chain performance:")
        for chain_id, perf in stats['chain_performance'].items():
            success_rate = perf['successful'] / perf['total'] if perf['total'] > 0 else 0
            print(f"    {chain_id}: {success_rate:.1%} ({perf['successful']}/{perf['total']})")
    
    # 6. Execution history analysis
    print("\n📚 Execution History:")
    
    history = orchestrator.get_execution_history()
    total_sessions = len(history.get('sessions', {}))
    print(f"  Sessions tracked: {total_sessions}")
    
    if total_sessions > 0:
        # Show most recent session
        recent_session = max(history.get('sessions', {}).items(), key=lambda x: x[1][-1]['timestamp'])
        session_id, executions = recent_session
        
        print(f"  Recent session: {session_id}")
        print(f"  Executions: {len(executions)}")
        
        for execution in executions[-3:]:  # Show last 3 executions
            status = "✅" if execution['success'] else "❌"
            fallback_info = f" (fallback: {execution['fallback_used']})" if execution.get('fallback_used') else ""
            print(f"    {status} {execution['plan'].primary_chain}{fallback_info}")
    
    print("\n🎉 Demo completed! Orchestrator has full control over chains.")
    
    return True


async def demo_chain_factory_capabilities():
    """Demonstrate advanced factory capabilities."""
    
    print("\n🏭 Chain Factory Capabilities Demo")
    print("=" * 40)
    
    from mindflow_backend.chains.factory import get_chain_factory
    
    factory = get_chain_factory()
    
    # 1. Registry information
    print("\n📊 Registry Information:")
    registry_info = factory.get_registry_info()
    print(f"  Total chains: {registry_info['total_chains']}")
    print(f"  Cache size: {registry_info['cache_size']}")
    print(f"  Active executions: {registry_info['active_executions']}")
    
    print(f"  Chains by complexity:")
    for complexity, count in registry_info['chains_by_complexity'].items():
        print(f"    {complexity}: {count}")
    
    print(f"  Chains by capability:")
    for capability, count in registry_info['chains_by_capability'].items():
        if count > 0:
            print(f"    {capability}: {count}")
    
    # 2. Chain metadata inspection
    print("\n🔍 Chain Metadata Inspection:")
    
    for chain_id in ["analysis_task", "coding_task", "conditional_workflow"]:
        metadata = factory.registry.get_metadata(chain_id)
        if metadata:
            print(f"\n  {metadata.name} ({metadata.chain_id}):")
            print(f"    Description: {metadata.description}")
            print(f"    Complexity: {metadata.complexity.value}")
            print(f"    Estimated time: {metadata.estimated_execution_time}s")
            print(f"    Required agents: {[a.value for a in metadata.required_agents]}")
            print(f"    Capabilities: {[c.value for c in metadata.capabilities]}")
            print(f"    Max parallel: {metadata.max_parallel_instances}")
    
    # 3. Chain discovery for tasks
    print("\n🔎 Chain Discovery for Tasks:")
    
    tasks = [
        ("analysis", None),
        ("coding", "medium"),
        ("complex", "high"),
        ("research", None),
    ]
    
    for task_type, complexity in tasks:
        suitable_chains = factory.registry.find_chains_for_task(task_type, 
                                                               ChainComplexity(complexity) if complexity else None)
        
        print(f"\n  Task: {task_type} ({complexity or 'any'}):")
        for chain in suitable_chains:
            print(f"    • {chain.name} ({chain.complexity.value})")
    
    return True


async def demo_backward_compatibility():
    """Demonstrate backward compatibility with existing catalog."""
    
    print("\n🔄 Backward Compatibility Demo")
    print("=" * 35)
    
    # Old-style catalog access
    from mindflow_backend.chains.catalog import get_chain, list_available_chains
    
    print("\n📋 Legacy Catalog Access:")
    
    # List chains
    chains = list_available_chains()
    print(f"  Available chains: {len(chains)}")
    for chain in chains:
        print(f"    • {chain['chain_id']}: {chain['name']}")
    
    # Get chain info
    try:
        from mindflow_backend.chains.catalog import get_chain_info
        info = get_chain_info("analysis_task")
        print(f"\n📊 Chain Info (analysis_task):")
        print(f"  Name: {info['name']}")
        print(f"  Capabilities: {info['capabilities']}")
        print(f"  Complexity: {info['complexity']}")
    except Exception as e:
        print(f"  Error getting chain info: {e}")
    
    # Find chains for task
    try:
        from mindflow_backend.chains.catalog import find_chains_for_task
        coding_chains = find_chains_for_task("coding")
        print(f"\n🔍 Coding Chains: {len(coding_chains)}")
        for chain in coding_chains:
            print(f"    • {chain['chain_id']}: {chain['complexity']}")
    except Exception as e:
        print(f"  Error finding coding chains: {e}")
    
    print("\n✅ Backward compatibility maintained!")
    
    return True


async def main():
    """Run all demos."""
    
    print("🚀 MindFlow Chain System - Complete Control Demo")
    print("=" * 60)
    
    try:
        # Run all demos
        await demo_orchestrator_chain_control()
        await demo_chain_factory_capabilities()
        await demo_backward_compatibility()
        
        print("\n🎊 All demos completed successfully!")
        print("\n📝 Key Takeaways:")
        print("  ✅ Orchestrator has complete control over chain selection")
        print("  ✅ Dynamic configuration based on task requirements")
        print("  ✅ Automatic fallback and error handling")
        print("  ✅ Performance monitoring and optimization")
        print("  ✅ Backward compatibility maintained")
        print("  ✅ Extensible system for new chains")
        
    except Exception as e:
        _logger.error("demo_failed", error=str(e))
        print(f"\n❌ Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
