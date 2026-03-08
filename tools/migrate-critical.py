#!/usr/bin/env python3
"""
Critical Files Migration Script

This script identifies and migrates critical files that still have
personality references, excluding the personality directory itself.
"""

import os
import re
from pathlib import Path

def migrate_critical_files():
    """Migrate only critical files outside personality directory."""
    critical_files = [
        "python/validate_architecture.py",
        "python/validate_prompt_structure.py", 
        "python/tests/unit/agents/test_contracts_import.py",
        "python/mindflow_backend/config/personality_rules.py",
        "python/mindflow_backend/agents/interfaces/orchestrator/personality.py",
        "python/mindflow_backend/agents/interfaces/core/personality.py",
        "python/mindflow_backend/agents/interfaces/core/__init__.py",
        "python/mindflow_backend/agents/interfaces/__init__.py",
        "python/mindflow_backend/api/interfaces/service_interface.py",
        "python/mindflow_backend/services/interfaces/orchestration_interfaces.py",
        "python/mindflow_backend/services/orchestration/orchestration_service.py",
        "python/mindflow_backend/schemas/__init__.py",
        "python/mindflow_backend/schemas/orchestration/personality.py",
        "python/mindflow_backend/agents/specialists/rule_engine.py",
    ]
    
    base_path = Path(".")
    migrated_count = 0
    
    print("🔧 Migrating critical files...")
    
    for file_path_str in critical_files:
        file_path = base_path / file_path_str
        
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue
        
        # Skip if it's in personality directory
        if "personality/" in file_path_str and file_path_str != "python/mindflow_backend/config/personality_rules.py":
            print(f"⏭️  Skipping personality directory file: {file_path}")
            continue
        
        print(f"🔄 Migrating: {file_path}")
        
        # Run migration on this file
        result = os.system(f"python3 tools/migrate-personality-to-specialists.py --file {file_path}")
        
        if result == 0:
            migrated_count += 1
            print(f"✅ Successfully migrated: {file_path}")
        else:
            print(f"❌ Failed to migrate: {file_path}")
    
    print(f"\n📊 Migration summary:")
    print(f"✅ Successfully migrated: {migrated_count} files")
    print(f"📁 Total critical files: {len(critical_files)}")

if __name__ == "__main__":
    migrate_critical_files()
