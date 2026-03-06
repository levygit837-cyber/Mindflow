#!/usr/bin/env python3
"""Validate the new OmniMind agent architecture.

Tests that all modules can be imported correctly and the
new structure works as expected.
"""

import sys
import traceback
from pathlib import Path

def test_import(module_path: str, description: str) -> bool:
    """Test importing a module."""
    try:
        __import__(module_path)
        print(f"✅ {description}")
        return True
    except Exception as e:
        print(f"❌ {description}: {e}")
        traceback.print_exc()
        return False

def test_subsystem(subsystem: str, description: str) -> bool:
    """Test importing a subsystem."""
    try:
        module = __import__(f"omnimind_backend.agents.{subsystem}", fromlist=[''])
        print(f"✅ {description}")
        
        # Test key components
        if subsystem == "context":
            assert hasattr(module, 'AgentContextRetriever')
            assert hasattr(module, 'get_agent_context_retriever')
        elif subsystem == "personality":
            assert hasattr(module, 'get_personality_selector')
            assert hasattr(module, 'get_personality_config_builder')
                
        return True
    except Exception as e:
        print(f"❌ {description}: {e}")
        traceback.print_exc()
        return False

def main():
    """Run architecture validation tests."""
    print("🏗️  Validating OmniMind Agent Architecture")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 0
    
    # Test core imports
    core_tests = [
        ("omnimind_backend.agents.core.interfaces", "Core interfaces"),
        ("omnimind_backend.agents.core.container", "Dependency injection container"),
        ("omnimind_backend.agents.core.exceptions", "Custom exceptions"),
        ("omnimind_backend.agents.core.initialization", "System initialization"),
    ]
    
    for module, desc in core_tests:
        total_tests += 1
        if test_import(module, desc):
            tests_passed += 1
    
    # Test subsystem imports
    subsystem_tests = [
        ("context", "Context subsystem"),
        ("personality", "Personality subsystem"),
        ("review", "Review subsystem"),
    ]
    
    for subsystem, desc in subsystem_tests:
        total_tests += 1
        if test_subsystem(subsystem, desc):
            tests_passed += 1
    
    # Test component imports
    component_tests = [
        ("omnimind_backend.agents.context.cache", "Context cache"),
        ("omnimind_backend.agents.context.vector_store", "Vector store"),
        ("omnimind_backend.agents.context.analyzer", "Content analyzer"),
        ("omnimind_backend.agents.personality.cache", "Personality cache"),
        ("omnimind_backend.agents.personality.rule_engine", "Rule engine"),
        ("omnimind_backend.agents.personality.configuration", "Configuration builders"),
        ("omnimind_backend.agents.personality.sub_personalities", "Sub-personalities"),
        ("omnimind_backend.agents.personality.dynamic_prompts", "Dynamic prompts"),
        ("omnimind_backend.agents.review.analyzer", "Review analyzer"),
        ("omnimind_backend.agents.review.parser", "Result parser"),
    ]
    
    for module, desc in component_tests:
        total_tests += 1
        if test_import(module, desc):
            tests_passed += 1
    
    # Test configuration imports
    config_tests = [
        ("omnimind_backend.config.agents", "Agent configuration"),
        ("omnimind_backend.config.personality_rules", "Personality rules"),
    ]
    
    for module, desc in config_tests:
        total_tests += 1
        if test_import(module, desc):
            tests_passed += 1
    
    # Test legacy compatibility
    legacy_tests = [
        ("omnimind_backend.agents", "Main agents module (legacy compatibility)"),
    ]
    
    for module, desc in legacy_tests:
        total_tests += 1
        if test_import(module, desc):
            tests_passed += 1
    
    # Test sub-personalities specifically
    try:
        from omnimind_backend.agents.personality.sub_personalities import (
            get_sub_personality,
            get_all_sub_personalities,
            find_best_sub_personality,
        )
        
        # Test getting sub-personalities
        security_guard = get_sub_personality("security_guard")
        assert security_guard is not None
        
        all_sub = get_all_sub_personalities()
        assert len(all_sub) > 0
        
        best_match = find_best_sub_personality(
            "security audit needed",
            ["vulnerability", "authentication"],
            "core"
        )
        
        print("✅ Sub-personalities functionality")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Sub-personalities functionality: {e}")
        traceback.print_exc()
    
    total_tests += 1
    
    # Test dynamic prompts
    try:
        from omnimind_backend.agents.personality.dynamic_prompts import (
            get_dynamic_prompt_builder,
            PromptContext,
        )
        
        builder = get_dynamic_prompt_builder()
        context = PromptContext(
            task_description="Test task",
            task_complexity="simple",
            personality="core"
        )
        
        prompt = builder.build_system_prompt(context)
        assert len(prompt) > 0
        
        print("✅ Dynamic prompts functionality")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Dynamic prompts functionality: {e}")
        traceback.print_exc()
    
    total_tests += 1
    
    # Results
    print("\n" + "=" * 50)
    print(f"📊 Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All architecture validation tests passed!")
        print("✅ The new OmniMind agent architecture is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
