"""JSON reporter for penetration test results."""

import json

from ..config import PenTestResult


class JSONReporter:
    """Generate JSON reports from penetration test results."""

    def generate(self, result: PenTestResult) -> str:
        """Generate JSON report.

        Args:
            result: PenTestResult to report on

        Returns:
            JSON report string
        """
        return json.dumps(result.to_dict(), indent=2)
