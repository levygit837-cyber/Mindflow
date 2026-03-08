#!/usr/bin/env python3
"""
Automated Migration Tool: Personality → Specialists

This script helps migrate code from the deprecated personality system 
to the new specialists system.

Usage:
    python tools/migrate-personality-to-specialists.py --path ./src
    python tools/migrate-personality-to-specialists.py --file my_module.py
    python tools/migrate-personality-to-specialists.py --dry-run --path ./src
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Migration mappings
IMPORT_REPLACEMENTS = {
    r'from mindflow_backend\.agents\.personality import': 'from mindflow_backend.agents.specialists import',
    r'from \.personality import': 'from .specialists import',
    r'import mindflow_backend\.agents\.personality': 'import mindflow_backend.agents.specialists',
}

FUNCTION_REPLACEMENTS = {
    'get_personality_selector': 'get_specialist_selector',
    'get_personality_config_builder': 'get_specialist_config_builder',
    'get_personality_rule_engine': 'get_specialist_rule_engine',
    'get_personality_cache': 'get_specialist_cache',
    'select_personality': 'select_specialist',
    'register_all_personalities': 'register_all_specialists',
}

CLASS_REPLACEMENTS = {
    'PersonalitySelector': 'SpecialistSelector',
    'PersonalityType': 'SpecialistType',
    'PersonalityConfiguration': 'SpecialistConfiguration',
    'PersonalitySelection': 'SpecialistSelection',
    'PersonalityDecisionResult': 'SpecialistDecisionResult',
    'PersonalityRuleEngine': 'SpecialistRuleEngine',
    'PersonalityConfigurationBuilder': 'SpecialistConfigurationBuilder',
    'PersonalityCache': 'SpecialistCache',
    'PersonalitySelectionRule': 'SpecialistSelectionRule',
    'PersonalityCacheEntry': 'SpecialistCacheEntry',
    'PersonalitySwitchContext': 'SpecialistSwitchContext',
}

SPECIALIST_REPLACEMENTS = {
    'SecurityGuardPersonality': 'SecuritySpecialist',
    'CriticPersonality': 'ReviewSpecialist',
    'CreativePersonality': 'CreativeSpecialist',
    'ArchTechPersonality': 'ArchitectureSpecialist',
    'BrainstormPersonality': 'BrainstormSpecialist',
    'DeepIterationPersonality': 'DeepAnalysisSpecialist',
}

API_REPLACEMENTS = {
    '/select-personality': '/select-specialist',
    'PersonalitySelectionRequest': 'SpecialistSelectionRequest',
    'PersonalitySelectionResponse': 'SpecialistSelectionResponse',
    'current_personality': 'current_specialist',
    'selected_personality': 'selected_specialist',
    'PersonalityRuleConfig': 'SpecialistRuleConfig',
    'get_personality_rules': 'get_specialist_rules',
}

# All replacements combined
ALL_REPLACEMENTS = {
    **FUNCTION_REPLACEMENTS,
    **CLASS_REPLACEMENTS,
    **SPECIALIST_REPLACEMENTS,
    **API_REPLACEMENTS,
}


class PersonalityMigrator:
    """Handles migration from personality to specialists system."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.files_processed = 0
        self.files_changed = 0
        self.replacements_made = 0
        
    def migrate_file(self, file_path: Path) -> Dict[str, int]:
        """Migrate a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
            return {"errors": 1}
        
        original_content = content
        changes_made = 0
        
        # Apply import replacements
        for old_pattern, new_text in IMPORT_REPLACEMENTS.items():
            content, count = re.subn(old_pattern, new_text, content)
            changes_made += count
        
        # Apply function/class replacements (whole word boundaries)
        for old_name, new_name in ALL_REPLACEMENTS.items():
            # Match whole words only
            pattern = r'\b' + re.escape(old_name) + r'\b'
            content, count = re.subn(pattern, new_name, content)
            changes_made += count
        
        # Update docstrings and comments
        content = self._update_docstrings(content)
        
        # Write back if changed
        if content != original_content:
            if self.dry_run:
                print(f"🔄 Would update: {file_path} ({changes_made} changes)")
                changes_made = 0  # Don't count dry runs
            else:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"✅ Updated: {file_path} ({changes_made} changes)")
                    self.files_changed += 1
                except Exception as e:
                    print(f"❌ Error writing {file_path}: {e}")
                    return {"errors": 1}
        
        self.files_processed += 1
        self.replacements_made += changes_made
        
        return {"changes": changes_made}
    
    def _update_docstrings(self, content: str) -> str:
        """Update docstrings and comments with new terminology."""
        replacements = {
            r'personality system': 'specialist system',
            r'personality selector': 'specialist selector',
            r'personality type': 'specialist type',
            r'sub-personality': 'specialist',
            r'subpersonality': 'specialist',
            r'personalities': 'specialists',
        }
        
        for old, new in replacements.items():
            # Update in comments and docstrings
            pattern = r'([\'"])([^\'"]*?)' + re.escape(old) + r'([^\'"]*?)([\'"])'
            content = re.sub(pattern, r'\1\2' + new + r'\3\4', content)
            
            # Update in comments
            content = re.sub(r'#.*?' + re.escape(old), lambda m: m.group(0).replace(old, new), content)
        
        return content
    
    def migrate_directory(self, directory: Path) -> None:
        """Migrate all Python files in a directory."""
        python_files = list(directory.rglob("*.py"))
        
        print(f"🔍 Found {len(python_files)} Python files to check...")
        
        for file_path in python_files:
            # Skip certain directories
            if any(skip in str(file_path) for skip in ['__pycache__', '.git', 'venv', '.venv']):
                continue
            
            self.migrate_file(file_path)
    
    def print_summary(self) -> None:
        """Print migration summary."""
        print("\n" + "="*50)
        print("📊 MIGRATION SUMMARY")
        print("="*50)
        print(f"Files processed: {self.files_processed}")
        print(f"Files changed: {self.files_changed}")
        print(f"Replacements made: {self.replacements_made}")
        
        if self.dry_run:
            print("🔍 DRY RUN MODE - No files were actually modified")
        else:
            print("✅ Migration completed successfully!")
        
        print("\n📋 Next Steps:")
        print("1. Review the changes with 'git diff'")
        print("2. Run tests to verify everything works")
        print("3. Fix any remaining import errors")
        print("4. Commit the changes")
        
        if self.files_changed > 0:
            print("\n⚠️  IMPORTANT: Test your code after migration!")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate code from personality to specialists system"
    )
    parser.add_argument(
        '--path', 
        type=str, 
        help='Directory path to migrate (default: current directory)'
    )
    parser.add_argument(
        '--file', 
        type=str, 
        help='Single file to migrate'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be changed without modifying files'
    )
    
    args = parser.parse_args()
    
    if not args.path and not args.file:
        print("❌ Please specify --path or --file")
        sys.exit(1)
    
    migrator = PersonalityMigrator(dry_run=args.dry_run)
    
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            sys.exit(1)
        
        migrator.migrate_file(file_path)
    else:
        directory = Path(args.path)
        if not directory.exists():
            print(f"❌ Directory not found: {directory}")
            sys.exit(1)
        
        migrator.migrate_directory(directory)
    
    migrator.print_summary()


if __name__ == "__main__":
    main()
