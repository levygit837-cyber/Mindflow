"""Tests for per-phase feature flags."""

from omnimind_backend.infra.config import Settings


def test_phase1_flags_default_off() -> None:
    s = Settings()
    # Note: enable_security_guard_agent was deprecated and removed
    assert s.enable_input_normalization is False
    assert s.enable_context_governance is False


def test_phase2_flags_default_off() -> None:
    s = Settings()
    assert s.enable_input_normalization is False
    assert s.enable_context_governance is False
    assert s.enable_session_chunks is False
    assert s.chunk_target_tokens == 3000


# Phase 3 flags (async workflows, workflow registry) were deprecated and removed

def test_phase4_flags_default_off() -> None:
    s = Settings()
    assert s.enable_dt_v2 is False


def test_flags_can_be_enabled() -> None:
    s = Settings(
        ENABLE_CONTEXT_GOVERNANCE="true",
    )
    assert s.enable_context_governance is True
