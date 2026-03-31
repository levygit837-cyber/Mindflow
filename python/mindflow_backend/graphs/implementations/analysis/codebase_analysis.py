"""Codebase Analysis Graph — Main graph implementation.

Implements a LangGraph that iteratively explores a codebase using Context+ tools,
with automatic fallback, coverage validation, and Project Memory indexing.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional

from langgraph.graph import StateGraph, END

from mindflow_backend.graphs.implementations.analysis.state import (
    AnalysisPhase,
    CodebaseAnalysisState,
)

logger = logging.getLogger(__name__)


# ============================================================
# NODE IMPLEMENTATIONS
# ============================================================

async def discovery_node(
    state: CodebaseAnalysisState,
    contextplus_executor: Callable,
    fallback_engine: Any,
) -> CodebaseAnalysisState:
    """Phase 1: Top-down discovery of project structure.
    
    Uses get_context_tree to map directories and files,
    with fallback to structural exploration if semantic fails.
    """
    logger.info(f"[Discovery] Starting exploration of {state.target_path}")
    state.current_phase = AnalysisPhase.DISCOVERY
    
    # Step 1: General structure
    result = await fallback_engine.execute_with_fallback(
        tool_name="get_context_tree",
        params={
            "target_path": state.target_path,
            "depth_limit": 2,
            "include_symbols": True,
        },
        tool_executor=contextplus_executor,
    )
    
    if result.fallback_used:
        state.record_fallback()
    
    if not result.success:
        state.add_error(f"Discovery failed: {result.error}")
        state.record_timeout() if "timeout" in (result.error or "") else None
        state.discovery_complete = True
        state.current_phase = AnalysisPhase.SKELETON
        return state
    
    # Extract directories and files from result
    tree_data = result.data
    state.discovered_directories = _extract_directories(tree_data)
    state.discovered_files = _extract_files(tree_data)
    
    # Step 2: Deep discovery for each directory
    for directory in state.discovered_directories:
        dir_result = await fallback_engine.execute_with_fallback(
            tool_name="get_context_tree",
            params={
                "target_path": directory,
                "depth_limit": 3,
                "include_symbols": True,
            },
            tool_executor=contextplus_executor,
        )
        
        if dir_result.success:
            new_files = _extract_files(dir_result.data)
            state.discovered_files.extend(new_files)
        else:
            state.add_warning(f"Could not explore {directory}: {dir_result.error}")
    
    # Deduplicate
    state.discovered_files = list(set(state.discovered_files))
    
    logger.info(
        f"[Discovery] Found {len(state.discovered_directories)} directories, "
        f"{len(state.discovered_files)} files"
    )
    
    state.discovery_complete = True
    state.current_phase = AnalysisPhase.SKELETON
    return state


async def skeleton_node(
    state: CodebaseAnalysisState,
    contextplus_executor: Callable,
    fallback_engine: Any,
) -> CodebaseAnalysisState:
    """Phase 2: Extract skeletons from all files.
    
    Uses get_file_skeleton to extract function/class signatures
    without reading full source code.
    """
    logger.info(f"[Skeleton] Processing {len(state.pending_files or state.discovered_files)} files")
    state.current_phase = AnalysisPhase.SKELETON
    
    files_to_process = state.pending_files or state.discovered_files
    processed = 0
    
    for file_path in files_to_process:
        # Skip already analyzed
        if file_path in state.analyzed_files:
            continue
        
        result = await fallback_engine.execute_with_fallback(
            tool_name="get_file_skeleton",
            params={"file_path": file_path},
            tool_executor=contextplus_executor,
        )
        
        if result.fallback_used:
            state.record_fallback()
        
        if result.success:
            state.analyzed_files[file_path] = {
                "functions": _extract_functions(result.data),
                "classes": _extract_classes(result.data),
                "imports": _extract_imports(result.data),
                "patterns": _detect_patterns(result.data),
            }
            processed += 1
        else:
            state.add_warning(f"Skeleton failed for {file_path}: {result.error}")
            state.failed_files.append(file_path)
    
    # Update pending
    state.pending_files = [
        f for f in state.discovered_files if f not in state.analyzed_files
    ]
    
    logger.info(
        f"[Skeleton] Analyzed {processed} files. "
        f"Total: {state.total_files_analyzed}/{state.total_files_discovered}"
    )
    
    state.skeleton_complete = True
    state.current_phase = AnalysisPhase.DEEP_ANALYSIS
    return state


async def deep_analysis_node(
    state: CodebaseAnalysisState,
    contextplus_executor: Callable,
    fallback_engine: Any,
) -> CodebaseAnalysisState:
    """Phase 3: Deep analysis of critical files.
    
    Identifies critical files (high complexity, many dependencies)
    and performs blast radius analysis.
    """
    logger.info("[DeepAnalysis] Analyzing critical files")
    state.current_phase = AnalysisPhase.DEEP_ANALYSIS
    
    # Identify critical files
    state.critical_files = _identify_critical_files(state.analyzed_files)
    
    for file_path in state.critical_files[:10]:
        file_data = state.analyzed_files.get(file_path, {})
        
        # Blast radius for key functions
        for func in file_data.get("functions", [])[:3]:
            result = await fallback_engine.execute_with_fallback(
                tool_name="get_blast_radius",
                params={
                    "symbol_name": func["name"],
                    "file_context": file_path,
                },
                tool_executor=contextplus_executor,
            )
            
            if result.success:
                state.blast_radius_map[func["name"]] = result.data
            elif result.fallback_used:
                state.record_fallback()
    
    # Count patterns
    for file_data in state.analyzed_files.values():
        for pattern in file_data.get("patterns", []):
            state.patterns_found[pattern] = state.patterns_found.get(pattern, 0) + 1
    
    logger.info(
        f"[DeepAnalysis] Analyzed {len(state.critical_files)} critical files, "
        f"found {len(state.blast_radius_map)} blast radius entries"
    )
    
    state.deep_analysis_complete = True
    state.current_phase = AnalysisPhase.INDEX_TO_MEMORY
    return state


async def index_to_memory_node(
    state: CodebaseAnalysisState,
) -> CodebaseAnalysisState:
    """Phase 4: Index analyzed code to Project Memory.
    
    Prepares elements for storage (actual persistence happens
    via ProjectMemoryIndexer when available).
    """
    logger.info("[IndexToMemory] Preparing code elements for indexing")
    state.current_phase = AnalysisPhase.INDEX_TO_MEMORY
    
    elements = []
    
    for file_path, file_data in state.analyzed_files.items():
        # Index functions
        for func in file_data.get("functions", []):
            elements.append({
                "name": func["name"],
                "type": "function",
                "file_path": file_path,
                "start_line": func.get("start_line", 0),
                "end_line": func.get("end_line", 0),
                "signature": func.get("signature", ""),
                "docstring": func.get("docstring"),
            })
        
        # Index classes
        for cls in file_data.get("classes", []):
            elements.append({
                "name": cls["name"],
                "type": "class",
                "file_path": file_path,
                "start_line": cls.get("start_line", 0),
                "end_line": cls.get("end_line", 0),
                "signature": cls.get("signature", ""),
                "docstring": cls.get("docstring"),
            })
            
            # Index methods
            for method in cls.get("methods", []):
                elements.append({
                    "name": method["name"],
                    "type": "method",
                    "file_path": file_path,
                    "parent_class": cls["name"],
                    "start_line": method.get("start_line", 0),
                    "end_line": method.get("end_line", 0),
                    "signature": method.get("signature", ""),
                })
    
    state.indexed_elements = elements
    state.memory_stats = {
        "total_indexed": len(elements),
        "functions": sum(1 for e in elements if e["type"] == "function"),
        "classes": sum(1 for e in elements if e["type"] == "class"),
        "methods": sum(1 for e in elements if e["type"] == "method"),
    }
    
    logger.info(
        f"[IndexToMemory] Prepared {len(elements)} elements: "
        f"{state.memory_stats['functions']} functions, "
        f"{state.memory_stats['classes']} classes, "
        f"{state.memory_stats['methods']} methods"
    )
    
    state.index_complete = True
    state.current_phase = AnalysisPhase.VALIDATION
    return state


async def validation_node(
    state: CodebaseAnalysisState,
    validator: Any,
) -> CodebaseAnalysisState:
    """Phase 5: Validate coverage against thresholds.
    
    Uses ContextPlusValidator to check if minimum coverage
    requirements are met.
    """
    logger.info("[Validation] Checking coverage")
    state.current_phase = AnalysisPhase.VALIDATION
    
    # Register files with validator
    validator.register_discovered_files(state.discovered_files)
    
    for file_path, file_data in state.analyzed_files.items():
        validator.mark_file_analyzed(
            file_path,
            functions=len(file_data.get("functions", [])),
            classes=len(file_data.get("classes", [])),
            patterns=file_data.get("patterns", []),
        )
    
    for file_path in state.failed_files:
        validator.mark_file_failed(file_path, "Analysis failed")
    
    # Validate
    passed, report = validator.validate()
    
    state.validation_passed = passed
    state.coverage_percentage = report.overall_coverage
    state.function_coverage = report.function_coverage_percentage
    state.class_coverage = report.class_coverage_percentage
    state.missing_files = validator.get_missing_files()
    
    logger.info(
        f"[Validation] Coverage: {state.coverage_percentage:.1f}% "
        f"({'PASS' if passed else 'FAIL'})"
    )
    
    state.current_phase = AnalysisPhase.LOOP if not passed else AnalysisPhase.REPORT
    return state


async def loop_node(state: CodebaseAnalysisState) -> CodebaseAnalysisState:
    """Prepare for next iteration when coverage is insufficient."""
    state.iteration_count += 1
    
    if state.iteration_count >= state.max_iterations:
        state.add_warning(
            f"Max iterations ({state.max_iterations}) reached. "
            f"Coverage: {state.coverage_percentage:.1f}%"
        )
        state.current_phase = AnalysisPhase.REPORT
        return state
    
    # Re-process missing files
    state.pending_files = state.missing_files
    
    logger.info(
        f"[Loop] Iteration {state.iteration_count}: "
        f"Re-processing {len(state.missing_files)} missing files"
    )
    
    state.current_phase = AnalysisPhase.SKELETON
    return state


async def report_node(state: CodebaseAnalysisState) -> CodebaseAnalysisState:
    """Generate final analysis report."""
    logger.info("[Report] Generating final report")
    state.current_phase = AnalysisPhase.REPORT
    
    sections = [
        "# Codebase Analysis Report",
        "",
        "## Summary",
        f"- **Target:** {state.target_path}",
        f"- **Files Discovered:** {state.total_files_discovered}",
        f"- **Files Analyzed:** {state.total_files_analyzed}",
        f"- **Coverage:** {state.coverage_percentage:.1f}%",
        f"- **Iterations:** {state.iteration_count}",
        f"- **Timeouts:** {state.timeouts_count}",
        f"- **Fallbacks:** {state.fallbacks_count}",
        "",
        "## Coverage Breakdown",
        f"- Functions: {state.function_coverage:.1f}%",
        f"- Classes: {state.class_coverage:.1f}%",
        "",
        "## Indexed Elements",
    ]
    
    if state.memory_stats:
        sections.extend([
            f"- Total: {state.memory_stats.get('total_indexed', 0)}",
            f"- Functions: {state.memory_stats.get('functions', 0)}",
            f"- Classes: {state.memory_stats.get('classes', 0)}",
            f"- Methods: {state.memory_stats.get('methods', 0)}",
        ])
    
    if state.patterns_found:
        sections.extend(["", "## Patterns Found"])
        for pattern, count in sorted(
            state.patterns_found.items(), key=lambda x: -x[1]
        ):
            sections.append(f"- {pattern}: {count}")
    
    if state.blast_radius_map:
        sections.extend(["", "## Critical Dependencies (Top 10)"])
        for symbol, deps in sorted(
            state.blast_radius_map.items(),
            key=lambda x: len(x[1]),
            reverse=True,
        )[:10]:
            sections.append(f"- **{symbol}**: {len(deps)} dependents")
    
    if state.errors:
        sections.extend(["", "## Errors"])
        for error in state.errors:
            sections.append(f"- {error}")
    
    if state.warnings:
        sections.extend(["", "## Warnings"])
        for warning in state.warnings[:20]:
            sections.append(f"- {warning}")
    
    state.report_markdown = "\n".join(sections)
    state.complete()
    
    return state


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _extract_directories(tree_data: Any) -> list[str]:
    """Extract directory paths from context tree result."""
    if isinstance(tree_data, dict):
        dirs = []
        for key, value in tree_data.items():
            if isinstance(value, dict):
                dirs.append(key)
        return dirs
    return []


def _extract_files(tree_data: Any) -> list[str]:
    """Extract file paths from context tree result."""
    if isinstance(tree_data, dict):
        files = []
        for key, value in tree_data.items():
            if isinstance(value, str) and key.endswith((".py", ".ts", ".js")):
                files.append(key)
            elif isinstance(value, dict):
                files.extend(_extract_files(value))
        return files
    return []


def _extract_functions(skeleton_data: Any) -> list[dict]:
    """Extract function definitions from skeleton data."""
    if isinstance(skeleton_data, dict):
        return skeleton_data.get("functions", [])
    return []


def _extract_classes(skeleton_data: Any) -> list[dict]:
    """Extract class definitions from skeleton data."""
    if isinstance(skeleton_data, dict):
        return skeleton_data.get("classes", [])
    return []


def _extract_imports(skeleton_data: Any) -> list[str]:
    """Extract import statements from skeleton data."""
    if isinstance(skeleton_data, dict):
        return skeleton_data.get("imports", [])
    return []


def _detect_patterns(skeleton_data: Any) -> list[str]:
    """Detect architectural patterns from skeleton data."""
    patterns = []
    if isinstance(skeleton_data, dict):
        classes = skeleton_data.get("classes", [])
        functions = skeleton_data.get("functions", [])
        
        # Simple pattern detection
        class_names = [c.get("name", "") for c in classes]
        func_names = [f.get("name", "") for f in functions]
        
        if any("Factory" in n for n in class_names):
            patterns.append("Factory")
        if any("Observer" in n or "Listener" in n for n in class_names):
            patterns.append("Observer")
        if any("Singleton" in n for n in class_names):
            patterns.append("Singleton")
        if any("Manager" in n for n in class_names):
            patterns.append("Manager")
        if any("Service" in n for n in class_names):
            patterns.append("Service")
        if any("Controller" in n for n in class_names):
            patterns.append("Controller")
        if any("Repository" in n for n in class_names):
            patterns.append("Repository")
        if any("Strategy" in n for n in class_names):
            patterns.append("Strategy")
    
    return patterns


def _identify_critical_files(analyzed_files: dict[str, dict]) -> list[str]:
    """Identify critical files based on complexity metrics."""
    scores = {}
    
    for file_path, data in analyzed_files.items():
        score = 0
        score += len(data.get("functions", [])) * 2
        score += len(data.get("classes", [])) * 5
        score += len(data.get("imports", []))
        scores[file_path] = score
    
    # Return top files by score
    sorted_files = sorted(scores.items(), key=lambda x: -x[1])
    return [f[0] for f in sorted_files[:15]]


# ============================================================
# CONDITIONAL ROUTING
# ============================================================

def should_continue_skeleton(state: CodebaseAnalysisState) -> str:
    """Route after skeleton: continue to deep analysis or skip to validation."""
    if state.timeouts_count > 5:
        return "validation"
    if state.total_files_analyzed > 0:
        return "deep_analysis"
    return "validation"


def should_loop_or_finish(state: CodebaseAnalysisState) -> str:
    """Route after validation: loop for more coverage or generate report."""
    if state.validation_passed:
        return "report"
    if state.iteration_count >= state.max_iterations:
        return "report"
    if state.missing_files and len(state.missing_files) > 0:
        return "loop"
    return "report"


# ============================================================
# GRAPH FACTORY
# ============================================================

def create_codebase_analysis_graph(
    contextplus_executor: Optional[Callable] = None,
    fallback_engine: Optional[Any] = None,
    validator: Optional[Any] = None,
) -> StateGraph:
    """Create and compile the Codebase Analysis Graph.
    
    Args:
        contextplus_executor: Async callable for Context+ tools
        fallback_engine: ContextPlusFallbackEngine instance
        validator: ContextPlusValidator instance
        
    Returns:
        Compiled StateGraph ready for execution
    """
    # Import here to avoid circular imports
    from mindflow_backend.agents.tools.contextplus_fallback import (
        ContextPlusFallbackEngine,
        FallbackConfig,
    )
    from mindflow_backend.agents.tools.contextplus_validator import (
        ContextPlusValidator,
        ValidationConfig,
    )
    
    # Use provided instances or create defaults
    _fallback_engine = fallback_engine or ContextPlusFallbackEngine(
        config=FallbackConfig(timeout_seconds=30.0)
    )
    _validator = validator or ContextPlusValidator(
        config=ValidationConfig(min_coverage_percentage=95.0)
    )
    
    # Create graph
    workflow = StateGraph(CodebaseAnalysisState)
    
    # Add nodes with bound dependencies
    workflow.add_node(
        "discovery",
        lambda s: discovery_node(s, contextplus_executor, _fallback_engine),
    )
    workflow.add_node(
        "skeleton",
        lambda s: skeleton_node(s, contextplus_executor, _fallback_engine),
    )
    workflow.add_node(
        "deep_analysis",
        lambda s: deep_analysis_node(s, contextplus_executor, _fallback_engine),
    )
    workflow.add_node("index_to_memory", index_to_memory_node)
    workflow.add_node(
        "validation",
        lambda s: validation_node(s, _validator),
    )
    workflow.add_node("loop", loop_node)
    workflow.add_node("report", report_node)
    
    # Define entry point
    workflow.set_entry_point("discovery")
    
    # Sequential edges
    workflow.add_edge("discovery", "skeleton")
    workflow.add_conditional_edges(
        "skeleton",
        should_continue_skeleton,
        {
            "deep_analysis": "deep_analysis",
            "validation": "validation",
        },
    )
    workflow.add_edge("deep_analysis", "index_to_memory")
    workflow.add_edge("index_to_memory", "validation")
    
    # Conditional edge: validation -> loop or report
    workflow.add_conditional_edges(
        "validation",
        should_loop_or_finish,
        {
            "loop": "loop",
            "report": "report",
        },
    )
    
    # Loop goes back to skeleton
    workflow.add_edge("loop", "skeleton")
    
    # Report ends
    workflow.add_edge("report", END)
    
    return workflow.compile()