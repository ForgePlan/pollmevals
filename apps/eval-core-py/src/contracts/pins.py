"""Pydantic v2 models for run-start pinning (stack, model, task).

These are immutable snapshots frozen at run creation — they record exactly
what participated in a Run so results are reproducible. Once a Run is
created, pins are write-once (ADR-0002).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Shared type aliases
# ---------------------------------------------------------------------------

_Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


# ---------------------------------------------------------------------------
# PricingSnapshot
# ---------------------------------------------------------------------------


class PricingSnapshot(BaseModel):
    """Pricing frozen at run start.

    Uses Decimal (not float) to avoid rounding errors when summing thousands
    of evals. Closes the industry gap flagged in EVID-001 and EVID-005.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    input_per_mtoken_usd: Decimal = Field(ge=Decimal(0))
    output_per_mtoken_usd: Decimal = Field(ge=Decimal(0))
    snapshot_at: datetime = Field(
        description="UTC datetime when price was captured. Must be timezone-aware."
    )

    def model_post_init(self, __context: object) -> None:
        if self.snapshot_at.tzinfo is None:
            raise ValueError("snapshot_at must be timezone-aware (UTC)")


# ---------------------------------------------------------------------------
# StackPin
# ---------------------------------------------------------------------------


class StackPin(BaseModel):
    """One stack participating in a Run, pinned at creation.

    stack_yaml_sha256 is the content hash of the adapter YAML file; any
    change to the stack config creates a new hash and therefore a new pin.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    stack_id: str
    stack_version: str
    stack_yaml_sha256: _Sha256


# ---------------------------------------------------------------------------
# ModelPin
# ---------------------------------------------------------------------------


class ModelPin(BaseModel):
    """One model + provider combination participating in a Run.

    provider_id matches the Inspect AI model-string prefix
    (anthropic / openai / google / openrouter / hosted_vllm / ollama).
    provider_route_id is the full route string used at invocation time
    (e.g. "openrouter/anthropic/claude-sonnet-4-6").
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: str
    provider_id: str
    provider_route_id: str
    pricing_snapshot: PricingSnapshot


# ---------------------------------------------------------------------------
# TaskPin
# ---------------------------------------------------------------------------


class TaskPin(BaseModel):
    """One task participating in a Run, pinned at creation.

    task_pack_sha256 is sha256(prompt.md + evaluator script + gold/).
    POLLMEVALS uses content-addressing rather than integer versioning
    (diverges from lm-eval-harness) so a task is immutable once published.
    See EVID-003.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str
    task_version: str
    task_pack_sha256: _Sha256
