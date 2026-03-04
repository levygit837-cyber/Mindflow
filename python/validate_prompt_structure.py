#!/usr/bin/env python3
"""Validate the new prompt structure organization.

Tests that all prompts can be imported correctly and the new structure works as expected.
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

def test_prompt_availability(module_path: str, prompt_names: list[str], description: str) -> bool:
    """Test that specific prompts are available in a module."""
    try:
        module = __import__(module_path, fromlist=prompt_names)
        missing_prompts = []
        for prompt_name in prompt_names:
            if not hasattr(module, prompt_name):
                missing_prompts.append(prompt_name)
        
        if missing_prompts:
            print(f"❌ {description}: missing prompts {missing_prompts}")
            return False
        else:
            print(f"✅ {description}: all prompts available")
            return True
    except Exception as e:
        print(f"❌ {description}: {e}")
        traceback.print_exc()
        return False

def main():
    """Run prompt structure validation tests."""
    print("🔍 Validating New Prompt Structure")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 0
    
    # Test core imports
    core_tests = [
        ("omnimind_backend.agents.prompts.base", "Base utilities"),
        ("omnimind_backend.agents.prompts.core", "Core personalities module"),
        ("omnimind_backend.agents.prompts.specialized", "Specialized functions module"),
        ("omnimind_backend.agents.prompts.composite", "Composite prompts module"),
    ]
    
    for module, desc in core_tests:
        total_tests += 1
        if test_import(module, desc):
            tests_passed += 1
    
    # Test main prompts module
    total_tests += 1
    if test_import("omnimind_backend.agents.prompts", "Main prompts module"):
        tests_passed += 1
    
    # Test core personalities availability
    core_prompts = [
        "ANALYST_SYSTEM_PROMPT",
        "CODER_SYSTEM_PROMPT", 
        "ORCHESTRATOR_SYSTEM_PROMPT",
        "RESEARCHER_SYSTEM_PROMPT",
    ]
    
    total_tests += 1
    if test_prompt_availability("omnimind_backend.agents.prompts", core_prompts, "Core personalities"):
        tests_passed += 1
    
    # Test specialized functions availability
    specialized_prompts = [
        "SECURITY_ANALYSIS_PROMPT",
        "ARCHITECTURE_REVIEW_PROMPT",
        "CODE_REVIEW_PROMPT",
        "BRAINSTORMING_PROMPT",
        "DEEP_ANALYSIS_PROMPT",
        "CONTEXT_GOVERNANCE_PROMPT",
        "AGENT_DELEGATION_PROMPT",
    ]
    
    total_tests += 1
    if test_prompt_availability("omnimind_backend.agents.prompts", specialized_prompts, "Specialized functions"):
        tests_passed += 1
    
    # Test composite prompts availability
    composite_prompts = [
        "FULL_ANALYST_PROMPT",
        "FULL_CODER_PROMPT",
        "FULL_ORCHESTRATOR_PROMPT",
    ]
    
    total_tests += 1
    if test_prompt_availability("omnimind_backend.agents.prompts", composite_prompts, "Composite prompts"):
        tests_passed += 1
    
    # Test legacy compatibility
    legacy_prompts = [
        "ANALYST_SYSTEM_PROMPT_LEGACY",
        "CODER_SYSTEM_PROMPT_LEGACY",
        "ORCHESTRATOR_SYSTEM_PROMPT_LEGACY",
    ]
    
    total_tests += 1
    if test_prompt_availability("omnimind_backend.agents.prompts", legacy_prompts, "Legacy compatibility"):
        tests_passed += 1
    
    # Test sub-personalities
    total_tests += 1
    if test_import("omnimind_backend.agents.personality.sub_personalities", "Sub-personalities module"):
        tests_passed += 1
    
    # Test sub-personality functionality
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
            "analyst"
        )
        
        print("✅ Sub-personalities functionality")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Sub-personalities functionality: {e}")
        traceback.print_exc()
    
    total_tests += 1
    
    # Test prompt content quality
    try:
        from omnimind_backend.agents.prompts import (
            ANALYST_SYSTEM_PROMPT,
            CODER_SYSTEM_PROMPT,
            SECURITY_ANALYSIS_PROMPT,
        )
        
        # Check that prompts have reasonable length
        assert len(ANALYST_SYSTEM_PROMPT) > 1000, "Analyst prompt too short"
        assert len(CODER_SYSTEM_PROMPT) > 1000, "Coder prompt too short"
        assert len(SECURITY_ANALYSIS_PROMPT) > 1000, "Security analysis prompt too short"
        
        # Check that prompts contain expected keywords
        assert "Analyst" in ANALYST_SYSTEM_PROMPT, "Analyst prompt missing identity"
        assert "Coder" in CODER_SYSTEM_PROMPT, "Coder prompt missing identity"
        assert "Security" in SECURITY_ANALYSIS_PROMPT, "Security prompt missing identity"
        
        print("✅ Prompt content quality")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Prompt content quality: {e}")
        traceback.print_exc()
    
    total_tests += 1
    
    # Results
    print("\n" + "=" * 50)
    print(f"📊 Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All prompt structure validation tests passed!")
        print("✅ The new prompt organization is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
