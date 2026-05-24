"""Tests for RFC-002 Slice A + B: JudgePanel skeleton, self-judging guard, score().

Coverage:
  - _normalise_model_family: all routing patterns from EVID-023 + RFC-002
  - _guard_self_judging: exact-ID, cross-route variant, different families
  - JudgePanel.__init__: validates guard wiring, empty judge list, successful construction
  - JudgePanel.score(): Slice B — Inspect AI list-of-scorers wiring (mocked)
  - JudgePanel.aggregate(): still raises NotImplementedError (Slice C stub)
  - Judgment / JudgeAggregation: pydantic field validation
"""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from src.contracts import JudgeAggregation, Judgment
from src.orchestrator.judge_panel import JudgePanel, SelfJudgingError, _normalise_model_family

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


def _make_fake_score(value: str, explanation: str = "test explanation") -> MagicMock:
    """Build a mock Inspect AI Score object."""
    score = MagicMock()
    score.value = value
    score.explanation = explanation
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
# Slice C stub — aggregate() still raises NotImplementedError (Slice B only)
# ---------------------------------------------------------------------------


class TestSliceCStub:
    """Verifies that aggregate() is still a Slice C stub."""

    @pytest.fixture
    def panel(self) -> JudgePanel:
        return JudgePanel(
            judge_models=["openrouter/openai/gpt-5-mini"],
            candidate_model_id="openrouter/anthropic/claude-haiku",
            rubric_version="1.0",
        )

    def test_aggregate_raises_not_implemented(self, panel: JudgePanel) -> None:
        with pytest.raises(NotImplementedError) as exc_info:
            panel.aggregate([])
        assert "Slice C" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Slice B — score() implementation tests
# ---------------------------------------------------------------------------


class TestJudgePanelScoreSliceB:
    """Tests for JudgePanel.score() — RFC-002 Slice B.

    All tests mock _run_judge_task, _read_raw_output, and _make_judge_models
    so no real LLM calls and no OPENAI_API_KEY are required.

    Verifies:
      - correct scorer list construction (one per judge)
      - max_tokens cap passes through to get_model config at init time
      - 2 judges → 2 Judgment objects with distinct judge_model_id
      - score "C" → rubric_scores["overall"] = 10.0 (1.0 * 10)
      - score "I" → rubric_scores["overall"] = 0.0
      - judge_order is set per shuffled position
    """

    @pytest.fixture(autouse=True)
    def mock_make_judge_models(self) -> object:
        """Prevent real Inspect AI model construction (requires OPENAI_API_KEY).

        _make_judge_models is lazily called inside score() to build scorer
        objects. We replace it with a method that returns dummy MagicMock
        objects of the right length — the scorer list is only used to build
        model_graded_qa instances, which themselves are mocked out via
        _run_judge_task.
        """

        def _fake_make_judge_models(self_panel: JudgePanel) -> list[MagicMock]:
            return [MagicMock(name=f"mock_model_{i}") for i in range(len(self_panel._judge_models))]

        with patch.object(JudgePanel, "_make_judge_models", _fake_make_judge_models):
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
                "model_graded_qa": _make_fake_score("C", "Judge 1 says correct"),
                "model_graded_qa_1": _make_fake_score("C", "Judge 2 says correct"),
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
        """Score value 'C' → rubric_scores['overall'] = 10.0, total_score = 10.0."""
        eval_result = _make_fake_eval_result()
        fake_log = _make_fake_eval_log(
            {
                "model_graded_qa": _make_fake_score("C", "Correct"),
                "model_graded_qa_1": _make_fake_score("C", "Also correct"),
            }
        )

        mock_run = AsyncMock(return_value=[fake_log])
        with (
            patch.object(two_judge_panel, "_run_judge_task", new=mock_run),
            patch.object(two_judge_panel, "_read_raw_output", return_value="output"),
        ):
            judgments = await two_judge_panel.score(eval_result, "be_01_jwt_auth")  # type: ignore[arg-type]

        for j in judgments:
            assert j.rubric_scores["overall"] == 10.0
            assert j.total_score == 10.0

    @pytest.mark.asyncio
    async def test_score_i_maps_to_0(self, two_judge_panel: JudgePanel) -> None:
        """Score value 'I' → rubric_scores['overall'] = 0.0, total_score = 0.0."""
        eval_result = _make_fake_eval_result()
        fake_log = _make_fake_eval_log(
            {
                "model_graded_qa": _make_fake_score("I", "Incorrect"),
                "model_graded_qa_1": _make_fake_score("I", "Also incorrect"),
            }
        )

        mock_run = AsyncMock(return_value=[fake_log])
        with (
            patch.object(two_judge_panel, "_run_judge_task", new=mock_run),
            patch.object(two_judge_panel, "_read_raw_output", return_value="output"),
        ):
            judgments = await two_judge_panel.score(eval_result, "be_01_jwt_auth")  # type: ignore[arg-type]

        for j in judgments:
            assert j.rubric_scores["overall"] == 0.0
            assert j.total_score == 0.0

    @pytest.mark.asyncio
    async def test_judge_order_assigned(self, two_judge_panel: JudgePanel) -> None:
        """Each Judgment carries a non-negative judge_order (0-indexed position)."""
        eval_result = _make_fake_eval_result()
        fake_log = _make_fake_eval_log(
            {
                "model_graded_qa": _make_fake_score("C"),
                "model_graded_qa_1": _make_fake_score("I"),
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
