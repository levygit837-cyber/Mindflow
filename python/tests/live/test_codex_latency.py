"""
Latency comparison: Codex (OpenAI via ChatGPT session token) vs Vertex AI.

Run with:
    RUN_CODEX_LATENCY_TESTS=1 pytest tests/live/test_codex_latency.py -v -s

Requires:
  - ~/.codex/auth.json (populated by `codex login`)
  - GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_API_KEY for Vertex AI

Strategy:
    The Codex CLI authenticates via ChatGPT OAuth. The resulting access_token is
    a valid JWT for https://api.openai.com/v1 (see `aud` claim). We pass it directly
    as the api_key to LangChain's ChatOpenAI, which sends it as
    `Authorization: Bearer <token>`. This mirrors exactly how the Codex CLI calls
    the OpenAI API without a traditional sk-... API key.
"""

from __future__ import annotations

import json
import os
import statistics
import time
from pathlib import Path
from typing import Any

import pytest

CODEX_HOME = Path(os.getenv("CODEX_HOME", Path.home() / ".codex"))
PROMPT = "Responda em uma frase: qual é a capital do Brasil?"


def _live_enabled() -> bool:
    return os.getenv("RUN_CODEX_LATENCY_TESTS", "").strip() == "1"


def _load_codex_token() -> str | None:
    """Extract the access_token from ~/.codex/auth.json."""
    auth_file = CODEX_HOME / "auth.json"
    if not auth_file.exists():
        return None
    try:
        data = json.loads(auth_file.read_text())
        tokens = data.get("tokens", {})
        return tokens.get("access_token") or data.get("access_token")
    except Exception:
        return None


def _codex_model() -> str:
    """Read the configured model from ~/.codex/config.toml."""
    config_file = CODEX_HOME / "config.toml"
    if not config_file.exists():
        return "gpt-4o"
    for line in config_file.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("model") and "=" in stripped:
            return stripped.split("=", 1)[1].strip().strip('"').strip("'")
    return "gpt-4o"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _measure_sync(fn, runs: int = 3) -> dict[str, float]:
    """Run fn `runs` times and return latency stats in seconds."""
    times: list[float] = []
    last_response: Any = None
    for _ in range(runs):
        t0 = time.perf_counter()
        last_response = fn()
        times.append(time.perf_counter() - t0)
    return {
        "min": min(times),
        "max": max(times),
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "runs": runs,
        "last_response": last_response,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

skip_unless_live = pytest.mark.skipif(
    not _live_enabled(),
    reason="Set RUN_CODEX_LATENCY_TESTS=1 to run live latency tests",
)


@pytest.mark.live
@skip_unless_live
def test_codex_token_available() -> None:
    """Validate that a Codex session token can be loaded."""
    token = _load_codex_token()
    assert token is not None, (
        "No access_token found in ~/.codex/auth.json. "
        "Run `codex login` first."
    )
    print(f"\n[codex] Token loaded (first 40 chars): {token[:40]}...")
    print(f"[codex] Configured model: {_codex_model()}")


@pytest.mark.live
@skip_unless_live
def test_codex_api_call() -> None:
    """Make a single call to the OpenAI API using the Codex session token."""
    from langchain_openai import ChatOpenAI

    token = _load_codex_token()
    assert token, "Codex token not available — run `codex login`"
    model_name = _codex_model()

    print(f"\n[codex] Calling model={model_name} via Bearer token...")

    llm = ChatOpenAI(
        model=model_name,
        api_key=token,  # Bearer token used as api_key
        base_url="https://api.openai.com/v1",
        timeout=60,
        max_retries=1,
    )

    t0 = time.perf_counter()
    result = llm.invoke(PROMPT)
    elapsed = time.perf_counter() - t0

    content = result.content if hasattr(result, "content") else str(result)
    print(f"[codex] Response ({elapsed:.2f}s): {content[:200]}")
    assert content.strip(), "Empty response from Codex/OpenAI"


@pytest.mark.live
@skip_unless_live
def test_vertex_api_call() -> None:
    """Make a single call to Vertex AI (Gemini) as baseline."""
    import os
    from langchain_google_genai import ChatGoogleGenerativeAI

    credentials_path = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS",
        str(Path.home() / "Downloads/serviceAccount/serviceAccountVertex.json"),
    )
    if Path(credentials_path).exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

    vertex_model = os.getenv("DEFAULT_MODEL", "gemini-2.0-flash")
    print(f"\n[vertex] Calling model={vertex_model}...")

    llm = ChatGoogleGenerativeAI(
        model=vertex_model,
        vertexai=True,
        location="global",
    )

    t0 = time.perf_counter()
    result = llm.invoke(PROMPT)
    elapsed = time.perf_counter() - t0

    content = result.content if hasattr(result, "content") else str(result)
    print(f"[vertex] Response ({elapsed:.2f}s): {content[:200]}")
    assert content.strip(), "Empty response from Vertex AI"


@pytest.mark.live
@skip_unless_live
def test_latency_comparison() -> None:
    """
    Compare latency between Codex (OpenAI bearer) and Vertex AI over 3 runs each.
    Prints a summary table at the end.
    """
    import os
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_openai import ChatOpenAI

    token = _load_codex_token()
    assert token, "Codex token not available — run `codex login`"
    codex_model_name = _codex_model()

    # --- Vertex AI setup ---
    credentials_path = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS",
        str(Path.home() / "Downloads/serviceAccount/serviceAccountVertex.json"),
    )
    if Path(credentials_path).exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

    vertex_model = os.getenv("DEFAULT_MODEL", "gemini-2.0-flash")

    codex_llm = ChatOpenAI(
        model=codex_model_name,
        api_key=token,
        base_url="https://api.openai.com/v1",
        timeout=90,
        max_retries=1,
    )
    vertex_llm = ChatGoogleGenerativeAI(
        model=vertex_model,
        vertexai=True,
        location="global",
    )

    print(f"\n{'='*60}")
    print(f"Latency comparison  (3 runs, prompt: '{PROMPT}')")
    print(f"  Codex model  : {codex_model_name}")
    print(f"  Vertex model : {vertex_model}")
    print(f"{'='*60}")

    # --- Codex runs ---
    print("\nRunning Codex calls...")
    codex_stats = _measure_sync(lambda: codex_llm.invoke(PROMPT), runs=3)
    codex_preview = (
        codex_stats["last_response"].content[:120]
        if hasattr(codex_stats["last_response"], "content")
        else str(codex_stats["last_response"])[:120]
    )

    # --- Vertex runs ---
    print("Running Vertex AI calls...")
    vertex_stats = _measure_sync(lambda: vertex_llm.invoke(PROMPT), runs=3)
    vertex_preview = (
        vertex_stats["last_response"].content[:120]
        if hasattr(vertex_stats["last_response"], "content")
        else str(vertex_stats["last_response"])[:120]
    )

    # --- Report ---
    print(f"\n{'─'*60}")
    print(f"{'Provider':<20} {'Min':>8} {'Median':>8} {'Mean':>8} {'Max':>8}")
    print(f"{'─'*60}")
    print(
        f"{'Codex (OpenAI)':<20} "
        f"{codex_stats['min']:>7.2f}s "
        f"{codex_stats['median']:>7.2f}s "
        f"{codex_stats['mean']:>7.2f}s "
        f"{codex_stats['max']:>7.2f}s"
    )
    print(
        f"{'Vertex AI (Gemini)':<20} "
        f"{vertex_stats['min']:>7.2f}s "
        f"{vertex_stats['median']:>7.2f}s "
        f"{vertex_stats['mean']:>7.2f}s "
        f"{vertex_stats['max']:>7.2f}s"
    )
    print(f"{'─'*60}")

    faster = "Codex" if codex_stats["median"] < vertex_stats["median"] else "Vertex AI"
    diff = abs(codex_stats["median"] - vertex_stats["median"])
    print(f"\n  Winner (median): {faster} by {diff:.2f}s")
    print(f"\n  Codex last response  : {codex_preview}")
    print(f"  Vertex last response : {vertex_preview}")
    print(f"{'='*60}\n")

    # Both providers must respond
    assert codex_stats["last_response"] is not None
    assert vertex_stats["last_response"] is not None


@pytest.mark.live
@skip_unless_live
def test_codex_token_not_expired() -> None:
    """
    Verify the access_token is not expired by decoding the JWT exp claim
    (no signature validation needed — we just check the timestamp).
    """
    import base64
    import time as _time

    token = _load_codex_token()
    assert token, "No token found"

    # Decode payload (middle segment of JWT)
    parts = token.split(".")
    assert len(parts) == 3, "access_token does not look like a JWT"

    padding = 4 - len(parts[1]) % 4
    payload_bytes = base64.urlsafe_b64decode(parts[1] + "=" * padding)
    payload = json.loads(payload_bytes)

    exp = payload.get("exp", 0)
    now = _time.time()
    remaining = exp - now

    print(f"\n[codex] Token exp: {exp}")
    print(f"[codex] Now      : {now:.0f}")
    print(f"[codex] Remaining: {remaining:.0f}s ({remaining/3600:.1f}h)")

    if remaining <= 0:
        pytest.skip(
            f"access_token is expired (by {abs(remaining):.0f}s). "
            "Run `codex login` to refresh."
        )

    assert remaining > 0, "Token is expired"
    print("[codex] Token is valid.")
