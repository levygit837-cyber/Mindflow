"""Post Tool Use Memory Observer for the Intelligent Memory System.

Synchronous observer that analyzes tool results immediately after execution,
using direct code parsing (no LLM calls) for maximum efficiency.

Analyzes:
- File write operations (write_file, edit_file, etc.)
- Code structure extraction (functions, classes, imports)
- Pattern detection without LLM overhead
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.category_manager import CategoryManager, MemoryScope
from mindflow_backend.memory.memory_service import MemoryService

_logger = get_logger(__name__)


@dataclass
class CodeAnalysis:
    """Result of code analysis."""

    has_patterns: bool = False
    file_path: str | None = None
    language: str | None = None
    functions: list[dict] = field(default_factory=list)
    classes: list[dict] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    patterns_detected: list[str] = field(default_factory=list)

    def to_memory_content(self) -> str:
        """Convert analysis to memory content."""
        parts = []

        if self.file_path:
            parts.append(f"File: {self.file_path}")

        if self.functions:
            func_names = [f["name"] for f in self.functions[:5]]
            parts.append(f"Functions: {', '.join(func_names)}{'...' if len(self.functions) > 5 else ''}")

        if self.classes:
            class_names = [c["name"] for c in self.classes]
            parts.append(f"Classes: {', '.join(class_names)}")

        if self.imports:
            parts.append(f"Imports: {len(self.imports)} imports")

        if self.patterns_detected:
            parts.append(f"Patterns: {', '.join(self.patterns_detected)}")

        return "\n".join(parts)


class DynamicCodeParser:
    """Parses code dynamically to extract structure and patterns.

    Uses AST for Python, regex-based parsing for TypeScript/JavaScript,
    and simple heuristics for other languages.
    """

    def parse(self, file_path: str, content: str) -> CodeAnalysis:
        """Parse code file and extract structure.

        Args:
            file_path: Path to the file
            content: File content

        Returns:
            CodeAnalysis with extracted information
        """
        ext = Path(file_path).suffix.lower()
        analysis = CodeAnalysis(file_path=file_path, language=ext.lstrip("."))

        if ext == ".py":
            return self._parse_python(content, analysis)
        elif ext in (".ts", ".tsx", ".js", ".jsx"):
            return self._parse_typescript(content, analysis)
        elif ext == ".json":
            return self._parse_json(content, analysis)
        elif ext in (".yaml", ".yml"):
            return self._parse_yaml(content, analysis)
        else:
            return self._parse_generic(content, analysis)

    def _parse_python(self, content: str, analysis: CodeAnalysis) -> CodeAnalysis:
        """Parse Python code using AST."""
        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        "name": node.name,
                        "line_start": node.lineno,
                        "line_end": getattr(node, "end_lineno", node.lineno),
                        "args": [arg.arg for arg in node.args.args],
                        "decorators": [
                            d.id for d in node.decorator_list
                            if isinstance(d, ast.Name)
                        ],
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                    }
                    analysis.functions.append(func_info)

                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "line_start": node.lineno,
                        "line_end": getattr(node, "end_lineno", node.lineno),
                        "methods": [
                            n.name for n in node.body
                            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                        ],
                        "bases": [
                            base.id for base in node.bases
                            if isinstance(base, ast.Name)
                        ],
                    }
                    analysis.classes.append(class_info)

                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            analysis.imports.append(alias.name)
                    else:  # ImportFrom
                        module = node.module or ""
                        for alias in node.names:
                            analysis.imports.append(f"{module}.{alias.name}")

            # Detect patterns
            analysis.patterns_detected = self._detect_python_patterns(tree, analysis)
            analysis.has_patterns = len(analysis.functions) > 0 or len(analysis.classes) > 0

        except SyntaxError as e:
            _logger.debug("python_parse_error", error=str(e))
            analysis.has_patterns = False

        return analysis

    def _parse_typescript(self, content: str, analysis: CodeAnalysis) -> CodeAnalysis:
        """Parse TypeScript/JavaScript using regex-based heuristics."""
        import re

        # Function detection
        func_patterns = [
            r'(?:async\s+)?function\s+(\w+)\s*\(',
            r'(?:export\s+)?(?:async\s+)?(?:function\s+)?(\w+)\s*[:\s]*\([^)]*\)\s*[:\s]*\w+\s*=>',
            r'(?:const|let|var)\s+(\w+)\s*[=:]\s*(?:async\s+)?\([^)]*\)\s*=>',
        ]

        for pattern in func_patterns:
            for match in re.finditer(pattern, content):
                func_name = match.group(1)
                if func_name and not func_name.startswith("_"):
                    analysis.functions.append({
                        "name": func_name,
                        "line_start": content[:match.start()].count("\n") + 1,
                    })

        # Class detection
        class_pattern = r'(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?'
        for match in re.finditer(class_pattern, content):
            analysis.classes.append({
                "name": match.group(1),
                "bases": [match.group(2)] if match.group(2) else [],
            })

        # Import detection
        import_patterns = [
            r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]',
            r'import\s+[\'"]([^\'"]+)[\'"]',
        ]
        for pattern in import_patterns:
            for match in re.finditer(pattern, content):
                analysis.imports.append(match.group(1))

        analysis.has_patterns = len(analysis.functions) > 0 or len(analysis.classes) > 0
        return analysis

    def _parse_json(self, content: str, analysis: CodeAnalysis) -> CodeAnalysis:
        """Parse JSON for structure."""
        try:
            data = json.loads(content)
            analysis.has_patterns = True

            if isinstance(data, dict):
                analysis.patterns_detected.append(f"root_object_with_{len(data)}_keys")
            elif isinstance(data, list):
                analysis.patterns_detected.append(f"array_with_{len(data)}_items")

        except json.JSONDecodeError:
            analysis.has_patterns = False

        return analysis

    def _parse_yaml(self, content: str, analysis: CodeAnalysis) -> CodeAnalysis:
        """Parse YAML for basic structure."""
        try:
            # Simple heuristic: count top-level keys
            lines = content.split("\n")
            top_level_keys = 0

            for line in lines:
                stripped = line.lstrip()
                if stripped and not stripped.startswith("#"):
                    if not line.startswith(" ") and not line.startswith("\t"):
                        if ":" in stripped:
                            top_level_keys += 1

            if top_level_keys > 0:
                analysis.has_patterns = True
                analysis.patterns_detected.append(f"config_with_{top_level_keys}_sections")

        except Exception:
            analysis.has_patterns = False

        return analysis

    def _parse_generic(self, content: str, analysis: CodeAnalysis) -> CodeAnalysis:
        """Generic parsing for unknown file types."""
        # Simple heuristics
        lines = content.split("\n")

        if len(lines) > 0:
            analysis.has_patterns = True
            analysis.patterns_detected.append(f"file_with_{len(lines)}_lines")

        return analysis

    def _detect_python_patterns(
        self,
        tree: ast.AST,
        analysis: CodeAnalysis,
    ) -> list[str]:
        """Detect common Python patterns in code."""
        patterns = []

        # Check for async usage
        has_async = any(
            isinstance(node, ast.AsyncFunctionDef)
            for node in ast.walk(tree)
        )
        if has_async:
            patterns.append("async_await")

        # Check for decorators
        has_decorators = any(
            hasattr(node, "decorator_list") and node.decorator_list
            for node in ast.walk(tree)
        )
        if has_decorators:
            patterns.append("decorators")

        # Check for type hints
        has_type_hints = any(
            hasattr(node, "annotation") and node.annotation is not None
            for node in ast.walk(tree)
        )
        if has_type_hints:
            patterns.append("type_hints")

        # Check for dataclasses
        uses_dataclasses = any(
            isinstance(node, ast.ClassDef) and any(
                isinstance(dec, ast.Name) and dec.id == "dataclass"
                for dec in node.decorator_list
            )
            for node in ast.walk(tree)
        )
        if uses_dataclasses:
            patterns.append("dataclasses")

        # Check for context managers (with statements)
        has_context_managers = any(
            isinstance(node, ast.With)
            for node in ast.walk(tree)
        )
        if has_context_managers:
            patterns.append("context_managers")

        return patterns


class PostToolUseObserver:
    """Synchronous observer for analyzing tool results.

    Integrates with ToolExecutor to analyze code changes immediately
    after write operations, using direct parsing (no LLM calls).
    """

    # Tools that write/modify files
    ANALYZABLE_TOOLS = {
        "write_file",
        "edit_file",
        "replace_in_file",
        "create_file",
        "apply_diff",
    }

    def __init__(
        self,
        memory_service: MemoryService,
        category_manager: CategoryManager | None = None,
    ) -> None:
        """Initialize the Post Tool Use Observer.

        Args:
            memory_service: Service for saving memories
            category_manager: Optional category manager
        """
        self.memory_service = memory_service
        self.category_manager = category_manager or CategoryManager()
        self.code_parser = DynamicCodeParser()

    async def on_tool_result(
        self,
        tool_name: str,
        tool_result: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> None:
        """Process tool result and extract memories.

        Called synchronously after tool execution completes.

        Args:
            tool_name: Name of the tool that was executed
            tool_result: Result dict from the tool
            context: Optional execution context (agent_id, session_id, etc.)
        """
        # Only analyze file modification tools
        if tool_name not in self.ANALYZABLE_TOOLS:
            return

        # Extract file path and content
        file_path = self._extract_file_path(tool_result)
        content = self._extract_content(tool_result)

        if not file_path or not content:
            return

        # Parse code
        analysis = self.code_parser.parse(file_path, content)

        if not analysis.has_patterns:
            return

        # Save as memory
        await self._save_code_memory(analysis, tool_name, context or {})

    def _extract_file_path(self, tool_result: dict[str, Any]) -> str | None:
        """Extract file path from tool result."""
        # Try various possible keys
        for key in ["file_path", "path", "file", "target_path"]:
            if key in tool_result:
                return tool_result[key]

        # Try nested in result
        result = tool_result.get("result", {})
        if isinstance(result, dict):
            for key in ["file_path", "path", "file"]:
                if key in result:
                    return result[key]

        return None

    def _extract_content(self, tool_result: dict[str, Any]) -> str | None:
        """Extract content from tool result."""
        # Direct content
        for key in ["content", "new_content", "code", "text"]:
            if key in tool_result:
                return tool_result[key]

        # Nested in result
        result = tool_result.get("result", {})
        if isinstance(result, dict):
            for key in ["content", "code", "text"]:
                if key in result:
                    return result[key]

        # Diff extraction
        diff = tool_result.get("diff", "")
        if diff:
            # Try to reconstruct content from diff
            return self._extract_from_diff(diff)

        return None

    def _extract_from_diff(self, diff: str) -> str | None:
        """Extract content from diff format."""
        # Simple heuristic: extract added lines
        lines = []
        for line in diff.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                lines.append(line[1:])

        return "\n".join(lines) if lines else None

    async def _save_code_memory(
        self,
        analysis: CodeAnalysis,
        tool_name: str,
        context: dict[str, Any],
    ) -> None:
        """Save code analysis as memory entry."""
        file_path = analysis.file_path or "unknown"

        # Build rich content
        content_parts = [
            f"Code modification detected via {tool_name}",
            f"File: {file_path}",
        ]

        if analysis.functions:
            funcs = ", ".join([f["name"] for f in analysis.functions[:5]])
            content_parts.append(f"Functions: {funcs}{'...' if len(analysis.functions) > 5 else ''}")

        if analysis.classes:
            classes = ", ".join([c["name"] for c in analysis.classes])
            content_parts.append(f"Classes: {classes}")

        if analysis.patterns_detected:
            content_parts.append(f"Patterns: {', '.join(analysis.patterns_detected)}")

        content = "\n".join(content_parts)

        # Classify
        category, subcategory = None, None
        if self.category_manager:
            category, subcategory = self.category_manager.classify_content(
                content=content,
                memory_type="pattern",
                source_tool=tool_name,
                file_path=file_path,
            )

        # Determine importance
        importance = 0.5
        if analysis.classes:
            importance += 0.1  # Classes are more important
        if len(analysis.functions) > 5:
            importance += 0.1  # Many functions = complex file
        if "async_await" in analysis.patterns_detected:
            importance += 0.05  # Modern Python

        # Extract tags
        tags = ["code_change", tool_name]
        if analysis.language:
            tags.append(analysis.language)
        tags.extend(analysis.patterns_detected[:3])

        try:
            await self.memory_service.save_memory(
                content=content,
                memory_type="pattern",
                scope=context.get("scope", MemoryScope.SESSION),
                project_id=context.get("project_id"),
                session_id=context.get("session_id"),
                category=category or "code_patterns",
                subcategory=subcategory,
                importance=min(importance, 1.0),
                source_agent_id=context.get("agent_id"),
                source_tool=tool_name,
                tags=tags,
                file_path=file_path,
                structured_data={
                    "functions": analysis.functions,
                    "classes": analysis.classes,
                    "imports_count": len(analysis.imports),
                    "patterns": analysis.patterns_detected,
                },
                generate_embedding=True,
            )

            _logger.debug(
                "post_tool_memory_saved",
                file_path=file_path,
                functions=len(analysis.functions),
                classes=len(analysis.classes),
            )

        except Exception as e:
            _logger.warning(
                "post_tool_memory_save_failed",
                file_path=file_path,
                error=str(e),
            )

    def can_analyze(self, tool_name: str) -> bool:
        """Check if this observer can analyze a tool."""
        return tool_name in self.ANALYZABLE_TOOLS
