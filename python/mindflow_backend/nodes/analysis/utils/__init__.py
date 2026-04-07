"""Utility functions for analysis nodes.

This module contains reusable utility functions with fine-grained
granularity specific to analysis tasks.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


async def scan_code_patterns(
    files: list[str],
    patterns: list[str],
    working_dir: str,
) -> dict[str, Any]:
    """Scan files for specific code patterns.

    Args:
        files: List of file paths to scan
        patterns: List of regex patterns to search for
        working_dir: Root directory

    Returns:
        Dictionary with pattern matches
    """
    from pathlib import Path
    import re

    matches = {}
    root_path = Path(working_dir)

    for file_path in files:
        full_path = root_path / file_path
        if not full_path.exists():
            continue

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            file_matches = []
            for pattern in patterns:
                regex = re.compile(pattern)
                for match in regex.finditer(content):
                    file_matches.append(
                        {
                            "pattern": pattern,
                            "line": content[: match.start()].count("\n") + 1,
                            "match": match.group(),
                        }
                    )

            if file_matches:
                matches[file_path] = file_matches

        except Exception as e:
            _logger.warning("pattern_scan_failed", file=file_path, error=str(e))

    _logger.info(
        "code_patterns_scanned",
        files_count=len(files),
        patterns_count=len(patterns),
        matches_count=sum(len(m) for m in matches.values()),
    )

    return {"matches": matches, "total_matches": sum(len(m) for m in matches.values())}


async def trace_symbol_dependencies(
    symbol: str,
    files: list[str],
    working_dir: str,
) -> dict[str, Any]:
    """Trace dependencies of a symbol across files.

    Args:
        symbol: Symbol name to trace
        files: List of file paths to search
        working_dir: Root directory

    Returns:
        Dictionary with symbol dependencies
    """
    from pathlib import Path
    import re

    root_path = Path(working_dir)
    dependencies = []

    # Pattern to find symbol references
    import_pattern = re.compile(rf"import\s+.*\b{symbol}\b")
    usage_pattern = re.compile(rf"\b{symbol}\b")

    for file_path in files:
        full_path = root_path / file_path
        if not full_path.exists():
            continue

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Find imports
            imports = []
            for match in import_pattern.finditer(content):
                imports.append(
                    {
                        "line": content[: match.start()].count("\n") + 1,
                        "statement": match.group(),
                    }
                )

            # Find usages
            usages = []
            for match in usage_pattern.finditer(content):
                usages.append(
                    {
                        "line": content[: match.start()].count("\n") + 1,
                        "context": content[max(0, match.start() - 50) : match.end() + 50],
                    }
                )

            if imports or usages:
                dependencies.append(
                    {
                        "file": file_path,
                        "imports": imports,
                        "usages": usages,
                    }
                )

        except Exception as e:
            _logger.warning("symbol_trace_failed", file=file_path, error=str(e))

    _logger.info(
        "symbol_dependencies_traced",
        symbol=symbol,
        files_count=len(files),
        dependencies_count=len(dependencies),
    )

    return {"symbol": symbol, "dependencies": dependencies}


async def analyze_file_structure(
    files: list[str],
    working_dir: str,
) -> dict[str, Any]:
    """Analyze structure of files (classes, functions, imports).

    Args:
        files: List of file paths to analyze
        working_dir: Root directory

    Returns:
        Dictionary with file structure analysis
    """
    from pathlib import Path
    import re

    root_path = Path(working_dir)
    structure = {}

    for file_path in files:
        full_path = root_path / file_path
        if not full_path.exists():
            continue

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract classes
            class_pattern = re.compile(r"^class\s+(\w+)")
            classes = []
            for match in class_pattern.finditer(content, re.MULTILINE):
                classes.append(
                    {
                        "name": match.group(1),
                        "line": content[: match.start()].count("\n") + 1,
                    }
                )

            # Extract functions
            func_pattern = re.compile(r"^def\s+(\w+)")
            functions = []
            for match in func_pattern.finditer(content, re.MULTILINE):
                functions.append(
                    {
                        "name": match.group(1),
                        "line": content[: match.start()].count("\n") + 1,
                    }
                )

            # Extract imports
            import_pattern = re.compile(r"^import\s+|^from\s+\S+\s+import")
            imports = []
            for match in import_pattern.finditer(content, re.MULTILINE):
                imports.append(
                    {
                        "statement": match.group().strip(),
                        "line": content[: match.start()].count("\n") + 1,
                    }
                )

            structure[file_path] = {
                "classes": classes,
                "functions": functions,
                "imports": imports,
            }

        except Exception as e:
            _logger.warning("file_structure_analysis_failed", file=file_path, error=str(e))

    return {"structure": structure}


async def interpret_findings_with_llm(
    patterns: dict[str, Any],
    dependencies: dict[str, Any],
    structure: dict[str, Any],
    agent_id: str,
) -> dict[str, Any]:
    """Interpret findings using LLM with Analyst prompt.

    Args:
        patterns: Pattern scan results
        dependencies: Symbol dependency results
        structure: File structure analysis
        agent_id: Agent identifier for prompt selection

    Returns:
        Dictionary with LLM interpretation
    """
    # For now, return a structured interpretation
    # In future, this will call the LLM with Analyst-specific prompt

    interpretation = {
        "key_findings": [],
        "patterns": patterns.get("matches", {}),
        "dependencies": dependencies.get("dependencies", []),
        "structure": structure.get("structure", {}),
    }

    # Extract key findings
    if patterns.get("total_matches", 0) > 0:
        interpretation["key_findings"].append(
            f"Found {patterns['total_matches']} pattern matches across files"
        )

    if dependencies.get("dependencies"):
        interpretation["key_findings"].append(
            f"Symbol traced across {len(dependencies['dependencies'])} files"
        )

    _logger.info(
        "findings_interpreted",
        agent_id=agent_id,
        key_findings_count=len(interpretation["key_findings"]),
    )

    return interpretation


async def extract_key_insights(
    findings: dict[str, Any],
    iteration: int,
) -> list[dict[str, Any]]:
    """Extract key insights from investigation findings.

    Args:
        findings: Investigation results
        iteration: Current iteration number

    Returns:
        List of key insights
    """
    insights = []
    patterns = findings.get("patterns_found", {}).get("matches", {})
    dependencies = findings.get("dependencies", {}).get("dependencies", [])

    # Extract insights from patterns
    for file_path, matches in patterns.items():
        if matches:
            insights.append(
                {
                    "type": "pattern_match",
                    "file": file_path,
                    "matches_count": len(matches),
                    "iteration": iteration,
                    "confidence": 0.7,  # Base confidence for pattern matches
                }
            )

    # Extract insights from dependencies
    for dep in dependencies:
        if dep.get("imports") or dep.get("usages"):
            insights.append(
                {
                    "type": "dependency",
                    "file": dep.get("file"),
                    "imports_count": len(dep.get("imports", [])),
                    "usages_count": len(dep.get("usages", [])),
                    "iteration": iteration,
                    "confidence": 0.8,  # Higher confidence for dependencies
                }
            )

    _logger.info(
        "key_insights_extracted",
        iteration=iteration,
        insights_count=len(insights),
    )

    return insights


async def calculate_confidence_score(
    insights: list[dict[str, Any]],
    previous_confidence: float,
) -> float:
    """Calculate confidence score based on insights.

    Args:
        insights: List of insights
        previous_confidence: Previous confidence score

    Returns:
        Updated confidence score (0.0 to 1.0)
    """
    if not insights:
        return previous_confidence

    # Calculate confidence based on insight quality and quantity
    total_confidence = sum(insight.get("confidence", 0.5) for insight in insights)
    avg_insight_confidence = total_confidence / len(insights)

    # Incrementally increase confidence, capped at 1.0
    # Each iteration adds at most 0.15 to confidence
    increment = min(avg_insight_confidence * 0.15, 0.15)
    new_confidence = min(previous_confidence + increment, 1.0)

    _logger.debug(
        "confidence_calculated",
        previous_confidence=previous_confidence,
        new_confidence=new_confidence,
        insights_count=len(insights),
    )

    return new_confidence


async def save_memory_annotation(
    insight: dict[str, Any],
    agent_id: str,
    mission_type: str,
    session_id: str,
) -> dict[str, Any]:
    """Save a single insight as memory annotation.

    Args:
        insight: Insight to save
        agent_id: Agent identifier
        mission_type: Type of mission
        session_id: Session identifier

    Returns:
        Dictionary with annotation metadata
    """
    import time

    annotation = {
        "content": str(insight),
        "agent_id": agent_id,
        "mission_type": mission_type,
        "session_id": session_id,
        "confidence": insight.get("confidence", 0.5),
        "timestamp": time.time(),
        "type": insight.get("type", "unknown"),
    }

    _logger.debug(
        "memory_annotation_saved",
        agent_id=agent_id,
        insight_type=insight.get("type"),
        confidence=annotation["confidence"],
    )

    return annotation


async def merge_annotations(
    annotations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Merge annotations from multiple investigation passes.

    Args:
        annotations: List of annotations to merge

    Returns:
        Dictionary with merged annotations grouped by type
    """
    grouped = {}
    total_confidence = 0.0

    for ann in annotations:
        ann_type = ann.get("type", "unknown")
        if ann_type not in grouped:
            grouped[ann_type] = []
        grouped[ann_type].append(ann)
        total_confidence += ann.get("confidence", 0.5)

    avg_confidence = total_confidence / len(annotations) if annotations else 0.0

    _logger.info(
        "annotations_merged",
        annotations_count=len(annotations),
        types_count=len(grouped),
        avg_confidence=avg_confidence,
    )

    return {
        "grouped": grouped,
        "total_count": len(annotations),
        "types": list(grouped.keys()),
        "avg_confidence": avg_confidence,
    }


async def identify_common_themes(
    grouped_annotations: dict[str, Any],
) -> list[str]:
    """Identify common themes across annotations.

    Args:
        grouped_annotations: Annotations grouped by type

    Returns:
        List of common themes
    """
    themes = []

    # Analyze pattern matches
    if "pattern_match" in grouped_annotations:
        pattern_count = len(grouped_annotations["pattern_match"])
        themes.append(f"Found {pattern_count} pattern matches across codebase")

    # Analyze dependencies
    if "dependency" in grouped_annotations:
        dep_count = len(grouped_annotations["dependency"])
        themes.append(f"Identified {dep_count} dependency relationships")

    # Analyze other types
    for ann_type, anns in grouped_annotations.items():
        if ann_type not in ["pattern_match", "dependency"]:
            themes.append(f"Identified {len(anns)} {ann_type} findings")

    _logger.info(
        "common_themes_identified",
        themes_count=len(themes),
    )

    return themes


async def generate_structured_narrative(
    grouped_annotations: dict[str, Any],
    themes: list[str],
    confidence: float,
) -> str:
    """Generate structured narrative from annotations.

    Args:
        grouped_annotations: Merged annotations
        themes: Common themes identified
        confidence: Overall confidence score

    Returns:
        Structured narrative string
    """
    narrative_parts = [
        f"Analysis completed with {confidence:.2%} confidence.",
        "",
        "Key Findings:",
    ]

    # Add themes as findings
    for theme in themes:
        narrative_parts.append(f"- {theme}")

    # Add type breakdown
    narrative_parts.append("")
    narrative_parts.append("Findings by Type:")
    for ann_type, anns in grouped_annotations.items():
        narrative_parts.append(f"- {ann_type}: {len(anns)} findings")

    narrative = "\n".join(narrative_parts)

    _logger.info(
        "structured_narrative_generated",
        narrative_length=len(narrative),
        confidence=confidence,
    )

    return narrative
