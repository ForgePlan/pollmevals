"""Tests for RFC-002 Slices A + B + C + D: JudgePanel scoring, calibration, probe.

Coverage:
  - _normalise_model_family: all routing patterns from EVID-023 + RFC-002
  - _guard_self_judging: exact-ID, cross-route variant, different families
  - JudgePanel.__init__: validates guard wiring, empty judge list, successful construction
  - JudgePanel.score(): Slice B — Inspect AI list-of-scorers wiring (mocked)
  - JudgePanel.aggregate(): Slice C — Krippendorff alpha + bootstrap CI
  - JudgePanel.run_calibration(): Slice D — calibration MAD + Spearman rank corr
  - JudgePanel.run_identification_probe(): Slice D — SC-4 anonymisation probe
  - Judgment / JudgeAggregation / CalibrationResult / ProbeResult: pydantic validation
  - _spearman_r: rank correlation helper (pure numpy, no scipy)
"""

from __future__ import annotations

import json
import pathlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from pydantic import ValidationError

from src.contracts import CalibrationResult, JudgeAggregation, Judgment, ProbeResult
from src.orchestrator.judge_panel import (
    JudgePanel,
    SelfJudgingError,
    _normalise_model_family,
    _spearman_r,
)

# ---------------------------------------------------------------------------
# Helpers — build a minimal fake EvalResult for score() tests
# ---------------------------------------------------------------------------


def _make_fake_eval_result(
    raw_output_uri: str = "file:///tmp/fake-raw-output.txt",
    model_id: str = "openrouter/meta-llama/llama-3.3-70b-instruct",
    stack_id: str = "raw-llm",
    task_id: str = "be_01_jwt_auth",
    seed: int = 42,
) -> object:
    """Build a minimal fake EvalResult with the fields score() reads."""
    from src.contracts import ArtifactRef, EvalArtifactRefs, EvalRow, EvalStats, EvalStatus
    from src.orchestrator.eval_caller import EvalRequest, EvalResult

    eval_id = "deadbeef01234567"

    def _ref(label: str) -> ArtifactRef:
        import hashlib

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
        model_id=model_id,
        stack_id=stack_id,
        task_id=task_id,
        seed=seed,
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
        model_id=model_id,
        stack_id=stack_id,
        task_id=task_id,
        seed=seed,
    )

    return EvalResult(
        request=request,
        eval_row=row,
        exception=None,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


def _make_doc01_rubric_json(score_per_criterion: float = 8.0) -> str:
    """Return a valid doc_01_cli_readme rubric JSON string.

    Produces a 5-criterion JSON matching the doc_01 rubric criteria.
    ``score_per_criterion`` defaults to 8.0 to ensure parse-back produces
    non-trivial scores (not 0.0 or 10.0 — easier to detect mis-parsing).
    """
    rubric_scores = {
        "structural_completeness": score_per_criterion,
        "factual_accuracy": score_per_criterion,
        "clarity": score_per_criterion,
        "actionability": score_per_criterion,
        "consistency": score_per_criterion,
    }
    return json.dumps(
        {
            "rubric_scores": rubric_scores,
            "total_score": score_per_criterion,
            "reasoning": "test explanation",
        }
    )


def _make_fake_score(
    value: str, explanation: str | None = None
) -> MagicMock:
    """Build a mock Inspect AI Score object.

    Default ``explanation`` is a valid 5-criterion doc_01 rubric JSON string
    so that score() parse-back works without further wiring.
    """
    score = MagicMock()
    score.value = value
    score.explanation = explanation if explanation is not None else _make_doc01_rubric_json()
    return score


def _make_fake_eval_log(scores_dict: dict[str, object]) -> MagicMock:
    """Build a mock EvalLog with the given per-scorer scores dict.

    Uses spec= so isinstance(log, EvalLog) passes in score() type narrowing.
    """
    from inspect_ai.log import EvalLog

    sample = MagicMock()
    sample.scores = scores_dict

    log = MagicMock(spec=EvalLog)
    log.samples = [sample]
    return log


# ---------------------------------------------------------------------------
# _normalise_model_family
# ---------------------------------------------------------------------------


class TestNormaliseModelFamily:
    """Covers the five routing patterns documented in RFC-002 Slice A."""

    # OpenRouter prefix + Anthropic
    def test_openrouter_anthropic(self) -> None:
        assert _normalise_model_family("openrouter/anthropic/claude-sonnet-4-6") == "anthropic"

    # OpenRouter prefix + OpenAI
    def test_openrouter_openai(self) -> None:
        assert _normalise_model_family("openrouter/openai/gpt-5-mini") == "openai"

    # OpenRouter prefix + Google
    def test_openrouter_google(self) -> None:
        assert _normalise_model_family("openrouter/google/gemini-3-flash-preview") == "google"

    # OpenRouter prefix + Meta-Llama
    def test_openrouter_meta_llama(self) -> None:
        result = _normalise_model_family("openrouter/meta-llama/llama-3.3-70b-instruct")
        assert result == "meta-llama"

    # openai/ routing prefix (used by Inspect AI to route through OPENAI_BASE_URL)
    # followed by Qwen vendor — see spike script line 213
    def test_openai_prefix_qwen(self) -> None:
        assert _normalise_model_family("openai/Qwen/Qwen3-14B") == "qwen"

    # LiteLLM proxy alias — family embedded as leading token in model name
    def test_proxy_alias_claude(self) -> None:
        assert _normalise_model_family("claude-sonnet-4-6-judge") == "anthropic"

    # Direct vendor path without openrouter prefix
    def test_direct_anthropic(self) -> None:
        assert _normalise_model_family("anthropic/claude-haiku") == "anthropic"

    # Direct vendor path — OpenAI without prefix
    def test_direct_openai(self) -> None:
        assert _normalise_model_family("openai/gpt-5-mini") == "openai"

    # Proxy alias — gemini prefix maps to google
    def test_proxy_alias_gemini(self) -> None:
        assert _normalise_model_family("gemini-3-flash") == "google"

    # Proxy alias — gpt prefix maps to openai
    def test_proxy_alias_gpt(self) -> None:
        assert _normalise_model_family("gpt-5-mini-judge") == "openai"

    # Unknown family: treated as its own unique family (no false self-judging refusal)
    def test_unknown_family_passthrough(self) -> None:
        family = _normalise_model_family("runpod/llama-4-70b")
        assert family == "runpod"

    # Static method on JudgePanel delegates to the module function
    def test_static_method_delegates(self) -> None:
        result = JudgePanel._normalise_model_family("openrouter/anthropic/claude-sonnet-4-6")
        assert result == "anthropic"


# ---------------------------------------------------------------------------
# Self-judging guard via _guard_self_judging
# ---------------------------------------------------------------------------


class TestSelfJudgingGuard:
    """Covers RFC-002 Slice A acceptance criteria AC-1 through AC-4."""

    # AC-1: exact same family via openrouter prefix
    def test_raises_exact_openrouter_family(self) -> None:
        with pytest.raises(SelfJudgingError) as exc_info:
            JudgePanel._guard_self_judging(
                judge_models=["openrouter/anthropic/claude-sonnet-4-6"],
                candidate_model_id="openrouter/anthropic/claude-haiku",
            )
        msg = str(exc_info.value)
        assert "anthropic" in msg
        assert "offender" in msg

    # AC-2: cross-route variant — judge uses openrouter/ prefix, candidate uses direct path
    def test_raises_cross_route_variant(self) -> None:
        with pytest.raises(SelfJudgingError):
            JudgePanel._guard_self_judging(
                judge_models=["openrouter/anthropic/claude-sonnet-4-6"],
                candidate_model_id="anthropic/claude-haiku",
            )

    # AC-3: different families — should NOT raise
    def test_accepts_different_families(self) -> None:
        # anthropic judge + google candidate — no error
        JudgePanel._guard_self_judging(
            judge_models=[
                "openrouter/anthropic/claude-sonnet-4-6",
                "openrouter/openai/gpt-5-mini",
                "openrouter/google/gemini-3-flash",
            ],
            candidate_model_id="openrouter/meta-llama/llama-3.3-70b-instruct",
        )
        # No exception raised — guard passes

    # Open-weight candidate with closed-family judges (from RFC-002 Slice A AC-3)
    def test_accepts_openweight_candidate(self) -> None:
        JudgePanel._guard_self_judging(
            judge_models=[
                "openrouter/anthropic/claude-sonnet-4-6",
                "openrouter/openai/gpt-5-mini",
                "openrouter/google/gemini-3-flash",
            ],
            candidate_model_id="openrouter/cerebras/qwen-3-14b",
        )
        # No exception raised

    # Offender is named in the error message
    def test_error_message_names_offender(self) -> None:
        offender = "openrouter/openai/gpt-5-mini"
        with pytest.raises(SelfJudgingError) as exc_info:
            JudgePanel._guard_self_judging(
                judge_models=["openrouter/anthropic/claude", offender],
                candidate_model_id="openrouter/openai/gpt-4o",
            )
        assert offender in str(exc_info.value)

    # Guard catches the FIRST offending judge, not just any
    def test_raises_on_first_offending_judge(self) -> None:
        with pytest.raises(SelfJudgingError) as exc_info:
            JudgePanel._guard_self_judging(
                judge_models=[
                    "openrouter/google/gemini-3-flash",  # ok
                    "openrouter/anthropic/claude-sonnet",  # offender
                ],
                candidate_model_id="anthropic/claude-haiku",
            )
        msg = str(exc_info.value)
        assert "claude-sonnet" in msg or "anthropic" in msg


# ---------------------------------------------------------------------------
# JudgePanel.__init__
# ---------------------------------------------------------------------------


class TestJudgePanelInit:
    """Covers constructor validation and property accessors."""

    # AC-4: empty judge_models → ValueError
    def test_empty_judge_models_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one judge required"):
            JudgePanel(
                judge_models=[],
                candidate_model_id="openrouter/anthropic/claude-haiku",
                rubric_version="1.0",
            )

    # Self-judging guard fires in __init__
    def test_self_judging_fires_in_init(self) -> None:
        with pytest.raises(SelfJudgingError):
            JudgePanel(
                judge_models=["openrouter/anthropic/claude-sonnet-4-6"],
                candidate_model_id="openrouter/anthropic/claude-haiku",
                rubric_version="1.0",
            )

    # Successful construction with different families
    def test_constructs_cleanly_different_families(self) -> None:
        panel = JudgePanel(
            judge_models=[
                "openrouter/anthropic/claude-sonnet-4-6",
                "openrouter/openai/gpt-5-mini",
                "openrouter/google/gemini-3-flash",
            ],
            candidate_model_id="openrouter/meta-llama/llama-3.3-70b-instruct",
            rubric_version="1.0",
        )
        assert len(panel.judge_models) == 3
        assert panel.rubric_version == "1.0"

    # judge_models property returns a copy (immutable view)
    def test_judge_models_property_is_copy(self) -> None:
        judge_list = ["openrouter/openai/gpt-5-mini"]
        panel = JudgePanel(
            judge_models=judge_list,
            candidate_model_id="openrouter/anthropic/claude-haiku",
            rubric_version="1.0",
        )
        panel.judge_models.append("extra")
        assert len(panel.judge_models) == 1  # original unchanged

    # Default api_key_env resolves to empty string when env var not set
    def test_api_key_empty_when_env_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENROUTER_API_KEY_JUDGE", raising=False)
        panel = JudgePanel(
            judge_models=["openrouter/openai/gpt-5-mini"],
            candidate_model_id="openrouter/anthropic/claude-haiku",
            rubric_version="1.0",
        )
        assert panel.api_key == ""

    # Custom api_key_env is picked up
    def test_custom_api_key_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_JUDGE_KEY", "sk-test-abc")
        panel = JudgePanel(
            judge_models=["openrouter/openai/gpt-5-mini"],
            candidate_model_id="openrouter/anthropic/claude-haiku",
            rubric_version="1.0",
            api_key_env="MY_JUDGE_KEY",
        )
        assert panel.api_key == "sk-test-abc"

    # judge_max_tokens default matches EVID-023 finding (512)
    def test_default_judge_max_tokens(self) -> None:
        panel = JudgePanel(
            judge_models=["openrouter/openai/gpt-5-mini"],
            candidate_model_id="openrouter/anthropic/claude-haiku",
            rubric_version="1.0",
        )
        assert panel._judge_max_tokens == 512


# ---------------------------------------------------------------------------
# Slice C — aggregate() implementation tests (RFC-002 Slice C / ADR-005)
# ---------------------------------------------------------------------------


def _make_judgment(
    judge_id: str,
    rubric_scores: dict[str, float],
    judge_order: int = 0,
) -> Judgment:
    """Build a minimal Judgment for aggregate() tests (no real LLM calls)."""
    total = float(sum(rubric_scores.values()) / max(len(rubric_scores), 1))
    return Judgment(
        judge_model_id=judge_id,
        judge_order=judge_order,
        rubric_version="1.0",
        rubric_scores=rubric_scores,
        total_score=min(10.0, max(0.0, total)),
        raw_explanation="test",
        latency_ms=0,
        tokens_in=0,
        tokens_out=0,
        cost_usd=Decimal("0"),
    )


class TestJudgePanelAggregateSliceC:
    """RFC-002 Slice C acceptance criteria + ADR-005 invariants.

    All tests are pure computation — no LLM calls, no network.
    """

    @pytest.fixture
    def three_judge_panel(self) -> JudgePanel:
        """Standard 3-judge panel fixture (3 different families)."""
        return JudgePanel(
            judge_models=[
                "claude-sonnet-4-6-judge",
                "gpt-5-mini-judge",
                "gemini-3-flash-judge",
            ],
            candidate_model_id="openrouter/meta-llama/llama-3.3-70b-instruct",
            rubric_version="1.0",
        )

    # ── Test 1: perfect agreement → alpha = 1.0, CI collapses ───────────────────
    def test_perfect_agreement_alpha_one(self, three_judge_panel: JudgePanel) -> None:
        """3 judges all give identical scores → alpha = 1.0, CI = [1.0, 1.0]."""
        judgments = [
            _make_judgment("claude-sonnet-4-6-judge", {"correctness": 8.0, "clarity": 7.0}, 0),
            _make_judgment("gpt-5-mini-judge", {"correctness": 8.0, "clarity": 7.0}, 1),
            _make_judgment("gemini-3-flash-judge", {"correctness": 8.0, "clarity": 7.0}, 2),
        ]
        agg = three_judge_panel.aggregate(judgments)

        assert agg.judge_status == "OK"
        assert agg.n_judges_used == 3
        assert agg.alpha_point is not None
        # Perfect agreement → alpha = 1.0 (within numerical tolerance)
        assert abs(agg.alpha_point - 1.0) < 1e-6, f"expected alpha=1.0, got {agg.alpha_point}"
        # CI both bounds should also be 1.0 (all resamples identical)
        assert agg.alpha_ci_lower is not None
        assert agg.alpha_ci_upper is not None
        assert abs(agg.alpha_ci_lower - 1.0) < 1e-6, f"CI lower={agg.alpha_ci_lower}"
        assert abs(agg.alpha_ci_upper - 1.0) < 1e-6, f"CI upper={agg.alpha_ci_upper}"

    # ── Test 2: orthogonal disagreement → alpha near 0, CI brackets 0 ──────────
    def test_orthogonal_disagreement_alpha_near_zero(self, three_judge_panel: JudgePanel) -> None:
        """Judges with maximally diverse scores → alpha near 0, CI includes 0."""
        # Spread scores maximally: one judge gives 0, one 5, one 10 on every criterion.
        judgments = [
            _make_judgment("claude-sonnet-4-6-judge", {"correctness": 0.0, "clarity": 10.0}, 0),
            _make_judgment("gpt-5-mini-judge", {"correctness": 5.0, "clarity": 5.0}, 1),
            _make_judgment("gemini-3-flash-judge", {"correctness": 10.0, "clarity": 0.0}, 2),
        ]
        agg = three_judge_panel.aggregate(judgments)

        assert agg.judge_status == "OK"
        assert agg.alpha_point is not None
        # alpha should be near 0 or negative (poor agreement / systematic disagreement)
        assert agg.alpha_point < 0.5, f"expected low alpha for disagreement, got {agg.alpha_point}"
        # CI should bracket or include 0
        assert agg.alpha_ci_lower is not None
        assert agg.alpha_ci_upper is not None
        assert agg.alpha_ci_lower <= 0.5, f"CI lower={agg.alpha_ci_lower} should be low"

    # ── Test 3: median per criterion correctness ──────────────────────────────
    def test_median_per_criterion(self, three_judge_panel: JudgePanel) -> None:
        """Hand-crafted 3-judge x 2-criterion matrix; verify median computation."""
        # Judge A: correctness=6, clarity=9
        # Judge B: correctness=8, clarity=7
        # Judge C: correctness=7, clarity=8
        # Expected medians: correctness=7.0, clarity=8.0
        judgments = [
            _make_judgment("claude-sonnet-4-6-judge", {"correctness": 6.0, "clarity": 9.0}, 0),
            _make_judgment("gpt-5-mini-judge", {"correctness": 8.0, "clarity": 7.0}, 1),
            _make_judgment("gemini-3-flash-judge", {"correctness": 7.0, "clarity": 8.0}, 2),
        ]
        agg = three_judge_panel.aggregate(judgments)

        assert agg.median_per_criterion["correctness"] == 7.0
        assert agg.median_per_criterion["clarity"] == 8.0

    # ── Test 4: degraded panel → DEGRADED status, alpha=None ────────────────────
    def test_degraded_panel_returns_degraded_status(self, three_judge_panel: JudgePanel) -> None:
        """Pass 2 judgments when panel requested 3 → DEGRADED with all alpha=None."""
        judgments = [
            _make_judgment("claude-sonnet-4-6-judge", {"correctness": 7.0}, 0),
            _make_judgment("gpt-5-mini-judge", {"correctness": 8.0}, 1),
            # gemini judge missing — simulates judge dropout (PRD-002 Q3)
        ]
        agg = three_judge_panel.aggregate(judgments)

        assert agg.judge_status == "DEGRADED"
        assert agg.n_judges_used == 2
        assert agg.alpha_point is None
        assert agg.alpha_ci_lower is None
        assert agg.alpha_ci_upper is None
        # Median is still computed even in DEGRADED (useful for partial scoring)
        assert "correctness" in agg.median_per_criterion

    # ── Test 5: bootstrap CI is deterministic with fixed seed ────────────────────
    def test_bootstrap_ci_deterministic(self, three_judge_panel: JudgePanel) -> None:
        """Same input twice → identical CI bounds (ADR-005 seed=42 invariant)."""
        judgments = [
            _make_judgment("claude-sonnet-4-6-judge", {"correctness": 6.0, "clarity": 8.0}, 0),
            _make_judgment("gpt-5-mini-judge", {"correctness": 8.0, "clarity": 7.0}, 1),
            _make_judgment("gemini-3-flash-judge", {"correctness": 7.0, "clarity": 9.0}, 2),
        ]
        agg1 = three_judge_panel.aggregate(judgments)
        agg2 = three_judge_panel.aggregate(judgments)

        assert agg1.alpha_ci_lower == agg2.alpha_ci_lower, (
            f"CI lower not deterministic: {agg1.alpha_ci_lower} vs {agg2.alpha_ci_lower}"
        )
        assert agg1.alpha_ci_upper == agg2.alpha_ci_upper, (
            f"CI upper not deterministic: {agg1.alpha_ci_upper} vs {agg2.alpha_ci_upper}"
        )

    # ── Test 6: golden alpha value — computationally verified ───────────────────
    def test_golden_alpha_known_matrix(self, three_judge_panel: JudgePanel) -> None:
        """Verify alpha on a matrix with a known computationally-derived value.

        3 coders x 5 items (ordinal scale 1-4):
          Coder A: [1, 2, 3, 3, 2]
          Coder B: [1, 2, 3, 3, 2]   (identical to A)
          Coder C: [2, 3, 4, 4, 3]   (systematic +1 shift from A/B)

        Verified value: krippendorff.alpha(matrix, level_of_measurement="ordinal")
        returns approximately 0.6113 for this configuration (computed by running
        the library directly — confirmed 2026-05-25).

        Matrix orientation: N judges rows x M criteria columns.
        krippendorff.alpha() contract: reliability_data rows=coders, cols=items.
        """
        # Judge rows x criteria columns:
        # judge1 (claude) = A = [1,2,3,3,2]
        # judge2 (gpt)    = B = [1,2,3,3,2]
        # judge3 (gemini) = C = [2,3,4,4,3]
        crit_names = [f"item_{i}" for i in range(5)]
        judge_scores: list[list[float]] = [
            [1.0, 2.0, 3.0, 3.0, 2.0],  # A
            [1.0, 2.0, 3.0, 3.0, 2.0],  # B
            [2.0, 3.0, 4.0, 4.0, 3.0],  # C
        ]
        judge_ids = ["claude-sonnet-4-6-judge", "gpt-5-mini-judge", "gemini-3-flash-judge"]
        judgments = [
            _make_judgment(
                judge_id,
                {cn: score for cn, score in zip(crit_names, scores, strict=True)},
                order,
            )
            for order, (judge_id, scores) in enumerate(zip(judge_ids, judge_scores, strict=True))
        ]
        agg = three_judge_panel.aggregate(judgments)

        assert agg.alpha_point is not None
        # Golden value: alpha approx 0.6113 (verified by direct library call 2026-05-25).
        assert abs(agg.alpha_point - 0.6113) < 0.001, (
            f"golden alpha mismatch: expected approx 0.6113, got {agg.alpha_point:.6f}"
        )
        # CI lower should be positive (moderate agreement matrix)
        assert agg.alpha_ci_lower is not None
        assert agg.alpha_ci_lower > 0.3, (
            f"CI lower={agg.alpha_ci_lower:.4f} unexpectedly low for golden matrix"
        )

    # ── Test 7: n_judges_requested stored correctly on panel ──────────────────
    def test_n_judges_requested_stored(self) -> None:
        """_n_judges_requested equals len(judge_models) at construction time."""
        panel = JudgePanel(
            judge_models=["gpt-5-mini-judge", "gemini-3-flash-judge"],
            candidate_model_id="openrouter/anthropic/claude-haiku",
            rubric_version="1.0",
        )
        assert panel._n_judges_requested == 2

    # ── Test 8: single-criterion matrix computes alpha without error ────────────
    def test_single_criterion_matrix(self, three_judge_panel: JudgePanel) -> None:
        """1-criterion x 3-judge matrix — edge case; alpha should compute without error."""
        judgments = [
            _make_judgment("claude-sonnet-4-6-judge", {"correctness": 7.0}, 0),
            _make_judgment("gpt-5-mini-judge", {"correctness": 8.0}, 1),
            _make_judgment("gemini-3-flash-judge", {"correctness": 9.0}, 2),
        ]
        # Should not raise; alpha may be low (1 criterion means no between-criterion
        # structure for the ordinal distance to differentiate on).
        agg = three_judge_panel.aggregate(judgments)
        assert agg.judge_status == "OK"
        assert "correctness" in agg.median_per_criterion
        assert agg.median_per_criterion["correctness"] == 8.0


# ---------------------------------------------------------------------------
# Slice B — score() implementation tests
# ---------------------------------------------------------------------------


class TestJudgePanelScoreSliceB:
    """Tests for JudgePanel.score() — RFC-002 Slice B.

    All tests mock _run_judge_task, _read_raw_output, _make_judge_models,
    and _load_rubric_criteria so no real LLM calls, no OPENAI_API_KEY, and
    no file-system rubric.yaml access are required.

    Verifies:
      - correct scorer list construction (one per judge)
      - max_tokens cap passes through to get_model config at init time
      - 2 judges → 2 Judgment objects with distinct judge_model_id
      - rubric JSON parsed → per-criterion dict emitted in Judgment
      - judge_order is set per shuffled position
    """

    # Canonical doc_01 rubric criteria used for mocking _load_rubric_criteria.
    _DOC01_CRITERIA: ClassVar[dict[str, dict[str, object]]] = {
        "structural_completeness": {"weight": 0.20, "description": "structure", "anchors": {}},
        "factual_accuracy": {"weight": 0.20, "description": "accuracy", "anchors": {}},
        "clarity": {"weight": 0.20, "description": "clarity", "anchors": {}},
        "actionability": {"weight": 0.20, "description": "actionability", "anchors": {}},
        "consistency": {"weight": 0.20, "description": "consistency", "anchors": {}},
    }

    @pytest.fixture(autouse=True)
    def mock_make_judge_models(self) -> object:
        """Prevent real Inspect AI model construction (requires OPENAI_API_KEY).

        _make_judge_models is lazily called inside score() to build scorer
        objects. We replace it with a method that returns dummy MagicMock
        objects of the right length — the scorer list is only used to build
        rubric scorer instances, which themselves are mocked out via
        _run_judge_task.
        """

        def _fake_make_judge_models(self_panel: JudgePanel) -> list[MagicMock]:
            return [MagicMock(name=f"mock_model_{i}") for i in range(len(self_panel._judge_models))]

        with patch.object(JudgePanel, "_make_judge_models", _fake_make_judge_models):
            yield

    @pytest.fixture(autouse=True)
    def mock_load_rubric_criteria(self) -> object:
        """Prevent file-system rubric.yaml access in score() tests.

        Returns the doc_01 5-criterion rubric so tests don't need the repo
        CWD to contain evals/task-packs/.
        """
        import src.orchestrator.judge_panel as _jp

        with patch.object(_jp, "_load_rubric_criteria", return_value=self._DOC01_CRITERIA):
            yield

    @pytest.fixture
    def two_judge_panel(self) -> JudgePanel:
        return JudgePanel(
            judge_models=[
                "claude-sonnet-4-6-judge",
                "gpt-5-mini-judge",
            ],
            candidate_model_id="openrouter/meta-llama/llama-3.3-70b-instruct",
            rubric_version="1.0",
        )

    @pytest.fixture
    def three_judge_panel(self) -> JudgePanel:
        return JudgePanel(
            judge_models=[
                "claude-sonnet-4-6-judge",
                "gpt-5-mini-judge",
                "gemini-3-flash-judge",
            ],
            candidate_model_id="openrouter/meta-llama/llama-3.3-70b-instruct",
            rubric_version="1.0",
        )

    @pytest.mark.asyncio
    async def test_two_judges_return_two_judgments(self, two_judge_panel: JudgePanel) -> None:
        """2 judges in panel → 2 Judgment objects returned."""
        eval_result = _make_fake_eval_result()
        fake_log = _make_fake_eval_log(
            {
                "judge_0": _make_fake_score("C"),
                "judge_1": _make_fake_score("C"),
            }
        )

        mock_run = AsyncMock(return_value=[fake_log])
        with (
            patch.object(two_judge_panel, "_run_judge_task", new=mock_run),
            patch.object(two_judge_panel, "_read_raw_output", return_value="candidate output"),
        ):
            judgments = await two_judge_panel.score(eval_result, "be_01_jwt_auth")  # type: ignore[arg-type]

        assert len(judgments) == 2
        judge_ids = {j.judge_model_id for j in judgments}
        assert judge_ids == {"claude-sonnet-4-6-judge", "gpt-5-mini-judge"}

    @pytest.mark.asyncio
    async def test_score_c_maps_to_10(self, two_judge_panel: JudgePanel) -> None:
        """Rubric JSON with all criteria = 10.0 → 5-key dict and total_score = 10.0."""
        eval_result = _make_fake_eval_result()
        all_10_json = _make_doc01_rubric_json(score_per_criterion=10.0)
        fake_log = _make_fake_eval_log(
            {
                "judge_0": _make_fake_score("C", all_10_json),
                "judge_1": _make_fake_score("C", all_10_json),
            }
        )

        mock_run = AsyncMock(return_value=[fake_log])
        with (
            patch.object(two_judge_panel, "_run_judge_task", new=mock_run),
            patch.object(two_judge_panel, "_read_raw_output", return_value="output"),
        ):
            judgments = await two_judge_panel.score(eval_result, "be_01_jwt_auth")  # type: ignore[arg-type]

        doc01_criteria = set(self._DOC01_CRITERIA.keys())
        for j in judgments:
            assert set(j.rubric_scores.keys()) == doc01_criteria
            assert all(v == 10.0 for v in j.rubric_scores.values())
            assert j.total_score == 10.0

    @pytest.mark.asyncio
    async def test_score_i_maps_to_0(self, two_judge_panel: JudgePanel) -> None:
        """Rubric JSON with all criteria = 0.0 → 5-key dict and total_score = 0.0."""
        eval_result = _make_fake_eval_result()
        all_0_json = _make_doc01_rubric_json(score_per_criterion=0.0)
        fake_log = _make_fake_eval_log(
            {
                "judge_0": _make_fake_score("I", all_0_json),
                "judge_1": _make_fake_score("I", all_0_json),
            }
        )

        mock_run = AsyncMock(return_value=[fake_log])
        with (
            patch.object(two_judge_panel, "_run_judge_task", new=mock_run),
            patch.object(two_judge_panel, "_read_raw_output", return_value="output"),
        ):
            judgments = await two_judge_panel.score(eval_result, "be_01_jwt_auth")  # type: ignore[arg-type]

        doc01_criteria = set(self._DOC01_CRITERIA.keys())
        for j in judgments:
            assert set(j.rubric_scores.keys()) == doc01_criteria
            assert all(v == 0.0 for v in j.rubric_scores.values())
            assert j.total_score == 0.0

    @pytest.mark.asyncio
    async def test_judge_order_assigned(self, two_judge_panel: JudgePanel) -> None:
        """Each Judgment carries a non-negative judge_order (0-indexed position)."""
        eval_result = _make_fake_eval_result()
        fake_log = _make_fake_eval_log(
            {
                "judge_0": _make_fake_score("C"),
                "judge_1": _make_fake_score("I"),
            }
        )

        mock_run = AsyncMock(return_value=[fake_log])
        with (
            patch.object(two_judge_panel, "_run_judge_task", new=mock_run),
            patch.object(two_judge_panel, "_read_raw_output", return_value="output"),
        ):
            judgments = await two_judge_panel.score(eval_result, "be_01_jwt_auth")  # type: ignore[arg-type]

        orders = [j.judge_order for j in judgments]
        assert sorted(orders) == [0, 1]  # both positions assigned
        assert len(set(orders)) == 2  # distinct

    @pytest.mark.asyncio
    async def test_rubric_version_propagated(self, two_judge_panel: JudgePanel) -> None:
        """rubric_version from panel init appears on every Judgment."""
        eval_result = _make_fake_eval_result()
        fake_log = _make_fake_eval_log(
            {
                "model_graded_qa": _make_fake_score("C"),
                "model_graded_qa_1": _make_fake_score("C"),
            }
        )

        mock_run = AsyncMock(return_value=[fake_log])
        with (
            patch.object(two_judge_panel, "_run_judge_task", new=mock_run),
            patch.object(two_judge_panel, "_read_raw_output", return_value="output"),
        ):
            judgments = await two_judge_panel.score(eval_result, "task_x")  # type: ignore[arg-type]

        for j in judgments:
            assert j.rubric_version == "1.0"

    @pytest.mark.asyncio
    async def test_raw_explanation_captured(self, two_judge_panel: JudgePanel) -> None:
        """Score.explanation text is stored in Judgment.raw_explanation."""
        eval_result = _make_fake_eval_result()
        fake_log = _make_fake_eval_log(
            {
                "model_graded_qa": _make_fake_score("C", "Because the JWT is valid"),
                "model_graded_qa_1": _make_fake_score("I", "Missing refresh token"),
            }
        )

        mock_run = AsyncMock(return_value=[fake_log])
        with (
            patch.object(two_judge_panel, "_run_judge_task", new=mock_run),
            patch.object(two_judge_panel, "_read_raw_output", return_value="output"),
        ):
            judgments = await two_judge_panel.score(eval_result, "be_01_jwt_auth")  # type: ignore[arg-type]

        explanations = {j.raw_explanation for j in judgments}
        assert "Because the JWT is valid" in explanations
        assert "Missing refresh token" in explanations

    @pytest.mark.asyncio
    async def test_max_tokens_cap_passed_to_get_model(self, two_judge_panel: JudgePanel) -> None:
        """GenerateConfig(max_tokens=512) is set on judge model objects (EVID-023 finding #3)."""
        # Access the judge_config that was set at init time.
        cfg = two_judge_panel._judge_config
        assert cfg.max_tokens == 512

    @pytest.mark.asyncio
    async def test_three_judges_distinct_ids(self, three_judge_panel: JudgePanel) -> None:
        """3 judges → 3 Judgment objects with distinct judge_model_id."""
        eval_result = _make_fake_eval_result()
        fake_log = _make_fake_eval_log(
            {
                "model_graded_qa": _make_fake_score("C"),
                "model_graded_qa_1": _make_fake_score("C"),
                "model_graded_qa_2": _make_fake_score("I"),
            }
        )

        mock_run = AsyncMock(return_value=[fake_log])
        with (
            patch.object(three_judge_panel, "_run_judge_task", new=mock_run),
            patch.object(three_judge_panel, "_read_raw_output", return_value="output"),
        ):
            judgments = await three_judge_panel.score(eval_result, "be_01_jwt_auth")  # type: ignore[arg-type]

        assert len(judgments) == 3
        ids = {j.judge_model_id for j in judgments}
        assert ids == {"claude-sonnet-4-6-judge", "gpt-5-mini-judge", "gemini-3-flash-judge"}

    @pytest.mark.asyncio
    async def test_proxy_alias_prefixes_openai(self, two_judge_panel: JudgePanel) -> None:
        """_proxy_alias_for prepends 'openai/' if not already present."""
        assert two_judge_panel._proxy_alias_for("claude-sonnet-4-6-judge") == (
            "openai/claude-sonnet-4-6-judge"
        )
        # Already prefixed — no double-prefix.
        assert two_judge_panel._proxy_alias_for("openai/gpt-5-mini-judge") == (
            "openai/gpt-5-mini-judge"
        )

    @pytest.mark.asyncio
    async def test_run_raises_on_empty_logs(self, two_judge_panel: JudgePanel) -> None:
        """RuntimeError if eval_async returns empty list."""
        eval_result = _make_fake_eval_result()

        mock_run = AsyncMock(return_value=[])
        with (
            patch.object(two_judge_panel, "_run_judge_task", new=mock_run),
            patch.object(two_judge_panel, "_read_raw_output", return_value="output"),
            pytest.raises(RuntimeError, match="returned no logs"),
        ):
            await two_judge_panel.score(eval_result, "be_01_jwt_auth")  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_read_raw_output_placeholder_for_non_file_uri(
        self, two_judge_panel: JudgePanel
    ) -> None:
        """Non-file:// URIs return a placeholder (R2, etc.)."""
        eval_result = _make_fake_eval_result(
            raw_output_uri="r2://runs/abc123/evals/deadbeef01234567/raw-abc.txt"
        )
        placeholder = two_judge_panel._read_raw_output(eval_result)  # type: ignore[arg-type]
        assert placeholder.startswith("[non-local artifact uri=")

    def test_read_raw_output_placeholder_for_unreadable_file(
        self, two_judge_panel: JudgePanel
    ) -> None:
        """If the local file doesn't exist, a placeholder is returned (no crash)."""
        eval_result = _make_fake_eval_result(
            raw_output_uri="file:///tmp/this-file-definitely-does-not-exist-12345.txt"
        )
        result = two_judge_panel._read_raw_output(eval_result)  # type: ignore[arg-type]
        assert result.startswith("[artifact not readable:")

    def test_read_raw_output_reads_existing_file(
        self, two_judge_panel: JudgePanel, tmp_path: pathlib.Path
    ) -> None:
        """If the local file exists, its content is returned verbatim."""
        artifact = tmp_path / "raw-abc123.txt"
        artifact.write_text("hello world from candidate", encoding="utf-8")
        eval_result = _make_fake_eval_result(raw_output_uri=f"file://{artifact}")
        result = two_judge_panel._read_raw_output(eval_result)  # type: ignore[arg-type]
        assert result == "hello world from candidate"


# ---------------------------------------------------------------------------
# Judgment pydantic model validation
# ---------------------------------------------------------------------------


class TestJudgmentModel:
    """Minimal field validation for the Judgment contract."""

    def _minimal_judgment(self, **overrides: object) -> dict[str, object]:
        base: dict[str, object] = {
            "judge_model_id": "openrouter/openai/gpt-5-mini",
            "judge_order": 0,
            "rubric_version": "1.0",
            "rubric_scores": {"correctness": 8.0, "clarity": 7.5},
            "total_score": 7.75,
            "raw_explanation": "The output is correct and concise.",
            "latency_ms": 1200,
            "tokens_in": 250,
            "tokens_out": 60,
            "cost_usd": Decimal("0.05"),
        }
        base.update(overrides)
        return base

    def test_valid_judgment(self) -> None:
        j = Judgment(**self._minimal_judgment())  # type: ignore[arg-type]
        assert j.total_score == 7.75
        assert j.tokens_in == 250

    def test_negative_judge_order_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Judgment(**self._minimal_judgment(judge_order=-1))  # type: ignore[arg-type]

    def test_negative_tokens_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Judgment(**self._minimal_judgment(tokens_in=-1))  # type: ignore[arg-type]

    def test_negative_latency_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Judgment(**self._minimal_judgment(latency_ms=-1))  # type: ignore[arg-type]

    def test_score_above_10_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Judgment(**self._minimal_judgment(total_score=10.1))  # type: ignore[arg-type]

    def test_score_below_0_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Judgment(**self._minimal_judgment(total_score=-0.1))  # type: ignore[arg-type]

    def test_negative_cost_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Judgment(**self._minimal_judgment(cost_usd=Decimal("-0.01")))  # type: ignore[arg-type]

    def test_frozen_immutable(self) -> None:
        j = Judgment(**self._minimal_judgment())  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            j.total_score = 5.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# JudgeAggregation pydantic model validation
# ---------------------------------------------------------------------------


class TestJudgeAggregationModel:
    """Minimal field validation for the JudgeAggregation contract."""

    def _minimal_agg(self, **overrides: object) -> dict[str, object]:
        base: dict[str, object] = {
            "median_per_criterion": {"correctness": 8.0, "clarity": 7.5},
            "judge_status": "OK",
            "n_judges_used": 3,
        }
        base.update(overrides)
        return base

    def test_valid_ok_aggregation(self) -> None:
        agg = JudgeAggregation(**self._minimal_agg())  # type: ignore[arg-type]
        assert agg.judge_status == "OK"
        assert agg.alpha_point is None  # optional, default None

    def test_valid_degraded_aggregation(self) -> None:
        agg = JudgeAggregation(  # type: ignore[call-arg]
            **self._minimal_agg(judge_status="DEGRADED", n_judges_used=2)  # type: ignore[arg-type]
        )
        assert agg.judge_status == "DEGRADED"
        assert agg.n_judges_used == 2

    def test_with_alpha_fields(self) -> None:
        agg = JudgeAggregation(  # type: ignore[call-arg]
            **self._minimal_agg(  # type: ignore[arg-type]
                alpha_point=0.82,
                alpha_ci_lower=0.71,
                alpha_ci_upper=0.91,
            )
        )
        assert agg.alpha_point == 0.82
        assert agg.alpha_ci_lower == 0.71

    def test_invalid_judge_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            JudgeAggregation(**self._minimal_agg(judge_status="UNKNOWN"))  # type: ignore[arg-type]

    def test_zero_judges_rejected(self) -> None:
        with pytest.raises(ValidationError):
            JudgeAggregation(**self._minimal_agg(n_judges_used=0))  # type: ignore[arg-type]

    def test_frozen_immutable(self) -> None:
        agg = JudgeAggregation(**self._minimal_agg())  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            agg.judge_status = "DEGRADED"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# _spearman_r helper
# ---------------------------------------------------------------------------


class TestSpearmanR:
    """Unit tests for the module-level _spearman_r helper (no scipy dep)."""

    def test_perfect_positive_correlation(self) -> None:
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        assert abs(_spearman_r(x, y) - 1.0) < 1e-9

    def test_perfect_negative_correlation(self) -> None:
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
        assert abs(_spearman_r(x, y) - (-1.0)) < 1e-9

    def test_known_correlation(self) -> None:
        # gold order: perfect > good > mediocre > poor > broken
        gold = np.array([9.0, 7.5, 5.0, 2.5, 0.5])
        # slightly noisy judge scores that preserve exact same rank order
        judge = np.array([8.8, 7.2, 5.3, 2.8, 0.6])
        rs = _spearman_r(gold, judge)
        assert abs(rs - 1.0) < 1e-9, f"expected 1.0 for rank-preserving scores, got {rs}"

    def test_ties_handled(self) -> None:
        # All same gold score — all three values tie at the same rank (2.0 avg).
        # d = rank(gold) - rank(judge) = [2.0 - 1.0, 2.0 - 2.0, 2.0 - 3.0]
        # = [1.0, 0.0, -1.0], sum(d²) = 2.0
        # r_s = 1 - 6*2 / (3*(9-1)) = 1 - 12/24 = 0.5
        # Most importantly: must not raise.
        gold = np.array([5.0, 5.0, 5.0])
        judge = np.array([4.0, 5.0, 6.0])
        rs = _spearman_r(gold, judge)
        assert isinstance(rs, float)
        assert -1.0 <= rs <= 1.0

    def test_degenerate_single_sample(self) -> None:
        rs = _spearman_r(np.array([7.0]), np.array([7.0]))
        assert rs == 0.0  # n < 2 → 0.0 by contract


# ---------------------------------------------------------------------------
# Slice D — run_calibration() tests
# ---------------------------------------------------------------------------


def _make_three_judge_panel() -> JudgePanel:
    return JudgePanel(
        judge_models=[
            "claude-sonnet-4-6-judge",
            "gpt-5-mini-judge",
            "gemini-3-flash-judge",
        ],
        candidate_model_id="openrouter/meta-llama/llama-3.3-70b-instruct",
        rubric_version="1.0",
    )


def _write_calibration_fixture(
    tmp_path: pathlib.Path,
    task_id: str,
    samples_per_level: int = 2,
) -> pathlib.Path:
    """Create minimal calibration fixture under tmp_path/evals/task-packs/<task_id>/."""
    GOLD = {"perfect": 9.0, "good": 7.5, "mediocre": 5.0, "poor": 2.5, "broken": 0.5}

    pack_root = tmp_path / "evals" / "task-packs" / task_id
    calib_root = pack_root / "calibration"
    for level in GOLD:
        level_dir = calib_root / level
        level_dir.mkdir(parents=True, exist_ok=True)
        for i in range(samples_per_level):
            (level_dir / f"sample-{i:03d}.md").write_text(
                f"# {level} sample {i}\nContent for {task_id}.", encoding="utf-8"
            )

    yaml_content = (
        f"task_id: {task_id}\n"
        "rubric_version: '1.0'\n"
        "gold_scores:\n"
        + "".join(f"  {k}: {v}\n" for k, v in GOLD.items())
        + "mad_threshold: 1.5\n"
        f"n_samples_per_level: {samples_per_level}\n"
    )
    (pack_root / "calibration.yaml").write_text(yaml_content, encoding="utf-8")
    return pack_root


class TestRunCalibration:
    """Tests for JudgePanel.run_calibration() — RFC-002 Slice D."""

    GOLD: ClassVar[dict[str, float]] = {
        "perfect": 9.0,
        "good": 7.5,
        "mediocre": 5.0,
        "poor": 2.5,
        "broken": 0.5,
    }

    # ── Test 1: calibration with scores close to gold → MAD ≤ 1.5, passed=True ─

    @pytest.mark.asyncio
    async def test_calibration_passes_when_scores_near_gold(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mock judge returning gold ± 0.3 → MAD ≤ 0.3, passed=True."""
        _write_calibration_fixture(tmp_path, "be_01_jwt_auth", samples_per_level=2)
        panel = _make_three_judge_panel()

        # Each judge returns gold_score + small perturbation (well within 1.5 threshold).
        call_count = {"n": 0}

        async def _near_gold_score(
            self_panel: JudgePanel,
            judge_id: str,
            sample_content: str,
            task_id: str,
        ) -> float:
            call_count["n"] += 1
            level = sample_content.split()[1]  # "# <level> sample <i>"
            return self.GOLD.get(level, 5.0) + 0.3

        monkeypatch.chdir(tmp_path)
        with patch.object(JudgePanel, "_score_calibration_sample", _near_gold_score):
            result = await panel.run_calibration("be_01_jwt_auth")

        assert isinstance(result, CalibrationResult)
        assert result.task_id == "be_01_jwt_auth"
        assert result.passed is True
        for jc in result.judge_calibrations.values():
            assert jc.mad <= 1.5, f"MAD {jc.mad} exceeds threshold for {jc.judge_id}"
            assert jc.samples_evaluated == 10  # 5 levels x 2 samples each

    # ── Test 2: calibration fails when judge has systematic +2.0 bias ────────────

    @pytest.mark.asyncio
    async def test_calibration_fails_when_mad_exceeds_threshold(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mock judge returning gold + 2.0 → MAD ≈ 2.0, passed=False."""
        _write_calibration_fixture(tmp_path, "be_01_jwt_auth", samples_per_level=2)
        panel = _make_three_judge_panel()

        async def _biased_score(
            self_panel: JudgePanel,
            judge_id: str,
            sample_content: str,
            task_id: str,
        ) -> float:
            level = sample_content.split()[1]
            raw = self.GOLD.get(level, 5.0) + 2.0
            # Clamp to [0, 10] to stay within valid range.
            return min(10.0, raw)

        monkeypatch.chdir(tmp_path)
        with patch.object(JudgePanel, "_score_calibration_sample", _biased_score):
            result = await panel.run_calibration("be_01_jwt_auth")

        assert result.passed is False
        # At least one judge (all three in this case) should have MAD > 1.5.
        assert any(jc.mad > 1.5 for jc in result.judge_calibrations.values())

    # ── Test 3: calibration_hash is deterministic for same content ───────────────

    @pytest.mark.asyncio
    async def test_calibration_hash_deterministic(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Same fixture + same scores → same calibration_hash on two runs."""
        _write_calibration_fixture(tmp_path, "be_01_jwt_auth", samples_per_level=2)
        panel = _make_three_judge_panel()

        async def _fixed_score(
            self_panel: JudgePanel,
            judge_id: str,
            sample_content: str,
            task_id: str,
        ) -> float:
            level = sample_content.split()[1]
            return self.GOLD.get(level, 5.0)

        monkeypatch.chdir(tmp_path)
        with patch.object(JudgePanel, "_score_calibration_sample", _fixed_score):
            result1 = await panel.run_calibration("be_01_jwt_auth")
            result2 = await panel.run_calibration("be_01_jwt_auth")

        assert result1.calibration_hash == result2.calibration_hash, (
            "calibration_hash not deterministic for identical content"
        )
        assert len(result1.calibration_hash) == 64, "expected SHA-256 hex digest (64 chars)"

    # ── Test 4: gold_scores round-trip from calibration.yaml ──────────────────────

    @pytest.mark.asyncio
    async def test_gold_scores_loaded_from_yaml(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CalibrationResult.gold_scores matches what was written to calibration.yaml."""
        _write_calibration_fixture(tmp_path, "be_01_jwt_auth", samples_per_level=2)
        panel = _make_three_judge_panel()

        async def _noop(
            self_panel: JudgePanel,
            judge_id: str,
            sample_content: str,
            task_id: str,
        ) -> float:
            level = sample_content.split()[1]
            return self.GOLD.get(level, 5.0)

        monkeypatch.chdir(tmp_path)
        with patch.object(JudgePanel, "_score_calibration_sample", _noop):
            result = await panel.run_calibration("be_01_jwt_auth")

        assert result.gold_scores == self.GOLD

    # ── Test 5: missing calibration.yaml raises FileNotFoundError ─────────────────

    @pytest.mark.asyncio
    async def test_missing_yaml_raises(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FileNotFoundError when calibration.yaml is absent."""
        monkeypatch.chdir(tmp_path)
        panel = _make_three_judge_panel()
        with pytest.raises(FileNotFoundError, match=r"calibration\.yaml not found"):
            await panel.run_calibration("nonexistent_task")

    # ── Test 6: rank_correlation is 1.0 when judge preserves gold rank order ──────

    @pytest.mark.asyncio
    async def test_rank_correlation_perfect_for_rank_preserving_judge(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Judge that perfectly preserves gold rank order → rank_correlation ≈ 1.0."""
        _write_calibration_fixture(tmp_path, "be_01_jwt_auth", samples_per_level=1)
        panel = _make_three_judge_panel()

        async def _rank_preserving(
            self_panel: JudgePanel,
            judge_id: str,
            sample_content: str,
            task_id: str,
        ) -> float:
            level = sample_content.split()[1]
            # Slightly different scale but preserves rank order exactly.
            return self.GOLD.get(level, 5.0) * 0.9 + 0.5

        monkeypatch.chdir(tmp_path)
        with patch.object(JudgePanel, "_score_calibration_sample", _rank_preserving):
            result = await panel.run_calibration("be_01_jwt_auth")

        for jc in result.judge_calibrations.values():
            assert jc.rank_correlation >= 0.99, (
                "expected rank_correlation~=1.0 for rank-preserving judge, "
                f"got {jc.rank_correlation}"
            )


# ---------------------------------------------------------------------------
# Slice D — run_identification_probe() tests
# ---------------------------------------------------------------------------


def _write_probe_fixture(
    tmp_path: pathlib.Path,
    task_id: str,
    samples_per_family: int = 5,
    families: tuple[str, ...] = ("anthropic", "openai", "google", "qwen", "meta"),
) -> pathlib.Path:
    """Create identification_probe fixture under tmp_path/evals/task-packs/<task_id>/."""
    probe_dir = tmp_path / "evals" / "task-packs" / task_id / "identification_probe"
    probe_dir.mkdir(parents=True, exist_ok=True)
    for family in families:
        for i in range(samples_per_family):
            (probe_dir / f"{family}-{i:03d}.md").write_text(
                f"Output for task {task_id} by family {family}, sample {i}.",
                encoding="utf-8",
            )
    return probe_dir


class TestRunIdentificationProbe:
    """Tests for JudgePanel.run_identification_probe() — RFC-002 Slice D, SC-4."""

    FAMILIES = ("anthropic", "openai", "google", "qwen", "meta")

    # ── Test 1: random guessing → accuracy ≈ 0.20, passed=True ──────────────────

    @pytest.mark.asyncio
    async def test_random_guessing_accuracy_below_threshold(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Judge guessing randomly → accuracy = 1/5 = 0.20 ≤ 0.30, passed=True."""
        _write_probe_fixture(tmp_path, "be_01_jwt_auth", samples_per_family=5)
        panel = _make_three_judge_panel()

        # Deterministic "random" guesser: always returns the same wrong family.
        # With 5 families x 5 samples = 25 samples per judge,
        # always guessing "openai" gives 5 correct (openai samples) + 20 wrong = 20%.
        async def _always_openai(
            self_panel: JudgePanel,
            judge_id: str,
            sample_content: str,
            probe_families: frozenset[str],
            task_id: str,
        ) -> str:
            return "openai"

        monkeypatch.chdir(tmp_path)
        with patch.object(JudgePanel, "_score_identification_sample", _always_openai):
            result = await panel.run_identification_probe("be_01_jwt_auth")

        assert isinstance(result, ProbeResult)
        assert result.passed is True, f"expected passed=True, accuracy={result.overall_accuracy}"
        # 5 families x 5 samples = 25 per judge; "openai" correct for 5/25 = 0.2
        assert abs(result.overall_accuracy - 0.2) < 1e-6, (
            f"expected 0.2, got {result.overall_accuracy}"
        )

    # ── Test 2: judges with 50% accuracy → passed=False ──────────────────────────

    @pytest.mark.asyncio
    async def test_high_accuracy_probe_fails(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Judges correctly guessing half the samples → accuracy ≈ 0.5, passed=False."""
        _write_probe_fixture(tmp_path, "be_01_jwt_auth", samples_per_family=10)
        panel = _make_three_judge_panel()

        # Judge reads the family name directly from sample text (cheating).
        # Every sample file contains "by family <family>" — judge extracts it.
        # This gives 100% accuracy. We simulate 50% by returning correct family
        # for even-indexed samples and wrong family for odd-indexed ones.
        sample_index: dict[str, int] = {"i": 0}

        async def _half_correct(
            self_panel: JudgePanel,
            judge_id: str,
            sample_content: str,
            probe_families: frozenset[str],
            task_id: str,
        ) -> str:
            # Extract actual family from content (strip punctuation from each word).
            actual = "anthropic"
            for raw_word in sample_content.split():
                word = raw_word.strip(".,;:")
                if word in probe_families:
                    actual = word
                    break
            idx = sample_index["i"]
            sample_index["i"] += 1
            # Even samples: return the correct family (correct guess).
            # Odd samples: return a wrong family (always incorrect).
            wrong = next(f for f in probe_families if f != actual)
            return actual if idx % 2 == 0 else wrong

        monkeypatch.chdir(tmp_path)
        with patch.object(JudgePanel, "_score_identification_sample", _half_correct):
            result = await panel.run_identification_probe("be_01_jwt_auth")

        assert result.passed is False, (
            f"expected passed=False for high accuracy, got {result.overall_accuracy}"
        )
        assert result.overall_accuracy > 0.30

    # ── Test 3: empty probe dir → n_samples=0, passed=True ────────────────────────

    @pytest.mark.asyncio
    async def test_empty_probe_dir_returns_zero_samples(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty identification_probe/ → n_samples=0, accuracy=0.0, passed=True."""
        # Create empty probe dir (no .md files).
        probe_dir = tmp_path / "evals" / "task-packs" / "be_01_jwt_auth" / "identification_probe"
        probe_dir.mkdir(parents=True, exist_ok=True)
        panel = _make_three_judge_panel()

        monkeypatch.chdir(tmp_path)
        result = await panel.run_identification_probe("be_01_jwt_auth")

        assert result.n_samples == 0
        assert result.overall_accuracy == 0.0
        assert result.passed is True

    # ── Test 4: missing probe dir raises FileNotFoundError ────────────────────────

    @pytest.mark.asyncio
    async def test_missing_probe_dir_raises(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FileNotFoundError when identification_probe/ is absent."""
        monkeypatch.chdir(tmp_path)
        panel = _make_three_judge_panel()
        with pytest.raises(FileNotFoundError, match="identification_probe"):
            await panel.run_identification_probe("nonexistent_task")

    # ── Test 5: judges_used list matches panel construction ────────────────────────

    @pytest.mark.asyncio
    async def test_judges_used_matches_panel(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ProbeResult.judges_used matches the judge_models from JudgePanel init."""
        _write_probe_fixture(tmp_path, "be_01_jwt_auth", samples_per_family=2)
        panel = _make_three_judge_panel()

        async def _noop_guess(
            self_panel: JudgePanel,
            judge_id: str,
            sample_content: str,
            probe_families: frozenset[str],
            task_id: str,
        ) -> str:
            return "anthropic"

        monkeypatch.chdir(tmp_path)
        with patch.object(JudgePanel, "_score_identification_sample", _noop_guess):
            result = await panel.run_identification_probe("be_01_jwt_auth")

        assert set(result.judges_used) == {
            "claude-sonnet-4-6-judge",
            "gpt-5-mini-judge",
            "gemini-3-flash-judge",
        }
        assert set(result.per_judge_accuracy.keys()) == set(result.judges_used)


# ---------------------------------------------------------------------------
# CalibrationResult + ProbeResult pydantic model validation
# ---------------------------------------------------------------------------


class TestCalibrationResultModel:
    """Minimal field validation for CalibrationResult contract."""

    def _minimal_calib(self, **overrides: object) -> dict[str, object]:
        from src.contracts import JudgeCalibration

        base: dict[str, object] = {
            "task_id": "be_01_jwt_auth",
            "judge_calibrations": {
                "gpt-5-mini-judge": JudgeCalibration(
                    judge_id="gpt-5-mini-judge",
                    mad=0.5,
                    rank_correlation=0.95,
                    samples_evaluated=10,
                )
            },
            "passed": True,
            "gold_scores": {"perfect": 9.0, "broken": 0.5},
            "calibration_hash": "a" * 64,
            "mad_threshold": 1.5,
        }
        base.update(overrides)
        return base

    def test_valid_calibration_result(self) -> None:
        r = CalibrationResult(**self._minimal_calib())  # type: ignore[arg-type]
        assert r.passed is True
        assert r.mad_threshold == 1.5

    def test_frozen_immutable(self) -> None:
        r = CalibrationResult(**self._minimal_calib())  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            r.passed = False  # type: ignore[misc]

    def test_negative_mad_threshold_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CalibrationResult(**self._minimal_calib(mad_threshold=-0.1))  # type: ignore[arg-type]


class TestProbeResultModel:
    """Minimal field validation for ProbeResult contract."""

    def _minimal_probe(self, **overrides: object) -> dict[str, object]:
        base: dict[str, object] = {
            "task_id": "be_01_jwt_auth",
            "judges_used": ["gpt-5-mini-judge"],
            "n_samples": 25,
            "per_judge_accuracy": {"gpt-5-mini-judge": 0.2},
            "overall_accuracy": 0.2,
            "passed": True,
        }
        base.update(overrides)
        return base

    def test_valid_probe_result(self) -> None:
        r = ProbeResult(**self._minimal_probe())  # type: ignore[arg-type]
        assert r.passed is True
        assert r.overall_accuracy == 0.2

    def test_accuracy_above_1_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProbeResult(**self._minimal_probe(overall_accuracy=1.1))  # type: ignore[arg-type]

    def test_negative_accuracy_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProbeResult(**self._minimal_probe(overall_accuracy=-0.1))  # type: ignore[arg-type]

    def test_negative_n_samples_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProbeResult(**self._minimal_probe(n_samples=-1))  # type: ignore[arg-type]

    def test_frozen_immutable(self) -> None:
        r = ProbeResult(**self._minimal_probe())  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            r.passed = False  # type: ignore[misc]
