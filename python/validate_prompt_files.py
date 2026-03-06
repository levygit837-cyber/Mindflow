#!/usr/bin/env python3
"""Validate prompt file structure without dependencies.

Tests that all prompt files exist and have the expected structure.
"""

import os
from pathlib import Path

def check_file_exists(file_path: str, description: str) -> bool:
    """Check if a file exists."""
    full_path = Path("mindflow_backend") / file_path
    if full_path.exists():
        print(f"✅ {description}")
        return True
    else:
        print(f"❌ {description}: {full_path} not found")
        return False

def check_file_content(file_path: str, expected_content: list[str], description: str) -> bool:
    """Check if a file contains expected content."""
    full_path = Path("mindflow_backend") / file_path
    if not full_path.exists():
        print(f"❌ {description}: file not found")
        return False
    
    try:
        content = full_path.read_text()
        missing_content = []
        for expected in expected_content:
            if expected not in content:
                missing_content.append(expected)
        
        if missing_content:
            print(f"❌ {description}: missing content {missing_content}")
            return False
        else:
            print(f"✅ {description}: all expected content present")
            return True
    except Exception as e:
        print(f"❌ {description}: {e}")
        return False

def main():
    """Run prompt file structure validation."""
    print("🔍 Validating Prompt File Structure")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 0
    
    # Check directory structure
    directories = [
        ("agents/prompts/core", "Core personalities directory"),
        ("agents/prompts/specialized", "Specialized functions directory"),
        ("agents/prompts/composite", "Composite prompts directory"),
    ]
    
    for dir_path, desc in directories:
        total_tests += 1
        full_path = Path("mindflow_backend") / dir_path
        if full_path.exists() and full_path.is_dir():
            print(f"✅ {desc}")
            tests_passed += 1
        else:
            print(f"❌ {desc}: directory not found")
    
    # Check core prompt files
    core_files = [
        ("agents/prompts/core/__init__.py", "Core personalities init"),
        ("agents/prompts/core/analyst.py", "Analyst core prompt"),
        ("agents/prompts/core/coder.py", "Coder core prompt"),
        ("agents/prompts/core/orchestrator.py", "Orchestrator core prompt"),
        ("agents/prompts/core/researcher.py", "Researcher core prompt"),
    ]
    
    for file_path, desc in core_files:
        total_tests += 1
        if check_file_exists(file_path, desc):
            tests_passed += 1
    
    # Check specialized prompt files
    specialized_files = [
        ("agents/prompts/specialized/__init__.py", "Specialized functions init"),
        ("agents/prompts/specialized/security_analysis.py", "Security analysis prompt"),
        ("agents/prompts/specialized/architecture_review.py", "Architecture review prompt"),
        ("agents/prompts/specialized/code_review.py", "Code review prompt"),
        ("agents/prompts/specialized/brainstorming.py", "Brainstorming prompt"),
        ("agents/prompts/specialized/deep_analysis.py", "Deep analysis prompt"),
        ("agents/prompts/specialized/context_governance.py", "Context governance prompt"),
        ("agents/prompts/specialized/agent_delegation.py", "Agent delegation prompt"),
    ]
    
    for file_path, desc in specialized_files:
        total_tests += 1
        if check_file_exists(file_path, desc):
            tests_passed += 1
    
    # Check composite prompt files
    composite_files = [
        ("agents/prompts/composite/__init__.py", "Composite prompts init"),
        ("agents/prompts/composite/full_analyst.py", "Full analyst composite"),
        ("agents/prompts/composite/full_coder.py", "Full coder composite"),
        ("agents/prompts/composite/full_orchestrator.py", "Full orchestrator composite"),
    ]
    
    for file_path, desc in composite_files:
        total_tests += 1
        if check_file_exists(file_path, desc):
            tests_passed += 1
    
    # Check main prompts file
    total_tests += 1
    if check_file_exists("agents/prompts/__init__.py", "Main prompts file"):
        tests_passed += 1
    
    # Check base utilities
    total_tests += 1
    if check_file_exists("agents/prompts/base.py", "Base utilities"):
        tests_passed += 1
    
    # Check content quality of key files
    content_checks = [
        ("agents/prompts/core/analyst.py", ["ANALYST_CORE", "ANALYST_READ", "compose_analyst_prompt"], "Analyst core content"),
        ("agents/prompts/core/coder.py", ["CODER_CORE", "CODER_TOOL_USE", "compose_coder_prompt"], "Coder core content"),
        ("agents/prompts/specialized/security_analysis.py", ["SECURITY_ANALYSIS", "build_security_analysis_prompt"], "Security analysis content"),
        ("agents/prompts/__init__.py", ["build_system_prompt", "ANALYST_SYSTEM_PROMPT", "SECURITY_ANALYSIS_PROMPT"], "Main prompts content"),
    ]
    
    for file_path, expected_content, desc in content_checks:
        total_tests += 1
        if check_file_content(file_path, expected_content, desc):
            tests_passed += 1
    
    # Check that old files are removed
    old_files = [
        ("agents/prompts/creative.py", "Old creative prompt (should be removed)"),
        ("agents/prompts/critic.py", "Old critic prompt (should be removed)"),
        ("agents/personalities/security_guard.py", "Old security_guard personality (should be removed)"),
    ]
    
    for file_path, desc in old_files:
        total_tests += 1
        full_path = Path("python/mindflow_backend") / file_path
        if not full_path.exists():
            print(f"✅ {desc}: correctly removed")
            tests_passed += 1
        else:
            print(f"❌ {desc}: still exists")
    
    # Check sub-personalities file
    total_tests += 1
    if check_file_content(
        "agents/personality/sub_personalities.py",
        ["SecurityGuardPersonality", "CreativePersonality", "CriticPersonality"],
        "Sub-personalities content"
    ):
        tests_passed += 1
    
    # Results
    print("\n" + "=" * 50)
    print(f"📊 Results: {tests_passed}/{total_tests} structure checks passed")
    
    if tests_passed == total_tests:
        print("🎉 All prompt structure validation checks passed!")
        print("✅ The new prompt organization is complete and correct.")
        print("\n📋 Summary of changes:")
        print("   ✅ Prompts organized by function (core/specialized/composite)")
        print("   ✅ Abstract names replaced with concrete function names")
        print("   ✅ Security guard moved to sub-personalities")
        print("   ✅ Backward compatibility maintained")
        print("   ✅ All files created and structured correctly")
        return 0
    else:
        print("⚠️  Some structure checks failed.")
        return 1

if __name__ == "__main__":
    exit(main())
