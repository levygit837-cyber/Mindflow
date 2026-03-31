#!/usr/bin/env python3
"""Script to clean all enhanced and DeepAgents references from MindFlow tools."""

import re
from pathlib import Path


def clean_file(file_path: Path) -> bool:
    """Clean enhanced and DeepAgents references from a file."""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Remove "enhanced" references (case insensitive)
        content = re.sub(r'(?i)enhanced', '', content)
        
        # Remove "DeepAgents" references (case insensitive)
        content = re.sub(r'(?i)deepagents', '', content)
        
        # Clean up double spaces that might result from removal
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
    """Clean all tool files."""
    base_path = Path(__file__).parent / "mindflow_backend" / "tools"
    
    # Find all Python files
    py_files = list(base_path.rglob("*.py"))
    
    cleaned_files = []
    
    for file_path in py_files:
        if clean_file(file_path):
            cleaned_files.append(str(file_path.relative_to(base_path)))
    
    print(f"Cleaned {len(cleaned_files)} files:")
    for file_path in cleaned_files:
        print(f"  - {file_path}")

if __name__ == "__main__":
    main()
