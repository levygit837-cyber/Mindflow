#!/usr/bin/env python3
"""Remove enhanced references from agents/tools system."""

import re
from pathlib import Path


def clean_enhanced_references(file_path: Path) -> bool:
    """Remove enhanced references from a file."""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Remove "enhanced" references (case insensitive)
        content = re.sub(r'(?i)enhanced', '', content)
        
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
    """Clean enhanced references from agents/tools."""
    base_path = Path("mindflow_backend/agents/tools")
    
    print("🧹 Phase 1: Removing enhanced references...")
    
    # Find all Python files
    py_files = list(base_path.rglob("*.py"))
    
    cleaned_files = []
    
    for file_path in py_files:
        if clean_enhanced_references(file_path):
            cleaned_files.append(str(file_path.relative_to(base_path)))
    
    print(f"✅ Cleaned {len(cleaned_files)} files:")
    for file_path in cleaned_files:
        print(f"  - {file_path}")
    
    print("\n📊 Enhanced References Summary:")
    print(f"  - Files processed: {len(py_files)}")
    print(f"  - Files cleaned: {len(cleaned_files)}")
    print("  - Enhanced references: Removed")
    print("  - Status: Clean naming achieved")

if __name__ == "__main__":
    main()
