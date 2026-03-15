"""Conditional File Analysis Chain.

Extends FileAnalysisChain with an iterative "do I need more files?" loop:

  1. intent_analysis  — identify files/patterns  (same as FileAnalysisChain)
  2. discovery        — scan filesystem           (same as FileAnalysisChain)
  3. sequential_read  — read identified files
  4. structure        — LLM produces analysis
  5. condition_check  — LLM decides: is the analysis complete?
  6. [if needs more]  — identify additional files, loop back to step 3

The loop is bounded by ``max_iterations`` (default 3).
On each iteration only *new* files are read — already-read content accumulates.

The chain does NOT create LLM instances. The Orchestrator passes the specialist
via ``context["llm"]`` so that chain behavior is fully controlled by whoever
invoked it.
"""

from __future__ import annotations

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


_CONDITION_SYSTEM = """\
You are a code analysis reviewer. Given the current analysis and original request,
decide whether additional files must be read to fully answer the question.

Respond ONLY with valid JSON (no markdown):
{
  "needs_more": true,
  "reason": "what is still missing or unclear",
  "additional_files": ["path/to/missing_file.py"],
  "additional_patterns": ["**/*test*.py"]
}
Set "needs_more" to false if the analysis is already complete.
Be conservative — only request more files if truly necessary."""


@dataclass(frozen=True, slots=True)
class ConditionalFileChainConfig:
    chain_id: str = "conditional_file_analysis"
    max_files_to_read: int = 20
    max_file_size_chars: int = 8_000
    max_context_chars: int = 60_000
    max_iterations: int = 3


class ConditionalFileChain:
    """File analysis chain with conditional re-reading loop.

    Requires ``context["llm"]`` — the LLM instance injected by the Orchestrator.
    """

    def __init__(self, config: ConditionalFileChainConfig | None = None) -> None:
        self.config = config or ConditionalFileChainConfig()
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
            return {"response": "", "error": "ConditionalFileChain: `message` is required."}

        # LLM must be provided by the Orchestrator — chains do not create their own.
        llm = context.get("llm")
        if llm is None:
            return {
                "response": "",
                "error": (
                    "ConditionalFileChain: `llm` is required in context. "
                    "The Orchestrator must inject the specialist LLM before calling this chain."
                ),
            }

        root_dir: str | None = (
            context.get("root_dir")
            or context.get("folder_path")
            or getattr(self.settings, "working_path", None)
        )
        session_id: str = str(context.get("session_id") or "")

        _logger.info("conditional_file_chain_start", session_id=session_id)

        planning_result = await self._base._run_scope_planner(message, root_dir)

        # Steps 1–2: intent + initial discovery
        intent_result = await self._base._run_intent_analysis(
            message,
            root_dir,
            llm,
            planner_result=planning_result,
        )
        if intent_result.get("error"):
            return intent_result

        if planning_result["discovered_files"]:
            discovery_result = {
                "discovered_files": planning_result["discovered_files"],
                "directory_map": planning_result["directory_map"],
                "coverage": planning_result["coverage"],
            }
        else:
            discovery_result = await self._base._run_discovery(root_dir, intent_result["intent"])
            discovery_result["coverage"] = planning_result["coverage"]

        # Mutable state accumulated across iterations
        all_contents: dict[str, str] = {}
        read_errors: list[str] = []
        iteration_log: list[dict] = []
        files_to_read = list(discovery_result["discovered_files"])
        current_analysis = ""

        for iteration in range(self.config.max_iterations + 1):
            _logger.info(
                "conditional_file_chain_iteration",
                iteration=iteration,
                new_files=len([f for f in files_to_read if f not in all_contents]),
                session_id=session_id,
            )

            # Step 3: Read only files not yet seen
            new_files = [f for f in files_to_read if f not in all_contents]
            if new_files:
                read_result = await self._base._run_sequential_read(root_dir, new_files)
                all_contents.update(read_result["file_contents"])
                read_errors.extend(read_result["read_errors"])
                iteration_log.append({
                    "iteration": iteration,
                    "files_read": list(read_result["file_contents"].keys()),
                    "read_errors": read_result["read_errors"],
                })

            # Step 4: Structure everything accumulated so far
            structure_result = await self._base._run_structure(
                message=message,
                file_contents=all_contents,
                directory_map=discovery_result["directory_map"],
                llm=llm,
            )
            if structure_result.get("error"):
                return structure_result

            current_analysis = structure_result.get("response", "")

            # Hard stop at max_iterations
            if iteration >= self.config.max_iterations:
                _logger.info("conditional_file_chain_max_iterations_reached")
                break

            # Step 5: Condition check — do we need more?
            condition = await self._run_condition_check(
                message=message,
                current_analysis=current_analysis,
                files_read=list(all_contents.keys()),
                llm=llm,
            )

            if not condition.get("needs_more", False):
                _logger.info("conditional_file_chain_complete", iteration=iteration)
                break

            # Step 6: Resolve additional files for next iteration
            extra: list[str] = list(condition.get("additional_files") or [])
            for pattern in condition.get("additional_patterns") or []:
                if root_dir:
                    try:
                        for m in Path(root_dir).glob(pattern):
                            if m.is_file() and str(m) not in all_contents:
                                extra.append(str(m))
                    except Exception:
                        pass

            if not extra:
                _logger.info("conditional_file_chain_no_extra_files", iteration=iteration)
                break

            files_to_read = extra[: self.config.max_files_to_read]

        return {
            "response": current_analysis,
            "error": None,
            "chain": {
                "intent": intent_result["intent"],
                "discovered_files": discovery_result["discovered_files"],
                "all_files_read": list(all_contents.keys()),
                "read_errors": read_errors,
                "coverage": {
                    **(discovery_result.get("coverage") or {}),
                    "files_read": list(all_contents.keys()),
                },
                "iterations": iteration_log,
                "total_iterations": len(iteration_log),
            },
        }

    async def _run_condition_check(
        self,
        *,
        message: str,
        current_analysis: str,
        files_read: list[str],
        llm: Any,
    ) -> dict[str, Any]:
        """Ask the LLM whether additional files are required."""
        try:
            files_list = "\n".join(f"  - {f}" for f in files_read[:30])
            if len(files_read) > 30:
                files_list += f"\n  ... e mais {len(files_read) - 30} arquivo(s)"

            user_content = (
                f"Solicitação original:\n{message}\n\n"
                f"Arquivos já lidos:\n{files_list}\n\n"
                f"Análise atual (trecho):\n{current_analysis[:2_000]}\n\n"
                "A análise está completa, ou precisamos de mais arquivos?"
            )
            response = await llm.ainvoke([
                {"role": "system", "content": _CONDITION_SYSTEM},
                {"role": "user", "content": user_content},
            ])
            raw = response.content if hasattr(response, "content") else str(response)
            return _extract_json(raw) or {"needs_more": False}
        except Exception as exc:
            _logger.warning("condition_check_failed", error=str(exc))
            return {"needs_more": False}


def create_conditional_file_chain(
    config: ConditionalFileChainConfig | None = None,
) -> ConditionalFileChain:
    """Factory function for chain registry."""
    return ConditionalFileChain(config)
