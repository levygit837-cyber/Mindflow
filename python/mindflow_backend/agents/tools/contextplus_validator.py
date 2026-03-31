"""Context+ Validator — Coverage and precision validation for codebase analysis.

Validates that the Agent Analyst has achieved minimum coverage and precision
when mapping a codebase. Tracks files analyzed, functions documented,
and ensures quality standards are met.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CoverageStatus(Enum):
    """Status of coverage for a file or module."""
    PENDING = "pending"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class FileCoverage:
    """Coverage information for a single file."""
    
    path: str
    status: CoverageStatus = CoverageStatus.PENDING
    total_functions: int = 0
    documented_functions: int = 0
    total_classes: int = 0
    documented_classes: int = 0
    total_methods: int = 0
    documented_methods: int = 0
    dependencies_mapped: bool = False
    patterns_identified: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    
    @property
    def function_coverage(self) -> float:
        """Calculate function documentation coverage."""
        if self.total_functions == 0:
            return 1.0
        return self.documented_functions / self.total_functions
    
    @property
    def class_coverage(self) -> float:
        """Calculate class documentation coverage."""
        if self.total_classes == 0:
            return 1.0
        return self.documented_classes / self.total_classes
    
    @property
    def method_coverage(self) -> float:
        """Calculate method documentation coverage."""
        if self.total_methods == 0:
            return 1.0
        return self.documented_methods / self.total_methods
    
    @property
    def overall_coverage(self) -> float:
        """Calculate overall coverage for this file."""
        total_items = (
            self.total_functions + self.total_classes + self.total_methods
        )
        if total_items == 0:
            return 1.0
        
        documented_items = (
            self.documented_functions
            + self.documented_classes
            + self.documented_methods
        )
        return documented_items / total_items


@dataclass
class ValidationConfig:
    """Configuration for validation rules."""
    
    min_coverage_percentage: float = 95.0
    min_function_coverage: float = 90.0
    min_class_coverage: float = 95.0
    max_timeout_rate: float = 5.0
    min_confidence_score: float = 0.7
    require_cross_validation: bool = True
    max_iterations_per_file: int = 3
    
    # File patterns to always analyze
    required_patterns: list[str] = field(
        default_factory=lambda: ["*.py", "*.ts"]
    )
    
    # File patterns to skip
    skip_patterns: list[str] = field(
        default_factory=lambda: [
            "*test*",
            "*__pycache__*",
            "*.pyc",
            "node_modules/*",
            ".git/*",
            "*.min.js",
            "*.min.css",
        ]
    )


@dataclass
class ValidationReport:
    """Complete validation report."""
    
    total_files_discovered: int = 0
    files_analyzed: int = 0
    files_partial: int = 0
    files_failed: int = 0
    files_skipped: int = 0
    
    total_functions: int = 0
    documented_functions: int = 0
    total_classes: int = 0
    documented_classes: int = 0
    
    timeout_count: int = 0
    fallback_count: int = 0
    
    patterns_found: dict[str, int] = field(default_factory=dict)
    modules_mapped: list[str] = field(default_factory=list)
    
    file_coverages: dict[str, FileCoverage] = field(default_factory=dict)
    
    @property
    def file_coverage_percentage(self) -> float:
        """Calculate percentage of files fully analyzed."""
        if self.total_files_discovered == 0:
            return 0.0
        return (self.files_analyzed / self.total_files_discovered) * 100
    
    @property
    def function_coverage_percentage(self) -> float:
        """Calculate percentage of functions documented."""
        if self.total_functions == 0:
            return 100.0
        return (self.documented_functions / self.total_functions) * 100
    
    @property
    def class_coverage_percentage(self) -> float:
        """Calculate percentage of classes documented."""
        if self.total_classes == 0:
            return 100.0
        return (self.documented_classes / self.total_classes) * 100
    
    @property
    def overall_coverage(self) -> float:
        """Calculate weighted overall coverage."""
        file_weight = 0.4
        func_weight = 0.35
        class_weight = 0.25
        
        return (
            self.file_coverage_percentage * file_weight
            + self.function_coverage_percentage * func_weight
            + self.class_coverage_percentage * class_weight
        )
    
    def to_markdown(self) -> str:
        """Generate Markdown report."""
        sections = [
            "# Codebase Analysis Validation Report",
            "",
            "## Coverage Summary",
            "",
            f"| Metric | Value | Target | Status |",
            f"|--------|-------|--------|--------|",
            f"| Files Analyzed | {self.files_analyzed}/{self.total_files_discovered} "
            f"({self.file_coverage_percentage:.1f}%) | 95% | "
            f"{'✅' if self.file_coverage_percentage >= 95 else '❌'} |",
            f"| Functions Documented | {self.documented_functions}/{self.total_functions} "
            f"({self.function_coverage_percentage:.1f}%) | 90% | "
            f"{'✅' if self.function_coverage_percentage >= 90 else '❌'} |",
            f"| Classes Documented | {self.documented_classes}/{self.total_classes} "
            f"({self.class_coverage_percentage:.1f}%) | 95% | "
            f"{'✅' if self.class_coverage_percentage >= 95 else '❌'} |",
            f"| **Overall Coverage** | **{self.overall_coverage:.1f}%** | **95%** | "
            f"{'✅' if self.overall_coverage >= 95 else '❌'} |",
            "",
            "## Reliability Metrics",
            "",
            f"- Timeouts: {self.timeout_count}",
            f"- Fallbacks: {self.fallback_count}",
            f"- Files Failed: {self.files_failed}",
            f"- Files Skipped: {self.files_skipped}",
            "",
            "## Modules Mapped",
            "",
        ]
        
        for module in self.modules_mapped:
            sections.append(f"- {module}")
        
        sections.extend([
            "",
            "## Patterns Identified",
            "",
        ])
        
        for pattern, count in sorted(
            self.patterns_found.items(), key=lambda x: -x[1]
        ):
            sections.append(f"- {pattern}: {count} occurrences")
        
        sections.extend([
            "",
            "## Files Needing Attention",
            "",
        ])
        
        for path, coverage in self.file_coverages.items():
            if coverage.status in (
                CoverageStatus.FAILED,
                CoverageStatus.PARTIAL,
                CoverageStatus.PENDING,
            ):
                sections.append(
                    f"- **{path}** [{coverage.status.value}] "
                    f"({coverage.overall_coverage:.0%} coverage)"
                )
                for note in coverage.notes:
                    sections.append(f"  - {note}")
        
        return "\n".join(sections)


class ContextPlusValidator:
    """Validator for codebase analysis coverage and precision.
    
    Tracks analysis progress and validates that minimum coverage
    thresholds are met before considering the analysis complete.
    
    Usage:
        validator = ContextPlusValidator()
        validator.register_discovered_files(["file1.py", "file2.py"])
        validator.mark_file_analyzed("file1.py", functions=10, classes=2)
        report = validator.validate()
    """
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        self.config = config or ValidationConfig()
        self.file_coverages: dict[str, FileCoverage] = {}
        self.timeout_count: int = 0
        self.fallback_count: int = 0
        self.patterns_found: dict[str, int] = {}
        self.modules_mapped: list[str] = []
    
    def register_discovered_files(self, file_paths: list[str]) -> None:
        """Register files discovered during exploration."""
        for path in file_paths:
            if self._should_skip(path):
                continue
            
            if path not in self.file_coverages:
                self.file_coverages[path] = FileCoverage(path=path)
    
    def _should_skip(self, file_path: str) -> bool:
        """Check if file should be skipped based on patterns."""
        for pattern in self.config.skip_patterns:
            if Path(file_path).match(pattern):
                return True
        return False
    
    def mark_file_analyzing(self, file_path: str) -> None:
        """Mark file as currently being analyzed."""
        if file_path in self.file_coverages:
            self.file_coverages[file_path].status = CoverageStatus.ANALYZING
    
    def mark_file_analyzed(
        self,
        file_path: str,
        functions: int = 0,
        classes: int = 0,
        methods: int = 0,
        documented_functions: Optional[int] = None,
        documented_classes: Optional[int] = None,
        documented_methods: Optional[int] = None,
        patterns: Optional[list[str]] = None,
    ) -> None:
        """Mark file as fully analyzed with coverage details."""
        if file_path not in self.file_coverages:
            self.file_coverages[file_path] = FileCoverage(path=file_path)
        
        coverage = self.file_coverages[file_path]
        coverage.status = CoverageStatus.ANALYZED
        coverage.total_functions = functions
        coverage.total_classes = classes
        coverage.total_methods = methods
        coverage.documented_functions = (
            documented_functions if documented_functions is not None else functions
        )
        coverage.documented_classes = (
            documented_classes if documented_classes is not None else classes
        )
        coverage.documented_methods = (
            documented_methods if documented_methods is not None else methods
        )
        
        if patterns:
            coverage.patterns_identified = patterns
            for pattern in patterns:
                self.patterns_found[pattern] = (
                    self.patterns_found.get(pattern, 0) + 1
                )
    
    def mark_file_partial(
        self,
        file_path: str,
        reason: str,
        functions: int = 0,
        documented_functions: int = 0,
    ) -> None:
        """Mark file as partially analyzed."""
        if file_path not in self.file_coverages:
            self.file_coverages[file_path] = FileCoverage(path=file_path)
        
        coverage = self.file_coverages[file_path]
        coverage.status = CoverageStatus.PARTIAL
        coverage.total_functions = functions
        coverage.documented_functions = documented_functions
        coverage.notes.append(reason)
    
    def mark_file_failed(self, file_path: str, reason: str) -> None:
        """Mark file analysis as failed."""
        if file_path not in self.file_coverages:
            self.file_coverages[file_path] = FileCoverage(path=file_path)
        
        self.file_coverages[file_path].status = CoverageStatus.FAILED
        self.file_coverages[file_path].notes.append(reason)
    
    def mark_file_skipped(self, file_path: str, reason: str) -> None:
        """Mark file as intentionally skipped."""
        if file_path not in self.file_coverages:
            self.file_coverages[file_path] = FileCoverage(path=file_path)
        
        self.file_coverages[file_path].status = CoverageStatus.SKIPPED
        self.file_coverages[file_path].notes.append(reason)
    
    def record_timeout(self) -> None:
        """Record a timeout event."""
        self.timeout_count += 1
    
    def record_fallback(self) -> None:
        """Record a fallback usage."""
        self.fallback_count += 1
    
    def register_module(self, module_name: str) -> None:
        """Register a module as mapped."""
        if module_name not in self.modules_mapped:
            self.modules_mapped.append(module_name)
    
    def validate(self) -> tuple[bool, ValidationReport]:
        """Validate coverage against configuration thresholds.
        
        Returns:
            Tuple of (passed, report)
        """
        report = ValidationReport()
        
        # Count totals
        report.total_files_discovered = len(self.file_coverages)
        report.timeout_count = self.timeout_count
        report.fallback_count = self.fallback_count
        report.patterns_found = dict(self.patterns_found)
        report.modules_mapped = list(self.modules_mapped)
        report.file_coverages = dict(self.file_coverages)
        
        # Count by status
        for coverage in self.file_coverages.values():
            if coverage.status == CoverageStatus.ANALYZED:
                report.files_analyzed += 1
            elif coverage.status == CoverageStatus.PARTIAL:
                report.files_partial += 1
            elif coverage.status == CoverageStatus.FAILED:
                report.files_failed += 1
            elif coverage.status == CoverageStatus.SKIPPED:
                report.files_skipped += 1
            
            report.total_functions += coverage.total_functions
            report.documented_functions += coverage.documented_functions
            report.total_classes += coverage.total_classes
            report.documented_classes += coverage.documented_classes
        
        # Check thresholds
        passed = True
        reasons = []
        
        if report.file_coverage_percentage < self.config.min_coverage_percentage:
            passed = False
            reasons.append(
                f"File coverage {report.file_coverage_percentage:.1f}% "
                f"< {self.config.min_coverage_percentage}%"
            )
        
        if report.function_coverage_percentage < self.config.min_function_coverage:
            passed = False
            reasons.append(
                f"Function coverage {report.function_coverage_percentage:.1f}% "
                f"< {self.config.min_function_coverage}%"
            )
        
        if report.class_coverage_percentage < self.config.min_class_coverage:
            passed = False
            reasons.append(
                f"Class coverage {report.class_coverage_percentage:.1f}% "
                f"< {self.config.min_class_coverage}%"
            )
        
        if not passed:
            logger.warning(
                f"Validation FAILED: {'; '.join(reasons)}"
            )
        else:
            logger.info(
                f"Validation PASSED: "
                f"{report.overall_coverage:.1f}% overall coverage"
            )
        
        return passed, report
    
    def get_missing_files(self) -> list[str]:
        """Get list of files that haven't been fully analyzed."""
        return [
            path
            for path, coverage in self.file_coverages.items()
            if coverage.status in (
                CoverageStatus.PENDING,
                CoverageStatus.ANALYZING,
            )
        ]
    
    def get_failed_files(self) -> list[str]:
        """Get list of files that failed analysis."""
        return [
            path
            for path, coverage in self.file_coverages.items()
            if coverage.status == CoverageStatus.FAILED
        ]
    
    def get_progress_summary(self) -> dict:
        """Get current progress summary."""
        total = len(self.file_coverages)
        analyzed = sum(
            1
            for c in self.file_coverages.values()
            if c.status == CoverageStatus.ANALYZED
        )
        
        return {
            "total_files": total,
            "analyzed": analyzed,
            "pending": len(self.get_missing_files()),
            "failed": len(self.get_failed_files()),
            "coverage_percentage": (
                (analyzed / total * 100) if total > 0 else 0
            ),
            "timeouts": self.timeout_count,
            "fallbacks": self.fallback_count,
        }