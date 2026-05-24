#!/usr/bin/env python3
"""OpenRouter smoke test — sanity-checks ADR-003 5-model lineup.

Tests:
1. OPENROUTER_API_KEY is set and accepted by /credits
2. /models endpoint enumerable
3. Each of 5 ADR-003 candidate model slugs resolvable on OpenRouter
4. Minimal chat completion call works for each (~$0.0001/model)

Exit codes:
  0 — at least 3 of 5 models respond (meets PRD-001 SC-4 degraded threshold per ADR-003 + ER-2)
  1 — fewer than 3 models respond (smoke run would itself fail)
  2 — auth or network error before any model call

Usage:
  uv run --project apps/eval-core-py python infra/scripts/smoke-openrouter.py
  OR (with .env loaded by Makefile):
  make openrouter-smoke

This is a pre-flight check for `make smoke-run` (Phase 2B). Costs ~$0.0003 total.

Does NOT mutate any forgeplan artifacts or write any files. Read-only sanity probe.
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
        "  uv run --project apps/eval-core-py python infra/scripts/smoke-openrouter.py\n"
        "  OR: pip install httpx",
        file=sys.stderr,
    )
    sys.exit(2)


OPENROUTER_BASE: Final[str] = "https://openrouter.ai/api/v1"
TIMEOUT_S: Final[float] = 30.0
MIN_MODELS_OK: Final[int] = 3  # PRD-001 + ER-2 degraded threshold
HTTP_OK: Final[int] = 200
MILLICENT_THRESHOLD_USD: Final[float] = 0.001  # display as $X.YYm below this

# ADR-003 5-model lineup — match best available slug at runtime.
# Format: (logical_name, list_of_substrings_to_match_on_openrouter_id)
# Substrings checked in order — first match wins. Case-insensitive substring search.
ADR_003_CANDIDATES: Final[list[tuple[str, list[str]]]] = [
    (
        "claude-sonnet-4.6",
        ["anthropic/claude-sonnet-4.6", "anthropic/claude-sonnet-4", "anthropic/claude-3.5-sonnet"],
    ),
    ("gpt-5-mini", ["openai/gpt-5-mini", "openai/gpt-5", "openai/gpt-4o-mini"]),
    ("gemini-3-flash", ["google/gemini-3-flash", "google/gemini-3", "google/gemini-2.5-flash"]),
    ("qwen-3-14b", ["cerebras/qwen-3-14b", "qwen/qwen-3-14b", "qwen/qwen-2.5-14b"]),
    (
        "llama-4-70b",
        ["meta-llama/llama-4-70b", "meta-llama/llama-3.3-70b", "meta-llama/llama-3.1-70b"],
    ),
]

PROMPT: Final[str] = "Reply with exactly the word PONG and nothing else."


@dataclass
class ModelResult:
    logical_name: str
    resolved_slug: str | None
    ok: bool
    latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    error: str | None = None


def _fmt_currency(usd: float) -> str:
    if usd == 0:
        return "$0"
    if usd < MILLICENT_THRESHOLD_USD:
        return f"${usd * 1000:.2f}m"  # millicents
    return f"${usd:.4f}"


def _resolve_slug(candidate_substrings: list[str], all_model_ids: set[str]) -> str | None:
    """Return best OpenRouter model id matching any candidate substring.

    Prefers paid variants over :free tier (free tier has aggressive rate limits
    that cause HTTP 429 during smoke). For each candidate substring, scan
    matches and prefer the one WITHOUT `:free` suffix.
    """
    for sub in candidate_substrings:
        sub_lower = sub.lower()
        matches = [m for m in all_model_ids if sub_lower in m.lower()]
        if not matches:
            continue
        # Prefer non-:free
        paid = [m for m in matches if ":free" not in m.lower()]
        return (paid or matches)[0]
    return None


def _enumerate_models(client: httpx.Client, api_key: str) -> set[str]:
    resp = client.get(
        f"{OPENROUTER_BASE}/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    resp.raise_for_status()
    data = resp.json()
    return {m["id"] for m in data.get("data", [])}


def _test_chat(
    client: httpx.Client,
    api_key: str,
    model_slug: str,
) -> ModelResult:
    logical = next(
        (n for n, _ in ADR_003_CANDIDATES if n in model_slug or model_slug in n), model_slug
    )
    start = time.monotonic()
    try:
        resp = client.post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/ForgePlan/pollmevals",
                "X-Title": "POLLMEVALS smoke-openrouter",
            },
            # Temperature deliberately UNSET — GPT-5 / o1 / o3 family rejects
            # non-default temperature. Smoke test doesn't need determinism (it's
            # a sanity check, not a benchmark — `make smoke-run` uses seed=N).
            # max_tokens=16 is the minimum GPT-5 accepts (reserved for internal
            # reasoning tokens). Lower values rejected with HTTP 400.
            json={
                "model": model_slug,
                "messages": [{"role": "user", "content": PROMPT}],
                "max_tokens": 16,
            },
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        if resp.status_code != HTTP_OK:
            return ModelResult(
                logical_name=logical,
                resolved_slug=model_slug,
                ok=False,
                latency_ms=latency_ms,
                error=f"HTTP {resp.status_code}: {resp.text[:100]}",
            )
        body = resp.json()
        usage = body.get("usage", {})
        return ModelResult(
            logical_name=logical,
            resolved_slug=model_slug,
            ok=True,
            latency_ms=latency_ms,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            cost_usd=float(usage.get("cost", 0.0)),
        )
    except httpx.RequestError as exc:
        return ModelResult(
            logical_name=logical,
            resolved_slug=model_slug,
            ok=False,
            latency_ms=int((time.monotonic() - start) * 1000),
            error=f"network: {type(exc).__name__}",
        )


def main() -> int:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set in env.", file=sys.stderr)
        print("  Run via: make openrouter-smoke", file=sys.stderr)
        print(
            "  OR: set -a && source .env && set +a && python infra/scripts/smoke-openrouter.py",
            file=sys.stderr,
        )
        return 2

    print("=== OpenRouter smoke test (ADR-003 lineup) ===\n")

    with httpx.Client(timeout=TIMEOUT_S) as client:
        # Step 1: auth check via /credits (free)
        try:
            credits_resp = client.get(
                f"{OPENROUTER_BASE}/credits",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            credits_resp.raise_for_status()
            credits = credits_resp.json().get("data", {})
            total_credits = credits.get("total_credits", "?")
            total_usage = credits.get("total_usage", 0)
            print(f"✓ auth OK — credits={total_credits}, total_usage=${total_usage:.4f}")
        except httpx.HTTPError as exc:
            print(f"✗ auth FAILED: {exc}", file=sys.stderr)
            return 2

        # Step 2: enumerate models
        try:
            all_models = _enumerate_models(client, api_key)
            print(f"✓ /models — {len(all_models)} models available on OpenRouter\n")
        except httpx.HTTPError as exc:
            print(f"✗ /models FAILED: {exc}", file=sys.stderr)
            return 2

        # Step 3: resolve + test each ADR-003 candidate
        results: list[ModelResult] = []
        for logical_name, substrings in ADR_003_CANDIDATES:
            resolved = _resolve_slug(substrings, all_models)
            if resolved is None:
                print(f"✗ {logical_name:18s} — no match for any of {substrings}")
                results.append(
                    ModelResult(
                        logical_name=logical_name,
                        resolved_slug=None,
                        ok=False,
                        error="not on OpenRouter",
                    )
                )
                continue
            print(f"… {logical_name:18s} → {resolved}", flush=True)
            result = _test_chat(client, api_key, resolved)
            result.logical_name = logical_name
            mark = "✓" if result.ok else "✗"
            if result.ok:
                tokens = f"{result.prompt_tokens}→{result.completion_tokens} tok"
                cost = _fmt_currency(result.cost_usd)
                print(f"  {mark} {result.latency_ms}ms · {tokens} · {cost}")
            else:
                print(f"  {mark} {result.error}")
            results.append(result)

    # Summary
    ok_count = sum(1 for r in results if r.ok)
    total_cost = sum(r.cost_usd for r in results)
    total_latency = sum(r.latency_ms for r in results)
    print(
        f"\n=== summary: {ok_count}/{len(results)} models OK · "
        f"total ~{_fmt_currency(total_cost)} · "
        f"total latency {total_latency}ms ==="
    )

    if ok_count >= MIN_MODELS_OK:
        print(f"✓ meets degraded threshold (≥{MIN_MODELS_OK} models per PRD-001 + ER-2)")
        return 0
    print(
        f"✗ below degraded threshold (<{MIN_MODELS_OK} models) — smoke run would fail. "
        "Update ADR-003 model lineup or check provider availability.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
