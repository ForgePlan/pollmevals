#!/usr/bin/env python3
"""validate-task-specs.py — POLLMEVALS task-spec validator.

Walks ``evals/task-packs/*/task.yaml`` and validates each file against
``packages/contracts/schemas/task.schema.json``.

History
-------
Originally imported ``pollmevals_eval_core.registry.load_task_specs`` which
does not exist in the repository (orphan import, GitHub issue #1). Rewritten
in this commit to use pure stdlib + pyyaml + jsonschema, removing the phantom
dependency entirely.

RFC-004 (Slice 1) extended this script with requirements[] validation rules:
  MUST rules (hard errors — block the pack):
    1. Unique requirement ids.
    2. maps_to ∈ allowed component set for the task category.
    3. auto requirements must map to a deterministic component (not a judge criterion).
    4. prompt_ref must resolve to a real numbered item in prompt_template.
    5. Σ weight_components == 1.0 (tolerance ±1e-6).

  SHOULD rules (warnings — do not block):
    6. ≥ 20 requirement items per task (target for atomic coverage).
    7. For tasks with a gold/tests.spec.* file, warn when auto-requirement count
       ≠ hidden-test count (the 1:1 binding; full enforcement is the Evaluator
       Wiring Agent's job at run-wire time, not static validation).
       Also parses ``it("[R3] …")`` / ``test("[R3] …")`` tags from vitest test
       files to check requirement-id coverage.

Usage
-----
Run from the repo root::

    python infra/scripts/validate-task-specs.py           # validate all
    python infra/scripts/validate-task-specs.py --task be_01_jwt_auth

Via uv (no local install needed)::

    uv run --with pyyaml --with jsonschema \\
        python infra/scripts/validate-task-specs.py

Install deps explicitly::

    pip install pyyaml jsonschema
    # or:  uv pip install pyyaml jsonschema

Exit codes
----------
0  All validated task specs are valid.
1  At least one spec failed validation (or no specs were found).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# Dependency guard — give an actionable error before any other import fails.
# ---------------------------------------------------------------------------
try:
    import yaml
except ImportError:  # pragma: no cover
    print(
        "ERROR: pyyaml is not installed.\n"
        "  pip install pyyaml jsonschema\n"
        "  OR: uv run --with pyyaml --with jsonschema "
        "python infra/scripts/validate-task-specs.py",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    from jsonschema import ValidationError, validate
except ImportError:  # pragma: no cover
    print(
        "ERROR: jsonschema is not installed.\n"
        "  pip install pyyaml jsonschema\n"
        "  OR: uv run --with pyyaml --with jsonschema "
        "python infra/scripts/validate-task-specs.py",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths (resolved relative to THIS file so the script is CWD-agnostic).
# ---------------------------------------------------------------------------
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
_SCHEMA_PATH: Final[Path] = _REPO_ROOT / "packages" / "contracts" / "schemas" / "task.schema.json"
_TASK_PACKS_ROOT: Final[Path] = _REPO_ROOT / "evals" / "task-packs"

# ---------------------------------------------------------------------------
# RFC-004: allowed maps_to sets per category.
#
# auto requirements must map to a DETERMINISTIC weight_components key for the
# category (i.e. a component derived from executable checks, not judge medians).
# judge requirements map to rubric criterion names (not constrained here since
# rubric.yaml is not read; we only check that an auto req doesn't map to a
# judge-only criterion).
#
# JUDGE-ONLY criteria — auto requirements must NOT map to these names.
# These are the criteria that only the judge panel can score; they have no
# executable backing test.
# ---------------------------------------------------------------------------
_JUDGE_ONLY_CRITERIA: Final[frozenset[str]] = frozenset(
    {
        "pattern_match",
        "code_clarity",
        "test_alignment",
        "structural_completeness",
        "factual_accuracy",
        "clarity",
        "actionability",
        "consistency",
    }
)

# Deterministic (executable / auto-sourced) components per category.
# Maps category string → set of valid maps_to values for check_type="auto".
# NOTE: "security" is currently a PROPOSAL (RFC-004 §Security-component proposal)
# and is NOT included in the allowed set; security requirements map to
# "correctness" until the proposal is formally adopted.
_AUTO_ALLOWED: Final[dict[str, frozenset[str]]] = {
    "backend": frozenset({"correctness", "test_coverage", "complexity", "linter", "type_safety"}),
    "frontend": frozenset(
        {"correctness", "accessibility", "test_coverage", "type_safety", "ux_states"}
    ),
    # docs: no auto requirements are valid (all doc requirements are judge-only).
    # An empty set causes any auto requirement to fail the maps_to check.
    "docs": frozenset(),
}

# Tolerance for Σ weight_components = 1.0 check.
_WEIGHT_SUM_TOLERANCE: Final[float] = 1e-6

# Minimum requirement count (SHOULD warning threshold).
_MIN_REQUIREMENTS_WARN: Final[int] = 20

# Regex to parse numbered items from prompt_template.
# Matches lines like "  1. ...", "  2. ...", "1. ...", etc.
_NUMBERED_ITEM_RE: Final[re.Pattern[str]] = re.compile(r"^\s*(\d+)\.\s")

# Regex to parse [Rn] tags from vitest/pytest test names.
# Matches patterns like: it("[R3] some title", ...) or test("[R3] ...", ...)
_REQUIREMENT_TAG_RE: Final[re.Pattern[str]] = re.compile(r"\[R(\d+)\]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_prompt_numbered_items(prompt_template: str) -> set[int]:
    """Return the set of 1-based numbered item indices found in *prompt_template*.

    Looks for lines matching the pattern ``N. <text>`` (possibly indented) under
    a "Hard requirements" section or anywhere in the template, so we can validate
    that prompt_ref integers point to real items.
    """
    indices: set[int] = set()
    for line in prompt_template.splitlines():
        m = _NUMBERED_ITEM_RE.match(line)
        if m:
            indices.add(int(m.group(1)))
    return indices


def _parse_test_requirement_tags(test_file: Path) -> set[str]:
    """Parse requirement ids tagged in vitest test titles using the ``[Rn]`` convention.

    Scans the test file for patterns like ``it("[R3] …")`` / ``test("[R3] …")``
    and returns the set of requirement ids found (e.g. {"R3", "R12"}).
    """
    try:
        content = test_file.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"WARNING: could not read test file {test_file}: {exc}", file=sys.stderr)
        return set()
    matches = _REQUIREMENT_TAG_RE.findall(content)
    return {f"R{n}" for n in matches}


# ---------------------------------------------------------------------------
# RFC-004 requirements rules (called from validate_one after schema check)
# ---------------------------------------------------------------------------


def _check_unique_ids(reqs: list[dict[str, object]], rel: str) -> list[str]:
    """MUST-1 — requirement ids must be unique within a task."""
    seen: set[str] = set()
    duplicates: list[str] = []
    for req in reqs:
        rid = str(req.get("id", ""))
        if rid in seen:
            duplicates.append(rid)
        seen.add(rid)
    if duplicates:
        return [f"  ✗ {rel}: [MUST-1] duplicate requirement ids: {sorted(set(duplicates))}"]
    return []


def _check_maps_to(reqs: list[dict[str, object]], category: str, rel: str) -> list[str]:
    """MUST-2 / MUST-3 — auto requirements map to an allowed deterministic component.

    One message per offending requirement: MUST-3 is the specific judge-only case,
    MUST-2 the generic out-of-allowed-set case.
    """
    auto_allowed = _AUTO_ALLOWED.get(category, frozenset())
    errors: list[str] = []
    for req in reqs:
        if req.get("check_type") != "auto":
            continue
        maps_to = str(req.get("maps_to", ""))
        if maps_to in _JUDGE_ONLY_CRITERIA:
            errors.append(
                f"  ✗ {rel}: [MUST-3] requirement {req.get('id')!r}: "
                f"check_type='auto' cannot map to judge-only criterion {maps_to!r}. "
                f"Change check_type to 'judge' or change maps_to to a deterministic component."
            )
        elif maps_to not in auto_allowed:
            errors.append(
                f"  ✗ {rel}: [MUST-2] requirement {req.get('id')!r}: "
                f"maps_to={maps_to!r} is not in the allowed auto set for "
                f"category {category!r}: {sorted(auto_allowed)}"
            )
    return errors


def _check_prompt_refs(reqs: list[dict[str, object]], prompt_template: str, rel: str) -> list[str]:
    """MUST-4 — every prompt_ref resolves to a numbered item in prompt_template.

    A declared prompt_ref against a template with NO numbered items is an error
    (guards the empty-set silent-pass defect), not a silent pass.
    """
    numbered_items = _parse_prompt_numbered_items(prompt_template)
    errors: list[str] = []
    for req in reqs:
        prompt_ref = req.get("prompt_ref")
        if not isinstance(prompt_ref, int):
            continue
        if not numbered_items:
            errors.append(
                f"  ✗ {rel}: [MUST-4] requirement {req.get('id')!r}: "
                f"prompt_ref={prompt_ref} declared but prompt_template has no numbered "
                f"items (expected a 'N. ...' list to reference)."
            )
        elif prompt_ref not in numbered_items:
            errors.append(
                f"  ✗ {rel}: [MUST-4] requirement {req.get('id')!r}: "
                f"prompt_ref={prompt_ref} does not match any numbered item in prompt_template "
                f"(found items: {sorted(numbered_items)})"
            )
    return errors


def _check_weight_sum(weight_components: dict[str, object], rel: str) -> list[str]:
    """MUST-5 — Σ weight_components == 1.0 (tolerance ±1e-6)."""
    if not weight_components:
        return []
    weight_values = [v for v in weight_components.values() if isinstance(v, (int, float))]
    if not weight_values:
        return []
    weight_sum = sum(weight_values)
    if abs(weight_sum - 1.0) > _WEIGHT_SUM_TOLERANCE:
        return [
            f"  ✗ {rel}: [MUST-5] Σ weight_components = {weight_sum:.8f} "
            f"(expected 1.0 ± {_WEIGHT_SUM_TOLERANCE}). "
            f"Weights: {dict(weight_components)}"
        ]
    return []


def _check_should_warnings(
    reqs: list[dict[str, object]], task_pack_dir: Path, rel: str
) -> list[str]:
    """SHOULD-6 (atomic-item count) + SHOULD-7 (auto-req ↔ test-tag 1:1 coverage)."""
    warnings: list[str] = []

    total_reqs = len(reqs)
    if total_reqs < _MIN_REQUIREMENTS_WARN:
        warnings.append(
            f"  ⚠ {rel}: [SHOULD-6] only {total_reqs} requirement items "
            f"(target ≥ {_MIN_REQUIREMENTS_WARN}). "
            f"Consider adding more atomic items for better auditing."
        )

    auto_ids = {str(r.get("id", "")) for r in reqs if r.get("check_type") == "auto"}
    if not auto_ids:
        return warnings

    test_files = list(task_pack_dir.glob("gold/tests.spec.*"))
    test_files.extend(task_pack_dir.glob("gold/tests_*.py"))
    test_files.extend(task_pack_dir.glob("gold/test_*.py"))
    if not test_files:
        return warnings

    tagged_ids: set[str] = set()
    for tf in test_files:
        tagged_ids.update(_parse_test_requirement_tags(tf))

    if not tagged_ids:
        warnings.append(
            f"  ⚠ {rel}: [SHOULD-7] {len(auto_ids)} auto requirements defined "
            f"but no [Rn] tags found in {[str(tf.name) for tf in test_files]}. "
            f"Tag each test title with its requirement id."
        )
        return warnings

    untagged = auto_ids - tagged_ids
    unmatched = tagged_ids - auto_ids
    if untagged:
        warnings.append(
            f"  ⚠ {rel}: [SHOULD-7] auto requirements with no matching "
            f"test tag [Rn]: {sorted(untagged)}"
        )
    if unmatched:
        warnings.append(
            f"  ⚠ {rel}: [SHOULD-7] test tags [Rn] with no matching "
            f"auto requirement: {sorted(unmatched)}"
        )
    return warnings


def _validate_requirements(
    data: dict[str, object],
    task_pack_dir: Path,
    rel: str,
) -> tuple[bool, list[str]]:
    """Validate the RFC-004 requirements[] rules for a single task.

    Returns ``(is_valid, messages)``. ``is_valid`` is False if any MUST rule was
    violated; SHOULD warnings are included in ``messages`` but do not affect it.
    A task with no ``requirements`` field (old pack) skips every rule.
    """
    requirements = data.get("requirements")
    if requirements is None:
        return True, []
    if not isinstance(requirements, list):
        return False, [f"  ✗ {rel}: requirements must be a list"]

    # Schema already validated item shapes; keep only dict items defensively.
    reqs: list[dict[str, object]] = [r for r in requirements if isinstance(r, dict)]
    category = str(data.get("category", "")).lower()
    weight_components_raw = data.get("weight_components", {})
    weight_components: dict[str, object] = (
        weight_components_raw if isinstance(weight_components_raw, dict) else {}
    )
    prompt_template = str(data.get("prompt_template", ""))

    errors: list[str] = []
    errors += _check_unique_ids(reqs, rel)
    errors += _check_maps_to(reqs, category, rel)
    errors += _check_prompt_refs(reqs, prompt_template, rel)
    errors += _check_weight_sum(weight_components, rel)
    warnings = _check_should_warnings(reqs, task_pack_dir, rel)

    return len(errors) == 0, errors + warnings


# ---------------------------------------------------------------------------
# Core validate_one
# ---------------------------------------------------------------------------


def _load_schema() -> dict[str, object]:
    """Load and parse the task JSON Schema from disk."""
    if not _SCHEMA_PATH.exists():
        print(f"ERROR: schema not found: {_SCHEMA_PATH}", file=sys.stderr)
        sys.exit(1)
    with _SCHEMA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)  # type: ignore[no-any-return]


def validate_one(task_yaml: Path, schema: dict[str, object]) -> bool:
    """Validate a single task.yaml file against *schema* and RFC-004 rules.

    Prints a ``✓`` or ``✗`` line to stdout.

    Parameters
    ----------
    task_yaml:
        Absolute path to the task.yaml file.
    schema:
        Pre-loaded JSON Schema dict.

    Returns
    -------
    bool
        ``True`` when the spec is valid, ``False`` otherwise.
    """
    rel: str = str(task_yaml.relative_to(_REPO_ROOT))

    try:
        with task_yaml.open(encoding="utf-8") as fh:
            data: object = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        print(f"  ✗ {rel}: YAML parse error — {exc}")
        return False

    if not isinstance(data, dict):
        print(f"  ✗ {rel}: expected a YAML mapping, got {type(data).__name__}")
        return False

    try:
        validate(instance=data, schema=schema)
    except ValidationError as exc:
        path_str: str = " → ".join(str(p) for p in exc.absolute_path) or "(root)"
        print(f"  ✗ {rel}: {path_str} — {exc.message}")
        return False

    # RFC-004 requirements[] validation (only when present; old packs unaffected).
    task_pack_dir = task_yaml.parent
    req_valid, req_messages = _validate_requirements(data, task_pack_dir, rel)
    for msg in req_messages:
        print(msg)

    if req_valid:
        print(f"  ✓ {rel}")
    return req_valid


def validate_all(schema: dict[str, object] | None = None) -> tuple[int, int]:
    """Validate every ``task.yaml`` found under ``evals/task-packs/``.

    Parameters
    ----------
    schema:
        Pre-loaded schema dict.  Loaded from disk if ``None``.

    Returns
    -------
    tuple[int, int]
        ``(passed, total)`` counts.
    """
    if schema is None:
        schema = _load_schema()

    task_files: list[Path] = sorted(_TASK_PACKS_ROOT.glob("*/task.yaml"))
    if not task_files:
        print(f"WARNING: no task.yaml files found under {_TASK_PACKS_ROOT}", file=sys.stderr)
        return 0, 0

    passed: int = 0
    for tf in task_files:
        if validate_one(tf, schema):
            passed += 1

    return passed, len(task_files)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate POLLMEVALS task-spec YAML files against the task JSON Schema.",
        epilog=("Example: python infra/scripts/validate-task-specs.py --task be_01_jwt_auth"),
    )
    parser.add_argument(
        "--task",
        metavar="SLUG",
        default=None,
        help=(
            "Validate a single task pack by its directory name under evals/task-packs/. "
            "Omit to validate all task packs."
        ),
    )
    return parser


def main() -> None:
    """Entry point."""
    parser = _build_parser()
    args = parser.parse_args()

    schema = _load_schema()

    if args.task is not None:
        task_yaml = _TASK_PACKS_ROOT / args.task / "task.yaml"
        if not task_yaml.exists():
            print(
                f"ERROR: {task_yaml} not found.\n"
                f"  Available task packs: "
                + ", ".join(p.name for p in sorted(_TASK_PACKS_ROOT.iterdir()) if p.is_dir()),
                file=sys.stderr,
            )
            sys.exit(1)
        ok = validate_one(task_yaml, schema)
        print(f"\n{'1/1' if ok else '0/1'} task spec valid")
        sys.exit(0 if ok else 1)

    passed, total = validate_all(schema)
    print(f"\n{passed}/{total} task specs valid")
    sys.exit(0 if passed == total and total > 0 else 1)


if __name__ == "__main__":
    main()
