"""POLLMEVALS run manifest contracts (Pydantic v2, run-manifest.schema.json v1.0.0).

Public API — import from here, not from sub-modules:

    from contracts import Manifest, RunStatus, EvalRow, ArtifactRef, ...
    from contracts import TaskRequirement, RequirementResult  # RFC-004
"""

from .aggregates import CountsByStatus, RunAggregates
from .artifact_ref import ArtifactRef
from .eval_row import ErrorClass, EvalArtifactRefs, EvalRow, EvalStats, EvalStatus
from .judge import CalibrationResult, JudgeAggregation, JudgeCalibration, Judgment, ProbeResult
from .manifest import (
    METHODOLOGY_VERSION_V0_1_0,
    SCHEMA_VERSION_V1_0_0,
    Manifest,
    Region,
    RunStatus,
    RunType,
)
from .pins import ModelPin, PricingSnapshot, StackPin, TaskPin
from .task import RequirementResult, TaskRequirement

__all__ = [
    "METHODOLOGY_VERSION_V0_1_0",
    "SCHEMA_VERSION_V1_0_0",
    "ArtifactRef",
    "CalibrationResult",
    "CountsByStatus",
    "ErrorClass",
    "EvalArtifactRefs",
    "EvalRow",
    "EvalStats",
    "EvalStatus",
    "JudgeAggregation",
    "JudgeCalibration",
    "Judgment",
    "Manifest",
    "ModelPin",
    "PricingSnapshot",
    "ProbeResult",
    "Region",
    "RequirementResult",
    "RunAggregates",
    "RunStatus",
    "RunType",
    "StackPin",
    "TaskPin",
    "TaskRequirement",
]
