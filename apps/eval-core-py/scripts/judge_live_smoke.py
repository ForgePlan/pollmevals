"""Live judge-panel smoke (RFC-002 operationalization — G1-G6 validation).

Cost-bounded real run against the LiteLLM proxy: validates that the judge panel
works end-to-end with real models — non-degenerate Krippendorff alpha (G1 +
alpha gate), per-judge cost/token/latency accounting (G6), and the calibration /
identification-probe eval paths (G2).

NOT a pytest test (it spends money). Run manually with .env sourced and the
LiteLLM proxy up:

    set -a && source .env && set +a
    uv run --project apps/eval-core-py python apps/eval-core-py/scripts/judge_live_smoke.py

~6 real judge calls (score x3 judges + 2 calibration + 1 probe) ≈ $0.05.

Proxy-auth note: the client authenticates to the LiteLLM proxy with
LITELLM_MASTER_KEY (sk-local...), NOT the OpenRouter upstream key. The panel now
defaults api_key_env to LITELLM_MASTER_KEY and passes base_url/api_key to
get_model + model= to eval_async, so this script needs no env workarounds — just
`source .env` (for LITELLM_MASTER_KEY) and a running proxy.
"""

from __future__ import annotations

import asyncio
import pathlib
import sys
from datetime import UTC, datetime
from decimal import Decimal

_REPO = pathlib.Path(__file__).resolve().parents[3]
_APP = _REPO / "apps" / "eval-core-py"
sys.path.insert(0, str(_APP))

from src.contracts import (  # noqa: E402
    ArtifactRef,
    EvalArtifactRefs,
    EvalRow,
    EvalStats,
    EvalStatus,
)
from src.orchestrator.eval_caller import EvalRequest, EvalResult  # noqa: E402
from src.orchestrator.judge_panel import JudgePanel  # noqa: E402

_TASK = "doc_01_cli_readme"
_PACK = _REPO / "evals" / "task-packs" / _TASK
_CANDIDATE_MODEL = "openrouter/meta-llama/llama-3.3-70b-instruct"  # meta-llama != judge families
# Strong, family-diverse judge panel (anthropic / openai / google) — judges MUST
# be capable models (CONTEXT.md: min 3, different families). gpt-5-mini is a
# reasoning model: under the old 768 cap its reasoning tokens exhausted the
# budget before it emitted JSON (empty completion). The rubric cap is now 2048
# (_DEFAULT_JUDGE_MAX_TOKENS_RUBRIC) to give reasoning judges room; if a judge
# still truncates, cap reasoning (reasoning_effort) rather than downgrade it.
# For an even stronger panel: gpt-5, claude-opus-4-7, gemini-2-5-pro, grok-4.
_JUDGES = ["claude-sonnet-4-6-judge", "gpt-5-mini-judge", "gemini-3-flash"]
_PROBE_FAMILIES = frozenset({"anthropic", "openai", "google", "qwen", "meta"})


def _make_eval_result(raw_output_uri: str) -> EvalResult:
    """Minimal real EvalResult whose raw_output points at a real README file."""
    import hashlib

    eval_id = "deadbeefcafe0101"

    def _ref(label: str) -> ArtifactRef:
        content = f"{label}:{eval_id}"
        sha256 = hashlib.sha256(content.encode()).hexdigest()
        return ArtifactRef(
            sha256=sha256,
            size_bytes=len(content),
            uri=raw_output_uri if label == "raw_output" else f"file:///tmp/{label}-{sha256}.txt",
            mime_type="text/plain",
        )

    row = EvalRow(
        eval_id=eval_id,
        model_id=_CANDIDATE_MODEL,
        stack_id="raw-llm",
        task_id=_TASK,
        seed=42,
        status=EvalStatus.SCORED,
        artifact_refs=EvalArtifactRefs(
            raw_output=_ref("raw_output"),
            normalized_output=_ref("normalized_output"),
            evaluator_json=_ref("evaluator_json"),
        ),
        stats=EvalStats(
            input_tokens=100,
            output_tokens=50,
            wall_clock_ms=1000,
            cost_usd=Decimal("0.01"),
        ),
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    request = EvalRequest(
        eval_id=eval_id,
        model_id=_CANDIDATE_MODEL,
        stack_id="raw-llm",
        task_id=_TASK,
        seed=42,
    )
    return EvalResult(
        request=request,
        eval_row=row,
        exception=None,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


async def main() -> int:
    # Turnkey: the only env requirement is LITELLM_MASTER_KEY (the proxy key),
    # provided by `source .env`. The panel now passes base_url/api_key to
    # get_model and model= to eval_async, and defaults api_key_env to the proxy
    # key — so NO OPENAI_* / INSPECT_EVAL_MODEL pre-wiring is needed (the three
    # wiring gaps the first live run surfaced are fixed in judge_panel.py).
    panel = JudgePanel(
        judge_models=_JUDGES,
        candidate_model_id=_CANDIDATE_MODEL,
        rubric_version="1.0",
    )

    candidate_path = _PACK / "calibration" / "good" / "sample-001.md"
    print(f"→ score(): {len(_JUDGES)} judges grade a real doc_01 README ({candidate_path.name})")
    eval_result = _make_eval_result(f"file://{candidate_path}")
    judgments = await panel.score(eval_result, _TASK)

    print(f"  got {len(judgments)} judgment(s):")
    for j in judgments:
        print(
            f"    judge={j.judge_model_id:<24} total={j.total_score:5.2f} "
            f"criteria={len(j.rubric_scores)} tok_in={j.tokens_in} tok_out={j.tokens_out} "
            f"lat_ms={j.latency_ms} cost=${j.cost_usd}"
        )

    agg = panel.aggregate(judgments)
    print(
        f"→ aggregate (alpha gate): status={agg.judge_status} n_used={agg.n_judges_used} "
        f"alpha_point={agg.alpha_point} alpha_ci_lower={agg.alpha_ci_lower}"
    )

    # ── G2: calibration eval path (perfect should score above broken) ──────
    print("→ G2 calibration smoke (1 judge x perfect/broken sample):")
    perfect = (_PACK / "calibration" / "perfect" / "sample-001.md").read_text(encoding="utf-8")
    broken = (_PACK / "calibration" / "broken" / "sample-001.md").read_text(encoding="utf-8")
    cp = await panel._score_calibration_sample(_JUDGES[0], perfect, _TASK)
    cb = await panel._score_calibration_sample(_JUDGES[0], broken, _TASK)
    ordering = "OK (perfect>broken)" if cp > cb else "INVERTED — investigate"
    print(f"    perfect={cp:.2f} broken={cb:.2f} → {ordering}")

    # ── G2: identification probe eval path ─────────────────────────────────
    probe_files = sorted((_PACK / "identification_probe").glob("*.md"))
    if probe_files:
        pf = probe_files[0]
        true_family = pf.stem.split("-")[0]
        guess = await panel._score_identification_sample(
            _JUDGES[0], pf.read_text(encoding="utf-8"), _PROBE_FAMILIES, _TASK
        )
        valid = guess in _PROBE_FAMILIES or guess == "unknown"
        print(
            f"→ G2 probe smoke: sample={pf.name} true={true_family} guess={guess} "
            f"(valid_output={valid})"
        )

    print("DONE — judge panel ran end-to-end against real models.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
