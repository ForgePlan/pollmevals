"""Round-trip tests for TaskRequirement and RequirementResult Pydantic models (RFC-004).

Pins the Pydantic models against the JSON Schema in task.schema.json to catch
drift between the Python side and the schema side — mirrors the role that
test_contracts.py plays for the manifest schema.

Coverage:
- TaskRequirement happy path and validation errors.
- RequirementResult happy path and validation errors.
- Schema round-trip: a task.yaml dict with requirements[] validates against
  task.schema.json (jsonschema).
- A task.yaml dict WITHOUT requirements[] also validates (backward compatibility).
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from pydantic import ValidationError

from src.contracts import RequirementResult, TaskRequirement

# Path to the task JSON Schema (resolved relative to this test file).
_REPO_ROOT = Path(__file__).parents[3]
_TASK_SCHEMA_PATH = _REPO_ROOT / "packages" / "contracts" / "schemas" / "task.schema.json"


# ---------------------------------------------------------------------------
# TaskRequirement
# ---------------------------------------------------------------------------


class TestTaskRequirement:
    def test_happy_path_auto(self) -> None:
        req = TaskRequirement(
            id="R7",
            text="Returns 401 when Authorization header is absent",
            check_type="auto",
            maps_to="correctness",
            prompt_ref=1,
        )
        assert req.id == "R7"
        assert req.check_type == "auto"
        assert req.maps_to == "correctness"
        assert req.prompt_ref == 1

    def test_happy_path_judge(self) -> None:
        req = TaskRequirement(
            id="R27",
            text="Functions are short and single-purpose",
            check_type="judge",
            maps_to="code_clarity",
            prompt_ref=3,
        )
        assert req.check_type == "judge"

    def test_id_pattern_enforced(self) -> None:
        with pytest.raises(ValidationError, match="pattern"):
            TaskRequirement(
                id="REQ-7",  # invalid: must match ^R[0-9]+$
                text="t",
                check_type="auto",
                maps_to="correctness",
                prompt_ref=1,
            )

    def test_id_lowercase_r_invalid(self) -> None:
        with pytest.raises(ValidationError):
            TaskRequirement(
                id="r1",  # lowercase r invalid
                text="t",
                check_type="auto",
                maps_to="correctness",
                prompt_ref=1,
            )

    def test_id_r_followed_by_non_digits_invalid(self) -> None:
        with pytest.raises(ValidationError):
            TaskRequirement(
                id="Rabc",
                text="t",
                check_type="auto",
                maps_to="correctness",
                prompt_ref=1,
            )

    def test_text_empty_string_raises(self) -> None:
        with pytest.raises(ValidationError):
            TaskRequirement(
                id="R1",
                text="",  # minLength=1 violated
                check_type="auto",
                maps_to="correctness",
                prompt_ref=1,
            )

    def test_check_type_invalid_value_raises(self) -> None:
        with pytest.raises(ValidationError):
            TaskRequirement(
                id="R1",
                text="t",
                check_type="manual",  # type: ignore[arg-type]  # not in enum
                maps_to="correctness",
                prompt_ref=1,
            )

    def test_prompt_ref_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            TaskRequirement(
                id="R1",
                text="t",
                check_type="auto",
                maps_to="correctness",
                prompt_ref=0,  # minimum=1 violated
            )

    def test_prompt_ref_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            TaskRequirement(
                id="R1",
                text="t",
                check_type="auto",
                maps_to="correctness",
                prompt_ref=-1,
            )

    def test_extra_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            TaskRequirement(
                id="R1",
                text="t",
                check_type="auto",
                maps_to="correctness",
                prompt_ref=1,
                unexpected="field",  # type: ignore[call-arg]
            )

    def test_frozen_raises_on_mutation(self) -> None:
        req = TaskRequirement(
            id="R1", text="t", check_type="auto", maps_to="correctness", prompt_ref=1
        )
        with pytest.raises(ValidationError):
            req.id = "R2"  # frozen raises at runtime

    def test_id_r_followed_by_multidigit_valid(self) -> None:
        req = TaskRequirement(
            id="R27",
            text="t",
            check_type="auto",
            maps_to="correctness",
            prompt_ref=1,
        )
        assert req.id == "R27"


# ---------------------------------------------------------------------------
# RequirementResult
# ---------------------------------------------------------------------------


class TestRequirementResult:
    def test_happy_path_auto_passed(self) -> None:
        result = RequirementResult(id="R1", check_type="auto", passed=True)
        assert result.passed is True

    def test_happy_path_auto_failed(self) -> None:
        result = RequirementResult(id="R2", check_type="auto", passed=False)
        assert result.passed is False

    def test_happy_path_judge_recorded_only(self) -> None:
        result = RequirementResult(id="R27", check_type="judge", passed=None)
        assert result.passed is None

    def test_check_type_invalid_value_raises(self) -> None:
        with pytest.raises(ValidationError):
            RequirementResult(id="R1", check_type="manual", passed=True)  # type: ignore[arg-type]

    def test_extra_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            RequirementResult(
                id="R1",
                check_type="auto",
                passed=True,
                sneaky="field",  # type: ignore[call-arg]
            )

    def test_frozen_raises_on_mutation(self) -> None:
        result = RequirementResult(id="R1", check_type="auto", passed=True)
        with pytest.raises(ValidationError):
            result.passed = False  # frozen raises at runtime

    def test_json_roundtrip_auto(self) -> None:
        result = RequirementResult(id="R1", check_type="auto", passed=True)
        dumped = result.model_dump_json()
        restored = RequirementResult.model_validate_json(dumped)
        assert restored == result

    def test_json_roundtrip_judge_none(self) -> None:
        result = RequirementResult(id="R27", check_type="judge", passed=None)
        dumped = result.model_dump_json()
        restored = RequirementResult.model_validate_json(dumped)
        assert restored.passed is None


# ---------------------------------------------------------------------------
# JSON Schema round-trips via task.schema.json
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def task_schema() -> dict:  # type: ignore[type-arg]
    assert _TASK_SCHEMA_PATH.exists(), f"task.schema.json not found at {_TASK_SCHEMA_PATH}"
    with open(_TASK_SCHEMA_PATH) as f:
        return json.load(f)  # type: ignore[no-any-return]


def _minimal_task_dict(with_requirements: bool = False) -> dict:  # type: ignore[type-arg]
    """Build a minimal valid task dict for schema validation."""
    base = {
        "schema_version": "pollmevals.task.v1",
        "id": "be_01",
        "slug": "jwt-auth",
        "version": "1.0",
        "category": "backend",
        "difficulty": "medium",
        "language": "typescript",
        "description": "A task description.",
        "prompt_template": "Do something.\n  1. Requirement one.\n",
        "success_criteria": ["All tests pass."],
        "weight_components": {"correctness": 0.5, "lint": 0.5},
    }
    if with_requirements:
        base["requirements"] = [
            {
                "id": "R1",
                "text": "Returns 401 when Authorization header is absent",
                "check_type": "auto",
                "maps_to": "correctness",
                "prompt_ref": 1,
            },
            {
                "id": "R2",
                "text": "Uses dependency injection for store",
                "check_type": "judge",
                "maps_to": "code_clarity",
                "prompt_ref": 1,
            },
        ]
    return base


class TestTaskSchemaRoundTrip:
    def test_task_without_requirements_validates(self, task_schema: dict) -> None:
        """Backward compatibility: old task packs without requirements[] must pass."""
        data = _minimal_task_dict(with_requirements=False)
        jsonschema.validate(data, task_schema)  # must not raise

    def test_task_with_requirements_validates(self, task_schema: dict) -> None:
        """New task packs with requirements[] must pass schema validation."""
        data = _minimal_task_dict(with_requirements=True)
        jsonschema.validate(data, task_schema)  # must not raise

    def test_requirement_with_invalid_id_pattern_fails(self, task_schema: dict) -> None:
        """A requirement with id not matching ^R[0-9]+$ must fail schema validation."""
        data = _minimal_task_dict(with_requirements=True)
        data["requirements"][0]["id"] = "REQ-1"  # invalid pattern
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, task_schema)

    def test_requirement_missing_required_field_fails(self, task_schema: dict) -> None:
        """A requirement missing 'text' must fail schema validation."""
        data = _minimal_task_dict(with_requirements=True)
        del data["requirements"][0]["text"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, task_schema)

    def test_requirement_with_extra_field_fails(self, task_schema: dict) -> None:
        """A requirement with an additional property must fail (additionalProperties: false)."""
        data = _minimal_task_dict(with_requirements=True)
        data["requirements"][0]["unexpected_field"] = "bad"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, task_schema)

    def test_requirement_check_type_invalid_fails(self, task_schema: dict) -> None:
        """check_type not in ['auto', 'judge'] must fail."""
        data = _minimal_task_dict(with_requirements=True)
        data["requirements"][0]["check_type"] = "manual"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, task_schema)

    def test_requirement_prompt_ref_zero_fails(self, task_schema: dict) -> None:
        """prompt_ref must be >= 1; zero must fail."""
        data = _minimal_task_dict(with_requirements=True)
        data["requirements"][0]["prompt_ref"] = 0
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, task_schema)

    def test_requirement_empty_text_fails(self, task_schema: dict) -> None:
        """text with minLength=1 must reject empty string."""
        data = _minimal_task_dict(with_requirements=True)
        data["requirements"][0]["text"] = ""
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, task_schema)
