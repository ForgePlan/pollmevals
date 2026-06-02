#!/usr/bin/env python
"""Diagnose why a judge (gpt-5-mini) returns unparseable rubric JSON.

Calls the judge model directly through the LiteLLM proxy with the SAME rubric
prompt the panel uses, and reports the decisive signals:
  - finish_reason  ("length" => truncated at max_tokens; "stop" => malformed)
  - raw completion + token usage
  - whether _parse_rubric_scores succeeds (and, optionally, JSON mode)

No executor needed — judges the be_01 GOLD solution (reproduces the 7-criterion
rubric that triggered the failure). Cost: ~$0.02 (1-2 gpt-5-mini calls).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "apps" / "eval-core-py"))

from src.orchestrator.judge_panel import (  # noqa: E402
    _build_rubric_prompt,
    _load_rubric_criteria,
    _parse_rubric_scores,
)


def _load_env(repo: Path) -> None:
    envf = repo / ".env"
    if not envf.exists():
        return
    for line in envf.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, _, v = s.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


async def _call(
    *,
    model: str,
    prompt: str,
    key: str,
    max_tokens: int,
    json_mode: bool,
    reasoning_effort: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    if reasoning_effort is not None:
        payload["reasoning_effort"] = reasoning_effort
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            "http://localhost:4000/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        r.raise_for_status()
        data: dict[str, object] = r.json()
        return data


def _report(tag: str, data: dict[str, object]) -> None:
    choices = data.get("choices")
    choice = choices[0] if isinstance(choices, list) and choices else {}
    finish = choice.get("finish_reason") if isinstance(choice, dict) else None
    msg = choice.get("message") if isinstance(choice, dict) else {}
    content = str(msg.get("content") or "") if isinstance(msg, dict) else ""
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}

    print(f"\n========== {tag} ==========")
    print(f"finish_reason: {finish!r}   usage: {usage}")
    print(f"content len:   {len(content)}")
    print(f"content HEAD:  {content[:200]!r}")
    print(f"content TAIL:  {content[-200:]!r}")
    parsed = _parse_rubric_scores(content, "diagnostic")
    print(f"parse result:  {parsed}")
    # raw json.loads attempt on the outermost {...} for the exact error
    stripped = content.strip()
    a, b = stripped.find("{"), stripped.rfind("}")
    cand = stripped[a : b + 1] if a != -1 and b > a else stripped
    try:
        json.loads(cand)
        print("raw json.loads: OK")
    except Exception as exc:
        print(f"raw json.loads: FAIL -> {exc}")


async def _main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm-spend", action="store_true")
    ap.add_argument("--model", default="gpt-5-mini-judge")
    ap.add_argument("--max-tokens", type=int, default=2048)
    args = ap.parse_args()

    os.chdir(REPO)
    _load_env(REPO)
    key = os.environ.get("LITELLM_MASTER_KEY", "")
    if not key:
        print("ERROR: LITELLM_MASTER_KEY not set", file=sys.stderr)
        return 2
    if not args.confirm_spend:
        print("DRY: pass --confirm-spend (~$0.02)")
        return 0

    criteria = _load_rubric_criteria("be_01_jwt_auth")
    candidate = (REPO / "evals/task-packs/be_01_jwt_auth/gold/solution.ts").read_text()
    prompt = _build_rubric_prompt(criteria, candidate)
    print(f"rubric criteria: {list(criteria)}  prompt chars: {len(prompt)}")

    base = await _call(
        model=args.model, prompt=prompt, key=key, max_tokens=args.max_tokens, json_mode=False
    )
    _report(f"{args.model} max_tokens={args.max_tokens} json_mode=OFF", base)

    jm = await _call(
        model=args.model, prompt=prompt, key=key, max_tokens=args.max_tokens, json_mode=True
    )
    _report(f"{args.model} max_tokens={args.max_tokens} json_mode=ON", jm)

    # The hypothesis fix: cap reasoning so tokens are left for the answer.
    re_low = await _call(
        model=args.model,
        prompt=prompt,
        key=key,
        max_tokens=args.max_tokens,
        json_mode=False,
        reasoning_effort="low",
    )
    _report(f"{args.model} max_tokens={args.max_tokens} reasoning_effort=low", re_low)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
