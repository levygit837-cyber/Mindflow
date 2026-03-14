"""Research analysis tools and components.

Provides analysis and synthesis components:
- Result synthesis and processing
- Source trust evaluation
- Content analysis and validation
"""

from __future__ import annotations

from .result_synthesizer import *
from .source_trust_engine import *

__all__ = [
    "get_result_synthesizer",
    "get_source_trust_engine",
]
