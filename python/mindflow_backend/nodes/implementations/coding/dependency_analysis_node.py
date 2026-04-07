"""DependencyAnalysisNode - Analyze dependencies before implementation.

This node analyzes project dependencies, detects conflicts, identifies
missing dependencies, and suggests updates before implementation.
"""

from __future__ import annotations

import time
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType

_logger = get_logger(__name__)


class DependencyAnalysisNode(BaseNode):
    """Analyze dependencies before implementation.

    This node examines the project's dependencies, detects version conflicts,
    identifies missing dependencies, and suggests updates to ensure smooth
    implementation.
    """

    def __init__(self, node_id: str = "dependency_analysis") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.AGENT,
            category=NodeCategory.TOOL_EXECUTION,
            description="Analyze dependencies and detect conflicts.",
        )
        self.config.required_inputs = {
            "working_directory",
            "project_context",
        }
        self.config.outputs = {
            "dependencies_analysis",
            "conflicts",
            "suggestions",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute dependency analysis."""
        start_time = time.time()
        try:
            working_directory = state.get("working_directory", ".")
            project_context = state.get("project_context", {})

            _logger.debug(
                "dependency_analysis_start",
                node_id=self.node_id,
                working_dir=working_directory,
                project_type=project_context.get("project_type", "unknown"),
            )

            # Analyze dependencies
            dependencies_analysis = await self._analyze_dependencies(
                working_directory, project_context
            )

            # Detect conflicts
            conflicts = await self._detect_conflicts(dependencies_analysis)

            # Generate suggestions
            suggestions = await self._generate_suggestions(
                dependencies_analysis, conflicts
            )

            result = {
                "dependencies_analysis": dependencies_analysis,
                "conflicts": conflicts,
                "suggestions": suggestions,
                "current_phase": "dependencies_analyzed",
            }

            duration = time.time() - start_time
            _logger.info(
                "dependency_analysis_complete",
                node_id=self.node_id,
                duration=duration,
                conflicts_count=len(conflicts),
                suggestions_count=len(suggestions),
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            _logger.error(
                "dependency_analysis_failed",
                node_id=self.node_id,
                duration=duration,
                error=str(e),
            )
            return {
                "current_phase": "error",
                "error": str(e),
                "dependencies_analysis": {},
                "conflicts": [],
                "suggestions": [],
            }

    async def _analyze_dependencies(
        self, working_directory: str, project_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze project dependencies.

        Args:
            working_directory: Working directory
            project_context: Project context

        Returns:
            Dictionary with dependency analysis
        """
        from pathlib import Path

        project_type = project_context.get("project_type", "unknown")
        dependencies = {
            "external": [],
            "internal": [],
            "dev": [],
            "versions": {},
        }

        try:
            if project_type == "python":
                # Check requirements.txt
                req_file = Path(working_directory) / "requirements.txt"
                if req_file.exists():
                    content = req_file.read_text()
                    for line in content.split("\n"):
                        line = line.strip()
                        if line and not line.startswith("#"):
                            # Parse version spec with multiple operators
                            import re
                            
                            # Match package name and version spec
                            # Patterns: package>=1.0.0, package==1.0.0, package<=1.0.0, package~=1.0.0, etc.
                            version_match = re.match(r"^([a-zA-Z0-9_-]+)([~><=!]+)([^;#\s]+)", line)
                            if version_match:
                                package = version_match.group(1)
                                operator = version_match.group(2)
                                version = version_match.group(3)
                                dependencies["external"].append(package)
                                dependencies["versions"][package] = f"{operator}{version}"
                            else:
                                # No version spec, just package name
                                # Remove any comments or extras
                                package = line.split("#")[0].split(";")[0].strip()
                                if package:
                                    dependencies["external"].append(package)
                                    dependencies["versions"][package] = "any"

                # Check pyproject.toml
                pyproject = Path(working_directory) / "pyproject.toml"
                if pyproject.exists():
                    content = pyproject.read_text()
                    # Simplified parsing
                    if "dependencies" in content:
                        _logger.debug("found_pyproject_dependencies")

            elif project_type in ("typescript", "javascript"):
                # Check package.json
                package_json = Path(working_directory) / "package.json"
                if package_json.exists():
                    import json
                    content = json.loads(package_json.read_text())

                    dependencies["external"] = list(content.get("dependencies", {}).keys())
                    dependencies["dev"] = list(content.get("devDependencies", {}).keys())
                    dependencies["versions"] = {
                        **content.get("dependencies", {}),
                        **content.get("devDependencies", {}),
                    }

        except Exception as e:
            _logger.warning("dependency_parsing_failed", error=str(e))
            dependencies["error"] = str(e)

        return dependencies

    async def _detect_conflicts(
        self, dependencies: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Detect dependency conflicts.

        Args:
            dependencies: Dependency analysis result

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Check for known conflicting packages
        known_conflicts = {
            "python": [
                ("numpy", "tensorflow", "Version compatibility"),
                ("django", "flask", "Framework conflict"),
            ],
            "javascript": [
                ("react", "vue", "Framework conflict"),
                ("webpack", "vite", "Build tool conflict"),
            ],
        }

        external_deps = dependencies.get("external", [])

        # Simple conflict detection (would be more sophisticated)
        for dep1, dep2, reason in known_conflicts.get("python", []):
            if dep1 in external_deps and dep2 in external_deps:
                conflicts.append({
                    "packages": [dep1, dep2],
                    "reason": reason,
                    "severity": "high",
                })

        return conflicts

    async def _generate_suggestions(
        self, dependencies: dict[str, Any], conflicts: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate update suggestions.

        Args:
            dependencies: Dependency analysis
            conflicts: Detected conflicts

        Returns:
            List of suggestions
        """
        suggestions = []

        # Suggest updates for conflicts
        for conflict in conflicts:
            suggestions.append({
                "type": "conflict_resolution",
                "message": f"Resolve conflict between {conflict['packages']}: {conflict['reason']}",
                "action": "review_dependencies",
                "priority": "high",
            })

        # Suggest version updates (simplified)
        versions = dependencies.get("versions", {})
        for package, version in versions.items():
            if version == "any":
                suggestions.append({
                    "type": "version_pin",
                    "message": f"Consider pinning version for {package}",
                    "package": package,
                    "action": "pin_version",
                    "priority": "low",
                })

        return suggestions

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []

        if "working_directory" not in state:
            errors.append("Missing required input: working_directory")

        if "project_context" not in state:
            errors.append("Missing required input: project_context")

        return errors
