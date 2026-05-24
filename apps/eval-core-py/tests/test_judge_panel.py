"""Tests for RFC-002 Slice A: JudgePanel skeleton + self-judging guard.

Coverage:
  - _normalise_model_family: all routing patterns from EVID-023 + RFC-002
  - _guard_self_judging: exact-ID, cross-route variant, different families
  - JudgePanel.__init__: validates guard wiring, empty judge list, successful construction
  - JudgePanel.score() / aggregate(): both raise NotImplementedError (Slice B/C stubs)
  - Judgment / JudgeAggregation: pydantic field validation
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.contracts import JudgeAggregation, Judgment
from src.orchestrator.judge_panel import JudgePanel, SelfJudgingError, _normalise_model_family

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
# Slice B/C stubs — score() and aggregate() raise NotImplementedError
# ---------------------------------------------------------------------------


class TestSliceStubs:
    """Verifies that score() and aggregate() are stubs per Slice A contract."""

    @pytest.fixture
    def panel(self) -> JudgePanel:
        return JudgePanel(
            judge_models=["openrouter/openai/gpt-5-mini"],
            candidate_model_id="openrouter/anthropic/claude-haiku",
            rubric_version="1.0",
        )

    @pytest.mark.asyncio
    async def test_score_raises_not_implemented(self, panel: JudgePanel) -> None:
        with pytest.raises(NotImplementedError) as exc_info:
            await panel.score(None, "be_01_jwt_auth")  # type: ignore[arg-type]
        assert "Slice B" in str(exc_info.value)

    def test_aggregate_raises_not_implemented(self, panel: JudgePanel) -> None:
        with pytest.raises(NotImplementedError) as exc_info:
            panel.aggregate([])
        assert "Slice C" in str(exc_info.value)


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
