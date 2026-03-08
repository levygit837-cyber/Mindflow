#!/usr/bin/env python3
"""
Script to audit schema coverage for OmniMind exception system.

This script analyzes the gap between exceptions and their corresponding schemas,
providing detailed coverage reports and gap analysis.
"""

from __future__ import annotations

import ast
import sys
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass, asdict
import importlib.util


@dataclass
class ExceptionInfo:
    """Information about an exception class."""
    name: str
    module: str
    file_path: str
    line_number: int
    base_classes: List[str]
    is_abstract: bool = False
    docstring: str = ""


@dataclass
class SchemaInfo:
    """Information about a schema class."""
    name: str
    module: str
    file_path: str
    line_number: int
    base_classes: List[str]
    fields: List[str]
    is_abstract: bool = False
    docstring: str = ""


@dataclass
class CoverageReport:
    """Coverage report data."""
    total_exceptions: int
    total_schemas: int
    coverage_percentage: float
    exceptions_by_category: Dict[str, List[ExceptionInfo]]
    schemas_by_category: Dict[str, List[SchemaInfo]]
    missing_schemas: List[Tuple[str, ExceptionInfo]]
    coverage_by_category: Dict[str, float]


class ExceptionAuditor:
    """Audits exception schema coverage."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.exceptions_dir = project_root / "python" / "mindflow_backend" / "exceptions"
        self.schemas_dir = project_root / "python" / "mindflow_backend" / "schemas" / "errors"
        
    def analyze_exceptions(self) -> Dict[str, List[ExceptionInfo]]:
        """Analyze all exception classes."""
        exceptions = {}
        
        for category_dir in self.exceptions_dir.iterdir():
            if category_dir.is_dir() and category_dir.name != "__pycache__":
                category_name = category_dir.name
                exceptions[category_name] = []
                
                for py_file in category_dir.glob("*.py"):
                    if py_file.name == "__init__.py":
                        continue
                    
                    try:
                        file_exceptions = self._extract_exceptions_from_file(py_file, category_name)
                        exceptions[category_name].extend(file_exceptions)
                    except Exception as e:
                        print(f"Error processing {py_file}: {e}")
        
        # Also check root exceptions files
        for py_file in self.exceptions_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            
            try:
                file_exceptions = self._extract_exceptions_from_file(py_file, "base")
                if "base" not in exceptions:
                    exceptions["base"] = []
                exceptions["base"].extend(file_exceptions)
            except Exception as e:
                print(f"Error processing {py_file}: {e}")
        
        return exceptions
    
    def _extract_exceptions_from_file(self, file_path: Path, category: str) -> List[ExceptionInfo]:
        """Extract exception classes from a Python file."""
        exceptions = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return exceptions
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it's an exception class
                if self._is_exception_class(node):
                    exception_info = ExceptionInfo(
                        name=node.name,
                        module=f"mindflow_backend.exceptions.{category}.{file_path.stem}",
                        file_path=str(file_path),
                        line_number=node.lineno,
                        base_classes=[self._get_base_class_name(base) for base in node.bases],
                        docstring=ast.get_docstring(node) or "",
                        is_abstract=self._is_abstract_class(node)
                    )
                    exceptions.append(exception_info)
        
        return exceptions
    
    def _is_exception_class(self, node: ast.ClassDef) -> bool:
        """Check if a class is an exception class."""
        # Check if inherits from Exception or any MindFlow exception
        for base in node.bases:
            base_name = self._get_base_class_name(base)
            if base_name in ["Exception", "MindFlowError", "SystemError", "BusinessLogicError"]:
                return True
        return False
    
    def _get_base_class_name(self, base: ast.AST) -> str:
        """Get the name of a base class."""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return base.attr
        return "Unknown"
    
    def _is_abstract_class(self, node: ast.ClassDef) -> bool:
        """Check if a class is abstract."""
        # Simple heuristic: check for @abstractmethod or ABC inheritance
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
                return True
        
        for base in node.bases:
            base_name = self._get_base_class_name(base)
            if base_name == "ABC":
                return True
        
        return False
    
    def analyze_schemas(self) -> Dict[str, List[SchemaInfo]]:
        """Analyze all schema classes."""
        schemas = {}
        
        for schema_file in self.schemas_dir.glob("*.py"):
            if schema_file.name == "__init__.py":
                continue
            
            category_name = schema_file.stem.replace("_errors", "")
            schemas[category_name] = []
            
            try:
                file_schemas = self._extract_schemas_from_file(schema_file, category_name)
                schemas[category_name].extend(file_schemas)
            except Exception as e:
                print(f"Error processing schema file {schema_file}: {e}")
        
        # Also check for base_exceptions.py and api_errors.py
        for schema_file in self.schemas_dir.glob("*_exceptions.py"):
            category_name = "base"  # All exception schemas go to base category
            if category_name not in schemas:
                schemas[category_name] = []
            
            try:
                file_schemas = self._extract_schemas_from_file(schema_file, category_name)
                schemas[category_name].extend(file_schemas)
            except Exception as e:
                print(f"Error processing exception schema file {schema_file}: {e}")
        
        # Check api_errors.py
        api_errors_file = self.schemas_dir / "api_errors.py"
        if api_errors_file.exists():
            category_name = "api"
            if category_name not in schemas:
                schemas[category_name] = []
            
            try:
                file_schemas = self._extract_schemas_from_file(api_errors_file, category_name)
                schemas[category_name].extend(file_schemas)
            except Exception as e:
                print(f"Error processing API schema file {api_errors_file}: {e}")
        
        return schemas
    
    def _extract_schemas_from_file(self, file_path: Path, category: str) -> List[SchemaInfo]:
        """Extract schema classes from a Python file."""
        schemas = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return schemas
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it's a schema class (inherits from BaseModel)
                if self._is_schema_class(node):
                    schema_info = SchemaInfo(
                        name=node.name,
                        module=f"mindflow_backend.schemas.errors.{file_path.stem}",
                        file_path=str(file_path),
                        line_number=node.lineno,
                        base_classes=[self._get_base_class_name(base) for base in node.bases],
                        fields=self._extract_fields(node),
                        docstring=ast.get_docstring(node) or "",
                        is_abstract=self._is_abstract_class(node)
                    )
                    schemas.append(schema_info)
        
        return schemas
    
    def _is_schema_class(self, node: ast.ClassDef) -> bool:
        """Check if a class is a schema class."""
        for base in node.bases:
            base_name = self._get_base_class_name(base)
            if base_name in ["BaseModel", "ErrorSchema"]:
                return True
        return False
    
    def _extract_fields(self, node: ast.ClassDef) -> List[str]:
        """Extract field names from a schema class."""
        fields = []
        
        for item in node.body:
            if isinstance(item, ast.AnnAssign):
                if isinstance(item.target, ast.Name):
                    fields.append(item.target.id)
        
        return fields
    
    def generate_coverage_report(self) -> CoverageReport:
        """Generate comprehensive coverage report."""
        exceptions = self.analyze_exceptions()
        schemas = self.analyze_schemas()
        
        # Flatten all exceptions and schemas
        all_exceptions = []
        for category_excs in exceptions.values():
            all_exceptions.extend(category_excs)
        
        all_schemas = []
        for category_schemas in schemas.values():
            all_schemas.extend(category_schemas)
        
        # Find missing schemas
        missing_schemas = []
        schema_names = {schema.name for schema in all_schemas}
        
        for exc in all_exceptions:
            expected_schema_name = f"{exc.name}Schema"
            if expected_schema_name not in schema_names:
                missing_schemas.append((expected_schema_name, exc))
        
        # Calculate coverage by category
        coverage_by_category = {}
        for category, category_exceptions in exceptions.items():
            category_schema_names = {
                schema.name for schema in schemas.get(category, [])
            }
            
            covered = 0
            for exc in category_exceptions:
                expected_schema_name = f"{exc.name}Schema"
                if expected_schema_name in category_schema_names:
                    covered += 1
            
            total = len(category_exceptions)
            coverage = (covered / total * 100) if total > 0 else 0
            coverage_by_category[category] = coverage
        
        total_exceptions = len(all_exceptions)
        total_schemas = len(all_schemas)
        coverage_percentage = (total_schemas / total_exceptions * 100) if total_exceptions > 0 else 0
        
        return CoverageReport(
            total_exceptions=total_exceptions,
            total_schemas=total_schemas,
            coverage_percentage=coverage_percentage,
            exceptions_by_category=exceptions,
            schemas_by_category=schemas,
            missing_schemas=missing_schemas,
            coverage_by_category=coverage_by_category
        )
    
    def export_report_json(self, report: CoverageReport, output_path: Path) -> None:
        """Export report as JSON."""
        # Convert dataclasses to dicts for JSON serialization
        report_dict = asdict(report)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
    
    def export_report_csv(self, report: CoverageReport, output_path: Path) -> None:
        """Export coverage summary as CSV."""
        import csv
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(['Category', 'Total Exceptions', 'Total Schemas', 'Coverage %'])
            
            # Write data
            for category, coverage in report.coverage_by_category.items():
                total_excs = len(report.exceptions_by_category.get(category, []))
                total_schemas = len(report.schemas_by_category.get(category, []))
                writer.writerow([category, total_excs, total_schemas, f"{coverage:.1f}%"])
            
            # Write totals
            writer.writerow(['TOTAL', report.total_exceptions, report.total_schemas, f"{report.coverage_percentage:.1f}%"])
    
    def print_summary(self, report: CoverageReport) -> None:
        """Print coverage summary to console."""
        print("\n" + "="*60)
        print("🔍 OMNIMIND EXCEPTION SCHEMA COVERAGE REPORT")
        print("="*60)
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total Exceptions: {report.total_exceptions}")
        print(f"   Total Schemas: {report.total_schemas}")
        print(f"   Overall Coverage: {report.coverage_percentage:.1f}%")
        
        print(f"\n📈 COVERAGE BY CATEGORY:")
        for category, coverage in sorted(report.coverage_by_category.items()):
            total_excs = len(report.exceptions_by_category.get(category, []))
            total_schemas = len(report.schemas_by_category.get(category, []))
            status = "✅" if coverage >= 80 else "⚠️" if coverage >= 50 else "❌"
            print(f"   {status} {category}: {coverage:.1f}% ({total_schemas}/{total_excs})")
        
        print(f"\n❌ MISSING SCHEMAS ({len(report.missing_schemas)}):")
        for schema_name, exc_info in sorted(report.missing_schemas):
            print(f"   - {schema_name} (from {exc_info.module})")
        
        print(f"\n🎯 RECOMMENDATIONS:")
        if report.coverage_percentage < 50:
            print("   - CRITICAL: Less than 50% coverage - immediate action required")
        elif report.coverage_percentage < 80:
            print("   - HIGH: Coverage below 80% - prioritize implementation")
        else:
            print("   - GOOD: Coverage above 80% - focus on remaining gaps")
        
        print(f"\n📋 NEXT STEPS:")
        print(f"   1. Implement missing schemas in priority order")
        print(f"   2. Create error handler interfaces")
        print(f"   3. Integrate patterns and enhance developer experience")
        
        print("\n" + "="*60)


def main():
    """Main function."""
    project_root = Path(__file__).parent.parent
    
    auditor = ExceptionAuditor(project_root)
    
    print("🔍 Analyzing exception schema coverage...")
    report = auditor.generate_coverage_report()
    
    # Print summary
    auditor.print_summary(report)
    
    # Export reports
    output_dir = project_root / "docs" / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # JSON report
    json_path = output_dir / "schema_coverage_report.json"
    auditor.export_report_json(report, json_path)
    print(f"\n📄 JSON report exported to: {json_path}")
    
    # CSV report
    csv_path = output_dir / "schema_coverage_summary.csv"
    auditor.export_report_csv(report, csv_path)
    print(f"📊 CSV report exported to: {csv_path}")
    
    # Detailed markdown report
    md_path = output_dir / "schema_gap_analysis.md"
    generate_markdown_report(report, md_path)
    print(f"📝 Markdown report exported to: {md_path}")
    
    return 0 if report.coverage_percentage >= 80 else 1


def generate_markdown_report(report: CoverageReport, output_path: Path) -> None:
    """Generate detailed markdown report."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# OmniMind Exception Schema Gap Analysis\n\n")
        
        f.write("## Executive Summary\n\n")
        f.write(f"- **Total Exceptions**: {report.total_exceptions}\n")
        f.write(f"- **Total Schemas**: {report.total_schemas}\n")
        f.write(f"- **Overall Coverage**: {report.coverage_percentage:.1f}%\n")
        f.write(f"- **Missing Schemas**: {len(report.missing_schemas)}\n\n")
        
        f.write("## Coverage by Category\n\n")
        f.write("| Category | Exceptions | Schemas | Coverage | Status |\n")
        f.write("|----------|------------|---------|----------|--------|\n")
        
        for category, coverage in sorted(report.coverage_by_category.items()):
            total_excs = len(report.exceptions_by_category.get(category, []))
            total_schemas = len(report.schemas_by_category.get(category, []))
            status = "✅ Good" if coverage >= 80 else "⚠️ Medium" if coverage >= 50 else "❌ Critical"
            f.write(f"| {category} | {total_excs} | {total_schemas} | {coverage:.1f}% | {status} |\n")
        
        f.write(f"\n## Missing Schemas\n\n")
        f.write("The following schemas are missing and need to be implemented:\n\n")
        
        for schema_name, exc_info in sorted(report.missing_schemas):
            f.write(f"### {schema_name}\n")
            f.write(f"- **Exception**: {exc_info.name}\n")
            f.write(f"- **Module**: {exc_info.module}\n")
            f.write(f"- **File**: {exc_info.file_path}\n")
            f.write(f"- **Line**: {exc_info.line_number}\n")
            if exc_info.docstring:
                f.write(f"- **Description**: {exc_info.docstring}\n")
            f.write("\n")
        
        f.write("## Implementation Priority\n\n")
        
        # Sort by criticality
        critical_categories = [cat for cat, cov in report.coverage_by_category.items() if cov == 0]
        medium_categories = [cat for cat, cov in report.coverage_by_category.items() if 0 < cov < 80]
        
        if critical_categories:
            f.write("### 🔴 Critical Priority (0% coverage)\n")
            for category in critical_categories:
                f.write(f"- **{category}**: All schemas missing\n")
            f.write("\n")
        
        if medium_categories:
            f.write("### 🟡 High Priority (partial coverage)\n")
            for category in medium_categories:
                f.write(f"- **{category}**: {report.coverage_by_category[category]:.1f}% coverage\n")
            f.write("\n")
        
        f.write("## Recommendations\n\n")
        f.write("1. **Immediate Action**: Implement schemas for critical categories\n")
        f.write("2. **Type Safety**: Create interface contracts for all error types\n")
        f.write("3. **Developer Experience**: Implement builder patterns and templates\n")
        f.write("4. **Testing**: Ensure 100% test coverage for new schemas\n")
        f.write("5. **Documentation**: Update API documentation with new schemas\n")


if __name__ == "__main__":
    sys.exit(main())
