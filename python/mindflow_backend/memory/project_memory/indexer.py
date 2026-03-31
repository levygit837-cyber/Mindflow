"""Indexer for Project Memory.

Maps and extracts all code elements from a project using Context+ tools,
then persists them to Project Memory storage.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Optional

from mindflow_backend.memory.project_memory.models import CodeElement, CodeType, ProjectMemory
from mindflow_backend.memory.project_memory.storage import ProjectMemoryStorage

logger = logging.getLogger(__name__)


class ProjectMemoryIndexer:
    """Indexes all code in a project into Project Memory.
    
    Uses Context+ tools to discover files, extract skeletons,
    and persist code elements with full source.
    """
    
    def __init__(
        self,
        storage: ProjectMemoryStorage,
        contextplus_executor: Optional[Callable] = None,
    ):
        self.storage = storage
        self.contextplus = contextplus_executor
    
    async def index_project(
        self,
        project_path: str,
        project_id: str,
        file_patterns: list[str] = None,
    ) -> ProjectMemory:
        """Index entire project.
        
        Args:
            project_path: Root path of the project
            project_id: Unique project identifier
            file_patterns: File patterns to include (default: *.py, *.ts)
            
        Returns:
            ProjectMemory with all indexed elements
        """
        if file_patterns is None:
            file_patterns = ["*.py", "*.ts", "*.js"]
        
        logger.info(f"Starting indexing of {project_path}")
        
        # Create memory
        memory = ProjectMemory(
            project_id=project_id,
            project_path=project_path,
            name=Path(project_path).name,
        )
        
        # Phase 1: Discover files
        files = await self._discover_files(project_path, file_patterns)
        logger.info(f"Discovered {len(files)} files")
        
        # Phase 2: Index each file
        for file_path in files:
            elements = await self._index_file(file_path)
            for element in elements:
                memory.add_element(element)
                await self.storage.save_element(element)
        
        logger.info(
            f"Indexing complete: {memory.total_elements} elements "
            f"({memory.total_functions} functions, "
            f"{memory.total_classes} classes, "
            f"{memory.total_methods} methods)"
        )
        
        return memory
    
    async def index_file(self, file_path: str) -> list[CodeElement]:
        """Index a single file."""
        elements = await self._index_file(file_path)
        for element in elements:
            await self.storage.save_element(element)
        return elements
    
    async def _discover_files(
        self,
        project_path: str,
        file_patterns: list[str],
    ) -> list[str]:
        """Discover all files matching patterns."""
        files = []
        
        for pattern in file_patterns:
            found = list(Path(project_path).rglob(pattern))
            files.extend([str(f) for f in found])
        
        # Filter out common non-source directories
        exclude = {"__pycache__", "node_modules", ".git", "venv", ".venv", "dist", "build"}
        files = [
            f for f in files
            if not any(ex in f for ex in exclude)
        ]
        
        return sorted(set(files))
    
    async def _index_file(self, file_path: str) -> list[CodeElement]:
        """Extract and index all elements from a file."""
        elements = []
        
        try:
            # Read file content
            content = Path(file_path).read_text(encoding="utf-8")
            lines = content.split("\n")
            
            # Parse with Context+ if available
            if self.contextplus:
                skeleton = await self.contextplus(
                    "get_file_skeleton",
                    {"file_path": file_path}
                )
                
                if skeleton:
                    # Extract functions
                    for func in skeleton.get("functions", []):
                        element = self._create_function_element(
                            file_path, func, lines
                        )
                        if element:
                            elements.append(element)
                    
                    # Extract classes
                    for cls in skeleton.get("classes", []):
                        element = self._create_class_element(
                            file_path, cls, lines
                        )
                        if element:
                            elements.append(element)
                        
                        # Extract methods
                        for method in cls.get("methods", []):
                            method_element = self._create_method_element(
                                file_path, method, cls["name"], lines
                            )
                            if method_element:
                                elements.append(method_element)
            
            # Fallback: simple regex-based extraction
            if not elements:
                elements = self._extract_simple(file_path, content)
        
        except Exception as e:
            logger.warning(f"Could not index {file_path}: {e}")
        
        return elements
    
    def _create_function_element(
        self,
        file_path: str,
        func_data: dict,
        lines: list[str],
    ) -> Optional[CodeElement]:
        """Create CodeElement for a function."""
        try:
            name = func_data.get("name", "")
            start = func_data.get("start_line", 1)
            end = func_data.get("end_line", start)
            
            # Extract source
            source_lines = lines[start - 1:end]
            full_source = "\n".join(source_lines)
            
            return CodeElement(
                id=CodeElement.generate_id(file_path, name, CodeType.FUNCTION),
                name=name,
                type=CodeType.FUNCTION,
                file_path=file_path,
                start_line=start,
                end_line=end,
                signature=func_data.get("signature", f"def {name}(...)"),
                full_source=full_source,
                docstring=func_data.get("docstring"),
                decorators=func_data.get("decorators", []),
                lines_of_code=end - start + 1,
            )
        except Exception as e:
            logger.warning(f"Could not create function element: {e}")
            return None
    
    def _create_class_element(
        self,
        file_path: str,
        cls_data: dict,
        lines: list[str],
    ) -> Optional[CodeElement]:
        """Create CodeElement for a class."""
        try:
            name = cls_data.get("name", "")
            start = cls_data.get("start_line", 1)
            end = cls_data.get("end_line", start)
            
            source_lines = lines[start - 1:end]
            full_source = "\n".join(source_lines)
            
            return CodeElement(
                id=CodeElement.generate_id(file_path, name, CodeType.CLASS),
                name=name,
                type=CodeType.CLASS,
                file_path=file_path,
                start_line=start,
                end_line=end,
                signature=cls_data.get("signature", f"class {name}:"),
                full_source=full_source,
                docstring=cls_data.get("docstring"),
                lines_of_code=end - start + 1,
            )
        except Exception as e:
            logger.warning(f"Could not create class element: {e}")
            return None
    
    def _create_method_element(
        self,
        file_path: str,
        method_data: dict,
        parent_class: str,
        lines: list[str],
    ) -> Optional[CodeElement]:
        """Create CodeElement for a method."""
        try:
            name = method_data.get("name", "")
            start = method_data.get("start_line", 1)
            end = method_data.get("end_line", start)
            
            source_lines = lines[start - 1:end]
            full_source = "\n".join(source_lines)
            
            return CodeElement(
                id=CodeElement.generate_id(file_path, name, CodeType.METHOD),
                name=name,
                type=CodeType.METHOD,
                file_path=file_path,
                start_line=start,
                end_line=end,
                signature=method_data.get("signature", f"def {name}(...)"),
                full_source=full_source,
                docstring=method_data.get("docstring"),
                parent_class=parent_class,
                lines_of_code=end - start + 1,
            )
        except Exception as e:
            logger.warning(f"Could not create method element: {e}")
            return None
    
    def _extract_simple(
        self,
        file_path: str,
        content: str,
    ) -> list[CodeElement]:
        """Simple regex-based extraction fallback."""
        import re
        
        elements = []
        lines = content.split("\n")
        
        # Find functions
        func_pattern = re.compile(r"^def\s+(\w+)\s*\(")
        for i, line in enumerate(lines):
            match = func_pattern.match(line)
            if match:
                name = match.group(1)
                # Find end of function (next def/class at same indent or EOF)
                start = i + 1
                end = self._find_block_end(lines, i)
                
                elements.append(CodeElement(
                    id=CodeElement.generate_id(file_path, name, CodeType.FUNCTION),
                    name=name,
                    type=CodeType.FUNCTION,
                    file_path=file_path,
                    start_line=start,
                    end_line=end,
                    signature=line.strip(),
                    full_source="\n".join(lines[i:end]),
                    lines_of_code=end - start + 1,
                ))
        
        # Find classes
        class_pattern = re.compile(r"^class\s+(\w+)")
        for i, line in enumerate(lines):
            match = class_pattern.match(line)
            if match:
                name = match.group(1)
                start = i + 1
                end = self._find_block_end(lines, i)
                
                elements.append(CodeElement(
                    id=CodeElement.generate_id(file_path, name, CodeType.CLASS),
                    name=name,
                    type=CodeType.CLASS,
                    file_path=file_path,
                    start_line=start,
                    end_line=end,
                    signature=line.strip(),
                    full_source="\n".join(lines[i:end]),
                    lines_of_code=end - start + 1,
                ))
        
        return elements
    
    def _find_block_end(self, lines: list[str], start_idx: int) -> int:
        """Find the end line of a code block."""
        if start_idx >= len(lines):
            return len(lines)
        
        # Get base indentation
        base_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
        
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            if not line.strip():  # Skip empty lines
                continue
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= base_indent and line.strip():
                return i
        
        return len(lines)