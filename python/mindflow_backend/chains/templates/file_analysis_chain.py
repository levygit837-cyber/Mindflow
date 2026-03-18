"""File Analysis Chain — sequential file discovery, reading, and structuring.

Workflow:
  1. intent_analysis  — LLM identifies target files/patterns from user request
  2. discovery        — filesystem scan to find matching files within root_dir
  3. sequential_read  — read files one by one via FileReadTool (respects security)
  4. structure        — LLM structures collected content into a coherent analysis

The chain does NOT create LLM instances. The Orchestrator passes the specialist
via ``context["llm"]`` (a LangChain model) so that chain behavior is fully
controlled by whoever invoked it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mindflow_backend.agents.tools.filesystem.file_operations import (
    DirectoryListTool,
    FileReadTool,
)
from mindflow_backend.chains.planners.codebase_scope_planner import CodebaseScopePlanner
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.workflow import WorkflowPlan

_logger = get_logger(__name__)


_INTENT_SYSTEM = """\
You are a file analysis planner. Given a user request and optional working directory,
identify which files need to be read to fully answer the request.

Respond ONLY with valid JSON (no markdown, no explanation):
{
  "target_files": ["path/to/specific_file.py"],
  "patterns": ["**/*.py", "src/**/*.ts"],
  "target_dirs": ["src/", "tests/"],
  "purpose": "brief description of the analysis goal",
  "priority_order": ["most_critical_pattern_first"]
}"""


_STRUCTURE_SYSTEM = """\
You are a code analysis expert. Given collected file contents, produce a structured analysis
that directly addresses the user's request. Format your response with:

- **Executive Summary** — main findings in 2–3 sentences
- **Key Findings** — per file or component, what matters
- **Patterns & Relationships** — connections across files
- **Actionable Insights** — concrete recommendations

Be concise, technical, and focused on what the user actually asked."""


@dataclass(frozen=True, slots=True)
class FileAnalysisChainConfig:
    chain_id: str = "file_analysis"
    max_files_to_read: int = 20
    max_file_size_chars: int = 8_000
    max_context_chars: int = 60_000


class FileAnalysisChain:
    """Sequential file analysis: intent → discover → read → structure.

    Requires ``context["llm"]`` — the LLM instance injected by the Orchestrator.
    """

    def __init__(self, config: FileAnalysisChainConfig | None = None) -> None:
        self.config = config or FileAnalysisChainConfig()
        self.settings = get_settings()
        self.scope_planner = CodebaseScopePlanner(max_files_per_domain=max(2, self.config.max_files_to_read // 5))

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        message: str = context.get("message") or ""
        if not message.strip():
            return {"response": "", "error": "FileAnalysisChain: `message` is required."}

        # LLM must be provided by the Orchestrator — chains do not create their own.
        llm = context.get("llm")
        if llm is None:
            return {
                "response": "",
                "error": (
                    "FileAnalysisChain: `llm` is required in context. "
                    "The Orchestrator must inject the specialist LLM before calling this chain."
                ),
            }

        root_dir: str | None = (
            context.get("root_dir")
            or context.get("folder_path")
            or getattr(self.settings, "working_path", None)
        )
        session_id: str = str(context.get("session_id") or "")

        _logger.info("file_analysis_chain_start", session_id=session_id, root_dir=root_dir)
        identity = self._extract_workflow_identity(context)

        planning_result = await self._run_scope_planner(message, root_dir)

        # Step 1 — Intent Analysis (kept as descriptive metadata, not discovery driver)
        intent_result = await self._run_intent_analysis(
            message,
            root_dir,
            llm,
            planner_result=planning_result,
        )
        if intent_result.get("error"):
            return intent_result

        # Step 2 — Discovery
        if planning_result["discovered_files"]:
            discovery_result = {
                "discovered_files": planning_result["discovered_files"],
                "directory_map": planning_result["directory_map"],
                "coverage": planning_result["coverage"],
            }
        else:
            discovery_result = await self._run_discovery(root_dir, intent_result["intent"])
            discovery_result["coverage"] = {
                "directories_mapped": planning_result["coverage"]["directories_mapped"],
                "files_considered": discovery_result["discovered_files"],
                "domains_covered": planning_result["coverage"]["domains_covered"],
                "omitted_items": planning_result["coverage"]["omitted_items"],
            }

        # Step 3 — Sequential Read
        read_result = await self._run_sequential_read(root_dir, discovery_result["discovered_files"])

        # Step 4 — Structure
        structure_result = await self._run_structure(
            message=message,
            file_contents=read_result["file_contents"],
            directory_map=discovery_result["directory_map"],
            llm=llm,
        )

        return {
            "response": structure_result.get("response", ""),
            "error": structure_result.get("error"),
            "chain": {
                "intent": intent_result["intent"],
                "discovered_files": discovery_result["discovered_files"],
                "directory_map": discovery_result["directory_map"],
                "files_read": list(read_result["file_contents"].keys()),
                "read_errors": read_result["read_errors"],
                "coverage": {
                    **(discovery_result.get("coverage") or {}),
                    "files_read": list(read_result["file_contents"].keys()),
                },
                "structured_data": {"files_analyzed": list(read_result["file_contents"].keys())},
                **identity,
            },
        }

    def _extract_workflow_identity(self, context: dict[str, Any]) -> dict[str, Any]:
        """Extract agent identity from the compiled workflow plan when present."""
        workflow_plan = context.get("workflow_plan")
        if not workflow_plan:
            return {}

        try:
            plan = WorkflowPlan.model_validate(workflow_plan)
        except Exception:
            return {}

        if not plan.steps:
            return {}

        step = plan.steps[0]
        return {
            "step_id": step.step_id,
            "agent_id": step.agent_id,
            "agent_role": step.agent_role,
            "specialist": step.specialist,
        }

    # ------------------------------------------------------------------ steps

    async def _run_intent_analysis(
        self,
        message: str,
        root_dir: str | None,
        llm: Any,
        planner_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ask the LLM to identify files and patterns needed to answer the request."""
        try:
            if planner_result and planner_result.get("discovered_files"):
                coverage = planner_result["coverage"]
                return {
                    "intent": {
                        "target_files": planner_result["discovered_files"],
                        "patterns": [],
                        "target_dirs": coverage.get("directories_mapped", []),
                        "purpose": message[:200],
                        "priority_order": coverage.get("domains_covered", []),
                        "selection_mode": "deterministic_scope_planner",
                    }
                }

            context_hint = f"\nWorking directory: {root_dir}" if root_dir else ""
            response = await llm.ainvoke([
                {"role": "system", "content": _INTENT_SYSTEM},
                {"role": "user", "content": f"Request:{context_hint}\n\n{message}"},
            ])
            raw = response.content if hasattr(response, "content") else str(response)
            intent = _extract_json(raw) or {
                "target_files": [],
                "patterns": ["**/*.py", "**/*.ts", "**/*.js"],
                "target_dirs": ["."],
                "purpose": message[:200],
                "priority_order": [],
            }
            _logger.info(
                "file_analysis_intent_done",
                patterns=intent.get("patterns"),
                target_files=len(intent.get("target_files") or []),
            )
            return {"intent": intent}
        except Exception as exc:
            _logger.error("file_analysis_intent_failed", error=str(exc))
            return {"response": "", "error": f"Intent analysis failed: {exc}"}

    async def _run_discovery(
        self,
        root_dir: str | None,
        intent: dict[str, Any],
    ) -> dict[str, Any]:
        """Discover files matching intent patterns within root_dir."""
        search_root = Path(root_dir) if root_dir else Path(".")
        discovered: list[str] = []
        directory_map: dict[str, Any] = {}

        # Get top-level directory structure for the map
        try:
            dir_tool = DirectoryListTool()
            dir_tool.root_dir = root_dir
            dir_result = await dir_tool.execute(
                directory_path=str(search_root),
                recursive=False,
                show_hidden=False,
            )
            if dir_result.get("success"):
                directory_map = dir_result.get("result") or {}
        except Exception as exc:
            _logger.warning("discovery_dir_tool_failed", error=str(exc))

        # Add specific target files if they exist
        for tf in intent.get("target_files") or []:
            candidate = Path(tf) if Path(tf).is_absolute() else search_root / tf
            if candidate.is_file():
                path_str = str(candidate)
                if path_str not in discovered:
                    discovered.append(path_str)

        # Glob patterns within target_dirs
        target_dirs = intent.get("target_dirs") or ["."]
        patterns = intent.get("patterns") or ["**/*.py"]

        for base in target_dirs:
            base_path = Path(base) if Path(base).is_absolute() else search_root / base
            if not base_path.exists():
                continue
            for pattern in patterns:
                try:
                    for match in base_path.glob(pattern):
                        if match.is_file():
                            path_str = str(match)
                            if path_str not in discovered:
                                discovered.append(path_str)
                except Exception as exc:
                    _logger.warning("discovery_glob_failed", pattern=pattern, error=str(exc))

        discovered = discovered[: self.config.max_files_to_read]
        _logger.info("file_analysis_discovery_done", files=len(discovered))
        return {"discovered_files": discovered, "directory_map": directory_map}

    async def _run_scope_planner(
        self,
        message: str,
        root_dir: str | None,
    ) -> dict[str, Any]:
        if not root_dir:
            return {
                "discovered_files": [],
                "directory_map": {},
                "coverage": {
                    "directories_mapped": [],
                    "files_considered": [],
                    "domains_covered": [],
                    "omitted_items": [],
                },
            }

        plan = await self.scope_planner.build_plan(message=message, root_dir=root_dir)
        discovered_files = [candidate.path for candidate in plan.candidates[: self.config.max_files_to_read]]
        coverage = {
            "directories_mapped": plan.directories_mapped,
            "files_considered": [candidate.path for candidate in plan.candidates],
            "domains_covered": [domain.name for domain in plan.domains],
            "omitted_items": plan.omitted_items,
        }
        return {
            "plan": plan,
            "discovered_files": discovered_files,
            "directory_map": plan.root_listing,
            "coverage": coverage,
        }

    async def _run_sequential_read(
        self,
        root_dir: str | None,
        files: list[str],
    ) -> dict[str, Any]:
        """Read files one by one using FileReadTool (enforces security boundaries)."""
        reader = FileReadTool()
        reader.root_dir = root_dir

        file_contents: dict[str, str] = {}
        read_errors: list[str] = []

        for file_path in files:
            try:
                result = await reader.execute(file_path=file_path)
                if result.get("success"):
                    raw_result = result.get("result") or {}
                    if isinstance(raw_result, dict):
                        content = (
                            raw_result.get("content")
                            or raw_result.get("text")
                            or raw_result.get("data")
                            or ""
                        )
                    else:
                        content = str(raw_result) if raw_result else ""
                    if len(content) > self.config.max_file_size_chars:
                        content = content[: self.config.max_file_size_chars] + "\n...[truncado]"
                    file_contents[file_path] = content
                else:
                    read_errors.append(f"{file_path}: {result.get('error', 'read failed')}")
            except Exception as exc:
                read_errors.append(f"{file_path}: {exc}")
                _logger.warning("file_read_failed", path=file_path, error=str(exc))

        _logger.info("sequential_read_done", read=len(file_contents), errors=len(read_errors))
        return {"file_contents": file_contents, "read_errors": read_errors}

    async def _run_structure(
        self,
        *,
        message: str,
        file_contents: dict[str, str],
        directory_map: dict[str, Any],
        llm: Any,
    ) -> dict[str, Any]:
        """LLM structures collected file contents into an analysis."""
        if not file_contents:
            return {
                "response": "Nenhum arquivo encontrado ou acessível para análise.",
                "error": None,
            }

        # Build content block within token budget
        parts: list[str] = []
        total = 0
        for path, content in file_contents.items():
            entry = f"### {path}\n```\n{content}\n```\n"
            if total + len(entry) > self.config.max_context_chars:
                parts.append(f"### {path}\n[omitido — limite de contexto atingido]\n")
            else:
                parts.append(entry)
                total += len(entry)

        user_content = (
            f"Solicitação original:\n{message}\n\n"
            f"Arquivos coletados:\n{''.join(parts)}"
        )

        try:
            response = await llm.ainvoke([
                {"role": "system", "content": _STRUCTURE_SYSTEM},
                {"role": "user", "content": user_content},
            ])
            text = response.content if hasattr(response, "content") else str(response)
            return {"response": text, "error": None}
        except Exception as exc:
            _logger.error("file_analysis_structure_failed", error=str(exc))
            return {"response": "", "error": f"Structure step failed: {exc}"}


# ---------------------------------------------------------------------------
# Shared JSON utility  (re-imported by conditional + parallel chains)
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict[str, Any] | None:
    """Extract the first JSON object from an LLM response, tolerating markdown fences."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for fence in ("```json", "```"):
        if fence in text:
            after = text[text.index(fence) + len(fence):]
            close = after.find("```")
            snippet = after[:close].strip() if close != -1 else after.strip()
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                pass
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    break
    return None


def create_file_analysis_chain(
    config: FileAnalysisChainConfig | None = None,
) -> FileAnalysisChain:
    """Factory function for chain registry."""
    return FileAnalysisChain(config)
