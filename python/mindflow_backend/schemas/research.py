"""Legacy research schemas compatibility module.

This module preserves older imports such as
`mindflow_backend.schemas.research` by re-exporting the canonical
research schemas from `mindflow_backend.schemas.agents.research`.
"""

from __future__ import annotations

from .agents.research import *  # noqa: F401,F403
