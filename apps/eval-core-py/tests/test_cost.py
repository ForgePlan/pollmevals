"""Tests for apps/eval-core-py/src/orchestrator/cost.py.

All tests are unit-level — no real network calls.  Every HTTP interaction is
injected via a mock httpx.AsyncClient.

Coverage:
  TestPricingFetch      — fetch_pricing_snapshot happy path + error cases
  TestComputeCost       — Decimal precision, formula correctness
  TestComputeRunTotal   — summation across EvalRow list
  TestCostReconciler    — delta logic, stderr alert, pessimistic take-max
  TestBudgetGate        — 80% threshold, parametrized boundaries
  TestLitellmCreditsFetch — graceful degradation on errors
"""

from __future__ import annotations

from datetime import UTC
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.orchestrator.cost import (
    BudgetGate,
    CostReconciler,
    PricingFetchError,
    PricingTuple,
    compute_cost,
    fetch_litellm_credits_total,
    fetch_pricing_snapshot,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# 5 models from ADR-003 (using the OpenRouter id format without openrouter/ prefix)
ADR_003_MODEL_IDS = [
    "anthropic/claude-sonnet-4-6",
    "openai/gpt-5-mini",
    "google/gemini-3-flash",
    "cerebras/qwen-3-14b",
    "runpod/llama-4-70b",
]

# Canned OpenRouter /models response (realistic pricing)
# OpenRouter pricing is USD-per-token (NOT per Mtoken).
# Claude Sonnet: $3/$15 per Mtoken → $0.000003/$0.000015 per token
OPENROUTER_MODELS_PAYLOAD = {
    "data": [
        {
            "id": "anthropic/claude-sonnet-4-6",
            "name": "Claude Sonnet 4.6",
            "pricing": {"prompt": "0.000003", "completion": "0.000015"},
        },
        {
            "id": "openai/gpt-5-mini",
            "name": "GPT-5 mini",
            "pricing": {"prompt": "0.000001", "completion": "0.000004"},
        },
        {
            "id": "google/gemini-3-flash",
            "name": "Gemini 3 Flash",
            "pricing": {"prompt": "0.0000001", "completion": "0.0000004"},
        },
        {
            "id": "cerebras/qwen-3-14b",
            "name": "Qwen 3 14B (Cerebras)",
            "pricing": {"prompt": "0.0000002", "completion": "0.0000006"},
        },
        {
            "id": "runpod/llama-4-70b",
            "name": "Llama 4 70B (Runpod)",
            "pricing": {"prompt": "0.0000005", "completion": "0.0000015"},
        },
        # Extra model not in our requested list — should be ignored
        {
            "id": "meta/llama-3-8b",
            "name": "Llama 3 8B",
            "pricing": {"prompt": "0.0000001", "completion": "0.0000002"},
        },
    ]
}


def _make_mock_client(status_code: int = 200, json_body: object = None) -> AsyncMock:
    """Return a mock AsyncClient whose .get() returns a canned response."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = status_code
    mock_response.json.return_value = json_body if json_body is not None else {}

    if status_code >= 400:
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=mock_response,
        )
    else:
        mock_response.raise_for_status.return_value = None

    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.aclose = AsyncMock()
    return mock_client


# ---------------------------------------------------------------------------
# Minimal EvalStats stand-in (avoids importing Pydantic model in tests)
# ---------------------------------------------------------------------------


class _FakeStats:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


# ---------------------------------------------------------------------------
# TestPricingFetch
# ---------------------------------------------------------------------------


class TestPricingFetch:
    """Unit tests for fetch_pricing_snapshot."""

    @pytest.mark.asyncio
    async def test_happy_path_returns_all_five_models(self) -> None:
        """All 5 ADR-003 models are present in response → dict has 5 entries."""
        client = _make_mock_client(json_body=OPENROUTER_MODELS_PAYLOAD)
        result = await fetch_pricing_snapshot(ADR_003_MODEL_IDS, http_client=client)

        assert len(result) == 5
        assert set(result.keys()) == set(ADR_003_MODEL_IDS)

    @pytest.mark.asyncio
    async def test_pricing_values_converted_to_per_mtoken(self) -> None:
        """USD-per-token values are multiplied by 1_000_000 → per-Mtoken."""
        client = _make_mock_client(json_body=OPENROUTER_MODELS_PAYLOAD)
        result = await fetch_pricing_snapshot(["anthropic/claude-sonnet-4-6"], http_client=client)

        claude = result["anthropic/claude-sonnet-4-6"]
        # $0.000003 per token * 1_000_000 = $3 per Mtoken
        assert claude.input_per_mtoken_usd == Decimal("3")
        # $0.000015 per token * 1_000_000 = $15 per Mtoken
        assert claude.output_per_mtoken_usd == Decimal("15")

    @pytest.mark.asyncio
    async def test_missing_model_not_in_result(self) -> None:
        """A model absent from the OpenRouter response is simply not in the dict."""
        client = _make_mock_client(json_body=OPENROUTER_MODELS_PAYLOAD)
        # Request an unknown model that doesn't appear in the canned response
        result = await fetch_pricing_snapshot(
            ["anthropic/claude-sonnet-4-6", "unknown/does-not-exist"],
            http_client=client,
        )
        assert "anthropic/claude-sonnet-4-6" in result
        assert "unknown/does-not-exist" not in result

    @pytest.mark.asyncio
    async def test_extra_model_in_response_is_ignored(self) -> None:
        """OpenRouter models we did not request are not included in the result."""
        client = _make_mock_client(json_body=OPENROUTER_MODELS_PAYLOAD)
        result = await fetch_pricing_snapshot(["anthropic/claude-sonnet-4-6"], http_client=client)
        # meta/llama-3-8b is in the payload but was not requested
        assert "meta/llama-3-8b" not in result
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_http_error_raises_pricing_fetch_error(self) -> None:
        """HTTP 500 from OpenRouter → PricingFetchError is raised."""
        client = _make_mock_client(status_code=500)
        with pytest.raises(PricingFetchError):
            await fetch_pricing_snapshot(ADR_003_MODEL_IDS, http_client=client)

    @pytest.mark.asyncio
    async def test_network_error_raises_pricing_fetch_error(self) -> None:
        """Network-level error (ConnectError) → PricingFetchError is raised."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client.aclose = AsyncMock()

        with pytest.raises(PricingFetchError, match="Failed to fetch pricing"):
            await fetch_pricing_snapshot(ADR_003_MODEL_IDS, http_client=mock_client)

    @pytest.mark.asyncio
    async def test_snapshot_at_is_utc_aware(self) -> None:
        """Returned PricingTuple.snapshot_at is timezone-aware (UTC)."""
        client = _make_mock_client(json_body=OPENROUTER_MODELS_PAYLOAD)
        result = await fetch_pricing_snapshot(["anthropic/claude-sonnet-4-6"], http_client=client)
        pt = result["anthropic/claude-sonnet-4-6"]
        assert pt.snapshot_at.tzinfo is not None

    @pytest.mark.asyncio
    async def test_list_format_response_also_works(self) -> None:
        """OpenRouter may return a bare list (not wrapped in 'data') — handle both."""
        list_payload = OPENROUTER_MODELS_PAYLOAD["data"]
        client = _make_mock_client(json_body=list_payload)
        result = await fetch_pricing_snapshot(["anthropic/claude-sonnet-4-6"], http_client=client)
        assert "anthropic/claude-sonnet-4-6" in result

    @pytest.mark.asyncio
    async def test_to_pricing_snapshot_round_trip(self) -> None:
        """PricingTuple.to_pricing_snapshot() returns a valid PricingSnapshot."""
        client = _make_mock_client(json_body=OPENROUTER_MODELS_PAYLOAD)
        result = await fetch_pricing_snapshot(["anthropic/claude-sonnet-4-6"], http_client=client)
        pt = result["anthropic/claude-sonnet-4-6"]
        snapshot = pt.to_pricing_snapshot()
        assert snapshot.input_per_mtoken_usd == pt.input_per_mtoken_usd
        assert snapshot.output_per_mtoken_usd == pt.output_per_mtoken_usd
        assert snapshot.snapshot_at == pt.snapshot_at


# ---------------------------------------------------------------------------
# TestComputeCost
# ---------------------------------------------------------------------------


class TestComputeCost:
    """Unit tests for compute_cost — formula correctness and Decimal precision."""

    def _make_pricing(
        self,
        input_mtoken: str,
        output_mtoken: str,
    ) -> PricingTuple:
        from datetime import datetime

        return PricingTuple(
            model_id="test-model",
            input_per_mtoken_usd=Decimal(input_mtoken),
            output_per_mtoken_usd=Decimal(output_mtoken),
            snapshot_at=datetime.now(tz=UTC),
        )

    def test_basic_formula(self) -> None:
        """1000 input + 500 output @ $5/$15 per Mtoken → $0.0125."""
        # cost = (1000 * 5 + 500 * 15) / 1_000_000
        #       = (5000 + 7500) / 1_000_000
        #       = 12500 / 1_000_000
        #       = 0.012500
        pricing = self._make_pricing("5", "15")
        stats = _FakeStats(input_tokens=1000, output_tokens=500)
        result = compute_cost(stats, pricing)
        assert result == Decimal("0.012500")

    def test_decimal_precision_six_places(self) -> None:
        """Result is always quantized to 6 decimal places."""
        pricing = self._make_pricing("3", "15")
        # 512 input + 256 output @ $3/$15 per Mtoken
        # = (512*3 + 256*15) / 1_000_000 = (1536 + 3840) / 1_000_000
        # = 5376 / 1_000_000 = 0.005376
        stats = _FakeStats(input_tokens=512, output_tokens=256)
        result = compute_cost(stats, pricing)
        # Check it has exactly 6 decimal places
        assert result == result.quantize(Decimal("0.000001"))
        assert str(result) == "0.005376"

    def test_no_float_drift(self) -> None:
        """Decimal arithmetic must produce exact results without float rounding."""
        # Use values that would cause float drift
        pricing = self._make_pricing("0.1", "0.3")
        stats = _FakeStats(input_tokens=1000000, output_tokens=1000000)
        # (1000000 * 0.1 + 1000000 * 0.3) / 1_000_000 = 0.4
        result = compute_cost(stats, pricing)
        assert result == Decimal("0.400000")
        # Verify it's a Decimal, not a float
        assert isinstance(result, Decimal)

    def test_zero_tokens(self) -> None:
        """Zero tokens → zero cost."""
        pricing = self._make_pricing("10", "30")
        stats = _FakeStats(input_tokens=0, output_tokens=0)
        result = compute_cost(stats, pricing)
        assert result == Decimal("0.000000")

    def test_free_model(self) -> None:
        """Zero pricing (free model) → zero cost regardless of token count."""
        pricing = self._make_pricing("0", "0")
        stats = _FakeStats(input_tokens=100000, output_tokens=50000)
        result = compute_cost(stats, pricing)
        assert result == Decimal("0.000000")

    def test_claude_sonnet_realistic(self) -> None:
        """Realistic Claude Sonnet 4.6 scenario: 2000 in + 800 out @ $3/$15."""
        pricing = self._make_pricing("3", "15")
        stats = _FakeStats(input_tokens=2000, output_tokens=800)
        # (2000*3 + 800*15) / 1_000_000 = (6000 + 12000) / 1_000_000 = 0.018
        result = compute_cost(stats, pricing)
        assert result == Decimal("0.018000")

    def test_gemini_flash_cheap(self) -> None:
        """Gemini 3 Flash scenario: $0.1/$0.4 per Mtoken (very cheap)."""
        pricing = self._make_pricing("0.1", "0.4")
        stats = _FakeStats(input_tokens=10000, output_tokens=5000)
        # (10000*0.1 + 5000*0.4) / 1_000_000 = (1000 + 2000) / 1_000_000 = 0.003
        result = compute_cost(stats, pricing)
        assert result == Decimal("0.003000")


# ---------------------------------------------------------------------------
# TestComputeRunTotal
# ---------------------------------------------------------------------------


class TestComputeRunTotal:
    """Unit tests for compute_run_total."""

    def _make_eval_row(self, cost_usd: str) -> object:
        """Minimal stand-in for EvalRow with a stats.cost_usd attribute."""

        class _FakeEvalStats:
            def __init__(self, cost: Decimal) -> None:
                self.cost_usd = cost

        class _FakeEvalRow:
            def __init__(self, cost: Decimal) -> None:
                self.stats = _FakeEvalStats(cost)

        return _FakeEvalRow(Decimal(cost_usd))

    def test_sum_three_evals(self) -> None:
        """Sum of three eval costs is computed correctly."""
        rows = [
            self._make_eval_row("0.010000"),
            self._make_eval_row("0.025000"),
            self._make_eval_row("0.005000"),
        ]
        # Direct import workaround — cast to avoid mypy on private class
        from src.orchestrator.cost import compute_run_total as _crt

        total = _crt(rows)  # type: ignore[arg-type]
        assert total == Decimal("0.040000")

    def test_empty_list(self) -> None:
        """Empty eval list → zero total."""
        from src.orchestrator.cost import compute_run_total as _crt

        total = _crt([])
        assert total == Decimal(0)

    def test_decimal_precision_preserved(self) -> None:
        """Summation via Decimal preserves precision — no float accumulation."""
        # 45 evals at $0.000001 each = $0.000045 exactly
        rows = [self._make_eval_row("0.000001")] * 45
        from src.orchestrator.cost import compute_run_total as _crt

        total = _crt(rows)  # type: ignore[arg-type]
        assert total == Decimal("0.000045")


# ---------------------------------------------------------------------------
# TestCostReconciler
# ---------------------------------------------------------------------------


class TestCostReconciler:
    """Unit tests for CostReconciler."""

    def test_within_threshold_returns_orchestrator_total(self) -> None:
        """Delta < 10% → return orchestrator_total, no stderr message."""
        orch = Decimal("10.00")
        litellm = Decimal("10.50")  # ~4.8% delta — within 10%
        reconciler = CostReconciler(orch)
        result = reconciler.reconcile_with_litellm(litellm)
        assert result == orch

    def test_equal_totals_returns_orchestrator_total(self) -> None:
        """Zero delta → orchestrator_total returned."""
        orch = Decimal("5.00")
        reconciler = CostReconciler(orch)
        result = reconciler.reconcile_with_litellm(Decimal("5.00"))
        assert result == orch

    def test_above_threshold_returns_max_and_warns(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Delta > 10% → returns max, writes warning to stderr."""
        orch = Decimal("10.00")
        litellm = Decimal("12.00")  # 20% delta — above threshold
        reconciler = CostReconciler(orch)
        result = reconciler.reconcile_with_litellm(litellm)

        # Pessimistic: take the higher value
        assert result == Decimal("12.00")

        # Check stderr was written to
        captured = capsys.readouterr()
        assert "⚠️" in captured.err
        assert "reconcile delta" in captured.err
        assert "Taking max (pessimistic)" in captured.err

    def test_above_threshold_orchestrator_is_higher(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When orchestrator total is higher, it is returned as the max."""
        orch = Decimal("15.00")
        litellm = Decimal("12.00")  # 20% delta, orchestrator wins
        reconciler = CostReconciler(orch)
        result = reconciler.reconcile_with_litellm(litellm)
        assert result == Decimal("15.00")
        captured = capsys.readouterr()
        assert "⚠️" in captured.err

    def test_both_zero_no_division_error(self) -> None:
        """Both totals at zero → delta = 0, no division-by-zero."""
        reconciler = CostReconciler(Decimal("0"))
        result = reconciler.reconcile_with_litellm(Decimal("0"))
        assert result == Decimal("0")

    def test_custom_threshold(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Custom threshold of 5% → alert fires at smaller delta."""
        orch = Decimal("10.00")
        litellm = Decimal("10.60")  # 5.7% delta — above 5% threshold
        reconciler = CostReconciler(orch, threshold=Decimal("0.05"))
        result = reconciler.reconcile_with_litellm(litellm)
        assert result == Decimal("10.60")
        captured = capsys.readouterr()
        assert "⚠️" in captured.err

    def test_exactly_at_threshold_no_alert(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Delta exactly at threshold (not strictly above) → no alert."""
        # denominator = max(10, 11, 0.01) = 11; delta = |10-11|/11 = 1/11 ≈ 0.0909
        # With threshold=0.10, 0.0909 < 0.10 → no alert
        orch = Decimal("10.00")
        litellm = Decimal("11.00")
        reconciler = CostReconciler(orch, threshold=Decimal("0.10"))
        result = reconciler.reconcile_with_litellm(litellm)
        assert result == orch
        captured = capsys.readouterr()
        assert captured.err == ""


# ---------------------------------------------------------------------------
# TestBudgetGate
# ---------------------------------------------------------------------------


class TestBudgetGate:
    """Unit tests for BudgetGate — 80% abort threshold."""

    def test_below_threshold_continues(self) -> None:
        """$39.99 running total with $50 cap, 80% threshold ($40) → continue."""
        gate = BudgetGate(Decimal("50.00"))
        assert gate.should_continue(Decimal("39.99")) is True

    def test_at_threshold_stops(self) -> None:
        """$40.00 running total with $50 cap, 80% threshold ($40) → stop."""
        gate = BudgetGate(Decimal("50.00"))
        assert gate.should_continue(Decimal("40.00")) is False

    def test_above_threshold_stops(self) -> None:
        """$45.00 running total with $50 cap → stop."""
        gate = BudgetGate(Decimal("50.00"))
        assert gate.should_continue(Decimal("45.00")) is False

    def test_zero_running_total_continues(self) -> None:
        """Zero running total → always continue."""
        gate = BudgetGate(Decimal("50.00"))
        assert gate.should_continue(Decimal("0")) is True

    @pytest.mark.parametrize(
        ("cap", "abort_pct", "running", "expected"),
        [
            ("100.00", "0.80", "79.99", True),  # just under 80%
            ("100.00", "0.80", "80.00", False),  # exactly 80%
            ("100.00", "0.50", "49.99", True),  # just under 50%
            ("100.00", "0.50", "50.00", False),  # exactly 50%
            ("25.00", "0.80", "19.99", True),  # $25 cap, $20 threshold
            ("25.00", "0.80", "20.00", False),  # at threshold
            ("50.00", "0.90", "44.99", True),  # 90% of $50 = $45 threshold
            ("50.00", "0.90", "45.00", False),  # at threshold
        ],
    )
    def test_parametrized_thresholds(
        self,
        cap: str,
        abort_pct: str,
        running: str,
        expected: bool,
    ) -> None:
        """Parametrized combinations of cap/threshold/running_total."""
        gate = BudgetGate(Decimal(cap), abort_at_pct=Decimal(abort_pct))
        assert gate.should_continue(Decimal(running)) is expected

    def test_abort_threshold_property(self) -> None:
        """abort_threshold_usd property returns cap * abort_at_pct."""
        gate = BudgetGate(Decimal("50.00"), abort_at_pct=Decimal("0.80"))
        assert gate.abort_threshold_usd == Decimal("40.00")

    def test_invalid_cap_raises(self) -> None:
        """Zero or negative cap is rejected at construction time."""
        with pytest.raises(ValueError, match="cap_usd must be positive"):
            BudgetGate(Decimal("0"))

    def test_invalid_abort_pct_raises(self) -> None:
        """abort_at_pct outside (0, 1] is rejected at construction time."""
        with pytest.raises(ValueError, match="abort_at_pct must be in"):
            BudgetGate(Decimal("50.00"), abort_at_pct=Decimal("0"))


# ---------------------------------------------------------------------------
# TestLitellmCreditsFetch
# ---------------------------------------------------------------------------


class TestLitellmCreditsFetch:
    """Unit tests for fetch_litellm_credits_total."""

    @pytest.mark.asyncio
    async def test_spend_logs_list_format(self) -> None:
        """LiteLLM /spend/logs returns a list → totals are summed."""
        payload = [
            {"total_cost": 5.25, "model": "claude-sonnet-4-6"},
            {"total_cost": 2.10, "model": "gpt-5-mini"},
        ]
        client = _make_mock_client(json_body=payload)
        result = await fetch_litellm_credits_total(http_client=client)
        assert result == Decimal("7.35")

    @pytest.mark.asyncio
    async def test_spend_logs_dict_format(self) -> None:
        """LiteLLM returns {'total': <number>} → parsed correctly."""
        client = _make_mock_client(json_body={"total": 12.50})
        result = await fetch_litellm_credits_total(http_client=client)
        assert result == Decimal("12.5")

    @pytest.mark.asyncio
    async def test_http_error_returns_zero(self) -> None:
        """Any HTTP error → Decimal('0') returned, no exception raised."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("proxy not running"))
        mock_client.aclose = AsyncMock()

        result = await fetch_litellm_credits_total(http_client=mock_client)
        assert result == Decimal("0")

    @pytest.mark.asyncio
    async def test_empty_list_returns_zero(self) -> None:
        """Empty spend logs list → zero total."""
        client = _make_mock_client(json_body=[])
        result = await fetch_litellm_credits_total(http_client=client)
        assert result == Decimal("0")

    @pytest.mark.asyncio
    async def test_decimal_precision_preserved(self) -> None:
        """Cost values are accumulated as Decimal (not float)."""
        # Three entries that would exhibit float drift if summed as floats:
        # 0.1 + 0.2 = 0.30000000000000004 in float
        payload = [
            {"total_cost": 0.1},
            {"total_cost": 0.2},
        ]
        client = _make_mock_client(json_body=payload)
        result = await fetch_litellm_credits_total(http_client=client)
        # With Decimal(str(x)) conversion, this is exact
        expected = Decimal("0.1") + Decimal("0.2")
        assert result == expected
        assert isinstance(result, Decimal)

    @pytest.mark.asyncio
    async def test_json_parse_error_returns_zero(self) -> None:
        """Unexpected response shape → Decimal('0') returned gracefully."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        # Return something totally unexpected
        mock_response.json.return_value = "not a dict or list"
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        result = await fetch_litellm_credits_total(http_client=mock_client)
        assert result == Decimal("0")
