#!/usr/bin/env python3
"""Validate the new OmniMind agent structure without dependencies.

Tests that all files exist and have the correct structure.
"""

import os
from pathlib import Path

def check_file_exists(file_path: str, description: str) -> bool:
    """Check if a file exists."""
    full_path = Path("python/omnimind_backend") / file_path
    if full_path.exists():
        print(f"✅ {description}")
        return True
    else:
        print(f"❌ {description}: {full_path} not found")
        return False

def check_directory_exists(dir_path: str, description: str) -> bool:
    """Check if a directory exists."""
    full_path = Path("python/omnimind_backend") / dir_path
    if full_path.exists() and full_path.is_dir():
        print(f"✅ {description}")
        return True
    else:
        print(f"❌ {description}: {full_path} not found")
        return False

def check_file_structure():
    """Check the new file structure."""
    print("🏗️  Validating OmniMind Agent Structure")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 0
    
    # Check core directories
    core_dirs = [
        ("agents/core", "Core interfaces directory"),
        ("agents/context", "Context subsystem directory"),
        ("agents/personality", "Personality subsystem directory"),
        ("agents/review", "Review subsystem directory"),
        ("config", "Configuration directory"),
        ("exceptions", "Exceptions directory"),
    ]
    
    for dir_path, desc in core_dirs:
        total_tests += 1
        if check_directory_exists(dir_path, desc):
            tests_passed += 1
    
    # Check core files
    core_files = [
        ("agents/core/interfaces.py", "Core interfaces"),
        ("agents/core/container.py", "DI container"),
        ("agents/core/exceptions.py", "Core exceptions"),
        ("agents/core/initialization.py", "System initialization"),
        ("config/agents.py", "Agent configuration"),
        ("config/personality_rules.py", "Personality rules"),
        ("exceptions/__init__.py", "Exceptions init"),
        ("exceptions/agents.py", "Agent exceptions"),
    ]
    
    for file_path, desc in core_files:
        total_tests += 1
        if check_file_exists(file_path, desc):
            tests_passed += 1
    
    # Check context subsystem files
    context_files = [
        ("agents/context/__init__.py", "Context subsystem init"),
        ("agents/context/retriever.py", "Context retriever (moved)"),
        ("agents/context/cache.py", "Context cache"),
        ("agents/context/vector_store.py", "Vector store"),
        ("agents/context/analyzer.py", "Content analyzer"),
    ]
    
    for file_path, desc in context_files:
        total_tests += 1
        if check_file_exists(file_path, desc):
            tests_passed += 1
    
    # Check personality subsystem files
    personality_files = [
        ("agents/personality/__init__.py", "Personality subsystem init"),
        ("agents/personality/selector.py", "Personality selector (moved)"),
        ("agents/personality/cache.py", "Personality cache"),
        ("agents/personality/rule_engine.py", "Rule engine"),
        ("agents/personality/configuration.py", "Configuration builders"),
        ("agents/personality/sub_personalities.py", "Sub-personalities"),
        ("agents/personality/dynamic_prompts.py", "Dynamic prompts"),
    ]
    
    for file_path, desc in personality_files:
        total_tests += 1
        if check_file_exists(file_path, desc):
            tests_passed += 1
    
    # Check review subsystem files
    review_files = [
        ("agents/review/__init__.py", "Review subsystem init"),
        ("agents/review/agent.py", "Session review agent (moved)"),
        ("agents/review/analyzer.py", "Review analyzer"),
        ("agents/review/parser.py", "Result parser"),
    ]
    
    for file_path, desc in review_files:
        total_tests += 1
        if check_file_exists(file_path, desc):
            tests_passed += 1
    
    # Check old files are moved
    old_files = [
        ("agents/context_retriever.py", "Old context_retriever.py (should be moved)"),
        ("agents/personality_selector.py", "Old personality_selector.py (should be moved)"),
        ("agents/session_review_agent.py", "Old session_review_agent.py (should be moved)"),
    ]
    
    for file_path, desc in old_files:
        total_tests += 1
        full_path = Path("python/omnimind_backend") / file_path
        if not full_path.exists():
            print(f"✅ {desc}: correctly moved")
            tests_passed += 1
        else:
            print(f"❌ {desc}: still exists in old location")
    
    # Check documentation
    doc_files = [
        ("AGENT_ARCHITECTURE.md", "Architecture documentation"),
    ]
    
    for file_path, desc in doc_files:
        total_tests += 1
        if check_file_exists(file_path, desc):
            tests_passed += 1
    
    # Results
    print("\n" + "=" * 50)
    print(f"📊 Results: {tests_passed}/{total_tests} structure checks passed")
    
    if tests_passed == total_tests:
        print("🎉 All structure validation checks passed!")
        print("✅ The new OmniMind agent structure is correct.")
        return True
    else:
        print("⚠️  Some structure checks failed.")
        return False

def check_file_contents():
    """Check that key files have expected content."""
    print("\n🔍 Checking file contents...")
    print("=" * 30)
    
    # Check __init__.py files have proper exports
    init_files = [
        ("agents/__init__.py", ["context", "personality", "review"]),
        ("agents/context/__init__.py", ["AgentContextRetriever", "get_agent_context_retriever"]),
        ("agents/personality/__init__.py", ["get_personality_selector", "DynamicPromptBuilder"]),
        ("agents/review/__init__.py", ["SessionReviewAgentImplementation", "get_session_review_agent"]),
    ]
    
    for file_path, expected_exports in init_files:
        full_path = Path("python/omnimind_backend") / file_path
        if full_path.exists():
            content = full_path.read_text()
            missing_exports = []
            for export in expected_exports:
                if export not in content:
                    missing_exports.append(export)
            
            if missing_exports:
                print(f"❌ {file_path}: missing exports {missing_exports}")
            else:
                print(f"✅ {file_path}: all expected exports present")
        else:
            print(f"❌ {file_path}: file not found")

def main():
    """Run structure validation."""
    # Change to the correct directory
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    os.chdir(project_dir)
    
    print(f"🔍 Validating from: {project_dir}")
    
    structure_ok = check_file_structure()
    check_file_contents()
    
    if structure_ok:
        print("\n🚀 Structure validation completed successfully!")
        print("📝 Next steps:")
        print("   1. Install dependencies: pip install -r requirements.txt")
        print("   2. Run full validation: python python/validate_architecture.py")
        print("   3. Test the new architecture in your code")
        return 0
    else:
        print("\n⚠️  Structure validation failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    exit(main())
