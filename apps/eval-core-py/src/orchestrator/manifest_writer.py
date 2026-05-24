"""Atomic, state-machine-enforced manifest writer.

Implements RFC-001 § Manifest write order:
1. created → executing → evaluating → aggregating → published (or degraded)
2. Each transition: write to .tmp → JSON Schema validate → os.rename → if terminal, chmod 0o444
3. Once published/degraded, file is immutable (mode 0o444 + RunStatus terminal)

Handles 3 known Pydantic v2 ↔ on-disk schema drifts (see _to_disk_format docstring):
  1. Decimal serialised as string — coerced to float for on-disk number fields.
  2. Optional ArtifactRef fields (stdout/stderr/trace_json) not nullable in schema —
     excluded when None.
  3. started_at/completed_at=None dropped; started_at should always be set pre-publish.
"""

from __future__ import annotations

import contextlib
import functools
import json
import os
from pathlib import Path
from typing import Any, NamedTuple, cast

import jsonschema

from src.contracts import Manifest, RunStatus

# ---------------------------------------------------------------------------
# Decimal field names — only these receive str→float coercion
# ---------------------------------------------------------------------------

_DECIMAL_FIELD_KEYS: frozenset[str] = frozenset(
    {
        "input_per_mtoken_usd",
        "output_per_mtoken_usd",
        "cost_usd",
        "total_cost_usd",
    }
)

# Path to the on-disk JSON Schema relative to the repo root.
# This module lives at:  apps/eval-core-py/src/orchestrator/manifest_writer.py
# Repo root is 4 levels up.
_REPO_ROOT: Path = Path(__file__).parents[4]
_SCHEMA_PATH: Path = _REPO_ROOT / "packages" / "contracts" / "schemas" / "run-manifest.schema.json"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ManifestWriterError(Exception):
    """Base exception for manifest write failures."""


class InvalidTransitionError(ManifestWriterError):
    """Raised when the requested status transition is not allowed by the state machine."""


class SchemaValidationError(ManifestWriterError):
    """Raised when the on-disk JSON Schema rejects the serialised manifest payload.

    Wraps jsonschema.ValidationError with additional context (manifest path, field path).
    """

    def __init__(self, message: str, cause: jsonschema.ValidationError) -> None:
        super().__init__(message)
        self.cause = cause


# ---------------------------------------------------------------------------
# ManifestPath — typed path bundle
# ---------------------------------------------------------------------------


class ManifestPath(NamedTuple):
    """Typed container for run-scoped manifest file paths.

    Computed properties:
      manifest_path  — the live JSON file: root/{run_hash}/manifest.json
      tmp_path       — atomic-write staging file: root/{run_hash}/manifest.json.tmp
    """

    run_hash: str
    root: Path

    @property
    def manifest_path(self) -> Path:
        return self.root / self.run_hash / "manifest.json"

    @property
    def tmp_path(self) -> Path:
        return self.manifest_path.with_suffix(".json.tmp")


# ---------------------------------------------------------------------------
# Schema loading (cached)
# ---------------------------------------------------------------------------


@functools.cache
def _load_on_disk_schema() -> dict[str, Any]:
    """Load run-manifest.schema.json from packages/contracts/schemas/ exactly once.

    Subsequent calls return the cached dict — never re-reads the file.
    Raises FileNotFoundError if the schema file is missing.
    """
    if not _SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"On-disk JSON Schema not found at {_SCHEMA_PATH}. "
            "Ensure packages/contracts/schemas/run-manifest.schema.json exists."
        )
    with _SCHEMA_PATH.open() as fh:
        return json.load(fh)  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _coerce_decimal_strings_to_numbers(obj: Any, parent_key: str = "") -> Any:
    """Recursively convert known Decimal-string fields to float.

    Pydantic v2 serialises Decimal as a JSON string (e.g. ``"0.001"``).
    The on-disk schema declares cost/price fields as ``"type": "number"``.

    Only keys listed in _DECIMAL_FIELD_KEYS are coerced — converting blindly
    would corrupt hex IDs that happen to be valid float literals.

    Args:
        obj:        The value to process (dict, list, or scalar).
        parent_key: The key under which `obj` appears in its parent dict.
                    Used to gate coercion to known Decimal field names.

    Returns:
        The same structure with known Decimal-string fields converted to float.
    """
    if isinstance(obj, dict):
        return {k: _coerce_decimal_strings_to_numbers(v, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_coerce_decimal_strings_to_numbers(item, parent_key) for item in obj]
    if isinstance(obj, str) and parent_key in _DECIMAL_FIELD_KEYS:
        return float(obj)
    return obj


def _to_disk_format(manifest: Manifest) -> dict[str, Any]:
    """Convert a Manifest instance to an on-disk-safe dict.

    Handles 3 known Pydantic v2 ↔ schema drifts:

    1. Decimal serialised as string (drift #1):
       Pydantic v2 renders Decimal as ``"0.001"`` (JSON string). The JSON
       Schema declares cost/price fields as ``"type": "number"``. Solution:
       walk the dict and coerce only the known Decimal-keyed fields to float.
       Precision loss on disk is acceptable — the manifest is the published
       snapshot; Decimal precision only matters during in-memory aggregation.

    2. Optional ArtifactRef fields serialised as null (drift #2):
       EvalArtifactRefs.stdout/stderr/trace_json are Optional[ArtifactRef].
       The on-disk schema treats their absence as "not present" (no null
       allowed for these keys). Solution: model_dump(exclude_none=True)
       drops all None-valued fields automatically.

    3. completed_at=None for in-progress evals (drift #3):
       Same fix — excluded by exclude_none=True. started_at should always
       be populated for any real eval before the manifest is written; only
       completed_at can legitimately be None (still running). Both are
       dropped when None and the schema permits their absence for non-terminal
       evals.

    Args:
        manifest: A valid Manifest instance.

    Returns:
        A dict ready for jsonschema.validate() and json.dumps().
    """
    # exclude_none=True simultaneously fixes drifts #2 and #3:
    # - stdout/stderr/trace_json: None → absent from output
    # - completed_at/started_at: None → absent from output
    payload: dict[str, Any] = manifest.model_dump(mode="json", exclude_none=True)

    # Fix drift #1: coerce Decimal-as-string to float for schema "type": "number"
    # cast required because _coerce_decimal_strings_to_numbers takes/returns Any
    # (the function is generic in structure-preserving traversal, not typed per-key).
    return cast(dict[str, Any], _coerce_decimal_strings_to_numbers(payload))


def _from_disk_format(payload: dict[str, Any]) -> dict[str, Any]:
    """Reverse the on-disk coercion when loading a manifest back into Pydantic.

    Pydantic accepts float for Decimal fields (it converts automatically), so
    no explicit Decimal back-conversion is needed — this is a pass-through that
    exists for symmetry and future extension.

    Args:
        payload: A raw dict loaded from manifest.json.

    Returns:
        The same dict (no transformation required for current drift set).
    """
    # Pydantic v2 coerces float → Decimal automatically on model_validate,
    # so the only drift to worry about here is "None-valued fields were dropped".
    # Since Pydantic Optional fields default to None, absent keys restore
    # correctly without any intervention.
    return payload


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_against_schema(payload: dict[str, Any], manifest_path: Path) -> None:
    """Validate the serialised payload against the on-disk JSON Schema.

    Args:
        payload:       The dict produced by _to_disk_format().
        manifest_path: Used only in error messages for context.

    Raises:
        SchemaValidationError: If jsonschema.validate() raises ValidationError.
    """
    schema = _load_on_disk_schema()
    try:
        jsonschema.validate(payload, schema)
    except jsonschema.ValidationError as exc:
        field_path = " -> ".join(str(p) for p in exc.absolute_path) or "<root>"
        raise SchemaValidationError(
            f"Manifest schema validation failed for {manifest_path}: "
            f"field path '{field_path}': {exc.message}",
            cause=exc,
        ) from exc


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------


def _atomic_write(path: Path, tmp_path: Path, payload: dict[str, Any]) -> None:
    """Write payload to disk atomically using .tmp + os.rename.

    Steps:
      1. Ensure parent directory exists.
      2. Write JSON to tmp_path with flush + fsync (durable write).
      3. os.rename(tmp_path, path) — atomic on POSIX (same filesystem).

    The .tmp file is cleaned up on successful rename. On failure before rename,
    the caller is responsible for cleanup (see ManifestWriter.write).

    Args:
        path:     Destination path (manifest.json).
        tmp_path: Staging path (manifest.json.tmp).
        payload:  The dict to serialise as JSON.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with tmp_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.flush()
        os.fsync(fh.fileno())
    os.rename(tmp_path, path)


def _chmod_immutable(path: Path) -> None:
    """Set the manifest file to read-only (0o444) for all users.

    Enforces ADR-0002: once a run reaches published or degraded, the
    manifest on disk is write-once.

    Args:
        path: Path to the manifest.json file (must already exist).

    Raises:
        ManifestWriterError: If the resulting file mode is not 0o444.
    """
    os.chmod(path, 0o444)
    actual_mode = path.stat().st_mode & 0o777
    if actual_mode != 0o444:
        raise ManifestWriterError(f"chmod 0o444 failed for {path}: mode is {oct(actual_mode)}")


# ---------------------------------------------------------------------------
# ManifestWriter
# ---------------------------------------------------------------------------


class ManifestWriter:
    """Atomic, state-machine-enforced writer for POLLMEVALS Run Manifests.

    Each call to write() enforces:
      - The incoming status is reachable from the on-disk status (state machine).
      - The serialised payload passes JSON Schema validation.
      - The write is atomic (.tmp + os.rename).
      - Terminal statuses (published, degraded) chmod the file to 0o444.

    Usage::

        mp = ManifestPath(run_hash="sha256:" + "a" * 64, root=Path("artifacts/runs"))
        writer = ManifestWriter(mp)
        writer.write(manifest)                       # created → executing, etc.
        writer.write(next_manifest)                  # executing → evaluating, etc.
    """

    _TERMINAL_STATUSES: frozenset[RunStatus] = frozenset({RunStatus.PUBLISHED, RunStatus.DEGRADED})

    def __init__(self, manifest_path: ManifestPath) -> None:
        self._mp = manifest_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write(
        self,
        manifest: Manifest,
        *,
        allow_terminal_overwrite: bool = False,
    ) -> None:
        """Write (or transition) the manifest to disk.

        Args:
            manifest:               The new manifest state to persist.
            allow_terminal_overwrite:
                When False (default), writing to an already-terminal manifest
                raises InvalidTransitionError. Set True only for migration /
                test scenarios where you need to overwrite a terminal file.
                Even with this flag, the file mode is re-applied (0o444).

        Raises:
            InvalidTransitionError:  State machine violation or terminal overwrite attempt.
            SchemaValidationError:   Payload fails JSON Schema validation.
            ManifestWriterError:     chmod verification fails.
        """
        dest = self._mp.manifest_path
        tmp = self._mp.tmp_path

        # --- Guard: existing terminal file ---
        if dest.exists():
            existing = self._load_raw_status()
            if existing in self._TERMINAL_STATUSES and not allow_terminal_overwrite:
                raise InvalidTransitionError(
                    f"Manifest at {dest} is already in terminal status "
                    f"'{existing}'; file is immutable (ADR-0002). "
                    "Pass allow_terminal_overwrite=True to bypass."
                )

            # --- State-machine transition check ---
            if existing is not None and not allow_terminal_overwrite:
                existing_manifest = self.read()
                if existing_manifest is not None and not existing_manifest.can_transition_to(
                    manifest.status
                ):
                    raise InvalidTransitionError(
                        f"Disallowed state machine transition: "
                        f"'{existing_manifest.status}' → '{manifest.status}'. "
                        "See SPEC-001 § State machine for allowed edges."
                    )

        # --- Serialise with drift fixes applied ---
        payload = _to_disk_format(manifest)

        # --- JSON Schema validation gate ---
        _validate_against_schema(payload, dest)

        # --- Atomic write ---
        try:
            _atomic_write(dest, tmp, payload)
        except Exception:
            # Clean up any leftover .tmp so subsequent writes see a clean slate.
            with contextlib.suppress(OSError):
                tmp.unlink()
            raise

        # --- chmod 0o444 for terminal statuses ---
        if manifest.status in self._TERMINAL_STATUSES:
            _chmod_immutable(dest)

    def read(self) -> Manifest | None:
        """Load and parse the on-disk manifest.

        Returns None if no manifest file exists yet.

        Pydantic automatically coerces float → Decimal on model_validate,
        and absent optional keys restore to None defaults — no explicit
        reverse-coercion is needed beyond _from_disk_format() (identity).
        """
        dest = self._mp.manifest_path
        if not dest.exists():
            return None
        with dest.open(encoding="utf-8") as fh:
            raw: dict[str, Any] = json.load(fh)
        return Manifest.model_validate(_from_disk_format(raw))

    def current_status(self) -> RunStatus | None:
        """Return the RunStatus stored on disk without full model validation.

        Returns None if no manifest file exists.
        Provides a fast path — avoids constructing the full Manifest object.
        """
        return self._load_raw_status()

    def is_published(self) -> bool:
        """Return True if the manifest is in a terminal status AND the file is read-only.

        Both conditions must hold: the status field must be published/degraded
        AND the file mode must be 0o444 (chmod applied on last write).
        """
        dest = self._mp.manifest_path
        if not dest.exists():
            return False
        status = self._load_raw_status()
        if status not in self._TERMINAL_STATUSES:
            return False
        mode = dest.stat().st_mode & 0o777
        return mode == 0o444

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_raw_status(self) -> RunStatus | None:
        """Read only the ``status`` field from the on-disk JSON.

        Does not construct a full Manifest — faster for guard checks.
        Returns None if the file does not exist.
        """
        dest = self._mp.manifest_path
        if not dest.exists():
            return None
        with dest.open(encoding="utf-8") as fh:
            raw: dict[str, Any] = json.load(fh)
        raw_status: str = raw.get("status", "")
        return RunStatus(raw_status) if raw_status else None
