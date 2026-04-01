"""Examples of callable tools.

This package contains reference implementations of tools using the
new callable pattern.
"""

from mindflow_backend.schemas.tools.examples.file_read_callable import (
    FileReadToolCallable,
    FileReadInput,
    file_read_impl,
)

__all__ = [
    "FileReadToolCallable",
    "FileReadInput",
    "file_read_impl",
]
