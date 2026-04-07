"""Analysis nodes for MindFlow Execution Graphs (Production Ready).

This module provides production-ready analysis nodes for codebase investigation:
- AnalysisInitializeNode: Setup analysis context with agent policy
- ReadContextNode: Filesystem scanning and structure mapping
- InvestigateNode: Pattern scanning and symbol tracing with real analysis
- AnnotateNode: Insight extraction and memory annotation
- SynthesizeNode: Theme identification and structured analysis generation
- AnalysisReportNode: Comprehensive report generation with metrics

All nodes integrate with mindflow_backend.nodes.analysis.utils for
code analysis, pattern detection, and structured output generation.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory

_logger = get_logger(__name__)


class AnalysisInitializeNode(BaseNode):
    """Initialize analysis context: tools, memory scope, agent policy."""

    def __init__(self, node_id: str = "initialize") -> None:
        super().__init__(
            node_id=node_id,
            name="Analysis Initialize",
            description="Setup tools, memory scope, agent policy, and analysis parameters.",
            category=NodeCategory.INITIALIZATION,
        )
        self.config.required_inputs = set()  # No strict requirements, uses defaults
        self.config.outputs = {
            "iteration",
            "confidence",
            "annotations",
            "analyzed_files",
            "agent_id",
            "mission_type",
            "current_phase",
            "max_iterations",
            "file_patterns",
            "symbol_to_trace",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Initialize analysis context with agent policy and configuration."""
        import time

        # Extract or set defaults
        agent_id = state.get("agent_id", "analyst")
        mission_type = state.get("mission_type", "codebase_analysis")
        session_id = state.get("session_id", "")
        query = state.get("query", "")
        
        # Analysis parameters
        max_iterations = state.get("max_iterations", 10)
        confidence_threshold = state.get("confidence_threshold", 0.85)
        file_patterns = state.get("file_patterns", ["*.py"])
        
        # Determine symbol to trace from query if not specified
        symbol_to_trace = state.get("symbol_to_trace", "")
        if not symbol_to_trace and query:
            # Try to extract class/function names from query
            import re
            class_match = re.search(r'class\s+(\w+)', query)
            func_match = re.search(r'(\w+)\s*\(', query)
            if class_match:
                symbol_to_trace = class_match.group(1)
            elif func_match:
                symbol_to_trace = func_match.group(1)

        # Setup working directory
        working_directory = state.get("working_directory", ".")
        
        _logger.info(
            "analysis_initialize_start",
            node_id=self.node_id,
            agent_id=agent_id,
            mission_type=mission_type,
            session_id=session_id or "(none)",
            max_iterations=max_iterations,
            confidence_threshold=confidence_threshold,
            symbol_to_trace=symbol_to_trace or "(none)",
        )

        # Record start time for metrics
        start_time = time.time()

        return {
            "iteration": 0,
            "confidence": 0.0,
            "annotations": [],
            "analyzed_files": {},
            "agent_id": agent_id,
            "mission_type": mission_type,
            "session_id": session_id,
            "query": query,
            "current_phase": "initialized",
            "max_iterations": max_iterations,
            "confidence_threshold": confidence_threshold,
            "file_patterns": file_patterns,
            "symbol_to_trace": symbol_to_trace,
            "working_directory": working_directory,
            "start_time": start_time,
        }


class ReadContextNode(BaseNode):
    """Read project context: filesystem scan, structure mapping."""

    def __init__(self, node_id: str = "read_context") -> None:
        super().__init__(
            node_id=node_id,
            name="Read Context",
            description="Scan filesystem and map project structure.",
            category=NodeCategory.DATA_COLLECTION,
        )
        self.config.required_inputs = {"working_directory"}
        self.config.outputs = {
            "project_structure",
            "relevant_files",
            "file_count",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute filesystem scan and structure mapping."""
        working_dir = state.get("working_directory", ".")
        file_patterns = state.get("file_patterns", ["*.py"])
        
        _logger.info(
            "read_context_start",
            node_id=self.node_id,
            working_dir=working_dir,
            patterns=file_patterns,
        )

        try:
            from pathlib import Path
            
            root_path = Path(working_dir)
            if not root_path.exists():
                raise ValueError(f"Working directory does not exist: {working_dir}")

            # Scan for relevant files
            relevant_files = []
            for pattern in file_patterns:
                relevant_files.extend(root_path.rglob(pattern))
            
            # Convert to relative paths
            relevant_files = [
                str(f.relative_to(root_path)) 
                for f in relevant_files 
                if f.is_file() and not any(part.startswith(".") for part in f.parts)
            ]

            # Analyze file structure using utility function
            from mindflow_backend.nodes.analysis.utils import analyze_file_structure
            
            structure = await analyze_file_structure(relevant_files, working_dir)

            _logger.info(
                "read_context_complete",
                node_id=self.node_id,
                files_found=len(relevant_files),
                structure_entries=len(structure.get("structure", {})),
            )

            return {
                "project_structure": structure,
                "relevant_files": relevant_files,
                "file_count": len(relevant_files),
                "current_phase": "context_read",
                "working_directory": working_dir,
            }

        except Exception as e:
            _logger.error("read_context_failed", node_id=self.node_id, error=str(e))
            return {
                "project_structure": {},
                "relevant_files": [],
                "file_count": 0,
                "current_phase": "context_read",
                "error": str(e),
            }

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []
        if "working_directory" not in state:
            errors.append("Missing required input: working_directory")
        return errors


class InvestigateNode(BaseNode):
    """Iterative investigation of codebase aspects."""

    def __init__(self, node_id: str = "investigate") -> None:
        super().__init__(
            node_id=node_id,
            name="Investigate",
            description="Investigate codebase aspects iteratively using pattern scanning and symbol tracing.",
            category=NodeCategory.ANALYSIS,
        )
        self.config.required_inputs = {"relevant_files", "working_directory"}
        self.config.outputs = {
            "findings",
            "patterns_found",
            "dependencies",
            "structure",
            "iteration",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute investigation using pattern scanning and symbol tracing."""
        from mindflow_backend.nodes.analysis.utils import (
            scan_code_patterns,
            trace_symbol_dependencies,
            analyze_file_structure,
            interpret_findings_with_llm,
        )

        relevant_files = state.get("relevant_files", [])
        working_dir = state.get("working_directory", ".")
        agent_id = state.get("agent_id", "analyst")
        symbol_to_trace = state.get("symbol_to_trace", "")
        iteration = state.get("iteration", 0) + 1

        _logger.info(
            "investigate_node_start",
            node_id=self.node_id,
            agent_id=agent_id,
            files_count=len(relevant_files),
            iteration=iteration,
            symbol_to_trace=symbol_to_trace or "(none)",
        )

        try:
            # Define common code patterns to search
            patterns = [
                r"class\s+\w+",  # Class definitions
                r"def\s+\w+",    # Function definitions  
                r"import\s+",    # Import statements
                r"async\s+def",   # Async functions
                r"@\w+",         # Decorators
            ]

            # 1. Scan code patterns
            patterns_found = await scan_code_patterns(relevant_files, patterns, working_dir)

            # 2. Trace symbol dependencies (if symbol specified)
            dependencies = {"symbol": symbol_to_trace, "dependencies": []}
            if symbol_to_trace:
                dependencies = await trace_symbol_dependencies(
                    symbol_to_trace, relevant_files, working_dir
                )

            # 3. Analyze file structure
            structure = await analyze_file_structure(relevant_files, working_dir)

            # 4. Interpret findings
            interpretation = await interpret_findings_with_llm(
                patterns_found, dependencies, structure, agent_id
            )

            _logger.info(
                "investigate_node_complete",
                node_id=self.node_id,
                iteration=iteration,
                patterns_count=patterns_found.get("total_matches", 0),
                dependencies_count=len(dependencies.get("dependencies", [])),
            )

            return {
                "findings": interpretation,
                "patterns_found": patterns_found,
                "dependencies": dependencies,
                "structure": structure,
                "iteration": iteration,
                "current_phase": "investigating",
            }

        except Exception as e:
            _logger.error("investigate_node_failed", node_id=self.node_id, error=str(e))
            return {
                "findings": {},
                "patterns_found": {},
                "dependencies": {},
                "structure": {},
                "iteration": iteration,
                "current_phase": "error",
                "error": str(e),
            }

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []
        if "relevant_files" not in state:
            errors.append("Missing required input: relevant_files (run ReadContextNode first)")
        if "working_directory" not in state:
            errors.append("Missing required input: working_directory")
        return errors


class AnnotateNode(BaseNode):
    """Annotate findings from investigation pass."""

    def __init__(self, node_id: str = "annotate") -> None:
        super().__init__(
            node_id=node_id,
            name="Annotate",
            description="Extract insights from findings and save memory annotations.",
            category=NodeCategory.ANALYSIS,
        )
        self.config.required_inputs = {"findings", "iteration"}
        self.config.outputs = {
            "annotations",
            "confidence",
            "insights",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Extract insights from findings and save annotations."""
        from mindflow_backend.nodes.analysis.utils import (
            extract_key_insights,
            calculate_confidence_score,
            save_memory_annotation,
        )

        findings = state.get("findings", {})
        iteration = state.get("iteration", 0)
        previous_annotations = list(state.get("annotations", []))
        previous_confidence = state.get("confidence", 0.0)
        agent_id = state.get("agent_id", "analyst")
        mission_type = state.get("mission_type", "analysis")
        session_id = state.get("session_id", "")

        _logger.info(
            "annotate_node_start",
            node_id=self.node_id,
            iteration=iteration,
            previous_annotations_count=len(previous_annotations),
        )

        try:
            # 1. Extract key insights from findings
            insights = await extract_key_insights(findings, iteration)

            # 2. Calculate updated confidence score
            confidence = await calculate_confidence_score(insights, previous_confidence)

            # 3. Save annotations to memory (if session_id provided)
            new_annotations = []
            if session_id:
                for insight in insights:
                    annotation = await save_memory_annotation(
                        insight=insight,
                        agent_id=agent_id,
                        mission_type=mission_type,
                        session_id=session_id,
                    )
                    new_annotations.append(annotation)
            else:
                # Create in-memory annotations without persistence
                import time
                for insight in insights:
                    new_annotations.append({
                        "content": str(insight),
                        "type": insight.get("type", "unknown"),
                        "confidence": insight.get("confidence", 0.5),
                        "iteration": iteration,
                        "timestamp": time.time(),
                    })

            # Merge with previous annotations
            all_annotations = previous_annotations + new_annotations

            _logger.info(
                "annotate_node_complete",
                node_id=self.node_id,
                iteration=iteration,
                new_insights_count=len(insights),
                confidence=confidence,
                total_annotations=len(all_annotations),
            )

            return {
                "annotations": all_annotations,
                "confidence": confidence,
                "insights": insights,
                "current_phase": "annotated",
                "iteration": iteration,
            }

        except Exception as e:
            _logger.error("annotate_node_failed", node_id=self.node_id, error=str(e))
            return {
                "annotations": previous_annotations,
                "confidence": previous_confidence,
                "insights": [],
                "current_phase": "error",
                "iteration": iteration,
                "error": str(e),
            }

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []
        if "findings" not in state:
            errors.append("Missing required input: findings (run InvestigateNode first)")
        return errors


class SynthesizeNode(BaseNode):
    """Synthesize all annotations into coherent analysis."""

    def __init__(self, node_id: str = "synthesize") -> None:
        super().__init__(
            node_id=node_id,
            name="Synthesize",
            description="Merge annotations, identify themes, and generate structured analysis.",
            category=NodeCategory.SYNTHESIS,
        )
        self.config.required_inputs = {"annotations", "confidence"}
        self.config.outputs = {
            "synthesis",
            "themes",
            "narrative",
            "final_confidence",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Merge annotations and generate structured analysis."""
        from mindflow_backend.nodes.analysis.utils import (
            merge_annotations,
            identify_common_themes,
            generate_structured_narrative,
        )

        annotations = state.get("annotations", [])
        confidence = state.get("confidence", 0.0)
        iteration = state.get("iteration", 0)

        _logger.info(
            "synthesize_node_start",
            node_id=self.node_id,
            annotations_count=len(annotations),
            confidence=confidence,
        )

        try:
            # 1. Merge all annotations
            merged = await merge_annotations(annotations)
            grouped_annotations = merged.get("grouped", {})

            # 2. Identify common themes
            themes = await identify_common_themes(grouped_annotations)

            # 3. Generate structured narrative
            narrative = await generate_structured_narrative(
                grouped_annotations, themes, confidence
            )

            # 4. Build comprehensive synthesis
            synthesis = {
                "summary": narrative,
                "themes": themes,
                "total_findings": merged.get("total_count", 0),
                "findings_by_type": {
                    ann_type: len(anns)
                    for ann_type, anns in grouped_annotations.items()
                },
                "iterations": iteration,
                "confidence": confidence,
                "key_insights": [
                    ann.get("content", "") 
                    for anns in grouped_annotations.values()
                    for ann in anns[:3]  # Top 3 from each type
                ],
            }

            _logger.info(
                "synthesize_node_complete",
                node_id=self.node_id,
                themes_count=len(themes),
                synthesis_length=len(narrative),
                final_confidence=confidence,
            )

            return {
                "synthesis": synthesis,
                "themes": themes,
                "narrative": narrative,
                "final_confidence": confidence,
                "current_phase": "synthesized",
            }

        except Exception as e:
            _logger.error("synthesize_node_failed", node_id=self.node_id, error=str(e))
            return {
                "synthesis": {"summary": f"Error during synthesis: {str(e)}"},
                "themes": [],
                "narrative": "",
                "final_confidence": confidence,
                "current_phase": "error",
                "error": str(e),
            }

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []
        if "annotations" not in state:
            errors.append("Missing required input: annotations (run AnnotateNode first)")
        return errors


class AnalysisReportNode(BaseNode):
    """Generate final analysis report."""

    def __init__(self, node_id: str = "report") -> None:
        super().__init__(
            node_id=node_id,
            name="Analysis Report",
            description="Generate comprehensive final analysis report with metrics.",
            category=NodeCategory.REPORTING,
        )
        self.config.required_inputs = {"synthesis", "annotations"}
        self.config.outputs = {
            "report",
            "result",
            "metrics",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Generate comprehensive analysis report."""
        import time
        from datetime import datetime

        synthesis = state.get("synthesis", {})
        annotations = state.get("annotations", [])
        confidence = state.get("confidence", 0.0)
        iteration = state.get("iteration", 0)
        findings = state.get("findings", {})
        patterns_found = state.get("patterns_found", {})
        project_structure = state.get("project_structure", {})
        
        # Calculate execution time if start time available
        duration_seconds = 0
        if "start_time" in state:
            duration_seconds = time.time() - state["start_time"]

        _logger.info(
            "analysis_report_start",
            node_id=self.node_id,
            annotations_count=len(annotations),
            confidence=confidence,
        )

        try:
            # Build comprehensive report
            report = {
                "title": f"Codebase Analysis Report",
                "generated_at": datetime.utcnow().isoformat(),
                "execution_summary": {
                    "iterations": iteration,
                    "duration_seconds": round(duration_seconds, 2),
                    "confidence_score": round(confidence, 2),
                    "status": "completed" if confidence >= 0.5 else "partial",
                },
                "findings": {
                    "total_annotations": len(annotations),
                    "findings_by_type": synthesis.get("findings_by_type", {}),
                    "themes": synthesis.get("themes", []),
                    "key_insights": synthesis.get("key_insights", [])[:10],  # Top 10
                },
                "code_metrics": {
                    "files_analyzed": state.get("file_count", 0),
                    "pattern_matches": patterns_found.get("total_matches", 0),
                    "structure_entries": len(project_structure.get("structure", {})),
                },
                "analysis_summary": synthesis.get("summary", "No summary available"),
                "detailed_results": {
                    "synthesis": synthesis,
                    "raw_findings": findings,
                    "annotations_sample": annotations[:5] if annotations else [],
                },
            }

            # Build simplified result for graph output
            result = {
                "iterations": iteration,
                "confidence": confidence,
                "annotations_count": len(annotations),
                "themes_count": len(synthesis.get("themes", [])),
                "files_analyzed": state.get("file_count", 0),
                "pattern_matches": patterns_found.get("total_matches", 0),
                "summary": synthesis.get("summary", "")[:500],  # First 500 chars
                "status": "completed" if confidence >= 0.5 else "partial",
            }

            # Build metrics
            metrics = {
                "nodes_executed": iteration * 2 + 3,  # Approximate: investigate + annotate per iteration + init + read + synthesize + report
                "nodes_failed": 1 if state.get("error") else 0,
                "total_tokens_used": 0,  # Would be populated by actual LLM calls
                "execution_time_seconds": round(duration_seconds, 2),
                "confidence_reached": confidence,
                "files_processed": state.get("file_count", 0),
                "patterns_identified": patterns_found.get("total_matches", 0),
            }

            _logger.info(
                "analysis_report_complete",
                node_id=self.node_id,
                report_sections=len(report),
                result_keys=len(result),
                confidence=confidence,
            )

            return {
                "report": report,
                "result": result,
                "metrics": metrics,
                "current_phase": "completed",
            }

        except Exception as e:
            _logger.error("analysis_report_failed", node_id=self.node_id, error=str(e))
            return {
                "report": {"error": str(e)},
                "result": {
                    "iterations": iteration,
                    "confidence": confidence,
                    "error": str(e),
                },
                "metrics": {"error": str(e)},
                "current_phase": "error",
                "error": str(e),
            }

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []
        if "synthesis" not in state:
            errors.append("Missing required input: synthesis (run SynthesizeNode first)")
        return errors


__all__ = [
    "AnalysisInitializeNode",
    "ReadContextNode",
    "InvestigateNode",
    "AnnotateNode",
    "SynthesizeNode",
    "AnalysisReportNode",
]
