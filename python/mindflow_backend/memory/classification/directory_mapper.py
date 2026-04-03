"""Directory-to-Category mapper for hierarchical memory classification.

Maps file paths to MemoryCategory/MemorySubCategory using glob patterns.
Zero-cost classification (no LLM calls), deterministic, and user-extensible.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.storage.models import MemoryCategory, MemorySubCategory

_logger = get_logger(__name__)


class DirectoryMapper:
    """Maps file paths to MemoryCategory/MemorySubCategory.

    Uses glob patterns for zero-cost classification.
    Auto-creates categories when first seen.
    """

    DEFAULT_PATTERNS: dict[str, list[str]] = {
        "api": ["**/api/**", "**/routes/**", "**/endpoints/**", "**/controllers/**"],
        "services": ["**/services/**", "**/service/**"],
        "models": ["**/models/**", "**/schemas/**", "**/entities/**"],
        "tests": ["**/tests/**", "**/test_*", "**/*_test.*"],
        "config": ["**/config/**", "**/.env*", "**/settings.*"],
        "frontend": ["**/components/**", "**/pages/**", "**/views/**"],
        "infrastructure": ["**/infra/**", "**/docker*", "**/deploy/**"],
        "memory": ["**/memory/**"],
        "docs": ["**/docs/**", "**/*.md"],
    }

    def __init__(self, custom_patterns: dict[str, list[str]] | None = None):
        """Initialize mapper with optional custom patterns.

        Args:
            custom_patterns: Optional dict of category_name -> [patterns].
                             Merged with DEFAULT_PATTERNS (patterns are added, not replaced).
        """
        self.patterns = self.DEFAULT_PATTERNS.copy()
        if custom_patterns:
            for category, patterns in custom_patterns.items():
                if category in self.patterns:
                    # Merge: add custom patterns to existing ones
                    self.patterns[category] = self.patterns[category] + patterns
                else:
                    # New category: just add it
                    self.patterns[category] = patterns

    def classify(self, file_path: str) -> tuple[str, str | None]:
        """Return (category_name, subcategory_name) for a file path.

        Args:
            file_path: Relative or absolute file path to classify.

        Returns:
            Tuple of (category_name, subcategory_name).
            If no pattern matches, returns ("other", None).
            If pattern matches but no subcategory can be inferred, returns (category, None).
        """
        # Normalize path separators to forward slashes for consistent matching
        normalized_path = file_path.replace("\\", "/")

        for category_name, patterns in self.patterns.items():
            matched_pattern = self._find_matching_pattern(normalized_path, patterns)
            if matched_pattern:
                subcategory = self._infer_subcategory(normalized_path, matched_pattern)
                return (category_name, subcategory)

        # Fallback: no pattern matched
        return ("other", None)

    def _find_matching_pattern(self, path: str, patterns: list[str]) -> str | None:
        """Find the first pattern that matches the path.

        Args:
            path: Normalized file path (forward slashes).
            patterns: List of glob patterns to check.

        Returns:
            The matched pattern, or None if no match.
        """
        path_parts = path.split("/")

        for pattern in patterns:
            # Handle different pattern types
            if pattern.startswith("**/") and pattern.endswith("/**"):
                # Pattern like **/api/** - check if segment exists in path
                segment = pattern[3:-3]  # Remove **/ and /**
                if segment in path_parts:
                    return pattern
            elif pattern.startswith("**/"):
                # Pattern like **/test_* - check if any part matches the suffix pattern
                suffix_pattern = pattern[3:]  # Remove **/
                for part in path_parts:
                    if fnmatch.fnmatch(part, suffix_pattern):
                        return pattern
            elif pattern.startswith("**/*."):
                # Pattern like **/*.md - check if filename matches
                extension_pattern = pattern[3:]  # Remove **/
                filename = path_parts[-1] if path_parts else ""
                if fnmatch.fnmatch(filename, extension_pattern):
                    return pattern
            else:
                # Simple pattern without ** - use fnmatch
                if fnmatch.fnmatch(path, pattern):
                    return pattern

        return None

    def _match_pattern(self, path: str, patterns: list[str]) -> bool:
        """Check if path matches any of the given glob patterns.

        Args:
            path: Normalized file path (forward slashes).
            patterns: List of glob patterns to match against.

        Returns:
            True if path matches any pattern, False otherwise.
        """
        return self._find_matching_pattern(path, patterns) is not None

    def _infer_subcategory(self, path: str, matched_pattern: str) -> str | None:
        """Infer subcategory from path segments after the pattern match.

        Example:
            path: "python/mindflow_backend/api/middleware/auth.py"
            matched_pattern: "**/api/**"
            → subcategory: "middleware"

        Args:
            path: Normalized file path.
            matched_pattern: The pattern that matched this path.

        Returns:
            Subcategory name (first directory after pattern match), or None.
        """
        path_parts = path.split("/")

        # Extract the significant segment from the pattern
        if matched_pattern.startswith("**/") and matched_pattern.endswith("/**"):
            # Pattern like **/api/** - the segment is between **/ and /**
            segment = matched_pattern[3:-3]
        elif matched_pattern.startswith("**/"):
            # Pattern like **/test_* or **/*.md - no clear directory segment
            # Can't infer subcategory from these patterns
            return None
        else:
            # Simple pattern without ** - can't reliably infer subcategory
            return None

        # Find the segment in the path
        try:
            segment_idx = path_parts.index(segment)
        except ValueError:
            # Segment not found in path (shouldn't happen if pattern matched)
            return None

        # Subcategory is the next directory after the segment
        # Make sure it's not the filename (last element)
        if segment_idx + 1 < len(path_parts) - 1:
            return path_parts[segment_idx + 1]

        return None

    async def get_or_create_ids(
        self, db: AsyncSession, *, project_id: int, file_path: str
    ) -> tuple[int | None, int | None]:
        """Return (category_id, subcategory_id), creating records if needed.

        Args:
            db: Async database session.
            project_id: ID of the ProjectMemory this belongs to.
            file_path: File path to classify.

        Returns:
            Tuple of (category_id, subcategory_id).
            Either or both may be None if classification fails or no subcategory.
        """
        category_name, subcategory_name = self.classify(file_path)

        # Get or create category
        category_id = await self._get_or_create_category(
            db, project_id=project_id, category_name=category_name
        )

        if category_id is None:
            _logger.warning(
                "failed_to_create_category",
                project_id=project_id,
                category_name=category_name,
            )
            return (None, None)

        # Get or create subcategory if present
        subcategory_id = None
        if subcategory_name:
            subcategory_id = await self._get_or_create_subcategory(
                db, category_id=category_id, subcategory_name=subcategory_name
            )

        return (category_id, subcategory_id)

    async def _get_or_create_category(
        self, db: AsyncSession, *, project_id: int, category_name: str
    ) -> int | None:
        """Get existing category or create new one.

        Args:
            db: Async database session.
            project_id: ID of the ProjectMemory.
            category_name: Name of the category.

        Returns:
            Category ID, or None if creation failed.
        """
        # Try to find existing category
        result = await db.execute(
            select(MemoryCategory).where(
                MemoryCategory.project_id == project_id,
                MemoryCategory.name == category_name,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return existing.id

        # Create new category
        try:
            # Get the pattern for this category (for documentation)
            pattern = ", ".join(self.patterns.get(category_name, []))

            new_category = MemoryCategory(
                project_id=project_id,
                name=category_name,
                path_pattern=pattern if pattern else None,
                description=f"Auto-created category for {category_name}",
            )
            db.add(new_category)
            await db.flush()  # Flush to get the ID without committing
            return new_category.id
        except Exception as exc:
            _logger.error(
                "failed_to_create_category",
                project_id=project_id,
                category_name=category_name,
                error=str(exc),
            )
            return None

    async def _get_or_create_subcategory(
        self, db: AsyncSession, *, category_id: int, subcategory_name: str
    ) -> int | None:
        """Get existing subcategory or create new one.

        Args:
            db: Async database session.
            category_id: ID of the parent MemoryCategory.
            subcategory_name: Name of the subcategory.

        Returns:
            Subcategory ID, or None if creation failed.
        """
        # Try to find existing subcategory
        result = await db.execute(
            select(MemorySubCategory).where(
                MemorySubCategory.category_id == category_id,
                MemorySubCategory.name == subcategory_name,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return existing.id

        # Create new subcategory
        try:
            new_subcategory = MemorySubCategory(
                category_id=category_id,
                name=subcategory_name,
                description=f"Auto-created subcategory for {subcategory_name}",
            )
            db.add(new_subcategory)
            await db.flush()  # Flush to get the ID without committing
            return new_subcategory.id
        except Exception as exc:
            _logger.error(
                "failed_to_create_subcategory",
                category_id=category_id,
                subcategory_name=subcategory_name,
                error=str(exc),
            )
            return None
