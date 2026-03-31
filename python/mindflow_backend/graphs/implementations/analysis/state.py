"""State definition for the Codebase Analysis Graph.

Defines the shared state that flows between all nodes in the graph,
tracking discovery progress, analysis results, and validation metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class AnalysisPhase(Enum):
    """Current phase of codebase analysis."""
    DISCOVERY = "discovery"
    SKELETON = "skeleton"
    DEEP_ANALYSIS = "deep_analysis"
    INDEX_TO_MEMORY = "index_to_memory"
    VALIDATION = "validation"
    LOOP = "loop"
    REPORT = "report"


@dataclass
class CodebaseAnalysisState:
    """State shared between all nodes of the Codebase Analysis Graph.
    
    This state accumulates results as the graph iterates through
    the codebase, tracking what has been discovered, analyzed,
    and indexed.
    """
    
    # === Configuration ===
    target_path: str = "."
    scope: str = "full"  # "full", "module", "feature"
    project_id: str = ""
    min_coverage: float = 95.0
    max_iterations: int = 10
    timeout_seconds: float = 30.0
    
    # === Flow Control ===
    current_phase: AnalysisPhase = AnalysisPhase.DISCOVERY
    iteration_count: int = 0
    should_continue: bool = True
    
    # === Discovery Phase ===
    discovered_directories: list[str] = field(default_factory=list)
    discovered_files: list[str] = field(default_factory=list)
    discovery_complete: bool = False
    
    # === Skeleton Phase ===
    analyzed_files: dict[str, dict[str, Any]] = field(default_factory=dict)
    pending_files: list[str] = field(default_factory=list)
    skeleton_complete: bool = False
    
    # === Deep Analysis Phase ===
    critical_files: list[str] = field(default_factory=list)
    blast_radius_map: dict[str, list[str]] = field(default_factory=dict)
    patterns_found: dict[str, int] = field(default_factory=dict)
    deep_analysis_complete: bool = False
    
    # === Index to Memory Phase ===
    indexed_elements: list[dict[str, Any]] = field(default_factory=list)
    memory_stats: dict[str, int] = field(default_factory=dict)
    index_complete: bool = False
    
    # === Validation Phase ===
    coverage_percentage: float = 0.0
    function_coverage: float = 0.0
    class_coverage: float = 0.0
    validation_passed: bool = False
    missing_files: list[str] = field(default_factory=list)
    failed_files: list[str] = field(default_factory=list)
    
    # === Report ===
    report_markdown: str = ""
    
    # === Metrics ===
    timeouts_count: int = 0
    fallbacks_count: int = 0
    total_execution_time: float = 0.0
    iteration_times: list[float] = field(default_factory=list)
    
    # === Errors ===
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    # === Timestamps ===
    started_at: str = ""
    completed_at: str = ""
    
    def start(self) -> None:
        """Mark analysis as started."""
        self.started_at = datetime.now().isoformat()
    
    def complete(self) -> None:
        """Mark analysis as completed."""
        self.completed_at = datetime.now().isoformat()
    
    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(f"[Iteration {self.iteration_count}] {error}")
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(f"[Iteration {self.iteration_count}] {warning}")
    
    def record_timeout(self) -> None:
        """Record a timeout event."""
        self.timeouts_count += 1
    
    def record_fallback(self) -> None:
        """Record a fallback usage."""
        self.fallbacks_count += 1
    
    @property
    def total_files_analyzed(self) -> int:
        """Total number of files fully analyzed."""
        return len(self.analyzed_files)
    
    @property
    def total_files_discovered(self) -> int:
        """Total number of files discovered."""
        return len(self.discovered_files)
    
    @property
    def analysis_progress(self) -> float:
        """Calculate analysis progress percentage."""
        if self.total_files_discovered == 0:
            return 0.0
        return (self.total_files_analyzed / self.total_files_discovered) * 100
    
    @property
    def is_complete(self) -> bool:
        """Check if analysis is complete."""
        return self.validation_passed or self.iteration_count >= self.max_iterations
    
    def to_summary(self) -> dict[str, Any]:
        """Generate a summary of the current state."""
        return {
            "phase": self.current_phase.value,
            "iteration": self.iteration_count,
            "files_discovered": self.total_files_discovered,
            "files_analyzed": self.total_files_analyzed,
            "coverage": f"{self.coverage_percentage:.1f}%",
            "timeouts": self.timeouts_count,
            "fallbacks": self.fallbacks_count,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "complete": self.is_complete,
        }