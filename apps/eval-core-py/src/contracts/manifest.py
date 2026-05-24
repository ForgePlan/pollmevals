"""Pydantic v2 model for the canonical POLLMEVALS Run Manifest.

The Manifest is the root document that records everything about a Run:
which stacks/models/tasks participated, all eval results, aggregates, and
the current lifecycle status.

Immutability contract (ADR-0002):
  Once status reaches 'published' or 'degraded', no field may be mutated.
  frozen=True ensures this at the Python layer. To "update" a manifest,
  use .model_copy(update={...}) — this produces a new instance, leaving
  the original untouched.

Schema version: pollmevals.run_manifest.v1.0.0 (rich schema, 2026-05-23).
Methodology version: v0.1.0 (frozen in docs/02-methodology/).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .aggregates import RunAggregates
from .eval_row import EvalRow
from .pins import ModelPin, StackPin, TaskPin

# ---------------------------------------------------------------------------
# Version constants — single source of truth in code
# ---------------------------------------------------------------------------

SCHEMA_VERSION_V1_0_0: Literal["pollmevals.run_manifest.v1.0.0"] = "pollmevals.run_manifest.v1.0.0"
METHODOLOGY_VERSION_V0_1_0: Literal["v0.1.0"] = "v0.1.0"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RunType(StrEnum):
    """Categories of POLLMEVALS runs."""

    SMOKE = "smoke"
    WEEKLY = "weekly"
    FLAGSHIP_TRIGGERED = "flagship_triggered"
    CALIBRATION = "calibration"
    ABLATION = "ablation"


class RunStatus(StrEnum):
    """Run lifecycle states.

    State machine (terminal states have no outgoing edges):
      created → executing → evaluating → aggregating → published
                                                     ↘ degraded
    published and degraded are terminal (ADR-0002).
    """

    CREATED = "created"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    AGGREGATING = "aggregating"
    PUBLISHED = "published"
    DEGRADED = "degraded"


class Region(StrEnum):
    """Execution region for a Run.

    Python enum member names use snake_case to satisfy identifier rules;
    the string *values* match the JSON schema enum ("eu-central").
    """

    EU_CENTRAL = "eu-central"


# ---------------------------------------------------------------------------
# State machine adjacency table
# ---------------------------------------------------------------------------

_ALLOWED_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.CREATED: frozenset({RunStatus.EXECUTING}),
    RunStatus.EXECUTING: frozenset({RunStatus.EVALUATING}),
    RunStatus.EVALUATING: frozenset({RunStatus.AGGREGATING}),
    RunStatus.AGGREGATING: frozenset({RunStatus.PUBLISHED, RunStatus.DEGRADED}),
    RunStatus.PUBLISHED: frozenset(),
    RunStatus.DEGRADED: frozenset(),
}

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

_RunHash = Annotated[str, Field(pattern=r"^sha256:[a-f0-9]{64}$")]
_Sha256OrNone = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


class Manifest(BaseModel):
    """Root document for one POLLMEVALS Run.

    All fields mirror the JSON schema run-manifest.schema.json v1.0.0 exactly
    (snake_case field names match JSON object keys — no alias needed because
    the schema also uses snake_case).

    Transition helpers:
        can_transition_to(new_status)  — check before producing a new manifest
        is_terminal()                  — True for published/degraded

    To change status (never mutate in place — ADR-0002):
        next_manifest = manifest.model_copy(update={"status": RunStatus.EXECUTING})
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["pollmevals.run_manifest.v1.0.0"]
    run_hash: _RunHash
    run_type: RunType
    methodology_version: Literal["v0.1.0"]
    created_at: datetime
    published_at: datetime | None = None
    region: Region = Region.EU_CENTRAL
    stack_pins: list[StackPin] = Field(min_length=1)
    model_pins: list[ModelPin] = Field(min_length=1)
    task_pins: list[TaskPin] = Field(min_length=1)
    seed_set: list[int] = Field(min_length=1)
    evals: list[EvalRow]
    aggregates: RunAggregates
    status: RunStatus
    inspect_eval_log_sha256: _Sha256OrNone | None = None
    inspect_ai_version: str | None = None
    orchestrator_version: str | None = None

    def can_transition_to(self, new_status: RunStatus) -> bool:
        """Return True if the current status allows a transition to new_status.

        This is a pure query — it does not mutate the manifest. To actually
        apply the transition, use .model_copy(update={"status": new_status}).
        """
        return new_status in _ALLOWED_TRANSITIONS[self.status]

    def is_terminal(self) -> bool:
        """Return True if this manifest has reached a terminal status.

        Terminal statuses (published, degraded) have no allowed transitions.
        Once terminal, the manifest record is write-once (ADR-0002).
        """
        return not _ALLOWED_TRANSITIONS[self.status]
