"""Penetration testing framework.

Provides automated security scanning for codebases with CI/CD integration.
"""

from .framework import PenTestFramework, PenTestResult, PenTestSeverity

__all__ = [
    "PenTestFramework",
    "PenTestResult",
    "PenTestSeverity",
]
