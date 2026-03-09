"""Migration status checker for exception system.

Shows which files have been migrated to the new simplified system
and which still need migration.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple


class MigrationStatusChecker:
    """Checks migration status of exception system files."""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.project_root = self.base_path.parent.parent
        self.migrated_files = []
        self.pending_files = []
        self.legacy_files = []
        
    def check_imports(self, file_path: Path) -> List[str]:
        """Check which exception imports a file uses."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            imports = []
            
            # Check for old imports
            old_patterns = [
                r'from.*\.core import',
                r'from.*\.core_simple import',
                r'from.*\.business import',
                r'from.*\.patterns import',
            ]
            
            for pattern in old_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    imports.append(f"OLD: {pattern}")
            
            # Check for new imports
            new_patterns = [
                r'from.*\.core_new import',
                r'from.*\.business_new import',
                r'from.*\.patterns_new import',
            ]
            
            for pattern in new_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    imports.append(f"NEW: {pattern}")
            
            return imports
            
        except Exception as e:
            return [f"ERROR: {e}"]
    
    def scan_exceptions_directory(self) -> None:
        """Scan exceptions directory for migration status."""
        print("🔍 Scanning exceptions directory...")
        
        for file_path in self.base_path.rglob("*.py"):
            if file_path.name.startswith("__"):
                continue
                
            imports = self.check_imports(file_path)
            
            if any("NEW:" in imp for imp in imports):
                self.migrated_files.append((str(file_path), imports))
            elif any("OLD:" in imp for imp in imports):
                self.pending_files.append((str(file_path), imports))
            else:
                self.legacy_files.append((str(file_path), imports))
    
    def scan_project_files(self) -> None:
        """Scan entire project for exception imports."""
        print("🔍 Scanning project files...")
        
        python_files = list(self.project_root.rglob("*.py"))
        
        for file_path in python_files:
            if "exceptions" in str(file_path):
                continue  # Already scanned
                
            imports = self.check_imports(file_path)
            
            if any("OLD:" in imp for imp in imports):
                self.pending_files.append((str(file_path), imports))
    
    def generate_report(self) -> None:
        """Generate migration status report."""
        print("\n" + "=" * 80)
        print("📊 EXCEPTION SYSTEM MIGRATION STATUS REPORT")
        print("=" * 80)
        
        print(f"\n📁 Directory scanned: {self.base_path}")
        print(f"🔍 Total Python files checked: {len(self.migrated_files) + len(self.pending_files) + len(self.legacy_files)}")
        
        # Migrated files
        print(f"\n✅ MIGRATED FILES: {len(self.migrated_files)}")
        print("-" * 50)
        for file_path, imports in self.migrated_files:
            rel_path = file_path.replace(str(self.project_root), "")
            print(f"   {rel_path}")
            for imp in imports:
                if "NEW:" in imp:
                    print(f"      ✓ {imp}")
        
        # Pending files
        print(f"\n⚠️  PENDING MIGRATION: {len(self.pending_files)}")
        print("-" * 50)
        for file_path, imports in self.pending_files:
            rel_path = file_path.replace(str(self.project_root), "")
            print(f"   {rel_path}")
            for imp in imports:
                if "OLD:" in imp:
                    print(f"      ⚠️  {imp}")
        
        # Legacy files
        if self.legacy_files:
            print(f"\n📄 LEGACY FILES: {len(self.legacy_files)}")
            print("-" * 50)
            for file_path, imports in self.legacy_files:
                rel_path = file_path.replace(str(self.project_root), "")
                print(f"   {rel_path}")
        
        # Summary
        total = len(self.migrated_files) + len(self.pending_files)
        if total > 0:
            percentage = (len(self.migrated_files) / total) * 100
            print(f"\n📈 MIGRATION PROGRESS: {percentage:.1f}%")
            print(f"   Completed: {len(self.migrated_files)}/{total}")
        
        # Recommendations
        print(f"\n🎯 RECOMMENDATIONS:")
        print("-" * 50)
        
        if self.pending_files:
            print("   1. Update remaining files to use _new imports")
            print("   2. Test each file after migration")
            print("   3. Remove old files after full migration")
        
        if len(self.migrated_files) > len(self.pending_files):
            print("   4. Migration is progressing well!")
            print("   5. Consider removing legacy files soon")
        
        print("\n" + "=" * 80)


def main():
    """Run migration status check."""
    checker = MigrationStatusChecker()
    checker.scan_exceptions_directory()
    checker.scan_project_files()
    checker.generate_report()


if __name__ == "__main__":
    main()
