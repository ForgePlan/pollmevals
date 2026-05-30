"""Pydantic v2 models for the POLLMEVALS task contract (RFC-004, lock-step with task.schema.json).

These models mirror the TypeScript types in packages/contracts/src/types.ts.
SPEC-001 reconciliation rule: when task.schema.json changes, this file changes
in the same commit. Drift between the two is caught by the round-trip tests in
tests/test_task_contracts.py.

Modules:
  TaskRequirement   — one atomic binary requirement item in task.requirements[].
  RequirementResult — one entry in evaluator_json.requirement_results[].
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TaskRequirement(BaseModel):
    """One atomic binary requirement in a task's requirements[] list (RFC-004).

    check_type "auto"  — executable check whose pass/fail feeds the deterministic
                         component score: 10 * (passed auto-reqs) / (total auto-reqs)
                         for the component named in maps_to.
    check_type "judge" — recorded in evaluator_json for traceability only (v0.2);
                         never wired to a score in v0.2.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(
        pattern=r"^R[0-9]+$",
        description="Unique requirement id within the task. Example: 'R7'.",
    )
    text: str = Field(
        min_length=1,
        description=("One atomic, binary assertion phrased so it is unambiguously true or false."),
    )
    check_type: Literal["auto", "judge"]
    maps_to: str = Field(
        description=(
            "For auto: a weight_components key (e.g. 'correctness', 'type_safety'). "
            "For judge: a rubric criterion name (e.g. 'code_clarity', 'pattern_match')."
        ),
    )
    prompt_ref: int = Field(
        ge=1,
        description=(
            "1-based index of the numbered item in prompt_template this requirement traces to."
        ),
    )


class RequirementResult(BaseModel):
    """One entry in evaluator_json.requirement_results[] (RFC-004).

    Emitted by the deterministic evaluator for every requirement in the task.
    auto items carry a boolean pass/fail; judge items carry None (recorded-only
    in v0.2, never scored).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(description="Requirement id, matching TaskRequirement.id.")
    check_type: Literal["auto", "judge"]
    passed: bool | None = Field(
        description=(
            "True/False for auto items (wired to executable check result). "
            "None for judge items (recorded for traceability, not scored in v0.2)."
        ),
    )
