"""Utility modules for coding nodes.

This module exports utility functions for code operations, linting,
test running, P2P communication, and LLM integration.
"""

from mindflow_backend.nodes.implementations.coding.utils.code_operations import (
    analyze_python_structure,
    detect_code_patterns,
    detect_language,
    extract_imports,
    get_file_dependencies,
    read_file_safe,
    validate_syntax,
    write_file_safe,
)
from mindflow_backend.nodes.implementations.coding.utils.linter import (
    detect_linter,
    detect_type_checker,
    quick_lint_check,
    run_linter,
    run_mypy,
    run_ruff,
    run_type_checker,
)
from mindflow_backend.nodes.implementations.coding.utils.llm_helper import (
    decompose_task_with_llm,
    generate_code_with_llm,
    generate_tests_with_llm,
)
from mindflow_backend.nodes.implementations.coding.utils.p2p_helper import (
    annotate_architectural_doubt,
    check_p2p_availability,
    consult_analyst_architecture,
    graceful_p2p_fallback,
    notify_orchestrator_progress,
    request_specialist_help,
)
from mindflow_backend.nodes.implementations.coding.utils.test_runner import (
    detect_test_framework,
    get_test_coverage,
    run_python_tests,
    run_tests,
)

__all__ = [
    # Code operations
    "read_file_safe",
    "write_file_safe",
    "detect_language",
    "analyze_python_structure",
    "detect_code_patterns",
    "validate_syntax",
    "extract_imports",
    "get_file_dependencies",
    # Linting
    "detect_linter",
    "detect_type_checker",
    "quick_lint_check",
    "run_linter",
    "run_mypy",
    "run_ruff",
    "run_type_checker",
    # Test runner
    "detect_test_framework",
    "get_test_coverage",
    "run_python_tests",
    "run_tests",
    # P2P helper
    "consult_analyst_architecture",
    "notify_orchestrator_progress",
    "annotate_architectural_doubt",
    "request_specialist_help",
    "check_p2p_availability",
    "graceful_p2p_fallback",
    # LLM helper
    "decompose_task_with_llm",
    "generate_code_with_llm",
    "generate_tests_with_llm",
]
