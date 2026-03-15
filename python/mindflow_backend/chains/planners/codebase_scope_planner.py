"""Deterministic codebase scope planner for file analysis chains."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from mindflow_backend.agents.tools.filesystem.file_operations import DirectoryListTool
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

_CODE_EXTENSIONS = {
    ".py", ".pyi", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml",
    ".toml", ".sql", ".md", ".proto", ".sh", ".go", ".rs", ".java", ".kt",
}

_DOMAIN_SPECS = {
    "contracts": (
        "interfaces",
        "interface",
        "contracts",
        "contract",
        "types",
        "dto",
    ),
    "models": (
        "models",
        "model",
        "schemas",
        "schema",
        "entities",
        "entity",
    ),
    "database": (
        "repositories",
        "repository",
        "sql",
        "queries",
        "query",
        "migrations",
        "migration",
        "storage",
        "database",
        "db",
        "infra/database",
    ),
    "services": (
        "services",
        "service",
        "usecases",
        "usecase",
        "handlers",
        "controllers",
        "routes",
        "api",
    ),
    "configuration": (
        "config",
        "settings",
        "env",
    ),
}

_DATABASE_KEYWORDS = {
    "banco",
    "database",
    "db",
    "persistencia",
    "persistence",
    "repository",
    "repositories",
    "query",
    "queries",
    "sql",
    "schema",
    "schemas",
    "migration",
    "migrations",
    "model",
    "models",
    "storage",
}


@dataclass(frozen=True, slots=True)
class CodebaseFileCandidate:
    path: str
    domain: str
    score: int
    reason: str


@dataclass(frozen=True, slots=True)
class CodebaseDomain:
    name: str
    directories: list[str] = field(default_factory=list)
    candidates: list[CodebaseFileCandidate] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class CodebaseScopePlan:
    root_dir: str
    root_listing: dict
    directories_mapped: list[str]
    domains: list[CodebaseDomain]
    candidates: list[CodebaseFileCandidate]
    omitted_items: list[str] = field(default_factory=list)


class CodebaseScopePlanner:
    """Map the workspace before reading files.

    The planner is intentionally deterministic:
    1. list the root directory
    2. identify domains/layers
    3. pick representative files per domain
    """

    def __init__(self, *, max_files_per_domain: int = 4) -> None:
        self.max_files_per_domain = max_files_per_domain

    async def build_plan(self, message: str, root_dir: str) -> CodebaseScopePlan:
        root_path = Path(root_dir).resolve()
        root_listing = await self._list_root(root_path)
        directories_mapped = [
            entry["path"]
            for entry in (root_listing.get("directories") or [])
        ]

        domain_priority = self._select_domain_priority(message)
        all_files = self._collect_files(root_path)
        domain_map: dict[str, list[CodebaseFileCandidate]] = {name: [] for name in domain_priority}
        assigned_paths: set[str] = set()

        for domain_name in domain_priority:
            keywords = _DOMAIN_SPECS[domain_name]
            matched_dirs = self._matched_directories(directories_mapped, keywords)
            ranked = self._rank_candidates(
                all_files=all_files,
                domain_name=domain_name,
                keywords=keywords,
                assigned_paths=assigned_paths,
            )
            selected = ranked[: self.max_files_per_domain]
            assigned_paths.update(candidate.path for candidate in selected)
            domain_map[domain_name] = selected
            _logger.info(
                "codebase_scope_domain_selected",
                domain=domain_name,
                count=len(selected),
                matched_dirs=len(matched_dirs),
            )

        domains = [
            CodebaseDomain(
                name=domain_name,
                directories=self._matched_directories(directories_mapped, _DOMAIN_SPECS[domain_name]),
                candidates=domain_map[domain_name],
            )
            for domain_name in domain_priority
            if domain_map[domain_name] or self._matched_directories(directories_mapped, _DOMAIN_SPECS[domain_name])
        ]

        candidates = [candidate for domain in domains for candidate in domain.candidates]
        omitted_items = [
            str(path)
            for path in all_files
            if str(path) not in {candidate.path for candidate in candidates}
        ]

        return CodebaseScopePlan(
            root_dir=str(root_path),
            root_listing=root_listing,
            directories_mapped=directories_mapped,
            domains=domains,
            candidates=candidates,
            omitted_items=omitted_items,
        )

    async def _list_root(self, root_path: Path) -> dict:
        tool = DirectoryListTool()
        tool.root_dir = str(root_path)
        result = await tool.execute(
            directory_path=str(root_path),
            recursive=False,
            show_hidden=False,
        )
        if result.get("success"):
            return result.get("result") or {}
        return {"directory_path": str(root_path), "directories": [], "files": []}

    def _collect_files(self, root_path: Path) -> list[Path]:
        return [
            path
            for path in root_path.rglob("*")
            if path.is_file() and path.suffix.lower() in _CODE_EXTENSIONS
        ]

    def _select_domain_priority(self, message: str) -> list[str]:
        lowered = message.lower()
        if any(keyword in lowered for keyword in _DATABASE_KEYWORDS):
            return ["contracts", "models", "database", "services", "configuration"]
        return ["contracts", "services", "models", "configuration", "database"]

    def _matched_directories(self, directories: list[str], keywords: tuple[str, ...]) -> list[str]:
        matches = []
        lowered_keywords = tuple(keyword.lower() for keyword in keywords)
        for directory in directories:
            normalized = directory.lower()
            if any(keyword in normalized for keyword in lowered_keywords):
                matches.append(directory)
        return matches

    def _rank_candidates(
        self,
        *,
        all_files: list[Path],
        domain_name: str,
        keywords: tuple[str, ...],
        assigned_paths: set[str],
    ) -> list[CodebaseFileCandidate]:
        candidates: list[CodebaseFileCandidate] = []
        for path in all_files:
            path_str = str(path)
            if path_str in assigned_paths:
                continue

            normalized = path_str.lower()
            score = 0
            matched_keywords = [keyword for keyword in keywords if keyword in normalized]
            if matched_keywords:
                score += 100
            if path.name.startswith(("main", "app", "index")):
                score += 10
            score += max(0, 20 - len(path.parts))

            if score <= 0:
                continue

            candidates.append(
                CodebaseFileCandidate(
                    path=path_str,
                    domain=domain_name,
                    score=score,
                    reason=", ".join(matched_keywords) if matched_keywords else "representative file",
                )
            )

        candidates.sort(key=lambda item: (-item.score, item.path))
        return candidates

