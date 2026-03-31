"""Data models for Project Memory.

Defines CodeElement (individual code items) and ProjectMemory
(the complete index of a project).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class CodeType(Enum):
    """Type of code element."""
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    CONSTANT = "constant"
    DECORATOR = "decorator"
    TYPE_ALIAS = "type_alias"


@dataclass
class CodeElement:
    """A single indexed code element (function, class, or method).
    
    Contains the full source code, metadata, and embedding for
    semantic search.
    """
    
    # Identification
    id: str
    name: str
    type: CodeType
    file_path: str
    
    # Location
    start_line: int
    end_line: int
    
    # Code
    signature: str
    full_source: str
    
    # Metadata
    docstring: Optional[str] = None
    decorators: list[str] = field(default_factory=list)
    parent_class: Optional[str] = None
    
    # Analysis
    complexity: int = 0
    lines_of_code: int = 0
    dependencies: list[str] = field(default_factory=list)
    
    # Embedding (for semantic search)
    embedding: Optional[list[float]] = None
    
    # Timestamps
    indexed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @staticmethod
    def generate_id(file_path: str, name: str, code_type: CodeType) -> str:
        """Generate unique ID for a code element."""
        content = f"{file_path}:{name}:{code_type.value}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_searchable_text(self) -> str:
        """Generate text for semantic indexing."""
        parts = [
            f"Name: {self.name}",
            f"Type: {self.type.value}",
            f"File: {self.file_path}",
            f"Signature: {self.signature}",
        ]
        if self.docstring:
            parts.append(f"Documentation: {self.docstring}")
        if self.parent_class:
            parts.append(f"Class: {self.parent_class}")
        return "\n".join(parts)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "signature": self.signature,
            "full_source": self.full_source,
            "docstring": self.docstring,
            "decorators": self.decorators,
            "parent_class": self.parent_class,
            "complexity": self.complexity,
            "lines_of_code": self.lines_of_code,
            "dependencies": self.dependencies,
            "indexed_at": self.indexed_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CodeElement:
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            type=CodeType(data["type"]),
            file_path=data["file_path"],
            start_line=data["start_line"],
            end_line=data["end_line"],
            signature=data["signature"],
            full_source=data["full_source"],
            docstring=data.get("docstring"),
            decorators=data.get("decorators", []),
            parent_class=data.get("parent_class"),
            complexity=data.get("complexity", 0),
            lines_of_code=data.get("lines_of_code", 0),
            dependencies=data.get("dependencies", []),
            indexed_at=data.get("indexed_at", ""),
        )


@dataclass
class ProjectMemory:
    """Complete memory index of a project.
    
    Contains all indexed code elements with multiple indices
    for fast lookup by name, file, or type.
    """
    
    project_id: str
    project_path: str
    name: str
    
    # Indices
    elements_by_id: dict[str, CodeElement] = field(default_factory=dict)
    elements_by_name: dict[str, list[str]] = field(default_factory=dict)
    elements_by_file: dict[str, list[str]] = field(default_factory=dict)
    elements_by_type: dict[str, list[str]] = field(default_factory=dict)
    
    # Statistics
    total_elements: int = 0
    total_functions: int = 0
    total_classes: int = 0
    total_methods: int = 0
    total_lines_indexed: int = 0
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    version: int = 1
    
    def add_element(self, element: CodeElement) -> None:
        """Add an element to all indices."""
        self.elements_by_id[element.id] = element
        self.elements_by_name.setdefault(element.name, []).append(element.id)
        self.elements_by_file.setdefault(element.file_path, []).append(element.id)
        self.elements_by_type.setdefault(element.type.value, []).append(element.id)
        
        self.total_elements += 1
        if element.type == CodeType.FUNCTION:
            self.total_functions += 1
        elif element.type == CodeType.CLASS:
            self.total_classes += 1
        elif element.type == CodeType.METHOD:
            self.total_methods += 1
        self.total_lines_indexed += element.lines_of_code
        
        self.last_updated = datetime.now().isoformat()
    
    def get_by_name(self, name: str) -> list[CodeElement]:
        """Get all elements with a given name."""
        ids = self.elements_by_name.get(name, [])
        return [self.elements_by_id[id] for id in ids if id in self.elements_by_id]
    
    def get_by_file(self, file_path: str) -> list[CodeElement]:
        """Get all elements in a file."""
        ids = self.elements_by_file.get(file_path, [])
        return [self.elements_by_id[id] for id in ids if id in self.elements_by_id]
    
    def get_by_type(self, code_type: CodeType) -> list[CodeElement]:
        """Get all elements of a given type."""
        ids = self.elements_by_type.get(code_type.value, [])
        return [self.elements_by_id[id] for id in ids if id in self.elements_by_id]
    
    def to_summary(self) -> dict[str, Any]:
        """Generate summary statistics."""
        return {
            "project_id": self.project_id,
            "name": self.name,
            "total_elements": self.total_elements,
            "functions": self.total_functions,
            "classes": self.total_classes,
            "methods": self.total_methods,
            "lines_indexed": self.total_lines_indexed,
            "files_indexed": len(self.elements_by_file),
            "created_at": self.created_at,
            "last_updated": self.last_updated,
        }