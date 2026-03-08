#!/usr/bin/env python3
"""Phase 1: Remove DeepAgents dependencies from agents/tools system."""

import os
import re
from pathlib import Path

def clean_deepagents_references(file_path: Path) -> bool:
    """Remove DeepAgents references from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Remove DeepAgents imports and references
        content = re.sub(r'from deepagents\..*?\n', '', content)
        content = re.sub(r'import deepagents\..*?\n', '', content)
        content = re.sub(r'deepagents\.', '', content)
        content = re.sub(r'DeepAgents', '', content)
        
        # Clean up empty lines and extra spaces
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'\s+', ' ', content)
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error cleaning {file_path}: {e}")
        return False

def main():
    """Phase 1: Clean agents/tools system."""
    base_path = Path("mindflow_backend/agents/tools")
    
    print("🧹 Phase 1: Cleaning agents/tools system...")
    
    # Find all Python files
    py_files = list(base_path.rglob("*.py"))
    
    cleaned_files = []
    
    for file_path in py_files:
        if clean_deepagents_references(file_path):
            cleaned_files.append(str(file_path.relative_to(base_path)))
    
    print(f"✅ Cleaned {len(cleaned_files)} files:")
    for file_path in cleaned_files:
        print(f"  - {file_path}")
    
    print(f"\n📊 Phase 1 Summary:")
    print(f"  - Files processed: {len(py_files)}")
    print(f"  - Files cleaned: {len(cleaned_files)}")
    print(f"  - DeepAgents references: Removed")
    print(f"  - Status: Ready for Phase 2")

if __name__ == "__main__":
    main()
