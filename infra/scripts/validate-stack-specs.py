#!/usr/bin/env python3
"""validate-stack-specs.py — POLLMEVALS stack-adapter spec validator.

Walks ``stacks/*/stack.yaml`` and validates each file against
``packages/contracts/schemas/stack.schema.json``.

Implements GitHub issue #2: add a stack-spec validator mirroring the
task-spec validator in structure and UX.

Usage
-----
Run from the repo root::

    python infra/scripts/validate-stack-specs.py           # validate all
    python infra/scripts/validate-stack-specs.py --stack raw-llm

Via uv (no local install needed)::

    uv run --with pyyaml --with jsonschema \\
        python infra/scripts/validate-stack-specs.py

Install deps explicitly::

    pip install pyyaml jsonschema
    # or:  uv pip install pyyaml jsonschema

Exit codes
----------
0  All validated stack specs are valid.
1  At least one spec failed validation (or no specs were found).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# Dependency guard — give an actionable error before any other import fails.
# ---------------------------------------------------------------------------
try:
    import yaml  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    print(
        "ERROR: pyyaml is not installed.\n"
        "  pip install pyyaml jsonschema\n"
        "  OR: uv run --with pyyaml --with jsonschema "
        "python infra/scripts/validate-stack-specs.py",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    from jsonschema import ValidationError, validate  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    print(
        "ERROR: jsonschema is not installed.\n"
        "  pip install pyyaml jsonschema\n"
        "  OR: uv run --with pyyaml --with jsonschema "
        "python infra/scripts/validate-stack-specs.py",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths (resolved relative to THIS file so the script is CWD-agnostic).
# ---------------------------------------------------------------------------
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
_SCHEMA_PATH: Final[Path] = _REPO_ROOT / "packages" / "contracts" / "schemas" / "stack.schema.json"
_STACKS_ROOT: Final[Path] = _REPO_ROOT / "stacks"


def _load_schema() -> dict[str, object]:
    """Load and parse the stack JSON Schema from disk."""
    if not _SCHEMA_PATH.exists():
        print(f"ERROR: schema not found: {_SCHEMA_PATH}", file=sys.stderr)
        sys.exit(1)
    with _SCHEMA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)  # type: ignore[no-any-return]


def validate_one(stack_yaml: Path, schema: dict[str, object]) -> bool:
    """Validate a single stack.yaml file against *schema*.

    Prints a ``✓`` or ``✗`` line to stdout.

    Parameters
    ----------
    stack_yaml:
        Absolute path to the stack.yaml file.
    schema:
        Pre-loaded JSON Schema dict.

    Returns
    -------
    bool
        ``True`` when the spec is valid, ``False`` otherwise.
    """
    rel: str = str(stack_yaml.relative_to(_REPO_ROOT))

    try:
        with stack_yaml.open(encoding="utf-8") as fh:
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

    print(f"  ✓ {rel}")
    return True


def validate_all(schema: dict[str, object] | None = None) -> tuple[int, int]:
    """Validate every ``stack.yaml`` found under ``stacks/``.

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

    stack_files: list[Path] = sorted(_STACKS_ROOT.glob("*/stack.yaml"))
    if not stack_files:
        print(f"WARNING: no stack.yaml files found under {_STACKS_ROOT}", file=sys.stderr)
        return 0, 0

    passed: int = 0
    for sf in stack_files:
        if validate_one(sf, schema):
            passed += 1

    return passed, len(stack_files)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate POLLMEVALS stack-adapter YAML files against the stack JSON Schema.",
        epilog=("Example: python infra/scripts/validate-stack-specs.py --stack raw-llm"),
    )
    parser.add_argument(
        "--stack",
        metavar="SLUG",
        default=None,
        help=(
            "Validate a single stack by its directory name under stacks/. "
            "Omit to validate all stacks."
        ),
    )
    return parser


def main() -> None:
    """Entry point."""
    parser = _build_parser()
    args = parser.parse_args()

    schema = _load_schema()

    if args.stack is not None:
        stack_yaml = _STACKS_ROOT / args.stack / "stack.yaml"
        if not stack_yaml.exists():
            print(
                f"ERROR: {stack_yaml} not found.\n"
                f"  Available stacks: "
                + ", ".join(p.name for p in sorted(_STACKS_ROOT.iterdir()) if p.is_dir()),
                file=sys.stderr,
            )
            sys.exit(1)
        ok = validate_one(stack_yaml, schema)
        print(f"\n{'1/1' if ok else '0/1'} stack spec valid")
        sys.exit(0 if ok else 1)

    passed, total = validate_all(schema)
    print(f"\n{passed}/{total} stack specs valid")
    sys.exit(0 if passed == total and total > 0 else 1)


if __name__ == "__main__":
    main()
