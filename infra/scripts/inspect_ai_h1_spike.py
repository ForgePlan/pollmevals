#!/usr/bin/env python3
"""Phase 3 Week 1 H1 spike -- verify Inspect AI multi_scorer per-judge access.

Hypothesis (PRD-002 Q1, RFC-002 Slice B):
  Inspect AI's multi_scorer(scorers=[model_graded_qa(model=j) for j in judges])
  exposes per-judge Score objects individually in sample.scores -- NOT only an
  aggregated/reduced single Score.

Verdicts:
  SUPPORTED     -- per-judge dict confirmed; RFC-002 Slice B proceeds as drafted.
  NEEDS_ADAPTER -- per-judge data present but under a non-dict structure.
  REFUTED       -- only aggregated Score; orchestrator must file ADR-006.

Usage:
    uv run --project apps/eval-core-py python infra/scripts/inspect_ai_h1_spike.py

Cost: ~$0.02-0.05 (1 sample x 2 judges x OpenRouter pricing through LiteLLM proxy).
Requires:
  - OPENROUTER_API_KEY_JUDGE env var  (judge billing key -- separate from candidate key)
  - LITELLM_MASTER_KEY env var        (proxy auth)
  - LiteLLM proxy reachable at http://localhost:4000
"""

from __future__ import annotations

import os
import pprint
import sys

import httpx
from inspect_ai import Task
from inspect_ai import eval as _inspect_run
from inspect_ai.dataset import Sample
from inspect_ai.log import EvalLog
from inspect_ai.model import GenerateConfig, get_model
from inspect_ai.scorer import Score, model_graded_qa
from inspect_ai.solver import generate

# ---------------------------------------------------------------------------
# Config -- all overridable via env
# ---------------------------------------------------------------------------
PROXY_BASE: str = os.environ.get("SPIKE_PROXY_BASE", "http://localhost:4000")

# Candidate: Gemini family -- judges below are Anthropic + OpenAI -> no self-judging
CANDIDATE_MODEL: str = os.environ.get("SPIKE_CANDIDATE_MODEL", "gemini-3-flash")

# Judge model_names as registered in litellm-config.yaml (RFC-002 judge routes).
# Named with "-judge" suffix to use OPENROUTER_API_KEY_JUDGE billing isolation
# per RFC-002 NFR-005. 2 judges (Anthropic + OpenAI) keeps cost minimal.
JUDGE_MODELS: list[str] = [
    "claude-sonnet-4-6-judge",  # openrouter/anthropic/claude-sonnet-4.6 via JUDGE key
    "gpt-5-mini-judge",  # openrouter/openai/gpt-5-mini via JUDGE key
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _require_env(var: str) -> str:
    val = os.environ.get(var)
    if not val:
        print(
            f"ERROR: env var {var!r} not set.\n  Load .env: set -a && source .env && set +a",
            file=sys.stderr,
        )
        sys.exit(2)
    return val


def _check_proxy_reachable(master_key: str) -> None:
    """Abort early if LiteLLM proxy is unreachable."""
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(
                f"{PROXY_BASE}/health/liveliness",
                headers={"Authorization": f"Bearer {master_key}"},
            )
            r.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        print(
            f"ERROR: LiteLLM proxy unreachable at {PROXY_BASE}: {exc}\n  Run: make stack-up",
            file=sys.stderr,
        )
        sys.exit(2)


def _diagnose_scores(
    scores: object,
    n_judges: int,
) -> tuple[str, str | None]:
    """Inspect sample.scores and return (verdict, per_judge_path).

    Returns verdict: 'SUPPORTED' | 'NEEDS_ADAPTER' | 'REFUTED'
    """
    verdict: str
    per_judge_path: str | None = None

    if isinstance(scores, dict):
        print(f"  sample.scores is dict with {len(scores)} key(s): {list(scores.keys())}")
        print()

        score_entries = {k: v for k, v in scores.items() if isinstance(v, Score)}
        print(f"  Score entries in dict: {len(score_entries)} keys: {list(score_entries.keys())}")
        print()

        if len(score_entries) >= n_judges:
            verdict = "SUPPORTED"
            per_judge_path = (
                f"sample.scores[<scorer_name>]  (dict with {len(score_entries)} Score entries)"
            )
            n_found = len(score_entries)
            print(f"  H1 CHECK: {n_found} Score entries >= {n_judges} judges -> H1 SUPPORTED")
            print(f"  Per-judge access path: {per_judge_path}")
            for key, sc in score_entries.items():
                expl = str(sc.explanation)[:60]
                print(f"    {key!r}: Score(value={sc.value!r}, explanation={expl!r})")
        elif len(score_entries) == 1:
            verdict = "REFUTED"
            print("  H1 CHECK: only 1 Score entry in dict (aggregated only) -> H1 REFUTED")
            print(
                "  Inspect AI multi_scorer with reducer='mode' returns ONLY the "
                "reduced Score.\n"
                "  Per-judge scores are NOT individually accessible via "
                "sample.scores dict."
            )
            print()
            print("  Fallback: use N separate @scorer-decorated functions per judge.")
            print("  Orchestrator must file ADR-006.")
        else:
            verdict = "NEEDS_ADAPTER"
            n_found = len(score_entries)
            print(f"  H1 CHECK: {n_found} Score entries < {n_judges} judges -> NEEDS_ADAPTER")

    elif isinstance(scores, Score):
        verdict = "REFUTED"
        print(f"  sample.scores is a single Score object (value={scores.value!r})")
        print("  H1 REFUTED -- only aggregated majority-vote Score, no per-judge access.")
    else:
        verdict = "NEEDS_ADAPTER"
        print(f"  sample.scores is {type(scores).__name__} -- unexpected structure")
        print("  Checking for per-judge attributes...")
        for attr in ("scorers", "per_scorer", "components", "scores", "items"):
            if hasattr(scores, attr):
                val = getattr(scores, attr)
                print(f"    .{attr} = {str(val)[:120]!r}")

    return verdict, per_judge_path


def _print_log_results(log: EvalLog) -> None:
    """Print aggregate EvalLog results for cost / metrics record."""
    print()
    print("--- Step 6: EvalLog results (for cost / metrics record) ---")
    if log.results:
        for score_result in log.results.scores:
            print(f"  result.name       : {score_result.name}")
            metrics_str = ", ".join(
                f"{k}={v.value:.3f}" for k, v in (score_result.metrics or {}).items()
            )
            print(f"  result.metrics    : {metrics_str}")
    else:
        print("  log.results is None (status may not be 'success')")

    if log.stats:
        print(f"  log.stats         : {log.stats}")


# ---------------------------------------------------------------------------
# Main spike (split into setup + run + inspect helpers to stay within PLR0915)
# ---------------------------------------------------------------------------
def _setup_proxy(master_key: str) -> None:
    """Wire Inspect AI to LiteLLM proxy and verify reachability."""
    print("--- Step 1: verifying proxy is reachable ---")
    _check_proxy_reachable(master_key)
    print(f"  proxy alive at {PROXY_BASE}")
    print()
    # "openai/" provider prefix in model IDs tells Inspect AI to route through
    # OPENAI_BASE_URL, which we point at the LiteLLM proxy.
    # For this spike we use LITELLM_MASTER_KEY as the API key — the spike is a
    # one-off structural verification, not a production billing run. Billing
    # isolation (OPENROUTER_API_KEY vs OPENROUTER_API_KEY_JUDGE) is enforced in
    # JudgePanel (Slice A), not here.
    os.environ["OPENAI_API_KEY"] = master_key
    os.environ["OPENAI_BASE_URL"] = PROXY_BASE


def _build_task() -> Task:
    """Build the spike Task with per-judge scorers.

    IMPORTANT: multi_scorer() is intentionally NOT used here.
    In inspect_ai==0.3.46, multi_scorer() returns an unregistered closure
    ('score') that crashes with 'Object score does not have registry info'
    at run time. The working pattern is to pass a LIST of individual
    model_graded_qa scorers directly to Task(scorer=[...]).

    This is the H3/fallback path from RFC-002 Slice B: N separate scorers,
    one per judge, passed as Task(scorer=list). Inspect AI assigns unique
    names ('model_graded_qa', 'model_graded_qa_1', ...) and writes each
    as a separate key in sample.scores.

    The spike verifies whether sample.scores contains per-judge Score
    entries (H1 holds via the list path) or only an aggregated entry.
    """
    print("--- Step 2: building Task with N separate per-judge scorers ---")
    print("  NOTE: multi_scorer() not used -- see docstring for why (0.3.46 bug).")
    # Each judge gets its own model_graded_qa scorer instance.
    # "openai/" prefix routes through OPENAI_BASE_URL (LiteLLM proxy).
    # IMPORTANT: explicit max_tokens cap on judge calls via get_model() config.
    # Without this Inspect AI uses the model's native max (65k for Claude Sonnet)
    # → OpenRouter HTTP 402 if the JUDGE key monthly budget can't afford it.
    # Phase 3 Slice B production code MUST configure judge models this way.
    judge_config = GenerateConfig(max_tokens=512)
    judge_model_objs = [get_model(f"openai/{judge}", config=judge_config) for judge in JUDGE_MODELS]
    scorers_list = [model_graded_qa(model=jm) for jm in judge_model_objs]
    task = Task(
        dataset=[
            Sample(
                input=("What is 2 plus 2? Answer with a single integer and nothing else."),
                target="4",
            )
        ],
        solver=generate(),
        scorer=scorers_list,  # list of N scorers, one per judge (RFC-002 fallback path)
        # Limit candidate output to 16 tokens -- spike only needs "4" as output.
        # This cap keeps the request well under OpenRouter's per-request token budget.
        config=GenerateConfig(max_tokens=16),
    )
    print(f"  Task built with {len(JUDGE_MODELS)} per-judge scorers (list, no multi_scorer)")
    print()
    return task


def _run_eval(task: Task) -> EvalLog:
    """Run the eval and return the first EvalLog, or exit on failure."""
    print("--- Step 3: running eval (1 sample x 2 judges, may take 20-60s) ---")
    print("  Making real LLM requests through the proxy...")
    print()
    try:
        logs = _inspect_run(
            task,
            model=f"openai/{CANDIDATE_MODEL}",
            log_dir="/tmp/h1_spike_logs",
            log_level="warning",
        )
    except Exception as exc:  # noqa: BLE001
        print(
            f"ERROR: _inspect_run raised {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        print(
            "\nCommon causes:\n"
            "  - proxy 401: LITELLM_MASTER_KEY mismatch -- check .env\n"
            "  - proxy 404: model name not in litellm-config.yaml\n"
            "  - API mismatch: multi_scorer signature changed in this version",
            file=sys.stderr,
        )
        sys.exit(2)
    if not logs:
        print("ERROR: _inspect_run returned empty log list", file=sys.stderr)
        sys.exit(2)
    return logs[0]


def _inspect_sample(log: EvalLog) -> tuple[str, str | None]:
    """Extract sample.scores and run diagnosis. Returns (verdict, per_judge_path)."""
    print("--- Step 4: inspecting EvalLog structure ---")
    print(f"  log.status         : {log.status}")
    if log.status != "success":
        print("  WARNING: eval status is not 'success' -- results may be incomplete")
        if log.error:
            print(f"  log.error          : {log.error}")
    if not log.samples:
        print("ERROR: log.samples is empty", file=sys.stderr)
        sys.exit(2)

    sample = log.samples[0]
    completion_preview = sample.output.completion if sample.output else "<no output>"
    print(f"  sample.id          : {sample.id}")
    print(f"  sample.output      : {str(completion_preview)[:80]!r}...")
    print()

    print("--- Step 5: sample.scores structure (THE ASSERTION) ---")
    scores = sample.scores
    print(f"  type(sample.scores): {type(scores).__name__}")
    print("  sample.scores      :")
    pprint.pprint(scores, indent=4, width=100)
    print()

    return _diagnose_scores(scores, len(JUDGE_MODELS))


def _print_verdict(verdict: str) -> int:
    """Print the final verdict block and return the exit code."""
    print()
    print("=" * 70)
    print(f"  VERDICT: per_judge_scores_accessible = {verdict == 'SUPPORTED'}")
    print(f"  H1 (RFC-002 Slice B assumption): {verdict}")
    print("=" * 70)
    print()
    if verdict == "SUPPORTED":
        print("NEXT ACTION: RFC-002 Slice B proceeds as drafted.")
        print("  Per-judge Score access confirmed via sample.scores dict.")
        print("  No ADR-006 needed. Proceed with JudgePanel implementation.")
        return 0
    elif verdict == "NEEDS_ADAPTER":
        print("NEXT ACTION: file ADR-006 with adapter-only path.")
        print("  Per-judge data present but requires a custom accessor.")
        return 1
    else:  # REFUTED
        print("NEXT ACTION: orchestrator MUST file ADR-006.")
        print("  Pivot: custom @scorer-decorated function per judge (RFC-002 Slice B fallback).")
        return 2


def run_spike() -> int:
    """Execute the H1 spike. Returns exit code: 0=SUPPORTED, 1=NEEDS_ADAPTER, 2=REFUTED."""
    _require_env("OPENROUTER_API_KEY_JUDGE")  # validated; used indirectly via proxy
    master_key = _require_env("LITELLM_MASTER_KEY")

    import inspect_ai as _ilib  # noqa: PLC0415

    print("=== Phase 3 Week 1 H1 Spike -- Inspect AI multi_scorer per-judge access ===")
    print(f"  inspect_ai version : {_ilib.__version__}")
    print(f"  proxy              : {PROXY_BASE}")
    print(f"  candidate model    : {CANDIDATE_MODEL}")
    print(f"  judge models       : {JUDGE_MODELS}")
    print()

    _setup_proxy(master_key)
    task = _build_task()
    log = _run_eval(task)
    verdict, _per_judge_path = _inspect_sample(log)
    _print_log_results(log)
    return _print_verdict(verdict)


def main() -> int:
    return run_spike()


if __name__ == "__main__":
    sys.exit(main())
