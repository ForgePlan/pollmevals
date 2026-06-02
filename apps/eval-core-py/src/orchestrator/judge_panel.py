"""JudgePanel — multi-judge scoring layer for POLLMEVALS (RFC-002).

This module is the parallel companion to eval_caller.py — same Protocol-driven
testability seam discipline (EVID-015), no inheritance, no framework coupling.

Slice A (this file): skeleton + self-judging guard.
Slice B (score()): Inspect AI list-of-scorers wiring (per EVID-023 findings).
Slice C (aggregate()): Krippendorff alpha + bootstrap CI computation.
Slice D (run_calibration()): calibration suite + identification probe.
Slice E (grid_runner.py): GridRunner integration.

Key finding from EVID-023 H1 spike:
  - multi_scorer() is BROKEN in inspect_ai==0.3.46 — do NOT use.
  - Production path: pass a LIST of model_graded_qa scorers to Task(scorer=[...]).
  - Inspect AI auto-assigns names: 'model_graded_qa', 'model_graded_qa_1', …
  - Judge max_tokens MUST be capped via get_model(config=GenerateConfig(max_tokens=N))
    to avoid OpenRouter HTTP 402 budget exhaustion on long-context models.

Concurrency is OUTSIDE this module — same discipline as eval_caller.py:13-14.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import pathlib
import random
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, cast

import numpy as np
import yaml
from inspect_ai.model import GenerateConfig

from src.contracts import (
    CalibrationResult,
    JudgeAggregation,
    JudgeCalibration,
    Judgment,
    ProbeResult,
)
from src.orchestrator.cost import PricingTuple, compute_cost

if TYPE_CHECKING:
    from inspect_ai import Task as InspectTask
    from inspect_ai.log import EvalLog
    from inspect_ai.model import Model as InspectModel
    from inspect_ai.scorer import Scorer
    from inspect_ai.solver import Generate, Solver, TaskState

    from src.orchestrator.eval_caller import EvalResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Family normalisation table
# Known vendor families: segment after optional "openrouter/" prefix.
# Keys are normalised segment values; values are the canonical family name.
# Order matters: more specific prefixes first (e.g. "meta-llama" before "meta").
# ---------------------------------------------------------------------------

_FAMILY_ALIASES: dict[str, str] = {
    # Anthropic
    "anthropic": "anthropic",
    "claude": "anthropic",  # LiteLLM proxy aliases like "claude-sonnet-4-6-judge"
    # OpenAI
    "openai": "openai",
    "gpt": "openai",  # proxy alias like "gpt-5-mini-judge"
    # Google
    "google": "google",
    "gemini": "google",  # proxy alias like "gemini-3-flash"
    # Meta / Llama
    "meta-llama": "meta-llama",
    "meta": "meta-llama",
    "llama": "meta-llama",
    # Qwen (Alibaba)
    "qwen": "qwen",
    "alibaba": "qwen",
}

# Default judge max_tokens cap per EVID-023 finding (prevents HTTP 402 on
# OpenRouter when key budget is low — Claude Sonnet native max is 65k).
_DEFAULT_JUDGE_MAX_TOKENS = 512

# Rubric-path token cap.  Set to 2048 so STRONG / reasoning judges (e.g.
# gpt-5-mini) have room for reasoning tokens PLUS the full per-criterion JSON —
# at 768 a reasoning judge exhausted the budget and returned an empty completion
# (RFC-002 live run).  The upper bound is the OpenRouter HTTP-402 hazard
# (EVID-023): OpenRouter pre-reserves max_tokens * completion_price, so this only
# stays safe on a FUNDED account — the live run's 402 at 1536 was a depleted key
# (monthly budget exhausted), NOT the cap being inherently too high.  If a
# reasoning judge still truncates at 2048, cap reasoning via reasoning_effort
# rather than raising further.  Separate from the binary path (512).
#
# DONE (2026-06-02, EVID-050): gpt-5-mini spent ALL 2048 tokens on reasoning
# (finish_reason="length", empty content → unparseable JSON → false 0.0). Fix =
# `reasoning_effort: low` on the gpt-5-mini-judge alias in
# infra/litellm-config.yaml. It lives PROXY-side because inspect_ai 0.3.46
# GenerateConfig has no reasoning_effort / extra_body passthrough.
_DEFAULT_JUDGE_MAX_TOKENS_RUBRIC = 2048

# G3: calibration sample file extensions per task language. be_01 uses .ts,
# fe_01 .tsx, doc_01 .md. The calibration loader must glob all of these or
# code packs are silently skipped.
_CALIBRATION_SAMPLE_EXTS: tuple[str, ...] = (".md", ".ts", ".tsx", ".py", ".txt")

# Identification-probe token cap (G2 / Slice D): the judge answers with a single
# family word, so a tight cap keeps the SC-4 anonymisation probe cheap.
_DEFAULT_JUDGE_MAX_TOKENS_PROBE = 32

# G6: default judge pricing for cost attribution.  Judge cost is computed from
# the real per-call token counts (captured in Score.metadata at generate time)
# times this rate.  Judges are a mix of vendor families; we use a
# Claude-Sonnet-class $3 / $15 per-Mtoken rate as a conservative blended default
# (slightly over-estimates -> budget-safe).  snapshot_at = Unix epoch is a
# sentinel meaning "estimate, not a fetched OpenRouter snapshot"; wiring real
# per-judge pricing from the proxy is a follow-up (does not touch this contract).
_DEFAULT_JUDGE_PRICING = PricingTuple(
    model_id="_judge_default",
    input_per_mtoken_usd=Decimal("3.0"),
    output_per_mtoken_usd=Decimal("15.0"),
    snapshot_at=datetime(1970, 1, 1, tzinfo=UTC),
)


@dataclass
class _JudgeTokenStats:
    """Minimal stats shim satisfying ``cost.EvalStatsLike`` for judge cost (G6).

    ``compute_cost`` only reads ``input_tokens`` / ``output_tokens``; this
    two-field record adapts the per-judge counts (read back from Score.metadata)
    to that protocol without importing inspect_ai's ModelUsage at runtime.

    Not ``frozen``: ``EvalStatsLike`` declares its members as settable, so a
    frozen (read-only) dataclass would fail the Protocol's structural check.
    """

    input_tokens: int
    output_tokens: int


# ---------------------------------------------------------------------------
# Module-level helpers (Slice D)
# ---------------------------------------------------------------------------


def cast_dict(value: object) -> dict[str, object]:
    """Safely cast YAML-loaded mapping to dict[str, object].

    yaml.safe_load returns ``dict[Any, Any]`` when the YAML node is a mapping.
    The isinstance guard narrows the type; the explicit cast makes mypy happy
    under --strict without requiring a broad ``Any`` annotation.
    """
    if not isinstance(value, dict):
        return {}
    # PyYAML loads YAML mappings as dict[str, Any] when keys are strings.
    # We assert the key type via explicit conversion for the mypy --strict path.
    return {str(k): v for k, v in value.items()}


def _spearman_r(x: np.ndarray, y: np.ndarray) -> float:
    """Compute Spearman rank correlation using numpy (no scipy dependency).

    Uses the standard formula:
        r_s = 1 - (6 * sum(d²)) / (n * (n² - 1))
    where d = rank(x) - rank(y) using average rank for ties.

    Returns 0.0 for degenerate inputs (n < 2 or zero-variance ranks).
    Range: [-1.0, 1.0].

    Args:
        x: 1-D numpy array of gold scores.
        y: 1-D numpy array of judge scores (same length as x).
    """
    n = len(x)
    if n < 2:
        return 0.0

    # Average-rank method — handles ties correctly (gold samples at the same
    # quality level share the same gold score and therefore share a rank).
    def _rank_with_ties(arr: np.ndarray) -> np.ndarray:
        order = np.argsort(arr, kind="stable")
        ranks = np.empty(n, dtype=float)
        ranks[order] = np.arange(1, n + 1, dtype=float)
        # Resolve ties: find groups of equal values and assign average rank.
        i = 0
        while i < n:
            j = i + 1
            while j < n and arr[order[i]] == arr[order[j]]:
                j += 1
            if j > i + 1:  # tie group found
                avg_rank = (i + 1 + j) / 2.0  # average of 1-indexed ranks
                for k in range(i, j):
                    ranks[order[k]] = avg_rank
            i = j
        return ranks

    rx = _rank_with_ties(x)
    ry = _rank_with_ties(y)
    d = rx - ry
    d_sq_sum = float(np.sum(d**2))
    denominator = n * (n**2 - 1)
    if denominator == 0:
        return 0.0
    rs = 1.0 - 6.0 * d_sq_sum / denominator
    # Clamp to [-1, 1] to guard against floating-point drift.
    return float(max(-1.0, min(1.0, rs)))


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class SelfJudgingError(ValueError):
    """Raised when judge_models contains the candidate's vendor family.

    Cardinal-sin guard per judge-policy.md:1. Family-level match (NOT raw
    string) — 'openrouter/anthropic/claude-haiku' and 'anthropic/claude-sonnet'
    both normalise to family 'anthropic'.

    SC-2 in PRD-002: zero self-judging incidents. This guard fires in
    JudgePanel.__init__ so the panel never reaches score() with a violation.
    """


class JudgeUnavailableError(Exception):
    """Raised by JudgePanel.score() when fewer than N judges responded but >= N-1.

    Carries the partial list of judgments that DID return so the caller
    (GridRunner judge hook) can pass them to JudgePanel.aggregate() — the
    DEGRADED path under PRD-002 Q3: proceed at N-1 with judge_status=DEGRADED
    and alpha=None for that eval.

    If fewer than N-1 judges respond, the panel raises a plain RuntimeError
    instead: the eval cannot satisfy the publication-policy minimum (>= 3
    judges per judge-policy.md), so the orchestrator records the row as
    FAILED rather than DEGRADED.

    Attributes:
        partial_judgments: List of Judgment objects from judges that responded.
            Always `len < n_judges_requested` and `len >= n_judges_requested - 1`.
        n_judges_requested: Configured panel size.
        message: Human-readable summary including which judge dropped out.
    """

    def __init__(
        self,
        message: str,
        partial_judgments: list[Judgment],
        n_judges_requested: int,
    ) -> None:
        super().__init__(message)
        self.partial_judgments = partial_judgments
        self.n_judges_requested = n_judges_requested


# ---------------------------------------------------------------------------
# Family normalisation (static, no network)
# ---------------------------------------------------------------------------


def _normalise_model_family(model_id: str) -> str:
    """Extract vendor family from a model ID string.

    Handles three routing patterns:
      1. OpenRouter prefix:  openrouter/anthropic/claude-sonnet-4-6  → anthropic
      2. Direct vendor:      anthropic/claude-haiku                  → anthropic
      3. LiteLLM proxy alias: claude-sonnet-4-6-judge               → anthropic
                              gpt-5-mini-judge                       → openai
                              gemini-3-flash                         → google

    Algorithm:
      - Split on '/'.
      - If first segment is 'openrouter', drop it.
      - The next segment is the family candidate.
      - Look up _FAMILY_ALIASES for the canonical name.
      - If not found, return the candidate as-is (unknown family treated as
        its own unique family — prevents false self-judging refusals for
        open-weight models served on specialised hosts like 'runpod').

    Examples (all verified by unit tests):
      openrouter/anthropic/claude-sonnet-4-6    → anthropic
      anthropic/claude-haiku                    → anthropic
      openrouter/openai/gpt-5-mini              → openai
      openrouter/google/gemini-3-flash-preview  → google
      openrouter/meta-llama/llama-3.3-70b       → meta-llama
      openai/Qwen/Qwen3-14B                     → qwen  (note: openai prefix here is the
                                                         provider hub, not the vendor family)
      claude-sonnet-4-6-judge                   → anthropic  (proxy alias)
    """
    parts = model_id.split("/")

    # Drop the aggregator prefix if present.
    if parts[0].lower() == "openrouter":
        parts = parts[1:]

    # Drop generic provider prefixes that are NOT themselves vendor families.
    # "openai/" used as the OPENAI_BASE_URL routing prefix in Inspect AI (see
    # inspect_ai_h1_spike.py:213) means the next segment is the actual vendor.
    # Only drop if there are 3+ segments: openai/Qwen/Qwen3-14B → Qwen/Qwen3-14B.
    # With 2 segments (openai/gpt-5-mini), "openai" is the vendor itself — keep it.
    if parts[0].lower() == "openai" and len(parts) >= 3:
        parts = parts[1:]

    family_candidate = parts[0].lower()

    # Handle proxy aliases that embed the family in the model name itself
    # (e.g. "claude-sonnet-4-6-judge" → "claude-" prefix → anthropic).
    if family_candidate not in _FAMILY_ALIASES:
        for prefix, canonical in _FAMILY_ALIASES.items():
            if family_candidate.startswith(prefix):
                return canonical
        # Unknown family — return the raw candidate so it's treated as its
        # own unique family (no false self-judging refusal for novel hosts).
        return family_candidate

    return _FAMILY_ALIASES[family_candidate]


# ---------------------------------------------------------------------------
# Rubric helpers (G1 — per-criterion scoring)
# ---------------------------------------------------------------------------


def _load_rubric_criteria(task_id: str) -> dict[str, dict[str, object]]:
    """Load rubric criteria from evals/task-packs/<task_id>/rubric.yaml.

    Returns a dict keyed by criterion name.  Each value is the raw criterion
    dict from YAML (contains at minimum ``weight``, ``description``,
    ``anchors``).  Never hardcodes criteria — dynamic per task.

    Path convention mirrors ``run_calibration()`` (:~674):
        ``pathlib.Path.cwd() / "evals" / "task-packs" / task_id / "rubric.yaml"``

    Args:
        task_id: eval task slug (e.g. ``"doc_01_cli_readme"``).

    Returns:
        dict[criterion_name, criterion_dict] — order preserved from YAML.

    Raises:
        FileNotFoundError: if ``rubric.yaml`` is missing for the task.
        ValueError: if the YAML is missing the ``criteria`` key.
    """
    repo_root = pathlib.Path.cwd()
    rubric_path = repo_root / "evals" / "task-packs" / task_id / "rubric.yaml"

    if not rubric_path.exists():
        raise FileNotFoundError(f"rubric.yaml not found for task {task_id!r}: {rubric_path}")

    raw = yaml.safe_load(rubric_path.read_text(encoding="utf-8"))
    raw_dict = cast_dict(raw)
    criteria_raw = raw_dict.get("criteria")
    if not isinstance(criteria_raw, dict):
        raise ValueError(
            f"rubric.yaml for task {task_id!r} is missing the 'criteria' key or it is not a mapping"
        )
    return {str(k): cast_dict(v) for k, v in criteria_raw.items()}


def _build_rubric_prompt(
    rubric_criteria: dict[str, dict[str, object]],
    candidate_output: str,
) -> str:
    """Build the per-criterion rubric scoring prompt presented to a judge.

    Shared by the production scorer (``_make_rubric_scorer``) and the
    calibration path (``_score_calibration_sample``) so both present IDENTICAL
    instructions — calibration measures the same scoring behaviour used in
    production, with no second prompt that could silently drift.
    """
    criteria_lines: list[str] = []
    for cname, cdict in rubric_criteria.items():
        weight = cdict.get("weight", 1.0)
        description = str(cdict.get("description", "")).strip()
        anchors_raw = cdict.get("anchors", {})
        # Anchor keys may be ints (YAML `0:`) or strings (`"0":`) — normalise to str.
        anchors: dict[str, object] = (
            {str(k): v for k, v in anchors_raw.items()} if isinstance(anchors_raw, dict) else {}
        )
        anchor_0 = str(anchors.get("0", "score 0")).strip()
        anchor_5 = str(anchors.get("5", "score 5")).strip()
        anchor_10 = str(anchors.get("10", "score 10")).strip()
        criteria_lines.append(
            f"Criterion: {cname} (weight={weight})\n"
            f"  Description: {description}\n"
            f"  Anchor 0:  {anchor_0}\n"
            f"  Anchor 5:  {anchor_5}\n"
            f"  Anchor 10: {anchor_10}"
        )

    criteria_block = "\n\n".join(criteria_lines)
    criterion_keys_json = json.dumps(list(rubric_criteria.keys()))

    return (
        "You are an expert code and documentation evaluator.\n\n"
        "Score the following candidate output against each rubric criterion "
        "on a scale from 0 to 10 (floats allowed, e.g. 7.5).\n\n"
        f"## Rubric criteria\n\n{criteria_block}\n\n"
        "## Candidate output\n\n"
        f"{candidate_output}\n\n"
        "## Instructions\n\n"
        "Respond with ONLY valid JSON (no markdown, no code fences), "
        "exactly in this shape:\n"
        '{"rubric_scores": {' + ", ".join(f'"{k}": <float_0_10>' for k in rubric_criteria) + "}, "
        '"total_score": <float_0_10>, '
        '"reasoning": "<brief explanation>"}\n\n'
        f"Criterion keys MUST be exactly: {criterion_keys_json}"
    )


def _parse_rubric_scores(explanation: str, judge_id: str) -> dict[str, float]:
    """Parse per-criterion scores from a judge's JSON explanation.

    Returns ``{criterion: clamped_0_10_float}``; on any parse failure logs a
    warning and falls back to ``{"overall": 0.0}`` (degenerate but non-crashing).
    Shared by ``score()`` and ``_score_calibration_sample`` so both interpret
    the judge's JSON identically.
    """
    rubric_scores: dict[str, float]
    # Judges sometimes wrap the JSON in markdown fences or surrounding prose
    # (RFC-002 live run: gpt-5-mini). Extract the outermost {...} object before
    # parsing; a truncated object (no closing brace) still falls through to the
    # fallback below.
    stripped = explanation.strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    candidate = stripped[start : end + 1] if start != -1 and end > start else stripped
    try:
        parsed = json.loads(candidate)
        raw_rubric = parsed.get("rubric_scores", {})
        rubric_scores = {
            str(k): max(0.0, min(10.0, float(v)))
            for k, v in raw_rubric.items()
            if isinstance(v, (int, float))
        }
        if not rubric_scores:
            raise ValueError("rubric_scores dict is empty or has no numeric values")
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning(
            "JudgePanel: failed to parse rubric JSON for judge %s (exc=%s); "
            "falling back to {'overall': 0.0}",
            judge_id,
            exc,
        )
        rubric_scores = {"overall": 0.0}
    return rubric_scores


def _read_judge_usage_meta(score_obj: object) -> tuple[int, int, int]:
    """Extract ``(tokens_in, tokens_out, latency_ms)`` from a Score's metadata.

    The rubric scorer stashes token counts + wall-clock latency in
    ``Score.metadata`` (G6).  Defensive on purpose: returns zeros when metadata
    is absent or not a real dict — unit tests feed MagicMock Score objects whose
    ``.metadata`` attribute is itself a MagicMock, and we must NOT treat that as
    usage data.
    """
    meta = getattr(score_obj, "metadata", None)
    if not isinstance(meta, dict):
        return 0, 0, 0

    def _as_int(value: object) -> int:
        if isinstance(value, (int, float)):
            return max(0, int(value))
        return 0

    return (
        _as_int(meta.get("tokens_in")),
        _as_int(meta.get("tokens_out")),
        _as_int(meta.get("latency_ms")),
    )


def _extract_family_guess(completion: str, probe_families: frozenset[str]) -> str:
    """Map a judge's free-text identification answer to a probe family.

    Prefers an exact first-word match, then falls back to a substring scan;
    returns ``"unknown"`` when no probe family appears (judge hedged, refused,
    or named a family outside the SC-4 list).
    """
    text = completion.lower().strip()
    if not text:
        return "unknown"
    first_word = text.split()[0].strip(".,!?\"'`:;")
    if first_word in probe_families:
        return first_word
    for family in sorted(probe_families):
        if family in text:
            return family
    return "unknown"


def _make_rubric_scorer(
    judge_model_obj: InspectModel,
    rubric_criteria: dict[str, dict[str, object]],
    idx: int,
) -> Scorer:
    """Build a custom Inspect AI scorer for per-criterion rubric scoring.

    The scorer presents all rubric criteria (name, weight, description,
    0/5/10 anchors) to the judge and asks for a JSON response:
        {"rubric_scores": {criterion: float_0_10, ...},
         "total_score": float,
         "reasoning": "..."}

    The JSON payload is stored in ``Score.explanation`` (Sub-choice B — the
    confirmed-present string field on the Score model).

    Named via ``scorer(name=f"judge_{idx}")`` (Sub-choice C) so the key in
    ``sample.scores`` is deterministic (``"judge_0"``, ``"judge_1"``, …)
    rather than relying on Inspect AI's auto-suffix pattern.

    Args:
        judge_model_obj: Inspect AI model object (with max_tokens already
            capped via GenerateConfig).
        rubric_criteria: loaded criteria dict from ``_load_rubric_criteria``.
        idx: 0-based position in the shuffled judge list — used as the scorer
            name suffix.

    Returns:
        A ``Scorer`` object ready to be placed in ``Task(scorer=[...])``.
    """
    from inspect_ai.model import GenerateConfig as _GenerateConfig
    from inspect_ai.scorer import Score, scorer

    @scorer(metrics=[], name=f"judge_{idx}")
    def _rubric_scorer_factory(
        model: InspectModel = judge_model_obj,
    ) -> Scorer:
        async def _score(state: TaskState, generate: Generate) -> Score:
            candidate_output = state.output.completion if state.output else ""

            prompt = _build_rubric_prompt(rubric_criteria, candidate_output)

            # Generate using the judge model — max_tokens capped via
            # GenerateConfig (_DEFAULT_JUDGE_MAX_TOKENS_RUBRIC) per EVID-023.
            # G6: time the call and capture token usage so score() can populate
            # per-judge latency / tokens / cost on each Judgment (the
            # cost-includes-judge-calls tenet).  Stashed in Score.metadata,
            # which score() reads back via _read_judge_usage_meta().
            t0 = time.perf_counter()
            response = await model.generate(
                input=prompt,
                config=_GenerateConfig(max_tokens=_DEFAULT_JUDGE_MAX_TOKENS_RUBRIC),
            )
            latency_ms = int((time.perf_counter() - t0) * 1000)
            completion = response.completion if response else ""
            usage = response.usage if response else None
            metadata: dict[str, object] = {
                "tokens_in": int(usage.input_tokens) if usage is not None else 0,
                "tokens_out": int(usage.output_tokens) if usage is not None else 0,
                "latency_ms": latency_ms,
            }
            return Score(value=0.0, explanation=completion, metadata=metadata)

        # Inspect AI consumes the async callable as the scorer implementation;
        # the runtime `@scorer` decorator handles registry wiring.
        return cast("Scorer", _score)

    return _rubric_scorer_factory()


def _compute_total_score(
    criterion_scores: dict[str, float],
    rubric_criteria: dict[str, dict[str, object]],
) -> float:
    """Compute the weighted total score (or equal-weight mean) from criterion scores.

    For equal-weight packs (all weights identical or all absent): plain mean.
    For weighted packs: ``sum(weight_i * score_i)`` normalised to [0, 10].

    Args:
        criterion_scores: dict mapping criterion name → float score in [0, 10].
        rubric_criteria: criteria metadata from ``_load_rubric_criteria``.

    Returns:
        float in [0.0, 10.0], clamped.
    """
    if not criterion_scores:
        return 0.0

    weights: list[float] = []
    for cname in criterion_scores:
        cdict = rubric_criteria.get(cname, {})
        w_raw = cdict.get("weight", None)
        weights.append(float(str(w_raw)) if w_raw is not None else 1.0)

    # Detect equal-weight: all weights numerically identical.
    if len(set(weights)) == 1:
        # Equal-weight: plain mean.
        total = sum(criterion_scores.values()) / len(criterion_scores)
    else:
        # Weighted sum — normalise by total weight to keep [0, 10] range.
        total_weight = sum(weights)
        if total_weight == 0.0:
            total = 0.0
        else:
            total = (
                sum(
                    w * criterion_scores[cname]
                    for w, cname in zip(weights, criterion_scores, strict=True)
                )
                / total_weight
            )

    return max(0.0, min(10.0, total))


# ---------------------------------------------------------------------------
# JudgePanel
# ---------------------------------------------------------------------------


class JudgePanel:
    """Multi-judge scoring panel for one evaluation pass.

    Parallel to EvalCaller — same Protocol-driven testability seam (EVID-015).
    Concurrency is the caller's responsibility (matches eval_caller.py:13-14).

    Self-judging guard fires in __init__ — raises SelfJudgingError immediately
    if any judge family matches the candidate family (PRD-002 SC-2, FR-002).

    Billing isolation: reads api_key_env (default OPENROUTER_API_KEY_JUDGE)
    from os.environ — separate from candidate's OPENROUTER_API_KEY (NFR-005).

    Args:
        judge_models: list of judge model IDs (≥1 required). Each must be in
            a different vendor family from the candidate, and ideally from
            different families among themselves (ADR-003 diversity constraint).
        candidate_model_id: the model being evaluated. Used solely for the
            self-judging guard — not passed to any LLM call.
        rubric_version: identifies which rubric YAML the judges will use.
        base_url: LiteLLM proxy base URL. Defaults to localhost:4000.
        api_key_env: env var name holding the judge billing key (NFR-005).
        judge_max_tokens: output token cap per judge call. Default 512 per
            EVID-023 finding — prevents HTTP 402 budget exhaustion.
    """

    def __init__(
        self,
        judge_models: list[str],
        candidate_model_id: str,
        rubric_version: str,
        *,
        base_url: str = "http://localhost:4000",
        api_key_env: str = "LITELLM_MASTER_KEY",
        judge_max_tokens: int = _DEFAULT_JUDGE_MAX_TOKENS,
    ) -> None:
        if not judge_models:
            raise ValueError("at least one judge required")

        # SC-2 guard: must fire before any other state is set.
        self._guard_self_judging(judge_models, candidate_model_id)

        self._judge_models = list(judge_models)
        self._n_judges_requested = len(judge_models)
        self._candidate_model_id = candidate_model_id
        self._rubric_version = rubric_version
        self._base_url = base_url.rstrip("/")
        self._api_key_env = api_key_env
        self._judge_max_tokens = judge_max_tokens

        # Store the GenerateConfig; model objects are created lazily in score()
        # to avoid requiring OPENAI_API_KEY at construction time (unit tests run
        # without real credentials — RFC-002 Slice A explicitly permits deferral).
        # Slice B's score() calls _make_judge_models() which calls get_model().
        # EVID-023: GenerateConfig(max_tokens=512) prevents HTTP 402 budget
        # exhaustion on OpenRouter (Claude Sonnet native max is 65k).
        self._judge_config = GenerateConfig(max_tokens=judge_max_tokens)
        # Lazily populated by _make_judge_models() on first score() call.
        self._judge_model_objects: list[InspectModel] | None = None

        logger.debug(
            "JudgePanel created: n_judges=%d candidate=%s rubric=%s max_tokens=%d",
            len(self._judge_models),
            candidate_model_id,
            rubric_version,
            judge_max_tokens,
        )

    # ------------------------------------------------------------------
    # Public interface (Slices B and C — stubs for Slice A)
    # ------------------------------------------------------------------

    async def score(self, eval_result: EvalResult, task_id: str) -> list[Judgment]:
        """Score one candidate output across the full judge panel.

        Uses Inspect AI's list-of-scorers path (Task(scorer=[s1, s2, s3])).
        Per-judge Score objects are read from EvalLog.samples[0].scores (a dict
        keyed by auto-assigned scorer names: 'model_graded_qa', 'model_graded_qa_1',
        ...).

        API source: Context7 /ukgovernmentbeis/inspect_ai — model_graded_qa,
        Task(scorer=[...]), EvalLog.samples[].scores pattern.
        Confirmed working by EVID-023 H1 spike (inspect_ai==0.3.46).

        NOTE: multi_scorer() is BROKEN in inspect_ai==0.3.46 (runtime crash
        "Object score does not have registry info"). Do NOT use multi_scorer()
        until upstream fix lands (github.com/UKGovernmentBEIS/inspect_ai/issues/4027).

        IMPORTANT: always cap judge max_tokens explicitly via
        get_model(judge, config=GenerateConfig(max_tokens=512)) — the default
        is the model's native max (65k for Claude Sonnet), which exhausts
        OpenRouter monthly budget on the first run (HTTP 402 confirmed EVID-023).

        Args:
            eval_result: the completed candidate evaluation (status=SCORED).
                         raw candidate output is read from the local artifact URI
                         stored in eval_result.eval_row.artifact_refs.raw_output.
            task_id: task identifier (e.g. "be_01_jwt_auth") — used as the
                     judge prompt context and for rubric loading in future slices.

        Returns:
            One Judgment per judge model. Position in the list matches the
            randomised judge_order (H2 position-bias mitigation per RFC-002).
        """
        from inspect_ai import Task
        from inspect_ai.dataset import Sample
        from inspect_ai.solver import solver as _solver

        # ── 1. Read raw candidate output from artifact URI ─────────────────
        raw_output_text = self._read_raw_output(eval_result)

        # ── 2. Load rubric criteria for this task (G1: per-criterion scoring)
        rubric_criteria = _load_rubric_criteria(task_id)

        # ── 3. Build forwarding solver — injects pre-computed output so
        #       judges grade existing text, not a new generation ────────────
        @_solver
        def _forwarding_solver(forced_output: str) -> Solver:
            """Return a solver that plants pre-computed text into TaskState.output.

            This avoids re-generating the candidate response — judges receive
            the same text that the candidate actually produced.
            """
            from inspect_ai.model import ModelOutput

            async def _solve(state: TaskState, generate: Generate) -> TaskState:
                state.output = ModelOutput.from_content(
                    model=str(state._model),
                    content=forced_output,
                )
                state.completed = True
                return state

            return _solve

        # ── 4. Randomise judge order (H2 position-bias mitigation) ──────────
        judge_ids_shuffled = list(self._judge_models)
        random.shuffle(judge_ids_shuffled)

        # ── 5. Build per-judge rubric scorers (G1 — replaces model_graded_qa)
        #       EVID-023 finding: list-of-scorers path works; multi_scorer broken.
        #       Each scorer uses explicit name "judge_{idx}" (Sub-choice C) so
        #       sample.scores keys are deterministic.
        judge_model_objs = self._make_judge_models()
        # Rebuild in shuffled order (judge_model_objs preserves init order,
        # so we need to re-map after shuffling).
        original_order = list(self._judge_models)
        judge_models_in_shuffled_order = [
            judge_model_objs[original_order.index(jid)] for jid in judge_ids_shuffled
        ]

        scorers = [
            _make_rubric_scorer(jm, rubric_criteria, idx)
            for idx, jm in enumerate(judge_models_in_shuffled_order)
        ]

        # ── 6. Build a minimal Task for judging ──────────────────────────────
        #       The forwarding solver injects raw_output_text into state.output.
        #       The rubric scorers then read state.output.completion.
        sample_input = (
            f"[POLLMEVALS judge task] task={task_id} "
            f"model={eval_result.request.model_id} "
            f"stack={eval_result.request.stack_id} "
            f"seed={eval_result.request.seed}"
        )

        judge_task = Task(
            dataset=[
                Sample(
                    input=sample_input,
                    target="",
                    metadata={"forced_output": raw_output_text},
                )
            ],
            solver=_forwarding_solver(forced_output=raw_output_text),
            scorer=scorers,
        )

        # ── 7. Run judges via Inspect AI eval_async ───────────────────────────
        #       We set OPENAI_BASE_URL + OPENAI_API_KEY so Inspect AI routes
        #       through the LiteLLM proxy (same pattern as spike script line 183).
        logs = await self._run_judge_task(judge_task)

        # ── 8. Parse per-judge Score from EvalLog.samples[0].scores ──────────
        #       Keys are now "judge_0", "judge_1", … (explicit names, Sub-choice C).
        #       Fallback to positional access if naming pattern shifted (EVID-023
        #       positional fallback retained for safety).
        if not logs:
            raise RuntimeError("JudgePanel.score(): Inspect AI eval_async returned no logs")
        # Import EvalLog for isinstance narrowing so mypy knows .samples exists.
        from inspect_ai.log import EvalLog as _EvalLog

        log = logs[0]
        if not isinstance(log, _EvalLog):
            raise RuntimeError(
                f"JudgePanel.score(): unexpected log type {type(log).__name__}; expected EvalLog"
            )
        if not log.samples:
            raise RuntimeError("JudgePanel.score(): EvalLog has no samples")

        sample = log.samples[0]
        # sample.scores is dict[str, Score] | None in inspect_ai type stubs.
        raw_scores = sample.scores
        scores_dict = raw_scores if isinstance(raw_scores, dict) else {}

        judgments: list[Judgment] = []
        for idx, judge_id in enumerate(judge_ids_shuffled):
            # Primary key: "judge_{idx}" (explicit name via scorer(name=...)).
            scorer_key = f"judge_{idx}"
            score_obj = scores_dict.get(scorer_key)

            if score_obj is None:
                # Fallback: positional access if naming pattern shifted.
                score_obj_list = list(scores_dict.values())
                score_obj = score_obj_list[idx] if idx < len(score_obj_list) else None

            if score_obj is None:
                logger.warning(
                    "JudgePanel.score(): no Score for judge %s (scorer_key=%s); available keys=%s",
                    judge_id,
                    scorer_key,
                    list(scores_dict.keys()),
                )
                # Skip this judge rather than crash; caller handles missing judgments.
                continue

            # G1: parse per-criterion JSON from Score.explanation (Sub-choice B)
            # via the shared parser (also used by the calibration path).
            raw_explanation = str(score_obj.explanation or "")
            rubric_scores = _parse_rubric_scores(raw_explanation, judge_id)

            total_score = _compute_total_score(rubric_scores, rubric_criteria)

            # G6: per-judge cost accounting.  The rubric scorer stashed token
            # counts + wall-clock latency in Score.metadata; read them back and
            # price the call so GridRunner's running total includes judge calls.
            tokens_in, tokens_out, latency_ms = _read_judge_usage_meta(score_obj)
            cost_usd = compute_cost(
                _JudgeTokenStats(input_tokens=tokens_in, output_tokens=tokens_out),
                _DEFAULT_JUDGE_PRICING,
            )

            judgments.append(
                Judgment(
                    judge_model_id=judge_id,
                    judge_order=idx,
                    rubric_version=self._rubric_version,
                    rubric_scores=rubric_scores,
                    total_score=total_score,
                    raw_explanation=raw_explanation,
                    latency_ms=latency_ms,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=cost_usd,
                )
            )

        return judgments

    def aggregate(self, judgments: list[Judgment]) -> JudgeAggregation:
        """Compute median + Krippendorff alpha + bootstrap CI across the panel.

        Per docs/02-methodology/scoring.md: median per criterion (NOT mean — EVID-001).
        Per PRD-002 Q2 / ADR-005: publication gate uses CI lower-bound >= 0.70
        (bootstrap 2000 resamples, 95% CI, deterministic seed=42 per ADR-005
        invariant "bootstrap_seed recorded in manifest for reproducibility").

        Matrix layout: N judge rows x M criteria columns.
        krippendorff.alpha() expects rows=coders (judges), cols=items (criteria).
        Krippendorff alpha level_of_measurement="ordinal" per ADR-005 invariant
        ("Rubric scores are ordered but score-distance is not metric").

        Degraded panel (PRD-002 Q3): if len(judgments) < _n_judges_requested
        return judge_status="DEGRADED" with all alpha fields = None.

        Args:
            judgments: list of Judgment objects from score() — one per judge.
                       At least 1 required (JudgeAggregation.n_judges_used >= 1).

        Returns:
            JudgeAggregation with median_per_criterion, alpha fields, and
            judge_status. Bootstrap CI uses 2000 resamples (ADR-005 / SC-1).

        Library: krippendorff>=0.7,<1 (Thomas Grill PyPI package).
        Import: krippendorff.alpha(reliability_data, level_of_measurement)
        Confirmed: Library-first lookup via Context7 (aleph-alpha variant found
        at /aleph-alpha/krippendorff-aleph-alpha uses different API; standard
        `krippendorff` PyPI package confirmed by RFC-002 pin + ADR-005 references).
        """
        import krippendorff  # type: ignore[import-untyped]
        import numpy as np

        # ── Collect all criteria present across all judgments (sorted for determinism)
        criteria = sorted({c for j in judgments for c in j.rubric_scores})

        # ── Compute median per criterion (always computed, even in DEGRADED path)
        median_per_criterion: dict[str, float] = {}
        for crit in criteria:
            scores_for_crit = [j.rubric_scores[crit] for j in judgments if crit in j.rubric_scores]
            if scores_for_crit:
                median_per_criterion[crit] = float(np.median(scores_for_crit))

        # ── Degraded panel check (PRD-002 Q3): N-1 → alpha=None ────────────────
        if len(judgments) < self._n_judges_requested:
            return JudgeAggregation(
                median_per_criterion=median_per_criterion,
                alpha_point=None,
                alpha_ci_lower=None,
                alpha_ci_upper=None,
                judge_status="DEGRADED",
                n_judges_used=len(judgments),
            )

        # ── Build N x M reliability matrix: N judge rows, M criteria columns ──
        # krippendorff.alpha() expects rows=coders (judges), cols=items (criteria).
        # NaN fills missing criterion scores (krippendorff treats NaN as "missing
        # data" — annotator did not rate this item, which is the correct semantics).
        n_judges = len(judgments)
        matrix = np.array(
            [[j.rubric_scores.get(crit, np.nan) for crit in criteria] for j in judgments],
            dtype=float,
        )

        # G1: Criterion-collapse detection.
        # Judges that return near-identical scores across all criteria produce a
        # degenerate row where std < 0.5 on the 0-10 scale; Krippendorff alpha is
        # unreachable regardless of inter-judge agreement on the single flat value.
        # Warning only (not error) -- the aggregation continues with the matrix.
        for judgment in judgments:
            row_scores = [
                judgment.rubric_scores[crit] for crit in criteria if crit in judgment.rubric_scores
            ]
            if len(row_scores) > 1:
                row_std = float(np.std(row_scores))
                if row_std < 0.5:
                    logger.warning(
                        "aggregate(): criterion collapse detected -- judge %s "
                        "has near-identical criterion scores (std=%.3f < 0.5); "
                        "Krippendorff alpha will remain degenerate for this panel.",
                        judgment.judge_model_id,
                        row_std,
                    )

        # ── Point estimate (ordinal level per ADR-005) ─────────────────────────
        alpha_point = float(
            krippendorff.alpha(
                reliability_data=matrix,
                level_of_measurement="ordinal",
            )
        )

        # ── Bootstrap 95% CI — 2000 resamples, deterministic seed=42 (ADR-005) ─
        # Resample judges (rows) with replacement — each resample is a virtual panel
        # of n_judges drawn with replacement from the actual panel.
        rng = np.random.default_rng(seed=42)
        boot_alphas: list[float] = []
        for _ in range(2000):
            # Resample judge rows with replacement.
            idx = rng.integers(0, n_judges, size=n_judges)
            boot_matrix = matrix[idx, :]
            try:
                a = float(
                    krippendorff.alpha(
                        reliability_data=boot_matrix,
                        level_of_measurement="ordinal",
                    )
                )
                # Reject NaN (degenerate sample where all judges gave identical
                # scores — alpha is undefined; krippendorff returns nan in that case).
                if not np.isnan(a):
                    boot_alphas.append(a)
            except Exception:
                # Degenerate sample — krippendorff may raise on edge cases.
                # Skip rather than crash; CI computed from valid samples only.
                pass

        if boot_alphas:
            alpha_ci_lower, alpha_ci_upper = (
                float(v) for v in np.percentile(boot_alphas, [2.5, 97.5])
            )
        else:
            # Fallback: all resamples degenerate → CI collapses to the point estimate.
            alpha_ci_lower = alpha_point
            alpha_ci_upper = alpha_point

        return JudgeAggregation(
            median_per_criterion=median_per_criterion,
            alpha_point=alpha_point,
            alpha_ci_lower=alpha_ci_lower,
            alpha_ci_upper=alpha_ci_upper,
            judge_status="OK",
            n_judges_used=len(judgments),
        )

    # ------------------------------------------------------------------
    # Slice D — Calibration suite (FR-004, SC-3)
    # ------------------------------------------------------------------

    async def run_calibration(self, task_id: str) -> CalibrationResult:
        """Run each judge over all calibration samples for one task.

        Loads ``evals/task-packs/<task_id>/calibration.yaml`` for gold scores,
        then for each of the five quality levels (perfect / good / mediocre /
        poor / broken) loads all ``*.md`` samples from the corresponding subdir.
        Each judge scores every sample via ``_score_calibration_sample()``.

        MAD formula: ``mean(|judge_score - gold_score|)`` per judge.
        Rank correlation: Spearman r computed with numpy ranking (no scipy dep).
        Passed: ``True`` iff all judges have ``MAD ≤ mad_threshold`` where
        ``mad_threshold`` comes from ``calibration.yaml`` (default 1.5 per
        PRD-002 SC-3).

        The ``calibration_hash`` is SHA-256 of the YAML content concatenated with
        all sample file bodies sorted lexicographically by path — stable across
        reruns on unchanged content; changes when samples or gold scores change
        (RFC-002 R4 drift detection anchor).

        Args:
            task_id: eval task slug (e.g. ``"be_01_jwt_auth"``).

        Returns:
            CalibrationResult with per-judge metrics and overall pass/fail.

        Raises:
            FileNotFoundError: if ``calibration.yaml`` or any required subdir is
                missing (author has not seeded the task-pack yet).
        """
        QUALITY_LEVELS = ("perfect", "good", "mediocre", "poor", "broken")

        # ── 1. Locate calibration root relative to CWD (repo root) ──────────
        repo_root = pathlib.Path.cwd()
        calib_root = repo_root / "evals" / "task-packs" / task_id
        yaml_path = calib_root / "calibration.yaml"

        if not yaml_path.exists():
            raise FileNotFoundError(f"calibration.yaml not found for task {task_id!r}: {yaml_path}")

        yaml_text = yaml_path.read_text(encoding="utf-8")
        calib_meta: dict[str, object] = yaml.safe_load(yaml_text)
        gold_scores: dict[str, float] = {
            k: float(str(v)) for k, v in cast_dict(calib_meta.get("gold_scores", {})).items()
        }
        mad_raw = calib_meta.get("mad_threshold", 1.5)
        mad_threshold: float = float(str(mad_raw))

        # ── 2. Load all samples from the five quality subdirs ────────────────
        # List of (quality_level, file_path, text_content) tuples.
        samples: list[tuple[str, pathlib.Path, str]] = []
        for level in QUALITY_LEVELS:
            level_dir = calib_root / "calibration" / level
            if not level_dir.is_dir():
                continue
            # G3: calibration samples are language-specific (be_01 .ts, fe_01
            # .tsx, doc_01 .md) -- glob all sample extensions, not just .md, or
            # be_01/fe_01 samples are silently skipped and only doc_01 calibrates.
            sample_files = sorted(
                f for ext in _CALIBRATION_SAMPLE_EXTS for f in level_dir.glob(f"*{ext}")
            )
            for sample_file in sample_files:
                samples.append((level, sample_file, sample_file.read_text(encoding="utf-8")))

        # ── 3. Compute calibration_hash (SHA-256 of YAML + all sample bodies) ─
        hasher = hashlib.sha256()
        hasher.update(yaml_text.encode("utf-8"))
        for _, _, body in sorted(samples, key=lambda t: str(t[1])):
            hasher.update(body.encode("utf-8"))
        calibration_hash = hasher.hexdigest()

        # ── 4. Per-judge scoring over all samples ────────────────────────────
        judge_records: dict[str, list[tuple[float, float]]] = {
            jid: [] for jid in self._judge_models
        }

        for judge_id in self._judge_models:
            for level, _path, content in samples:
                gold = gold_scores.get(level, 0.0)
                judge_score = await self._score_calibration_sample(
                    judge_id=judge_id,
                    sample_content=content,
                    task_id=task_id,
                )
                judge_records[judge_id].append((gold, judge_score))

        # ── 5. Compute per-judge MAD + Spearman rank correlation ─────────────
        judge_calibrations: dict[str, JudgeCalibration] = {}
        for judge_id, pairs in judge_records.items():
            if not pairs:
                judge_calibrations[judge_id] = JudgeCalibration(
                    judge_id=judge_id,
                    mad=0.0,
                    rank_correlation=0.0,
                    samples_evaluated=0,
                )
                continue

            gold_arr = np.array([p[0] for p in pairs], dtype=float)
            judge_arr = np.array([p[1] for p in pairs], dtype=float)

            mad = float(np.mean(np.abs(judge_arr - gold_arr)))
            rank_corr = _spearman_r(gold_arr, judge_arr)

            judge_calibrations[judge_id] = JudgeCalibration(
                judge_id=judge_id,
                mad=mad,
                rank_correlation=rank_corr,
                samples_evaluated=len(pairs),
            )

        # ── 6. Overall pass/fail (all judges must be within threshold) ────────
        passed = all(jc.mad <= mad_threshold for jc in judge_calibrations.values())

        return CalibrationResult(
            task_id=task_id,
            judge_calibrations=judge_calibrations,
            passed=passed,
            gold_scores=gold_scores,
            calibration_hash=calibration_hash,
            mad_threshold=mad_threshold,
        )

    async def run_identification_probe(self, task_id: str) -> ProbeResult:
        """SC-4 anonymisation effectiveness probe for one task.

        Loads anonymised samples from
        ``evals/task-packs/<task_id>/identification_probe/`` (markdown files).
        Each judge is prompted to guess which model family produced the output
        from a fixed list of 5 families (forced single-word choice).

        SC-4 (PRD-002): overall accuracy ≤ 0.30. Chance level = 1/5 = 0.20.

        The prompt given to each judge:
            "Below is a model output. Which of these model families most likely
            produced it? Respond with exactly one word from: anthropic, openai,
            google, qwen, meta.\\n\\nOutput:\\n<sample_content>"

        The correct label for each sample is read from the filename:
        ``<family>-<number>.md`` (e.g. ``anthropic-001.md`` → correct = "anthropic").
        Files without a matching family prefix count as unknown and are skipped.

        Args:
            task_id: eval task slug.

        Returns:
            ProbeResult with per-judge accuracy and overall pass/fail.

        Raises:
            FileNotFoundError: if the identification_probe directory is missing.
        """
        PROBE_FAMILIES = frozenset({"anthropic", "openai", "google", "qwen", "meta"})

        repo_root = pathlib.Path.cwd()
        probe_dir = repo_root / "evals" / "task-packs" / task_id / "identification_probe"

        if not probe_dir.exists():
            raise FileNotFoundError(
                f"identification_probe/ not found for task {task_id!r}: {probe_dir}"
            )

        # ── 1. Load labelled samples ─────────────────────────────────────────
        # Filename convention: <family>-<number>.md  (e.g. anthropic-001.md)
        labelled_samples: list[tuple[str, str]] = []  # (correct_family, content)
        for md_file in sorted(probe_dir.glob("*.md")):
            stem = md_file.stem  # e.g. "anthropic-001"
            family = stem.split("-")[0].lower()
            if family in PROBE_FAMILIES:
                labelled_samples.append((family, md_file.read_text(encoding="utf-8")))
            else:
                logger.debug(
                    "run_identification_probe: skipping %s — family %r not in probe list",
                    md_file.name,
                    family,
                )

        if not labelled_samples:
            logger.warning(
                "run_identification_probe: no labelled samples found in %s — "
                "returning empty result with accuracy=0.0 (passed=True)",
                probe_dir,
            )
            return ProbeResult(
                task_id=task_id,
                judges_used=list(self._judge_models),
                n_samples=0,
                per_judge_accuracy={jid: 0.0 for jid in self._judge_models},
                overall_accuracy=0.0,
                passed=True,
            )

        # ── 2. Per-judge accuracy computation ────────────────────────────────
        per_judge_correct: dict[str, int] = {jid: 0 for jid in self._judge_models}
        per_judge_total: dict[str, int] = {jid: 0 for jid in self._judge_models}

        for judge_id in self._judge_models:
            for correct_family, content in labelled_samples:
                guess = await self._score_identification_sample(
                    judge_id=judge_id,
                    sample_content=content,
                    probe_families=PROBE_FAMILIES,
                    task_id=task_id,
                )
                per_judge_total[judge_id] += 1
                if guess == correct_family:
                    per_judge_correct[judge_id] += 1

        # ── 3. Aggregate accuracy ────────────────────────────────────────────
        per_judge_accuracy: dict[str, float] = {}
        for jid in self._judge_models:
            total = per_judge_total[jid]
            per_judge_accuracy[jid] = per_judge_correct[jid] / total if total > 0 else 0.0

        total_pairs = sum(per_judge_total.values())
        total_correct = sum(per_judge_correct.values())
        overall_accuracy = total_correct / total_pairs if total_pairs > 0 else 0.0

        return ProbeResult(
            task_id=task_id,
            judges_used=list(self._judge_models),
            n_samples=total_pairs,
            per_judge_accuracy=per_judge_accuracy,
            overall_accuracy=round(overall_accuracy, 6),
            passed=overall_accuracy <= 0.30,
        )

    # ------------------------------------------------------------------
    # Self-judging guard (static — no network, no external deps)
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_model_family(model_id: str) -> str:
        """Public static wrapper — delegates to module-level function.

        Exposed as a static method so callers can test normalisation without
        constructing a full JudgePanel instance.
        """
        return _normalise_model_family(model_id)

    @classmethod
    def _guard_self_judging(cls, judge_models: list[str], candidate_model_id: str) -> None:
        """Raise SelfJudgingError if any judge family matches the candidate family.

        PRD-002 FR-002 + SC-2: zero self-judging incidents. Family-level match
        (NOT raw string) — prevents OpenRouter cross-route variants from slipping
        through (e.g. 'openrouter/anthropic/claude-haiku' and 'anthropic/claude-sonnet'
        both normalise to family 'anthropic').

        Semantics: NOT silent skip — raise immediately. The orchestrator catches
        SelfJudgingError and records a FAILED EvalRow with
        error_class=CONTRACT_VIOLATION.
        """
        cand_family = cls._normalise_model_family(candidate_model_id)
        for jm in judge_models:
            judge_family = cls._normalise_model_family(jm)
            if judge_family == cand_family:
                raise SelfJudgingError(
                    f"Self-judging refused: candidate family={cand_family!r} "
                    f"appears in judge_models={judge_models!r} (offender={jm!r}). "
                    f"See PRD-002 SC-2 and judge-policy.md:1."
                )

    # ------------------------------------------------------------------
    # Accessors (read-only views of init-time state)
    # ------------------------------------------------------------------

    @property
    def judge_models(self) -> list[str]:
        """Return the list of judge model IDs (copy — immutable view)."""
        return list(self._judge_models)

    @property
    def rubric_version(self) -> str:
        return self._rubric_version

    @property
    def api_key(self) -> str:
        """Resolve the judge API key from the environment at access time.

        Returns empty string if the env var is not set (allows unit tests to
        construct JudgePanel without real credentials).
        """
        return os.environ.get(self._api_key_env, "")

    # ------------------------------------------------------------------
    # Slice D — internal calibration + probe scoring helpers
    # ------------------------------------------------------------------

    async def _generate_one_judge(
        self,
        judge_id: str,
        prompt: str,
        max_tokens: int,
    ) -> str:
        """Generate one completion from a single judge model; return its text.

        Wires the LiteLLM proxy env (``OPENAI_BASE_URL`` / ``OPENAI_API_KEY``)
        the same way ``_run_judge_task`` does, because ``model.generate()`` here
        runs OUTSIDE an Inspect AI ``eval_async`` context.  Used by the
        calibration and identification helpers (Slice D), which score one
        ``(judge, sample)`` pair at a time rather than a full panel.

        Args:
            judge_id: judge model ID (must be in ``self._judge_models``).
            prompt: fully-built prompt string.
            max_tokens: generation cap (EVID-023: always cap to avoid HTTP 402).

        Returns:
            The judge's completion text ("" if the model returned nothing).
        """
        models = self._make_judge_models()
        try:
            idx = self._judge_models.index(judge_id)
        except ValueError as exc:
            raise ValueError(f"judge_id {judge_id!r} not in panel {self._judge_models}") from exc
        model = models[idx]

        old_base_url = os.environ.get("OPENAI_BASE_URL")
        old_api_key = os.environ.get("OPENAI_API_KEY")
        try:
            os.environ["OPENAI_BASE_URL"] = self._base_url
            os.environ["OPENAI_API_KEY"] = self.api_key or "none"
            response = await model.generate(
                input=prompt,
                config=GenerateConfig(max_tokens=max_tokens),
            )
            return response.completion if response else ""
        finally:
            if old_base_url is None:
                os.environ.pop("OPENAI_BASE_URL", None)
            else:
                os.environ["OPENAI_BASE_URL"] = old_base_url
            if old_api_key is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = old_api_key

    async def _score_calibration_sample(
        self,
        judge_id: str,
        sample_content: str,
        task_id: str,
    ) -> float:
        """Score one calibration sample with one judge, returning a 0-10 score.

        Reuses the SAME rubric prompt + parser as the production ``score()``
        path (``_build_rubric_prompt`` -> ``_generate_one_judge`` ->
        ``_parse_rubric_scores`` -> ``_compute_total_score``) so calibration
        measures the judge exactly as production scoring does — no second,
        drifting code path.

        In unit tests this method is replaced wholesale via ``patch.object`` so
        no real LLM calls are made; the real body runs only against the live
        LiteLLM proxy (validated by the RFC-002 live calibration run).

        Args:
            judge_id: judge model ID (must be in ``self._judge_models``).
            sample_content: text of the calibration sample.
            task_id: task identifier (selects the rubric for the prompt).

        Returns:
            float in [0.0, 10.0] — the judge's weighted rubric total.
        """
        rubric_criteria = _load_rubric_criteria(task_id)
        prompt = _build_rubric_prompt(rubric_criteria, sample_content)
        completion = await self._generate_one_judge(
            judge_id, prompt, _DEFAULT_JUDGE_MAX_TOKENS_RUBRIC
        )
        rubric_scores = _parse_rubric_scores(completion, judge_id)
        return _compute_total_score(rubric_scores, rubric_criteria)

    async def _score_identification_sample(
        self,
        judge_id: str,
        sample_content: str,
        probe_families: frozenset[str],
        task_id: str,
    ) -> str:
        """Prompt one judge to identify which model family produced a sample.

        Returns the judge's single-word guess normalised to lowercase, or
        ``"unknown"`` if the answer is not one of ``probe_families`` (judge
        hedged, refused, or named a family outside the SC-4 list).

        In unit tests this method is replaced wholesale via ``patch.object`` —
        no real LLM calls.  The real body runs only against the live proxy.

        Args:
            judge_id: judge model ID.
            sample_content: anonymised model output text.
            probe_families: set of valid one-word family guesses (SC-4 list).
            task_id: task identifier (kept for the mock seam; not in the prompt).

        Returns:
            str: one of ``probe_families`` or ``"unknown"``.
        """
        _ = task_id  # part of the patch.object seam; intentionally unused here
        families_csv = ", ".join(sorted(probe_families))
        prompt = (
            "Below is a single model output. Which of these model families "
            "most likely produced it? Respond with EXACTLY one word from this "
            f"list: {families_csv}.\n\nOutput:\n{sample_content}"
        )
        completion = await self._generate_one_judge(
            judge_id, prompt, _DEFAULT_JUDGE_MAX_TOKENS_PROBE
        )
        return _extract_family_guess(completion, probe_families)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_judge_models(self) -> list[InspectModel]:
        """Lazily instantiate Inspect AI judge model objects.

        Called by score() (Slice B). Deferred from __init__ so that unit
        tests can construct JudgePanel without OPENAI_API_KEY in the
        environment (the guard logic is credential-free).

        EVID-023: uses "openai/" prefix to route through OPENAI_BASE_URL
        (LiteLLM proxy). GenerateConfig(max_tokens=512) prevents HTTP 402.
        """
        from inspect_ai.model import get_model

        if self._judge_model_objects is None:
            # Pass base_url + api_key explicitly so the OpenAI client is built
            # without relying on OPENAI_* env vars being set at this point
            # (RFC-002 live run: get_model runs before _run_judge_task wires env).
            api_key = self.api_key or None
            self._judge_model_objects = [
                get_model(
                    self._proxy_alias_for(jm),
                    config=self._judge_config,
                    base_url=self._base_url,
                    api_key=api_key,
                )
                for jm in self._judge_models
            ]
        return self._judge_model_objects

    def _proxy_alias_for(self, judge_id: str) -> str:
        """Build the Inspect AI model string that routes through LiteLLM proxy.

        Per EVID-023 spike script (line 213): "openai/" prefix tells Inspect AI
        to use OPENAI_BASE_URL (which we point at the LiteLLM proxy at
        self._base_url).  The judge_id is passed through as-is; if it already
        contains a "/" the LiteLLM proxy resolves it via its model_list config.

        Examples:
          "claude-sonnet-4-6-judge"         → "openai/claude-sonnet-4-6-judge"
          "openrouter/anthropic/claude-..."  → "openai/openrouter/anthropic/claude-..."
              (technically valid; LiteLLM strips the openai/ routing prefix)

        For production use, judge model IDs should match the model_name entries
        in infra/litellm-config.yaml (e.g. "claude-sonnet-4-6-judge").
        """
        if judge_id.startswith("openai/"):
            return judge_id  # already prefixed
        return f"openai/{judge_id}"

    def _read_raw_output(self, eval_result: EvalResult) -> str:
        """Read the candidate's raw output text from the local artifact file.

        The artifact URI has the form "file://artifacts/evals/{row_id}/{label}-{sha256}.txt".
        We strip the "file://" prefix and resolve relative to CWD.

        If the file cannot be read (e.g. in unit tests with stub URIs), falls back
        to a placeholder string so that test mocks can verify the rest of the flow
        without requiring real disk I/O.
        """
        if eval_result.eval_row is None:
            return "[no eval_row — candidate output unavailable]"

        uri = eval_result.eval_row.artifact_refs.raw_output.uri
        if not uri.startswith("file://"):
            # Non-local URI (e.g. r2://...) — cannot read locally.
            return f"[non-local artifact uri={uri}]"

        file_path = pathlib.Path(uri[len("file://") :])
        try:
            return file_path.read_text(encoding="utf-8")
        except OSError:
            logger.debug(
                "_read_raw_output: cannot read artifact at %s — "
                "returning placeholder (unit test or missing artifact)",
                file_path,
            )
            return f"[artifact not readable: {uri}]"

    async def _run_judge_task(self, judge_task: InspectTask) -> list[EvalLog]:
        """Run a judge Task via Inspect AI eval_async, with proxy env wiring.

        Sets OPENAI_BASE_URL and OPENAI_API_KEY in the process environment so
        Inspect AI routes all "openai/" prefixed model calls through our
        LiteLLM proxy (same pattern as spike script, lines 183-184).

        Returns the list[EvalLog] from eval_async.
        """
        from inspect_ai import eval_async as _inspect_eval_async
        from inspect_ai.log import EvalLog as _EvalLog

        old_base_url = os.environ.get("OPENAI_BASE_URL")
        old_api_key = os.environ.get("OPENAI_API_KEY")
        try:
            os.environ["OPENAI_BASE_URL"] = self._base_url
            api_key = self.api_key or "none"
            os.environ["OPENAI_API_KEY"] = api_key

            # eval_async is a native coroutine in inspect_ai — await directly.
            # Pass a (pre-resolved) judge model as the top-level model: eval_async
            # requires one to initialise even though the forwarding solver
            # overwrites state.output and never calls it (RFC-002 live run). The
            # real judge calls come from the per-judge scorers.
            judge_models = self._make_judge_models()
            result = await _inspect_eval_async(
                judge_task,
                model=judge_models[0],
                log_dir="/tmp/pollmevals_judge_logs",
                log_level="warning",
            )
            if not result:
                return []
            return [r for r in result if isinstance(r, _EvalLog)]
        finally:
            # Restore original env state.
            if old_base_url is None:
                os.environ.pop("OPENAI_BASE_URL", None)
            else:
                os.environ["OPENAI_BASE_URL"] = old_base_url
            if old_api_key is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = old_api_key
