"""Base scanner class for security scanners."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple

from ..config import PenTestFinding, PenTestSeverity


class BaseScanner(ABC):
    """Abstract base class for security scanners."""

    def __init__(self):
        """Initialize scanner."""
        self.name = self.__class__.__name__

    @abstractmethod
    def scan(self, codebase_path: Path) -> Tuple[list[PenTestFinding], int]:
        """Scan codebase for security issues.

        Args:
            codebase_path: Path to codebase

        Returns:
            Tuple of (findings, files_scanned)
        """
        pass

    @abstractmethod
    def scan_file(self, file_path: Path) -> Tuple[list[PenTestFinding], int]:
        """Scan a single file for security issues.

        Args:
            file_path: Path to file

        Returns:
            Tuple of (findings, lines_scanned)
        """
        pass

    def _should_exclude_file(self, file_path: Path, exclude_patterns: list[str]) -> bool:
        """Check if file should be excluded from scan.

        Args:
            file_path: Path to file
            exclude_patterns: List of patterns to exclude

        Returns:
            True if file should be excluded
        """
        file_str = str(file_path)

        for pattern in exclude_patterns:
            if pattern in file_str:
                return True

        return False
