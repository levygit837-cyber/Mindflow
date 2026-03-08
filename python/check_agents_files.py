#!/usr/bin/env python3
"""Check for corrupted files in agents/tools directory."""

import os
from pathlib import Path

def check_file_format(file_path: Path) -> bool:
    """Check if file has proper line breaks."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file has at least one line break
        if '\n' not in content and len(content) > 200:
            return False  # Likely corrupted (all in one line)
        
        # Check if it has proper structure
        lines = content.split('\n')
        if len(lines) > 1:
            return True
        
        return True
        
    except Exception:
        return False

def main():
    """Check all Python files in agents/tools."""
    base_path = Path("mindflow_backend/agents/tools")
    
    corrupted_files = []
    good_files = []
    
    for file_path in base_path.rglob("*.py"):
        if check_file_format(file_path):
            good_files.append(str(file_path.relative_to(base_path)))
        else:
            corrupted_files.append(str(file_path.relative_to(base_path)))
    
    print(f"📊 Analysis Results:")
    print(f"✅ Good files: {len(good_files)}")
    print(f"❌ Corrupted files: {len(corrupted_files)}")
    
    if corrupted_files:
        print(f"\n🔧 Corrupted files that need fixing:")
        for file_path in corrupted_files:
            print(f"  - {file_path}")
    else:
        print(f"\n🎉 All files are properly formatted!")
    
    return len(corrupted_files) == 0

if __name__ == "__main__":
    main()
