#!/usr/bin/env python3
"""
Batch Migration Script: Personality → Specialists

This script migrates remaining files in batches, excluding the personality
directory which should maintain references for compatibility.
"""

import os
import sys
from pathlib import Path

def run_batch_migration():
    """Run migration on remaining files in batches."""
    base_path = Path("./python")
    
    # Files to exclude (personality directory and backup files)
    exclude_patterns = [
        "personality/",
        "backup/",
        "__pycache__/",
        ".git/",
        "test_",  # Exclude test files for now
        "validate_",  # Exclude validation scripts
    ]
    
    # Get all Python files that need migration
    files_to_migrate = []
    
    print("🔍 Scanning for files to migrate...")
    
    for file_path in base_path.rglob("*.py"):
        # Skip excluded patterns
        file_str = str(file_path)
        if any(pattern in file_str for pattern in exclude_patterns):
            continue
        
        # Check if file has personality references
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple check for personality references
            if any(keyword in content for keyword in [
                "from.*personality", "import.*personality", 
                "PersonalitySelector", "PersonalityType",
                "get_personality", "/select-personality"
            ]):
                files_to_migrate.append(file_path)
        except Exception:
            continue
    
    print(f"📊 Found {len(files_to_migrate)} files to migrate")
    
    # Process in batches of 10 files
    batch_size = 10
    for i in range(0, len(files_to_migrate), batch_size):
        batch = files_to_migrate[i:i + batch_size]
        print(f"\n🔄 Processing batch {i//batch_size + 1}/{(len(files_to_migrate)-1)//batch_size + 1}")
        
        for file_path in batch:
            print(f"  📁 Migrating: {file_path}")
            os.system(f"python3 tools/migrate-personality-to-specialists.py --file {file_path}")
    
    print(f"\n✅ Batch migration completed! Processed {len(files_to_migrate)} files")

if __name__ == "__main__":
    run_batch_migration()
