"""Retry policy schema for queue operations."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RetryPolicy(BaseModel):
    """Retry configuration shared by queue domains."""

    model_config = ConfigDict(extra="forbid")

    max_retries: int = Field(ge=0)
    retry_delay_seconds: int = Field(ge=0)
    backoff_multiplier: float = Field(default=1.0, ge=1.0)
    max_delay_seconds: int | None = Field(default=None, ge=0)

    def get_delay_for_attempt(self, attempt: int) -> int:
        """Return the retry delay for a specific attempt."""
        if attempt <= 1:
            delay = self.retry_delay_seconds
        else:
            delay = int(self.retry_delay_seconds * (self.backoff_multiplier ** (attempt - 1)))

        if self.max_delay_seconds is not None:
            return min(delay, self.max_delay_seconds)
        return delay
