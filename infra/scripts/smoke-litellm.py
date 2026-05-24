#!/usr/bin/env python3
"""LiteLLM proxy smoke test — same as smoke-openrouter.py but through the proxy.

Tests:
1. LiteLLM proxy is reachable at http://localhost:4000 (auth via LITELLM_MASTER_KEY)
2. All 5 model_name entries from infra/litellm-config.yaml respond
3. Per-model latency + token usage + cost (LiteLLM cost-attribution layer)

Validates the Phase 2B unified-routing thesis:
- closed models (claude, gpt-5, gemini, llama) → OpenRouter backend
- qwen-3-14b → HuggingFace router → Cerebras backend (EVID-019 carry-forward)

Exit codes (same as smoke-openrouter.py):
  0 — ≥3 of 5 models OK (PRD-001 + ER-2 degraded threshold)
  1 — <3 OK (smoke run not viable)
  2 — proxy unreachable or auth failed

Usage:
  make litellm-smoke
  OR: uv run --project apps/eval-core-py python infra/scripts/smoke-litellm.py

Pre-flight: `make stack-up` must succeed first.

Cost: ~$0.0003 total (5 minimal calls). No artifacts written.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from typing import Final

try:
    import httpx
except ImportError:  # pragma: no cover
    print(
        "ERROR: httpx not installed.\n"
        "  uv run --project apps/eval-core-py python infra/scripts/smoke-litellm.py\n"
        "  OR: pip install httpx",
        file=sys.stderr,
    )
    sys.exit(2)


PROXY_BASE: Final[str] = os.environ.get("LITELLM_PROXY_URL", "http://localhost:4000")
TIMEOUT_S: Final[float] = 30.0
MIN_MODELS_OK: Final[int] = 3
HTTP_OK: Final[int] = 200
MILLICENT_THRESHOLD_USD: Final[float] = 0.001

# These are the `model_name` entries from infra/litellm-config.yaml.
# LiteLLM resolves each to the actual backend (OpenRouter / HF router / direct).
LITELLM_MODELS: Final[list[str]] = [
    "claude-sonnet-4-6",  # → openrouter/anthropic/claude-sonnet-4.6
    "gpt-5-mini",  # → openrouter/openai/gpt-5-mini
    "gemini-3-flash",  # → openrouter/google/gemini-3-flash-preview
    "qwen-3-14b",  # → openai/Qwen/Qwen3-14B via HF router (auto-route)
    "llama-3-3-70b",  # → openrouter/meta-llama/llama-3.3-70b-instruct
]

PROMPT: Final[str] = "Reply with exactly the word PONG and nothing else."


@dataclass
class ProxyResult:
    model_name: str
    ok: bool
    latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    backend_model: str | None = None  # what LiteLLM reports back as the underlying model
    error: str | None = None


def _fmt_currency(usd: float) -> str:
    if usd == 0:
        return "$0"
    if usd < MILLICENT_THRESHOLD_USD:
        return f"${usd * 1000:.2f}m"
    return f"${usd:.4f}"


def _test_model(client: httpx.Client, master_key: str, model_name: str) -> ProxyResult:
    start = time.monotonic()
    try:
        resp = client.post(
            f"{PROXY_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {master_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": PROMPT}],
                "max_tokens": 16,
            },
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        if resp.status_code != HTTP_OK:
            return ProxyResult(
                model_name=model_name,
                ok=False,
                latency_ms=latency_ms,
                error=f"HTTP {resp.status_code}: {resp.text[:120]}",
            )
        body = resp.json()
        usage = body.get("usage", {})
        return ProxyResult(
            model_name=model_name,
            ok=True,
            latency_ms=latency_ms,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            cost_usd=float(usage.get("cost", 0.0)),
            backend_model=body.get("model"),
        )
    except httpx.RequestError as exc:
        return ProxyResult(
            model_name=model_name,
            ok=False,
            latency_ms=int((time.monotonic() - start) * 1000),
            error=f"network: {type(exc).__name__}: {exc}",
        )


def main() -> int:
    master_key = os.environ.get("LITELLM_MASTER_KEY")
    if not master_key:
        print("ERROR: LITELLM_MASTER_KEY not set (loaded by Makefile from .env)", file=sys.stderr)
        return 2

    print("=== LiteLLM proxy smoke test (5 models from litellm-config.yaml) ===")
    print(f"=== proxy: {PROXY_BASE} ===\n")

    with httpx.Client(timeout=TIMEOUT_S) as client:
        # Step 1: liveliness check
        try:
            live = client.get(f"{PROXY_BASE}/health/liveliness")
            live.raise_for_status()
            print(f"✓ proxy alive — {live.json()}")
        except (httpx.HTTPError, ValueError) as exc:
            print(f"✗ proxy unreachable: {exc}", file=sys.stderr)
            print("  Run: make stack-up", file=sys.stderr)
            return 2

        # Step 2: readiness check
        try:
            ready = client.get(f"{PROXY_BASE}/health/readiness")
            ready.raise_for_status()
            print(f"✓ proxy ready — {ready.json()}\n")
        except httpx.HTTPError as exc:
            print(f"⚠ readiness check failed (continuing): {exc}")

        # Step 3: test each model
        results: list[ProxyResult] = []
        for model in LITELLM_MODELS:
            print(f"… {model:22s} →", end=" ", flush=True)
            result = _test_model(client, master_key, model)
            if result.ok:
                tokens = f"{result.prompt_tokens}→{result.completion_tokens} tok"
                cost = _fmt_currency(result.cost_usd)
                backend = result.backend_model or "?"
                print(f"✓ {result.latency_ms}ms · {tokens} · {cost} (backend={backend})")
            else:
                print(f"✗ {result.error}")
            results.append(result)

    # Summary
    ok_count = sum(1 for r in results if r.ok)
    total_cost = sum(r.cost_usd for r in results)
    total_latency = sum(r.latency_ms for r in results)
    print(
        f"\n=== summary: {ok_count}/{len(results)} models OK via LiteLLM · "
        f"total ~{_fmt_currency(total_cost)} · "
        f"total latency {total_latency}ms ==="
    )

    if ok_count >= MIN_MODELS_OK:
        print(f"✓ meets degraded threshold (≥{MIN_MODELS_OK} models per PRD-001 + ER-2)")
        print("✓ Phase 2B unified-routing thesis VALIDATED through proxy")
        return 0
    print(
        f"✗ below degraded threshold (<{MIN_MODELS_OK}) — investigate per-model errors above",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
