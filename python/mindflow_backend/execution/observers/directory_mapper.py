"""Directory Mapper for automatic memory categorization.

Maps file paths to hierarchical memory categories using glob patterns.
Enables automatic categorization of code changes by project structure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

from mindflow_backend.infra.logging import get_logger

logger = get_logger(__name__)


class DirectoryMapper:
    """Maps file paths to memory categories using glob patterns.

    Provides automatic categorization of code changes based on directory structure.
    Supports hierarchical categorization (Category > SubCategory).
    """

    def __init__(self, project_root: str):
        """Initialize DirectoryMapper with project root path.

        Args:
            project_root: Absolute path to project root directory
        """
        self.project_root = Path(project_root)
        self.category_map = self._build_default_category_map()

    def _build_default_category_map(self) -> Dict[str, Tuple[str, str | None]]:
        """Build default category mapping for common project structures.

        Returns:
            Dict mapping glob patterns to (category, subcategory) tuples
        """
        return {
            # Backend API (most specific first)
            "**/api/v1/**": ("API", "V1"),
            "**/api/middleware/**": ("API", "Middleware"),
            "**/api/routes/**": ("API", "Routes"),
            "**/api/**": ("API", "Endpoints"),

            # Services
            "**/services/core/**": ("Services", "Core"),
            "**/services/external/**": ("Services", "External"),
            "**/services/**": ("Services", "Core"),

            # Agents
            "**/agents/tools/**": ("Agents", "Tools"),
            "**/agents/prompts/**": ("Agents", "Prompts"),
            "**/agents/**": ("Agents", "Specialists"),

            # Orchestrator
            "**/orchestrator/delegation/**": ("Orchestrator", "Delegation"),
            "**/orchestrator/planning/**": ("Orchestrator", "Planning"),
            "**/orchestrator/**": ("Orchestrator", "Routing"),

            # Memory
            "**/memory/agent_memory/**": ("Memory", "AgentMemory"),
            "**/memory/session_memory/**": ("Memory", "SessionMemory"),
            "**/memory/storage/**": ("Memory", "Storage"),
            "**/memory/**": ("Memory", "Storage"),

            # Execution
            "**/execution/observers/**": ("Execution", "Observers"),
            "**/execution/teams/**": ("Execution", "Teams"),
            "**/execution/**": ("Execution", "Runtime"),

            # Infrastructure
            "**/infra/database/**": ("Infrastructure", "Database"),
            "**/infra/config/**": ("Infrastructure", "Config"),
            "**/infra/**": ("Infrastructure", "Core"),

            # Storage
            "**/storage/postgresql/**": ("Storage", "PostgreSQL"),
            "**/storage/**": ("Storage", "Database"),

            # Runtime
            "**/runtime/monitoring/**": ("Runtime", "Monitoring"),
            "**/runtime/**": ("Runtime", "Core"),

            # Frontend
            "frontend/src/components/**": ("Frontend", "Components"),
            "frontend/src/pages/**": ("Frontend", "Pages"),
            "frontend/src/hooks/**": ("Frontend", "Hooks"),
            "frontend/src/store/**": ("Frontend", "Store"),
            "frontend/src/api/**": ("Frontend", "API"),
            "frontend/src/utils/**": ("Frontend", "Utils"),

            # CLI
            "cli/src/components/**": ("CLI", "Components"),
            "cli/src/commands/**": ("CLI", "Commands"),
            "cli/src/utils/**": ("CLI", "Utils"),

            # Tests
            "**/tests/unit/**": ("Tests", "Unit"),
            "**/tests/integration/**": ("Tests", "Integration"),
            "**/tests/live/**": ("Tests", "Live"),
            "frontend/tests/**": ("Tests", "Frontend"),

            # Documentation
            "docs/architecture/**": ("Documentation", "Architecture"),
            "docs/PRD/**": ("Documentation", "PRD"),
            "docs/**": ("Documentation", "General"),

            # Configuration
            "*.toml": ("Configuration", "Root"),
            "*.yaml": ("Configuration", "Root"),
            "*.yml": ("Configuration", "Root"),
            "*.json": ("Configuration", "Root"),
            ".env*": ("Configuration", "Environment"),
        }

    def add_pattern(self, pattern: str, category: str, subcategory: str | None = None) -> None:
        """Add a custom pattern to the category map.

        Args:
            pattern: Glob pattern to match (e.g., "src/custom/**")
            category: Category name
            subcategory: Optional subcategory name
        """
        self.category_map[pattern] = (category, subcategory)
        logger.debug(
            "directory_mapper_pattern_added",
            extra={"pattern": pattern, "category": category, "subcategory": subcategory},
        )

    def categorize_file(self, file_path: str) -> Tuple[str, str | None]:
        """Categorize a file path into (category, subcategory).

        Args:
            file_path: Absolute or relative file path

        Returns:
            Tuple of (category, subcategory). Subcategory may be None.
        """
        try:
            # Convert to Path and make relative to project root
            path = Path(file_path)

            # If absolute, make relative to project root
            if path.is_absolute():
                try:
                    rel_path = path.relative_to(self.project_root)
                except ValueError:
                    # Path is outside project root - use as-is
                    rel_path = path
            else:
                rel_path = path

            # Try to match against patterns (most specific first)
            sorted_patterns = sorted(
                self.category_map.items(),
                key=lambda x: len(x[0]),
                reverse=True,
            )

            for pattern, (category, subcategory) in sorted_patterns:
                if rel_path.match(pattern):
                    logger.debug(
                        "directory_mapper_match",
                        extra={
                            "file_path": str(file_path),
                            "pattern": pattern,
                            "category": category,
                            "subcategory": subcategory,
                        },
                    )
                    return (category, subcategory)

            # Fallback: use first directory as category, second as subcategory
            parts = rel_path.parts
            if len(parts) >= 2:
                category = parts[0].replace("_", " ").title()
                subcategory = parts[1].replace("_", " ").title()
                logger.debug(
                    "directory_mapper_fallback",
                    extra={
                        "file_path": str(file_path),
                        "category": category,
                        "subcategory": subcategory,
                    },
                )
                return (category, subcategory)
            elif len(parts) == 1:
                category = parts[0].replace("_", " ").title()
                logger.debug(
                    "directory_mapper_fallback_single",
                    extra={"file_path": str(file_path), "category": category},
                )
                return (category, None)
            else:
                # Ultimate fallback
                logger.debug(
                    "directory_mapper_fallback_general",
                    extra={"file_path": str(file_path)},
                )
                return ("General", None)

        except Exception as exc:
            logger.warning(
                "directory_mapper_error",
                extra={"file_path": str(file_path), "error": str(exc)},
            )
            return ("General", None)

    def get_category_stats(self) -> Dict[str, int]:
        """Get statistics about registered patterns.

        Returns:
            Dict mapping categories to pattern count
        """
        stats: Dict[str, int] = {}
        for _, (category, _) in self.category_map.items():
            stats[category] = stats.get(category, 0) + 1
        return stats
