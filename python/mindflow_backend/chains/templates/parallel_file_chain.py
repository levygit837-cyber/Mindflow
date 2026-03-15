"""Parallel File Analysis Chain.

Designed for large codebases or when multiple independent concerns need analysis.
Divides discovered files into logical scopes and reads all scopes concurrently,
then aggregates the results into a unified response.

Workflow:
  1. intent_analysis   — identify file patterns from user request
  2. discovery         — scan filesystem for matching files
  3. scope_definition  — LLM divides files into parallel logical scopes
  4. parallel_read     — asyncio.gather reads all scopes simultaneously
  5. aggregate         — LLM merges scope results into a unified analysis

State tracking:
  While scope X (e.g. "models") reads its files, scope Y (e.g. "routes") reads
  independently. Results are merged in the aggregate step. Each scope gets an
  equal share of the total context budget.

The chain does NOT create LLM instances. The Orchestrator passes the specialist
via ``context["llm"]`` so that chain behavior is fully controlled by whoever
invoked it.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mindflow_backend.chains.templates.file_analysis_chain import (
    FileAnalysisChain,
    FileAnalysisChainConfig,
    _extract_json,
)
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


_SCOPE_SYSTEM = """\
You are a code architecture analyst. Given a list of files and a user request,
divide the files into logical parallel analysis scopes.

Each scope should represent a coherent concern (e.g. "models", "routes", "tests",
"config", "utils"). Create at most 5 scopes. Every file must appear in exactly one scope.
Put unclassified files in a "general" scope.

Respond ONLY with valid JSON (no markdown):
{
  "scopes": [
    {
      "scope_id": "models",
      "purpose": "understand data models and schemas",
      "files": ["path/to/model.py", "path/to/schema.py"]
    },
    {
      "scope_id": "routes",
      "purpose": "understand API endpoints and request handling",
      "files": ["path/to/routes.py"]
    }
  ]
}"""


_AGGREGATE_SYSTEM = """\
You are a code synthesis expert. Given parallel analysis results from multiple file scopes,
produce a unified, coherent response to the original request.

Structure your response with:
- **Architecture Overview** — how the pieces fit together
- **Key Findings by Scope** — what each scope revealed
- **Cross-scope Relationships** — dependencies, patterns, data flows
- **Conclusions & Recommendations** — direct answer to the original request"""


@dataclass(frozen=True, slots=True)
class ParallelFileChainConfig:
    chain_id: str = "parallel_file_analysis"
    max_files_to_read: int = 40          # higher than sequential — parallelism handles the load
    max_file_size_chars: int = 6_000     # slightly smaller per-file to fit more scopes
    max_context_chars: int = 60_000      # shared total; split equally per scope
    max_scopes: int = 5


class ParallelFileChain:
    """Parallel file analysis for large codebases.

    Requires ``context["llm"]`` — the LLM instance injected by the Orchestrator.
    """

    def __init__(self, config: ParallelFileChainConfig | None = None) -> None:
        self.config = config or ParallelFileChainConfig()
        self.settings = get_settings()
        self._base = FileAnalysisChain(
            FileAnalysisChainConfig(
                max_files_to_read=self.config.max_files_to_read,
                max_file_size_chars=self.config.max_file_size_chars,
                max_context_chars=self.config.max_context_chars,
            )
        )

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        message: str = context.get("message") or ""
        if not message.strip():
            return {"response": "", "error": "ParallelFileChain: `message` is required."}

        # LLM must be provided by the Orchestrator — chains do not create their own.
        llm = context.get("llm")
        if llm is None:
            return {
                "response": "",
                "error": (
                    "ParallelFileChain: `llm` is required in context. "
                    "The Orchestrator must inject the specialist LLM before calling this chain."
                ),
            }

        root_dir: str | None = (
            context.get("root_dir")
            or context.get("folder_path")
            or getattr(self.settings, "working_path", None)
        )
        session_id: str = str(context.get("session_id") or "")

        _logger.info("parallel_file_chain_start", session_id=session_id)

        planning_result = await self._base._run_scope_planner(message, root_dir)

        # Step 1 — Intent Analysis
        intent_result = await self._base._run_intent_analysis(
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
            discovery_result = await self._base._run_discovery(root_dir, intent_result["intent"])
            discovery_result["coverage"] = planning_result["coverage"]
        discovered_files = discovery_result["discovered_files"]

        if not discovered_files:
            return {
                "response": "Nenhum arquivo encontrado para análise paralela.",
                "error": None,
                "chain": {"intent": intent_result["intent"], "discovered_files": []},
            }

        # Step 3 — Scope Definition
        _logger.info("parallel_file_chain_scope_def", files=len(discovered_files))
        if planning_result.get("plan") and planning_result["plan"].domains:
            scopes = [
                {
                    "scope_id": domain.name,
                    "purpose": f"analisar domínio {domain.name}",
                    "files": [candidate.path for candidate in domain.candidates],
                }
                for domain in planning_result["plan"].domains
                if domain.candidates
            ]
        else:
            scopes = await self._run_scope_definition(
                message=message,
                discovered_files=discovered_files,
                llm=llm,
            )

        # Step 4 — Parallel Read (all scopes at once)
        _logger.info("parallel_file_chain_parallel_read", scopes=len(scopes))
        scope_results = await self._run_parallel_read(root_dir, scopes)

        # Step 5 — Aggregate
        _logger.info("parallel_file_chain_aggregate", scopes_with_data=len(scope_results))
        aggregate_result = await self._run_aggregate(
            message=message,
            scope_results=scope_results,
            llm=llm,
        )

        return {
            "response": aggregate_result.get("response", ""),
            "error": aggregate_result.get("error"),
            "chain": {
                "intent": intent_result["intent"],
                "discovered_files": discovered_files,
                "scopes": [
                    {
                        "scope_id": s.get("scope_id", "?"),
                        "file_count": len(s.get("files") or []),
                        "purpose": s.get("purpose", ""),
                    }
                    for s in scopes
                ],
                "scope_summary": {
                    sid: {
                        "files": data["files"],
                        "chars_read": data["chars_read"],
                        "read_errors": data["read_errors"],
                    }
                    for sid, data in scope_results.items()
                },
                "coverage": {
                    **(discovery_result.get("coverage") or {}),
                    "files_read": discovered_files,
                },
            },
        }

    # ------------------------------------------------------------------ steps

    async def _run_scope_definition(
        self,
        *,
        message: str,
        discovered_files: list[str],
        llm: Any,
    ) -> list[dict[str, Any]]:
        """Ask LLM to divide discovered files into parallel logical scopes."""
        try:
            files_list = "\n".join(
                f"  - {f}" for f in discovered_files[: self.config.max_files_to_read]
            )
            user_content = (
                f"User request:\n{message}\n\n"
                f"Files to analyze:\n{files_list}\n\n"
                f"Divide into at most {self.config.max_scopes} parallel scopes."
            )
            response = await llm.ainvoke([
                {"role": "system", "content": _SCOPE_SYSTEM},
                {"role": "user", "content": user_content},
            ])
            raw = response.content if hasattr(response, "content") else str(response)
            parsed = _extract_json(raw)
            if parsed and isinstance(parsed.get("scopes"), list):
                scopes = parsed["scopes"][: self.config.max_scopes]
                _logger.info("scope_definition_done", scopes=len(scopes))
                return scopes
        except Exception as exc:
            _logger.warning("scope_definition_failed", error=str(exc))

        # Fallback: single scope with all discovered files
        return [
            {
                "scope_id": "general",
                "purpose": "full codebase analysis",
                "files": discovered_files,
            }
        ]

    async def _run_parallel_read(
        self,
        root_dir: str | None,
        scopes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Read all scopes concurrently using asyncio.gather.

        Each scope independently calls _run_sequential_read so files in scope X
        are read while scope Y files are being read at the same time.
        """

        async def read_scope(scope: dict[str, Any]) -> tuple[str, dict[str, Any]]:
            scope_id = scope.get("scope_id", "unknown")
            files = scope.get("files") or []
            purpose = scope.get("purpose", "")

            read_result = await self._base._run_sequential_read(root_dir, files)
            chars_read = sum(len(c) for c in read_result["file_contents"].values())

            _logger.info(
                "parallel_scope_read_done",
                scope_id=scope_id,
                files_read=len(read_result["file_contents"]),
                chars=chars_read,
            )
            return scope_id, {
                "purpose": purpose,
                "files": list(read_result["file_contents"].keys()),
                "file_contents": read_result["file_contents"],
                "read_errors": read_result["read_errors"],
                "chars_read": chars_read,
            }

        results = await asyncio.gather(
            *[read_scope(scope) for scope in scopes],
            return_exceptions=True,
        )

        scope_results: dict[str, Any] = {}
        for item in results:
            if isinstance(item, Exception):
                _logger.error("parallel_scope_exception", error=str(item))
            else:
                scope_id, data = item
                scope_results[scope_id] = data

        return scope_results

    async def _run_aggregate(
        self,
        *,
        message: str,
        scope_results: dict[str, Any],
        llm: Any,
    ) -> dict[str, Any]:
        """Merge all scope analyses into a unified response."""
        if not scope_results:
            return {"response": "Nenhum resultado de escopo disponível.", "error": None}

        per_scope_limit = self.config.max_context_chars // max(len(scope_results), 1)
        scope_blocks: list[str] = []

        for scope_id, data in scope_results.items():
            purpose = data.get("purpose", "")
            files = data.get("files") or []
            contents = data.get("file_contents") or {}

            short_names = ", ".join(Path(f).name for f in files[:8])
            if len(files) > 8:
                short_names += f" ... +{len(files) - 8} more"

            parts = [f"## Escopo: {scope_id} — {purpose}\nArquivos: {short_names}\n\n"]
            total = 0
            for path, content in contents.items():
                entry = f"### {path}\n```\n{content}\n```\n"
                if total + len(entry) > per_scope_limit:
                    parts.append(f"### {path}\n[omitido — limite do escopo]\n")
                else:
                    parts.append(entry)
                    total += len(entry)

            scope_blocks.append("".join(parts))

        user_content = (
            f"Solicitação original:\n{message}\n\n"
            f"Resultados dos escopos paralelos:\n{'---\n'.join(scope_blocks)}"
        )

        try:
            response = await llm.ainvoke([
                {"role": "system", "content": _AGGREGATE_SYSTEM},
                {"role": "user", "content": user_content},
            ])
            text = response.content if hasattr(response, "content") else str(response)
            return {"response": text, "error": None}
        except Exception as exc:
            _logger.error("parallel_aggregate_failed", error=str(exc))
            return {"response": "", "error": f"Aggregate step failed: {exc}"}


def create_parallel_file_chain(
    config: ParallelFileChainConfig | None = None,
) -> ParallelFileChain:
    """Factory function for chain registry."""
    return ParallelFileChain(config)
