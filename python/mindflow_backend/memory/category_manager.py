"""Category Manager for the Intelligent Memory System.

Manages memory categories with support for:
- Base categories (fixed system-wide)
- Dynamic sub-categories (project-specific)
- Automatic classification
- Scope management (global vs project)
- In-memory caching for performance
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.storage.models import (
    MemoryCategory,
    MemoryCategoryType,
    MemorySubCategory,
    ProjectMemory,
)

_logger = get_logger(__name__)


class MemoryScope(str, Enum):
    """Scope of memory entries."""
    GLOBAL = "global"
    PROJECT = "project"
    SESSION = "session"


class MemoryType(str, Enum):
    """Types of memory entries."""
    FACT = "fact"
    PATTERN = "pattern"
    PREFERENCE = "preference"
    ERROR = "error"
    INSIGHT = "insight"
    CONTEXT = "context"


class CategoryManager:
    """Manages memory categories and sub-categories.

    Provides:
    - Base category definitions (fixed)
    - Dynamic sub-category creation
    - Automatic content classification
    - Project-scoped category management
    - In-memory caching with TTL for performance
    """

    # Base categories (fixed, system-wide)
    BASE_CATEGORIES: dict[str, dict[str, Any]] = {
        "code_patterns": {
            "description": "Padrões de código identificados durante execuções",
            "is_dynamic": True,
            "default_importance": 0.6,
            "auto_extract": True,
        },
        "user_preferences": {
            "description": "Preferências do usuário sobre código, estilo, ferramentas",
            "is_dynamic": True,
            "default_importance": 0.7,
            "auto_extract": True,
        },
        "project_context": {
            "description": "Contexto específico do projeto",
            "is_dynamic": True,
            "default_importance": 0.6,
            "auto_extract": True,
        },
        "execution_patterns": {
            "description": "Padrões de execução de graphs e agentes",
            "is_dynamic": False,
            "default_importance": 0.5,
            "auto_extract": True,
        },
        "tool_usage": {
            "description": "Padrões de uso de ferramentas",
            "is_dynamic": False,
            "default_importance": 0.5,
            "auto_extract": True,
        },
        "error_patterns": {
            "description": "Padrões de erro e suas soluções",
            "is_dynamic": True,
            "default_importance": 0.8,
            "auto_extract": True,
        },
    }

    # Cache settings
    DEFAULT_CACHE_TTL = 300  # 5 minutes

    def __init__(self, cache_ttl: int | None = None) -> None:
        """Initialize the category manager.

        Args:
            cache_ttl: Cache time-to-live in seconds (default: 300s = 5min)
        """
        self._initialized = False
        self._cache_ttl = cache_ttl or self.DEFAULT_CACHE_TTL

        # In-memory caches with timestamp
        # Structure: {key: (value, timestamp)}
        self._category_cache: dict[str, tuple[Any, float]] = {}
        self._subcategory_cache: dict[str, tuple[Any, float]] = {}
        self._importance_cache: dict[str, tuple[float, float]] = {}

    def _get_cache_key(self, *parts: Any) -> str:
        """Generate a cache key from parts."""
        return ":".join(str(p) for p in parts)

    def _get_cached(self, cache: dict[str, tuple[Any, float]], key: str) -> Any | None:
        """Get value from cache if not expired."""
        if key not in cache:
            return None

        value, timestamp = cache[key]
        if time.time() - timestamp > self._cache_ttl:
            # Expired, remove from cache
            del cache[key]
            return None

        return value

    def _set_cached(self, cache: dict[str, tuple[Any, float]], key: str, value: Any) -> None:
        """Set value in cache with current timestamp."""
        cache[key] = (value, time.time())

    def _invalidate_cache(self, cache: dict[str, tuple[Any, float]], pattern: str | None = None) -> None:
        """Invalidate cache entries matching pattern."""
        if pattern is None:
            cache.clear()
        else:
            keys_to_remove = [k for k in cache.keys() if pattern in k]
            for key in keys_to_remove:
                del cache[key]

    def invalidate_category_cache(self, project_id: int | None = None) -> None:
        """Invalidate category cache.

        Args:
            project_id: If provided, only invalidate for this project
        """
        if project_id:
            self._invalidate_cache(self._category_cache, f":{project_id}:")
        else:
            self._category_cache.clear()
        _logger.debug("category_cache_invalidated", project_id=project_id)

    def invalidate_all_caches(self) -> None:
        """Invalidate all caches."""
        self._category_cache.clear()
        self._subcategory_cache.clear()
        self._importance_cache.clear()
        _logger.debug("all_category_caches_invalidated")

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache sizes
        """
        return {
            "category_cache_size": len(self._category_cache),
            "subcategory_cache_size": len(self._subcategory_cache),
            "importance_cache_size": len(self._importance_cache),
            "total_cached_items": (
                len(self._category_cache) +
                len(self._subcategory_cache) +
                len(self._importance_cache)
            ),
        }

    async def initialize(self, db: AsyncSession) -> None:
        """Initialize base categories in the database.

        Creates base category types if they don't exist.

        Args:
            db: Async database session
        """
        if self._initialized:
            return

        for name, config in self.BASE_CATEGORIES.items():
            # Check if exists
            result = await db.execute(
                select(MemoryCategoryType).where(MemoryCategoryType.name == name)
            )
            existing = result.scalar_one_or_none()

            if not existing:
                category_type = MemoryCategoryType(
                    name=name,
                    description=config["description"],
                    is_dynamic=config["is_dynamic"],
                    default_importance=config["default_importance"],
                    auto_extract=config["auto_extract"],
                )
                db.add(category_type)
                _logger.info("created_base_category_type", category_name=name)

        await db.commit()
        self._initialized = True
        _logger.info("category_manager_initialized")

    async def get_or_create_category(
        self,
        db: AsyncSession,
        project_id: int,
        category_name: str,
        description: str | None = None,
    ) -> MemoryCategory:
        """Get or create a memory category for a project.

        Uses cache for performance. Cache is automatically invalidated
        when new categories are created.

        Args:
            db: Async database session
            project_id: ID of the project
            category_name: Name of the category (must be in BASE_CATEGORIES)
            description: Optional description

        Returns:
            MemoryCategory instance

        Raises:
            ValueError: If category_name is not a valid base category
        """
        if category_name not in self.BASE_CATEGORIES:
            raise ValueError(
                f"Invalid category: {category_name}. "
                f"Must be one of: {list(self.BASE_CATEGORIES.keys())}"
            )

        # Check cache first
        cache_key = self._get_cache_key("category", project_id, category_name)
        cached = self._get_cached(self._category_cache, cache_key)
        if cached:
            _logger.debug("category_cache_hit", project_id=project_id, category_name=category_name)
            return cached

        # Try to find existing
        result = await db.execute(
            select(MemoryCategory).where(
                MemoryCategory.project_id == project_id,
                MemoryCategory.name == category_name,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Store in cache
            self._set_cached(self._category_cache, cache_key, existing)
            return existing

        # Create new category
        category = MemoryCategory(
            project_id=project_id,
            name=category_name,
            description=description or self.BASE_CATEGORIES[category_name]["description"],
            path_pattern=None,  # Can be set later
        )
        db.add(category)
        await db.flush()

        # Store new category in cache
        self._set_cached(self._category_cache, cache_key, category)

        _logger.info(
            "created_memory_category",
            category_name=category_name,
            project_id=project_id,
            category_id=category.id,
        )

        return category

    async def get_or_create_subcategory(
        self,
        db: AsyncSession,
        project_id: int,
        category_name: str,
        subcategory_name: str,
        description: str | None = None,
        path_pattern: str | None = None,
    ) -> MemorySubCategory:
        """Get or create a sub-category.

        Uses cache for performance. Cache is invalidated when new subcategories
        are created.

        Args:
            db: Async database session
            project_id: ID of the project
            category_name: Name of parent category
            subcategory_name: Name of sub-category
            description: Optional description
            path_pattern: Optional path pattern for auto-classification

        Returns:
            MemorySubCategory instance
        """
        # First ensure parent category exists (uses cache internally)
        category = await self.get_or_create_category(db, project_id, category_name)

        # Check cache first
        cache_key = self._get_cache_key("subcategory", category.id, subcategory_name)
        cached = self._get_cached(self._subcategory_cache, cache_key)
        if cached:
            _logger.debug("subcategory_cache_hit", category_id=category.id, subcategory_name=subcategory_name)
            return cached

        # Check if subcategory exists
        result = await db.execute(
            select(MemorySubCategory).where(
                MemorySubCategory.category_id == category.id,
                MemorySubCategory.name == subcategory_name,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Store in cache
            self._set_cached(self._subcategory_cache, cache_key, existing)
            return existing

        # Create new subcategory
        subcategory = MemorySubCategory(
            category_id=category.id,
            name=subcategory_name,
            path_pattern=path_pattern,
            description=description,
        )
        db.add(subcategory)
        await db.flush()

        # Store new subcategory in cache
        self._set_cached(self._subcategory_cache, cache_key, subcategory)

        _logger.info(
            "created_memory_subcategory",
            subcategory_name=subcategory_name,
            category_name=category_name,
            project_id=project_id,
            subcategory_id=subcategory.id,
        )

        return subcategory

    def classify_content(
        self,
        content: str,
        memory_type: str | None = None,
        source_tool: str | None = None,
        file_path: str | None = None,
    ) -> tuple[str, str | None]:
        """Classify content into (category, subcategory).

        Uses heuristics based on content analysis, tool used, and file path.

        Args:
            content: The content to classify
            memory_type: Type of memory (fact, pattern, preference, etc.)
            source_tool: Tool that generated the memory
            file_path: File path associated with the content

        Returns:
            Tuple of (category_name, subcategory_name | None)
        """
        content_lower = content.lower()

        # Heuristic 1: Based on file path
        if file_path:
            category, subcategory = self._classify_by_path(file_path)
            if category:
                return category, subcategory

        # Heuristic 2: Based on source tool
        if source_tool:
            category = self._classify_by_tool(source_tool)
            if category:
                return category, None

        # Heuristic 3: Based on content analysis
        category = self._classify_by_content(content_lower, memory_type)
        return category, None

    def _classify_by_path(self, file_path: str) -> tuple[str | None, str | None]:
        """Classify based on file path patterns."""
        path_lower = file_path.lower()

        # Code patterns
        if any(x in path_lower for x in ["/test", "_test.", "test_"]):
            return "code_patterns", "tests"
        if any(x in path_lower for x in ["/api/", "/routes/", "/controllers/"]):
            return "code_patterns", "api"
        if any(x in path_lower for x in ["/models/", "/schemas/", "/entities/"]):
            return "code_patterns", "models"
        if any(x in path_lower for x in ["/service", "/services/"]):
            return "code_patterns", "services"
        if any(x in path_lower for x in ["/frontend/", "/components/", "/ui/"]):
            return "code_patterns", "frontend"

        # Config/Error patterns
        if any(x in path_lower for x in ["config", ".env", "settings"]):
            return "project_context", "config"
        if any(x in path_lower for x in ["error", "exception", "handler"]):
            return "error_patterns", None

        return None, None

    def _classify_by_tool(self, source_tool: str) -> str | None:
        """Classify based on source tool."""
        tool_lower = source_tool.lower()

        tool_category_map = {
            "write_file": "code_patterns",
            "edit_file": "code_patterns",
            "replace_in_file": "code_patterns",
            "apply_diff": "code_patterns",
            "search": "execution_patterns",
            "grep": "execution_patterns",
            "browser": "execution_patterns",
            "test": "code_patterns",
            "lint": "error_patterns",
            "format": "code_patterns",
        }

        for tool_pattern, category in tool_category_map.items():
            if tool_pattern in tool_lower:
                return category

        return None

    def _classify_by_content(
        self, content_lower: str, memory_type: str | None
    ) -> str:
        """Classify based on content analysis."""
        # Priority: memory_type if provided
        if memory_type:
            type_category_map = {
                "error": "error_patterns",
                "preference": "user_preferences",
                "fact": "project_context",
                "pattern": "code_patterns",
            }
            if memory_type in type_category_map:
                return type_category_map[memory_type]

        # Content keywords
        if any(word in content_lower for word in ["erro", "error", "exception", "falha", "fail"]):
            return "error_patterns"
        if any(word in content_lower for word in ["prefer", "prefiro", "gosto", "like", "prefer"]):
            return "user_preferences"
        if any(word in content_lower for word in ["padrão", "pattern", "costume", "usually"]):
            return "code_patterns"
        if any(word in content_lower for word in ["projeto", "project", "contexto", "context"]):
            return "project_context"

        # Default
        return "project_context"

    async def get_category_importance(
        self,
        db: AsyncSession,
        category_name: str,
    ) -> float:
        """Get default importance for a category.

        Uses cache for database lookups. Base categories are returned
        directly without cache since they are in memory.

        Args:
            db: Async database session
            category_name: Name of the category

        Returns:
            Default importance score (0.0-1.0)
        """
        # Check base categories first (fast path, no cache needed)
        if category_name in self.BASE_CATEGORIES:
            return self.BASE_CATEGORIES[category_name]["default_importance"]

        # Check cache for database lookup
        cache_key = self._get_cache_key("importance", category_name)
        cached = self._get_cached(self._importance_cache, cache_key)
        if cached is not None:
            _logger.debug("importance_cache_hit", category_name=category_name)
            return cached

        # Check database
        result = await db.execute(
            select(MemoryCategoryType).where(MemoryCategoryType.name == category_name)
        )
        category_type = result.scalar_one_or_none()

        if category_type:
            importance = category_type.default_importance
            # Cache the result
            self._set_cached(self._importance_cache, cache_key, importance)
            return importance

        return 0.5  # Default fallback

    async def list_categories(
        self,
        db: AsyncSession,
        project_id: int | None = None,
    ) -> list[MemoryCategory]:
        """List all categories.

        Args:
            db: Async database session
            project_id: Optional project ID to filter by

        Returns:
            List of MemoryCategory instances
        """
        if project_id:
            result = await db.execute(
                select(MemoryCategory).where(MemoryCategory.project_id == project_id)
            )
        else:
            result = await db.execute(select(MemoryCategory))

        return list(result.scalars().all())

    async def list_subcategories(
        self,
        db: AsyncSession,
        category_id: int,
    ) -> list[MemorySubCategory]:
        """List subcategories for a category.

        Args:
            db: Async database session
            category_id: ID of the parent category

        Returns:
            List of MemorySubCategory instances
        """
        result = await db.execute(
            select(MemorySubCategory).where(MemorySubCategory.category_id == category_id)
        )
        return list(result.scalars().all())
