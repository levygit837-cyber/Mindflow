#!/usr/bin/env python3
"""
Validation Script: Personality → Specialists Migration

This script validates that the migration was successful and identifies
any remaining references to the deprecated personality system.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Set

class MigrationValidator:
    """Validates the migration from personality to specialists system."""
    
    def __init__(self, base_path: str = "./python"):
        self.base_path = Path(base_path)
        self.issues = []
        self.files_checked = 0
        self.python_files = 0
        
    def validate_migration(self) -> Dict[str, any]:
        """Run complete validation of the migration."""
        print("🔍 Starting migration validation...")
        
        # Check Python files
        self._check_python_files()
        
        # Check imports
        self._check_imports()
        
        # Check API endpoints
        self._check_api_endpoints()
        
        # Check test files
        self._check_test_files()
        
        # Generate report
        return self._generate_report()
    
    def _check_python_files(self) -> None:
        """Check all Python files for personality references."""
        print("📁 Checking Python files...")
        
        python_files = list(self.base_path.rglob("*.py"))
        self.python_files = len(python_files)
        
        personality_files = []
        for file_path in python_files:
            # Skip files in personality directory (expected to have references)
            if "personality/" in str(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for personality references
                if self._has_personality_references(content):
                    personality_files.append(file_path)
                    self.issues.append({
                        "type": "personality_reference",
                        "file": str(file_path),
                        "line_count": len(content.splitlines())
                    })
                
                self.files_checked += 1
                
            except Exception as e:
                print(f"❌ Error reading {file_path}: {e}")
        
        print(f"📊 Found {len(personality_files)} files with personality references")
    
    def _has_personality_references(self, content: str) -> bool:
        """Check if content has personality references (excluding allowed ones)."""
        # Skip if it's just the word "personality" in comments/docstrings
        # Look for actual code references
        
        patterns = [
            r'from.*personality.*import',
            r'import.*personality',
            r'\bPersonality\w*\b',  # PersonalityType, PersonalitySelector, etc.
            r'\bpersonality\w*\b',  # personality_selector, etc.
            r'/select-personality',
            r'PersonalitySelection',
            r'get_personality',
        ]
        
        for pattern in patterns:
            if re.search(pattern, content):
                return True
        
        return False
    
    def _check_imports(self) -> None:
        """Check for deprecated imports."""
        print("📦 Checking imports...")
        
        deprecated_imports = [
            "from mindflow_backend.agents.personality",
            "from mindflow_backend.schemas.orchestration.personality",
            "from mindflow_backend.agents.interfaces.orchestrator.personality",
            "from mindflow_backend.agents.interfaces.core.personality",
        ]
        
        for file_path in self.base_path.rglob("*.py"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for deprecated in deprecated_imports:
                    if deprecated in content:
                        self.issues.append({
                            "type": "deprecated_import",
                            "file": str(file_path),
                            "import": deprecated
                        })
            except Exception:
                continue
    
    def _check_api_endpoints(self) -> None:
        """Check API endpoints for personality references."""
        print("🌐 Checking API endpoints...")
        
        api_files = list(self.base_path.rglob("*.py"))
        
        for file_path in api_files:
            if "api" in str(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if "/select-personality" in content:
                        self.issues.append({
                            "type": "deprecated_endpoint",
                            "file": str(file_path),
                            "endpoint": "/select-personality"
                        })
                except Exception:
                    continue
    
    def _check_test_files(self) -> None:
        """Check test files for personality references."""
        print("🧪 Checking test files...")
        
        test_files = list(self.base_path.rglob("*test*.py"))
        
        for file_path in test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for test-specific patterns
                if "test_personality" in content or "personality_test" in content:
                    self.issues.append({
                        "type": "test_reference",
                        "file": str(file_path),
                        "pattern": "test_personality or personality_test"
                    })
            except Exception:
                continue
    
    def _generate_report(self) -> Dict[str, any]:
        """Generate validation report."""
        report = {
            "summary": {
                "total_python_files": self.python_files,
                "files_checked": self.files_checked,
                "total_issues": len(self.issues),
                "migration_status": self._get_migration_status()
            },
            "issues_by_type": self._group_issues_by_type(),
            "critical_issues": self._get_critical_issues(),
            "recommendations": self._get_recommendations()
        }
        
        self._print_report(report)
        return report
    
    def _get_migration_status(self) -> str:
        """Determine overall migration status."""
        if len(self.issues) == 0:
            return "COMPLETE ✅"
        elif len(self.issues) < 10:
            return "MOSTLY_COMPLETE ⚠️"
        elif len(self.issues) < 50:
            return "IN_PROGRESS 🔄"
        else:
            return "NEEDS_WORK ❌"
    
    def _group_issues_by_type(self) -> Dict[str, List]:
        """Group issues by type."""
        grouped = {}
        for issue in self.issues:
            issue_type = issue.get("type", "unknown")
            if issue_type not in grouped:
                grouped[issue_type] = []
            grouped[issue_type].append(issue)
        return grouped
    
    def _get_critical_issues(self) -> List:
        """Get critical issues that need immediate attention."""
        critical = []
        for issue in self.issues:
            if issue.get("type") in ["deprecated_import", "deprecated_endpoint"]:
                critical.append(issue)
        return critical
    
    def _get_recommendations(self) -> List[str]:
        """Get recommendations based on findings."""
        recommendations = []
        
        if len(self.issues) == 0:
            recommendations.append("✅ Migration appears complete! No issues found.")
        else:
            recommendations.append("🔧 Run the migration script on remaining files:")
            recommendations.append("   python3 tools/migrate-personality-to-specialists.py --path ./python")
            
            critical_count = len(self._get_critical_issues())
            if critical_count > 0:
                recommendations.append(f"⚠️  {critical_count} critical issues need immediate attention")
            
            if len(self.issues) > 20:
                recommendations.append("📊 Consider running migration in batches to manage changes")
        
        return recommendations
    
    def _print_report(self, report: Dict[str, any]) -> None:
        """Print detailed validation report."""
        print("\n" + "="*60)
        print("📊 MIGRATION VALIDATION REPORT")
        print("="*60)
        
        summary = report["summary"]
        print(f"📁 Total Python files: {summary['total_python_files']}")
        print(f"🔍 Files checked: {summary['files_checked']}")
        print(f"⚠️  Total issues: {summary['total_issues']}")
        print(f"📈 Migration status: {summary['migration_status']}")
        
        if report["issues_by_type"]:
            print("\n📋 Issues by type:")
            for issue_type, issues in report["issues_by_type"].items():
                print(f"  {issue_type}: {len(issues)}")
        
        if report["critical_issues"]:
            print(f"\n🚨 Critical issues ({len(report['critical_issues'])}):")
            for issue in report["critical_issues"][:5]:  # Show first 5
                print(f"  📁 {issue['file']}")
            if len(report["critical_issues"]) > 5:
                print(f"  ... and {len(report['critical_issues']) - 5} more")
        
        print("\n💡 Recommendations:")
        for rec in report["recommendations"]:
            print(f"  {rec}")
        
        print("\n" + "="*60)


def main():
    """Main validation function."""
    base_path = "./python" if len(sys.argv) < 2 else sys.argv[1]
    
    validator = MigrationValidator(base_path)
    report = validator.validate_migration()
    
    # Exit with error code if there are critical issues
    if len(report["critical_issues"]) > 0:
        print("\n❌ Critical issues found. Please address them before proceeding.")
        sys.exit(1)
    elif len(report["issues"]) > 0:
        print("\n⚠️  Issues found. Review and address as needed.")
        sys.exit(0)
    else:
        print("\n✅ Migration validation passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
