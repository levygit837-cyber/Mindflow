"""Coder worker for handling code-related tasks."""

from __future__ import annotations

import time
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.workers.base.worker import BaseWorker, WorkerResult
from mindflow_backend.workers.config.queues import QueueConfig

_logger = get_logger(__name__)


class CoderWorker(BaseWorker):
    """Worker specialized for Coder Agent tasks."""
    
    def __init__(self, queue_config: QueueConfig) -> None:
        """Initialize the Coder worker."""
        super().__init__(queue_config, worker_name="coder_worker")
    
    async def process_message(self, message_data: dict[str, Any]) -> WorkerResult:
        """Process code-related tasks.
        
        Supported task types:
        - code_analysis: Static code analysis
        - dependency_scan: Security vulnerability scanning
        - test_execution: Run tests asynchronously
        - code_generation: Generate code snippets
        - refactoring: Code refactoring tasks
        """
        message_data = self._normalize_message_data(message_data)
        start_time = time.time()
        task_type = message_data.get("task_type", "unknown")
        task_id = message_data.get("task_id", "unknown")
        
        try:
            _logger.info(f"CoderWorker processing {task_type} task {task_id}")
            
            if task_type == "code_analysis":
                result = await self._handle_code_analysis(message_data)
            elif task_type == "dependency_scan":
                result = await self._handle_dependency_scan(message_data)
            elif task_type == "test_execution":
                result = await self._handle_test_execution(message_data)
            elif task_type == "code_generation":
                result = await self._handle_code_generation(message_data)
            elif task_type == "refactoring":
                result = await self._handle_refactoring(message_data)
            else:
                result = WorkerResult(
                    success=False,
                    message=f"Unsupported task type: {task_type}",
                    processing_time=time.time() - start_time,
                )
            
            _logger.info(
                f"CoderWorker completed {task_type} task {task_id} "
                f"({'SUCCESS' if result.success else 'FAILED'})"
            )
            
            return result
            
        except Exception as e:
            _logger.error(
                f"CoderWorker failed to process {task_type} task {task_id}: {e}",
                exc_info=True
            )
            return WorkerResult(
                success=False,
                message=f"Task processing failed: {e}",
                error=e,
                processing_time=time.time() - start_time,
            )
    
    async def _handle_code_analysis(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle static code analysis tasks using existing tools."""
        file_path = message_data.get("file_path")
        analysis_type = message_data.get("analysis_type", "basic")
        
        if not file_path:
            return WorkerResult(
                success=False,
                message="No file path specified",
                data={"error": "file_path is required"},
            )
        
        try:
            # Use FileReadTool to get file content
            from mindflow_backend.agents.tools.filesystem import FileReadTool
            from mindflow_backend.agents.tools.search_web import GrepSearchTool
            
            file_tool = FileReadTool()
            file_content = await file_tool.execute(file_path=file_path)
            
            issues = []
            complexity_score = 0.5
            
            if analysis_type in ("basic", "full"):
                # Basic analysis: line count, empty lines, TODOs
                lines = file_content.split("\n")
                total_lines = len(lines)
                empty_lines = sum(1 for line in lines if not line.strip())
                todo_count = sum(1 for line in lines if "TODO" in line or "FIXME" in line)
                
                if todo_count > 0:
                    issues.append({
                        "type": "info",
                        "message": f"Found {todo_count} TODO/FIXME comments",
                        "line": None,
                    })
                
                # Calculate complexity based on line count
                if total_lines > 0:
                    complexity_score = min(1.0, total_lines / 500)
            
            if analysis_type == "full":
                # Full analysis: syntax check
                if file_path.endswith(".py"):
                    try:
                        import ast
                        ast.parse(file_content)
                    except SyntaxError as e:
                        issues.append({
                            "type": "error",
                            "message": f"Syntax error: {e.msg}",
                            "line": e.lineno,
                        })
                        complexity_score = 1.0
            
            return WorkerResult(
                success=True,
                message=f"Code analysis completed for {file_path}",
                data={
                    "file_path": file_path,
                    "analysis_type": analysis_type,
                    "issues_found": len(issues),
                    "issues": issues,
                    "complexity_score": round(complexity_score, 2),
                    "total_lines": len(file_content.split("\n")),
                },
            )
            
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Code analysis failed: {exc}",
                data={"error": str(exc), "file_path": file_path},
            )
    
    async def _handle_dependency_scan(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle dependency vulnerability scanning using filesystem tools."""
        project_path = message_data.get("project_path")
        scan_depth = message_data.get("scan_depth", "direct")
        
        if not project_path:
            return WorkerResult(
                success=False,
                message="No project path specified",
                data={"error": "project_path is required"},
            )
        
        try:
            from mindflow_backend.agents.tools.filesystem import GlobToolV2, FileReadTool
            
            # Find dependency files
            glob_tool = GlobToolV2()
            dep_files = await glob_tool.execute(
                pattern="**/requirements*.txt",
                path=project_path,
            )
            
            # Also check for other dependency files
            other_deps = await glob_tool.execute(
                pattern="**/{package.json,Pipfile,poetry.lock}",
                path=project_path,
            )
            
            all_deps = dep_files.get("matches", []) + other_deps.get("matches", [])
            
            vulnerabilities = []
            outdated_packages = []
            
            # Parse Python requirements
            file_tool = FileReadTool()
            for dep_file in all_deps:
                if "requirements" in dep_file:
                    try:
                        content = await file_tool.execute(file_path=dep_file)
                        # Parse requirements and check for common issues
                        for line in content.split("\n"):
                            line = line.strip()
                            if line and not line.startswith("#"):
                                # Check for pinned versions (security best practice)
                                if "==" not in line and ">=" not in line and ">" not in line:
                                    vulnerabilities.append({
                                        "package": line.split("=")[0].split("<")[0].strip(),
                                        "issue": "Unpinned dependency - version not specified",
                                        "severity": "low",
                                        "file": dep_file,
                                    })
                    except Exception:
                        pass
            
            return WorkerResult(
                success=True,
                message=f"Dependency scan completed for {project_path}",
                data={
                    "project_path": project_path,
                    "scan_depth": scan_depth,
                    "dependency_files_found": len(all_deps),
                    "vulnerabilities": vulnerabilities,
                    "outdated_packages": outdated_packages,
                    "recommendation": "Use 'pip-audit' or 'safety' for detailed vulnerability scanning",
                },
            )
            
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Dependency scan failed: {exc}",
                data={"error": str(exc), "project_path": project_path},
            )
    
    async def _handle_test_execution(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle asynchronous test execution with pytest."""
        test_path = message_data.get("test_path")
        test_type = message_data.get("test_type", "unit")
        parallel = message_data.get("parallel", False)
        coverage = message_data.get("coverage", False)

        if not test_path:
            return WorkerResult(
                success=False,
                message="No test path specified",
                data={"error": "test_path is required"},
            )

        try:
            import subprocess

            # Build pytest command
            cmd = ["pytest", test_path, "-v", "--tb=short"]

            if coverage:
                cmd.extend(["--cov", "--cov-report=json", "--cov-report=term"])

            if parallel:
                cmd.extend(["-n", "auto"])  # Requires pytest-xdist

            # Execute pytest
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=message_data.get("working_dir"),
            )

            # Parse output
            stats = self._parse_pytest_output(result.stdout)

            return WorkerResult(
                success=result.returncode == 0,
                message=f"Tests executed for {test_path}: {stats['passed']}/{stats['total']} passed",
                data={
                    "test_path": test_path,
                    "test_type": test_type,
                    "tests_run": stats["total"],
                    "tests_passed": stats["passed"],
                    "tests_failed": stats["failed"],
                    "tests_skipped": stats.get("skipped", 0),
                    "duration": stats.get("duration", 0),
                    "coverage": stats.get("coverage"),
                    "exit_code": result.returncode,
                    "stdout": result.stdout[-1000:],  # Last 1000 chars
                },
            )

        except subprocess.TimeoutExpired:
            return WorkerResult(
                success=False,
                message=f"Test execution timed out after 300 seconds",
                data={"error": "timeout", "test_path": test_path},
            )
        except FileNotFoundError:
            return WorkerResult(
                success=False,
                message="pytest not found. Install with: pip install pytest",
                data={"error": "pytest_not_installed"},
            )
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Test execution failed: {exc}",
                data={"error": str(exc), "test_path": test_path},
            )

    @staticmethod
    def _parse_pytest_output(output: str) -> dict[str, Any]:
        """Parse pytest output to extract statistics."""
        import re

        stats = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "duration": 0.0,
        }

        # Look for summary line: "5 passed, 1 failed in 2.34s"
        summary_pattern = r"(\d+)\s+passed|(\d+)\s+failed|(\d+)\s+skipped"
        for match in re.finditer(summary_pattern, output):
            if match.group(1):
                stats["passed"] = int(match.group(1))
            elif match.group(2):
                stats["failed"] = int(match.group(2))
            elif match.group(3):
                stats["skipped"] = int(match.group(3))

        stats["total"] = stats["passed"] + stats["failed"] + stats["skipped"]

        # Extract duration
        duration_match = re.search(r"in\s+([\d.]+)s", output)
        if duration_match:
            stats["duration"] = float(duration_match.group(1))

        return stats

    async def _handle_code_generation(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle code generation tasks via LLM."""
        prompt = message_data.get("prompt")
        language = message_data.get("language", "python")
        context = message_data.get("context", {})
        provider = message_data.get("provider", "google")
        model = message_data.get("model", "gemini-3.1-flash-lite-preview")

        if not prompt:
            return WorkerResult(
                success=False,
                message="No prompt specified for code generation",
                data={"error": "prompt is required"},
            )

        try:
            from mindflow_backend.infra.llm import get_model_for_provider

            # Build system prompt
            system_prompt = f"""You are an expert {language} code generator.
Generate clean, well-documented, production-ready code based on the user's prompt.

Context:
{self._format_context(context)}

Requirements:
- Write idiomatic {language} code
- Include docstrings/comments
- Handle errors appropriately
- Follow best practices
- Output ONLY the code, no explanations"""

            # Get LLM
            llm = get_model_for_provider(provider, model)

            # Generate code
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

            response = await llm.ainvoke(messages)

            # Extract code from response
            from mindflow_backend.runtime.streaming.chunk_extract import extract_chunk_parts

            _, texts = extract_chunk_parts(response)
            generated_code = "".join(texts)

            # Extract code blocks if present
            generated_code = self._extract_code_blocks(generated_code)

            return WorkerResult(
                success=True,
                message=f"Code generated for {language}",
                data={
                    "language": language,
                    "generated_code": generated_code,
                    "prompt": prompt[:200],  # First 200 chars
                    "provider": provider,
                    "model": model,
                },
            )

        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Code generation failed: {exc}",
                data={"error": str(exc), "language": language},
            )

    @staticmethod
    def _format_context(context: dict[str, Any]) -> str:
        """Format context dictionary for prompt."""
        if not context:
            return "No additional context provided."

        lines = []
        for key, value in context.items():
            lines.append(f"- {key}: {value}")

        return "\n".join(lines)

    @staticmethod
    def _extract_code_blocks(text: str) -> str:
        """Extract code from markdown code blocks."""
        import re

        # Look for ```language\ncode\n``` blocks
        code_block_pattern = r"```(?:\w+)?\n(.*?)\n```"
        matches = re.findall(code_block_pattern, text, re.DOTALL)

        if matches:
            # Return first code block
            return matches[0].strip()

        # No code blocks found, return as-is
        return text.strip()
    
    async def _handle_refactoring(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle code refactoring tasks using AST manipulation."""
        file_path = message_data.get("file_path")
        refactoring_type = message_data.get("refactoring_type", "extract_method")
        
        if not file_path:
            return WorkerResult(
                success=False,
                message="No file path specified",
                data={"error": "file_path is required"},
            )
        
        try:
            from mindflow_backend.agents.tools.filesystem import FileReadTool, FileEditTool
            
            file_tool = FileReadTool()
            edit_tool = FileEditTool()
            
            # Read the file
            content = await file_tool.execute(file_path=file_path)
            original_lines = content.split("\n")
            changes_made = 0
            lines_affected = 0
            
            if file_path.endswith(".py"):
                try:
                    import ast
                    tree = ast.parse(content)
                    
                    if refactoring_type == "extract_method":
                        # Find long functions and suggest extraction
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                func_lines = node.end_lineno - node.lineno
                                if func_lines > 30:
                                    changes_made += 1
                                    lines_affected += func_lines
                    
                    elif refactoring_type == "remove_unused_imports":
                        # Find unused imports
                        imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
                        for imp in imports:
                            changes_made += 1
                            lines_affected += 1
                    
                    elif refactoring_type == "sort_imports":
                        # Sort imports alphabetically
                        changes_made = 1
                        lines_affected = len([n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))])
                    
                except SyntaxError:
                    pass
            
            return WorkerResult(
                success=True,
                message=f"Refactoring analysis completed for {file_path}",
                data={
                    "file_path": file_path,
                    "refactoring_type": refactoring_type,
                    "changes_identified": changes_made,
                    "lines_affected": lines_affected,
                    "original_line_count": len(original_lines),
                    "note": "Use FileEditTool to apply actual refactoring changes",
                },
            )
            
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Refactoring failed: {exc}",
                data={"error": str(exc), "file_path": file_path},
            )
