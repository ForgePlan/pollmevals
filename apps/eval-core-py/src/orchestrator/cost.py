"""Cost attribution layer for POLLMEVALS smoke run.

Per RFC-001 § Cost attribution layer:
- pricing_snapshot fetched ONCE at run start (Invariant #3 — never mid-run update)
- per-eval cost computed via Decimal precision
- cross-check orchestrator total vs LiteLLM proxy /credits; if delta > 10%,
  alert to stderr + take higher of two + continue (per architect finding #8)

POLLMEVALS-specific layer — Inspect AI tracks token counts only (EVID-004 gap).
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

import httpx
from opentelemetry import trace

from src.contracts.eval_row import EvalRow
from src.contracts.pins import PricingSnapshot

logger = logging.getLogger(__name__)

tracer = trace.get_tracer(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OPENROUTER_MODELS_ENDPOINT = "https://openrouter.ai/api/v1/models"
# OpenRouter credits endpoint returns cumulative account usage
OPENROUTER_CREDITS_ENDPOINT = "https://openrouter.ai/api/v1/credits"
# LiteLLM proxy (Wave 1, infra/litellm-config.yaml) spend endpoint
LITELLM_DEFAULT_BASE_URL = "http://localhost:4000"
PRICING_CACHE_TTL_SECONDS = 3600
RECONCILE_DELTA_THRESHOLD = Decimal("0.10")  # 10%

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CostError(Exception):
    """Base class for all cost-attribution errors."""


class PricingFetchError(CostError):
    """HTTP or parse error while fetching pricing data.

    Wraps the underlying exception and carries the model_id context so callers
    can surface which model caused the failure.
    """

    def __init__(self, message: str, model_id: str | None = None) -> None:
        super().__init__(message)
        self.model_id = model_id


class BudgetBreachError(CostError):
    """Raised when cumulative run cost crosses the configured cap.

    Orchestrator catches this to transition the run to *degraded* status and
    stop scheduling new evals.  In-flight evals are allowed to complete
    (AC-3: "in-flight complete").
    """

    def __init__(self, cap_usd: Decimal, running_total: Decimal) -> None:
        super().__init__(f"Budget cap ${cap_usd} breached: running total ${running_total:.4f}")
        self.cap_usd = cap_usd
        self.running_total = running_total


# ---------------------------------------------------------------------------
# PricingTuple — internal immutable value object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PricingTuple:
    """Immutable pricing record for a single model captured at run start.

    OpenRouter /models returns ``pricing.prompt`` and ``pricing.completion`` as
    USD-per-token strings (NOT per-Mtoken).  We multiply by 1_000_000 here so
    downstream code works in the more natural "per-Mtoken" unit, consistent
    with PricingSnapshot in contracts.pins.

    Example (Claude Sonnet at $3/$15 per Mtoken):
        input_per_mtoken_usd  = Decimal("3.000000")
        output_per_mtoken_usd = Decimal("15.000000")
    """

    model_id: str
    input_per_mtoken_usd: Decimal
    output_per_mtoken_usd: Decimal
    snapshot_at: datetime  # must be UTC-aware

    def to_pricing_snapshot(self) -> PricingSnapshot:
        """Convert to the Pydantic PricingSnapshot contract type (contracts.pins)."""
        return PricingSnapshot(
            input_per_mtoken_usd=self.input_per_mtoken_usd,
            output_per_mtoken_usd=self.output_per_mtoken_usd,
            snapshot_at=self.snapshot_at,
        )


# ---------------------------------------------------------------------------
# fetch_pricing_snapshot
# ---------------------------------------------------------------------------


async def fetch_pricing_snapshot(
    model_ids: list[str],
    *,
    base_url: str = OPENROUTER_MODELS_ENDPOINT,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, PricingTuple]:
    """Fetch per-token pricing for the requested model IDs from OpenRouter.

    Returns a dict mapping each matched model_id to a PricingTuple.  Models
    absent from the OpenRouter response are simply not included in the dict —
    the caller is responsible for detecting and handling missing entries.

    Args:
        model_ids: List of OpenRouter model IDs to look up.  OpenRouter IDs
            follow the ``provider/model`` format (e.g.
            ``"anthropic/claude-sonnet-4-6"``).  POLLMEVALS model IDs from
            ADR-003 typically omit the ``openrouter/`` prefix when passed here;
            matching uses ``str.endswith`` so both forms work.
        base_url: OpenRouter /models endpoint.  Overrideable for tests.
        http_client: Injected AsyncClient for unit tests (avoids real network
            calls).  If None, a short-lived client is created and closed inside
            this function.

    Returns:
        Dict[model_id -> PricingTuple] for all matched models.

    Raises:
        PricingFetchError: On any HTTP error or unexpected response shape.
    """
    snapshot_at = datetime.now(tz=UTC)

    own_client = http_client is None
    client = (
        http_client
        if http_client is not None
        else httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
        )
    )

    try:
        try:
            response = await client.get(base_url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise PricingFetchError(f"Failed to fetch pricing from {base_url}: {exc}") from exc

        try:
            payload = response.json()
        except Exception as exc:
            raise PricingFetchError(f"Pricing response is not valid JSON: {exc}") from exc

        # OpenRouter returns {"data": [...]} with each item having
        # {"id": "...", "pricing": {"prompt": "0.000003", "completion": "0.000015"}}
        raw_models: list[dict[str, object]]
        if isinstance(payload, dict) and "data" in payload:
            data = payload["data"]
            if not isinstance(data, list):
                raise PricingFetchError(f"Unexpected 'data' field type: {type(data).__name__}")
            raw_models = [e for e in data if isinstance(e, dict)]
        elif isinstance(payload, list):
            raw_models = [e for e in payload if isinstance(e, dict)]
        else:
            raise PricingFetchError(f"Unexpected pricing response shape: {type(payload).__name__}")

        result: dict[str, PricingTuple] = {}
        for entry in raw_models:
            if not isinstance(entry, dict):
                continue
            entry_id = entry.get("id")
            if not isinstance(entry_id, str):
                continue

            # Match: check if any requested model_id is a suffix of the
            # OpenRouter entry id (handles "anthropic/claude-sonnet-4-6" vs
            # "openrouter/anthropic/claude-sonnet-4-6" prefix variants).
            matched_key: str | None = None
            for req_id in model_ids:
                if entry_id == req_id or entry_id.endswith(req_id) or req_id.endswith(entry_id):
                    matched_key = req_id
                    break
            if matched_key is None:
                continue

            pricing = entry.get("pricing")
            if not isinstance(pricing, dict):
                logger.warning("Model %s has no pricing dict, skipping", entry_id)
                continue

            try:
                # OpenRouter returns USD-per-token as a decimal string.
                # Multiply by 1_000_000 to convert to USD-per-Mtoken.
                prompt_per_token = Decimal(str(pricing.get("prompt", "0")))
                completion_per_token = Decimal(str(pricing.get("completion", "0")))
                input_per_mtoken = prompt_per_token * Decimal("1000000")
                output_per_mtoken = completion_per_token * Decimal("1000000")
            except Exception as exc:
                raise PricingFetchError(
                    f"Cannot parse pricing for model {entry_id}: {exc}",
                    model_id=entry_id,
                ) from exc

            result[matched_key] = PricingTuple(
                model_id=matched_key,
                input_per_mtoken_usd=input_per_mtoken,
                output_per_mtoken_usd=output_per_mtoken,
                snapshot_at=snapshot_at,
            )

        return result

    finally:
        if own_client:
            await client.aclose()


# ---------------------------------------------------------------------------
# compute_cost
# ---------------------------------------------------------------------------


def compute_cost(
    stats: EvalStatsLike,
    pricing: PricingTuple,
) -> Decimal:
    """Compute the USD cost of one eval using Decimal arithmetic.

    Formula (from RFC-001 § Cost attribution layer):
        cost = (input_tokens * input_per_mtoken_usd
                + output_tokens * output_per_mtoken_usd) / 1_000_000

    Args:
        stats: Any object with ``input_tokens: int`` and ``output_tokens: int``
               attributes.  Accepts EvalStats Pydantic model or the EvalStatsLike
               protocol.
        pricing: PricingTuple for the model that produced this eval.

    Returns:
        Decimal rounded to 6 decimal places (e.g. ``Decimal("0.012500")``).
    """
    input_cost = Decimal(stats.input_tokens) * pricing.input_per_mtoken_usd
    output_cost = Decimal(stats.output_tokens) * pricing.output_per_mtoken_usd
    total = (input_cost + output_cost) / Decimal(1_000_000)
    return total.quantize(Decimal("0.000001"))


# ---------------------------------------------------------------------------
# compute_run_total
# ---------------------------------------------------------------------------


def compute_run_total(evals: Iterable[EvalRow]) -> Decimal:
    """Sum cost_usd across all EvalRows in a completed run.

    Failed evals are included in the denominator (FR-009) — they may have
    incurred token costs before failing.

    Args:
        evals: Iterable of EvalRow instances (all statuses).

    Returns:
        Decimal total cost in USD.
    """
    return sum(
        (eval_row.stats.cost_usd for eval_row in evals),
        Decimal(0),
    )


# ---------------------------------------------------------------------------
# CostReconciler
# ---------------------------------------------------------------------------


class CostReconciler:
    """Reconcile orchestrator-computed total against an external cost source.

    Per architect finding #8 (EVID-007) and RFC-001 AC-3 / RR-3:
    - If delta > threshold: alert to stderr + take higher of two + continue.
    - If delta <= threshold: silently return orchestrator_total.
    """

    def __init__(
        self,
        orchestrator_total: Decimal,
        *,
        threshold: Decimal = RECONCILE_DELTA_THRESHOLD,
    ) -> None:
        self._orchestrator_total = orchestrator_total
        self._threshold = threshold

    def reconcile_with_litellm(self, litellm_total: Decimal) -> Decimal:
        """Compare orchestrator total to LiteLLM proxy total.

        Args:
            litellm_total: Cumulative spend reported by the LiteLLM proxy.

        Returns:
            The reconciled total — either orchestrator_total (if within
            threshold) or max(orchestrator_total, litellm_total) (pessimistic,
            if delta exceeds threshold).
        """
        orch = self._orchestrator_total
        litellm = litellm_total

        # Avoid division by zero: use max of both values floored at $0.01
        denominator = max(orch, litellm, Decimal("0.01"))
        delta_pct = abs(orch - litellm) / denominator
        delta_usd = orch - litellm

        span_attrs: dict[str, float] = {
            "pollmevals.cost.expected_usd": float(orch),
            "pollmevals.cost.actual_usd": float(litellm),
            "pollmevals.cost.delta_usd": float(delta_usd),
        }

        with tracer.start_as_current_span("cost.reconcile_litellm", attributes=span_attrs):
            if delta_pct > self._threshold:
                message = (
                    f"⚠️ cost reconcile delta {delta_pct:.1%} > "
                    f"threshold {self._threshold:.0%}: "
                    f"orchestrator={orch}, litellm={litellm}. "
                    f"Taking max (pessimistic).\n"
                )
                sys.stderr.write(message)
                return max(orch, litellm)

            return orch


# ---------------------------------------------------------------------------
# fetch_litellm_credits_total
# ---------------------------------------------------------------------------


async def fetch_litellm_credits_total(
    base_url: str = LITELLM_DEFAULT_BASE_URL,
    http_client: httpx.AsyncClient | None = None,
) -> Decimal:
    """Fetch cumulative spend from the LiteLLM proxy /spend/logs endpoint.

    Graceful degradation per RFC-001 Rollback Plan (§ Cost attribution OFF):
    if the proxy is unavailable, returns Decimal("0") and logs a warning
    rather than raising.  The orchestrator continues; it just lacks cross-check
    data for this polling cycle.

    Args:
        base_url: LiteLLM proxy base URL (default: http://localhost:4000).
        http_client: Injected AsyncClient for unit tests.

    Returns:
        Decimal total spend in USD, or Decimal("0") on any error.
    """
    own_client = http_client is None
    client = (
        http_client
        if http_client is not None
        else httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0))
    )

    try:
        # LiteLLM proxy exposes spend via /spend/logs (or /credits on some
        # versions).  We try /spend/logs first which returns an array of
        # spend log entries with a "total_cost" field per entry.
        # Fallback: /credits which may return {"total": <float>}.
        url = f"{base_url.rstrip('/')}/spend/logs"
        try:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()

            # /spend/logs returns a list of {total_cost: float, ...} entries
            if isinstance(payload, list):
                return sum(
                    (
                        Decimal(str(entry.get("total_cost", 0)))
                        for entry in payload
                        if isinstance(entry, dict)
                    ),
                    Decimal(0),
                )
            # Some LiteLLM versions return {"total": <number>}
            if isinstance(payload, dict):
                total = payload.get("total") or payload.get("total_cost") or 0
                return Decimal(str(total))

            logger.warning("Unexpected LiteLLM /spend/logs response shape: %s", type(payload))
            return Decimal("0")

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                # Endpoint not available on this LiteLLM version — try /credits
                pass
            else:
                raise

        # Fallback: /credits endpoint
        credits_url = f"{base_url.rstrip('/')}/credits"
        response = await client.get(credits_url)
        response.raise_for_status()
        payload = response.json()

        if isinstance(payload, dict):
            total = payload.get("total") or payload.get("total_cost") or 0
            return Decimal(str(total))

        logger.warning("Unexpected LiteLLM /credits response shape: %s", type(payload))
        return Decimal("0")

    except Exception as exc:
        logger.warning(
            "LiteLLM proxy unavailable for cost cross-check (%s: %s). "
            "Returning Decimal('0') — orchestrator continues without cross-check.",
            type(exc).__name__,
            exc,
        )
        return Decimal("0")

    finally:
        if own_client:
            await client.aclose()


# ---------------------------------------------------------------------------
# BudgetGate
# ---------------------------------------------------------------------------


class BudgetGate:
    """Guard that signals whether the orchestrator should schedule more evals.

    Per AC-3: when running total ≥ 80% of cap, stop scheduling new evals;
    in-flight evals are allowed to complete; run transitions to *degraded*.

    The ``abort_at_pct`` threshold is configurable for testing; the RFC
    default is 0.80 (80% of the $50 cap = $40.00).
    """

    def __init__(
        self,
        cap_usd: Decimal,
        *,
        abort_at_pct: Decimal = Decimal("0.80"),
    ) -> None:
        if cap_usd <= Decimal(0):
            raise ValueError(f"cap_usd must be positive, got {cap_usd}")
        if not (Decimal(0) < abort_at_pct <= Decimal(1)):
            raise ValueError(f"abort_at_pct must be in (0, 1], got {abort_at_pct}")
        self._cap = cap_usd
        self._abort_threshold = cap_usd * abort_at_pct

    @property
    def cap_usd(self) -> Decimal:
        """Configured hard budget cap in USD."""
        return self._cap

    @property
    def abort_threshold_usd(self) -> Decimal:
        """Abort threshold in USD (cap * abort_at_pct)."""
        return self._abort_threshold

    def should_continue(self, running_total: Decimal) -> bool:
        """Return True if the orchestrator may schedule additional evals.

        Args:
            running_total: Current cumulative cost in USD.

        Returns:
            True  — running_total < abort_threshold (safe to schedule more).
            False — running_total >= abort_threshold (stop scheduling).
        """
        return running_total < self._abort_threshold


# ---------------------------------------------------------------------------
# EvalStatsLike — structural Protocol for compute_cost (avoids circular import)
# ---------------------------------------------------------------------------


@runtime_checkable
class EvalStatsLike(Protocol):
    """Structural protocol for compute_cost.

    Any object with ``input_tokens: int`` and ``output_tokens: int`` attributes
    satisfies this protocol — both EvalStats Pydantic models and plain
    dataclasses work without needing to inherit from this class.
    """

    input_tokens: int
    output_tokens: int
