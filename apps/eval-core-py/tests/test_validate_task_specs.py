"""Unit tests for the RFC-004 requirements[] validation rules.

Covers the five MUST rules and the SHOULD-6 warning in
``infra/scripts/validate-task-specs.py::_validate_requirements`` — the
rejection paths that were previously unexercised (EVID-034 finding #2,
EVID-035 concern). Includes the regression for finding #1 (MUST-4
empty-numbered-items silent-pass defect).

The validator is a standalone script with a hyphenated filename, so it is
loaded by path via importlib rather than imported as a module.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

# ---------------------------------------------------------------------------
# Load the hyphenated validator script as a module.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[3]
_VALIDATOR_PATH = _REPO_ROOT / "infra" / "scripts" / "validate-task-specs.py"


def _load_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("validate_task_specs", _VALIDATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vts = _load_validator()


# ---------------------------------------------------------------------------
# Fixtures / builders
# ---------------------------------------------------------------------------
_DEFAULT_WEIGHTS = {
    "correctness": 0.40,
    "test_coverage": 0.15,
    "complexity": 0.10,
    "linter": 0.10,
    "type_safety": 0.10,
    "pattern_match": 0.15,
}


def _req(
    id_: str,
    *,
    check_type: str = "auto",
    maps_to: str = "correctness",
    prompt_ref: int = 1,
    text: str = "an atomic binary assertion",
) -> dict[str, object]:
    return {
        "id": id_,
        "text": text,
        "check_type": check_type,
        "maps_to": maps_to,
        "prompt_ref": prompt_ref,
    }


def _task(
    requirements: list[dict[str, object]],
    *,
    category: str = "backend",
    prompt_template: str = "Hard requirements:\n  1. First.\n  2. Second.\n",
    weights: dict[str, float] | None = None,
) -> dict[str, object]:
    return {
        "category": category,
        "prompt_template": prompt_template,
        "weight_components": _DEFAULT_WEIGHTS if weights is None else weights,
        "requirements": requirements,
    }


def _has(messages: list[str], token: str) -> bool:
    return any(token in m for m in messages)


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------


def test_old_pack_without_requirements_skips(tmp_path: Path) -> None:
    """A task with no requirements[] field skips all RFC-004 rules (old packs)."""
    ok, msgs = vts._validate_requirements({"category": "backend"}, tmp_path, "x")
    assert ok is True
    assert msgs == []


# ---------------------------------------------------------------------------
# MUST-1 — unique ids
# ---------------------------------------------------------------------------


def test_must1_duplicate_ids_rejected(tmp_path: Path) -> None:
    ok, msgs = vts._validate_requirements(_task([_req("R1"), _req("R1")]), tmp_path, "x")
    assert ok is False
    assert _has(msgs, "MUST-1")


# ---------------------------------------------------------------------------
# MUST-2 / MUST-3 — maps_to allowed set + judge-only guard (one message each)
# ---------------------------------------------------------------------------


def test_must2_maps_to_outside_category_rejected(tmp_path: Path) -> None:
    ok, msgs = vts._validate_requirements(
        _task([_req("R1", maps_to="not_a_real_component")]), tmp_path, "x"
    )
    assert ok is False
    assert _has(msgs, "MUST-2")


def test_must3_auto_mapped_to_judge_only_rejected(tmp_path: Path) -> None:
    ok, msgs = vts._validate_requirements(
        _task([_req("R1", maps_to="pattern_match")]), tmp_path, "x"
    )
    assert ok is False
    assert _has(msgs, "MUST-3")
    # De-dup (finding #3): a judge-only target must NOT also fire MUST-2.
    assert not _has(msgs, "MUST-2")


# ---------------------------------------------------------------------------
# MUST-4 — prompt_ref resolution (incl. the finding #1 regression)
# ---------------------------------------------------------------------------


def test_must4_unresolvable_prompt_ref_rejected(tmp_path: Path) -> None:
    ok, msgs = vts._validate_requirements(_task([_req("R1", prompt_ref=99)]), tmp_path, "x")
    assert ok is False
    assert _has(msgs, "MUST-4")


def test_must4_empty_numbered_items_regression(tmp_path: Path) -> None:
    """Finding #1: a prompt_template with NO numbered list must NOT silently pass.

    Before the fix, ``and numbered_items`` short-circuited on an empty set and
    every prompt_ref slipped through.
    """
    data = _task([_req("R1", prompt_ref=1)], prompt_template="Do the thing. No numbered list here.")
    ok, msgs = vts._validate_requirements(data, tmp_path, "x")
    assert ok is False
    assert _has(msgs, "MUST-4")


def test_must4_resolvable_prompt_ref_passes(tmp_path: Path) -> None:
    _ok, msgs = vts._validate_requirements(_task([_req("R1", prompt_ref=2)]), tmp_path, "x")
    assert not _has(msgs, "MUST-4")


# ---------------------------------------------------------------------------
# MUST-5 — Σ weight_components == 1.0 (±1e-6)
# ---------------------------------------------------------------------------


def test_must5_weights_not_summing_to_one_rejected(tmp_path: Path) -> None:
    ok, msgs = vts._validate_requirements(
        _task([_req("R1")], weights={"correctness": 0.5, "type_safety": 0.4}), tmp_path, "x"
    )
    assert ok is False
    assert _has(msgs, "MUST-5")


def test_must5_weights_summing_to_one_within_tolerance_passes(tmp_path: Path) -> None:
    weights = {"correctness": 0.3333333, "type_safety": 0.3333333, "linter": 0.3333334}
    _ok, msgs = vts._validate_requirements(_task([_req("R1")], weights=weights), tmp_path, "x")
    assert not _has(msgs, "MUST-5")


# ---------------------------------------------------------------------------
# SHOULD-6 — count warning does not block
# ---------------------------------------------------------------------------


def test_should6_few_requirements_warns_but_valid(tmp_path: Path) -> None:
    ok, msgs = vts._validate_requirements(_task([_req("R1")]), tmp_path, "x")
    assert ok is True  # SHOULD warnings never block
    assert _has(msgs, "SHOULD-6")


# ---------------------------------------------------------------------------
# Happy path — a full, valid requirement set produces no messages
# ---------------------------------------------------------------------------


def test_valid_full_requirement_set_passes_clean(tmp_path: Path) -> None:
    reqs = [_req(f"R{i}", prompt_ref=(1 if i % 2 else 2)) for i in range(1, 21)]
    ok, msgs = vts._validate_requirements(_task(reqs), tmp_path, "x")
    assert ok is True
    assert msgs == []  # 20 items meets SHOULD-6; no test files in tmp_path -> SHOULD-7 skipped


# ---------------------------------------------------------------------------
# Helper — numbered-item parsing
# ---------------------------------------------------------------------------


def test_parse_prompt_numbered_items() -> None:
    items = vts._parse_prompt_numbered_items("intro\n1. a\n  2. b\n3. c\nnot numbered")
    assert items == {1, 2, 3}


def test_parse_prompt_numbered_items_empty_when_no_list() -> None:
    assert vts._parse_prompt_numbered_items("prose only, no numbered items") == set()
