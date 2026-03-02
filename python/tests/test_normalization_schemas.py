"""Tests for normalization config schema."""

from omnimind_backend.schemas.normalization import NormalizationConfig


def test_defaults() -> None:
    cfg = NormalizationConfig()
    assert cfg.enabled is True
    assert cfg.max_input_tokens == 2000
    assert cfg.rewrite_threshold == 500
    assert cfg.rewrite_model == "flash"
    assert cfg.preserve_code_blocks is True


def test_disabled() -> None:
    cfg = NormalizationConfig(enabled=False)
    assert cfg.enabled is False
