"""Append-only NDJSON journal for crash-safe per-eval persistence.

Per NOTE-001:
- Each completed eval (scored or failed) → one line in manifest.journal.ndjson
- Write order: f.write(json.dumps(row) + "\\n") → f.flush() → os.fsync(fileno())
- File created with atomic .tmp + os.rename pattern (no half-written files)
- Reads are append-tolerant (can read mid-write without locking)

Used by:
- grid_runner (Wave 5) to persist each completed eval
- resume command (out of scope this wave) to recover missing eval_ids
"""

from __future__ import annotations

import errno
import json
import logging
import mmap
import os
from collections.abc import Generator, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from opentelemetry import trace
from opentelemetry.trace import StatusCode

logger = logging.getLogger(__name__)

tracer = trace.get_tracer(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class JournalCorruptionError(Exception):
    """Raised on malformed JSON entries or unexpected write failures."""


# ---------------------------------------------------------------------------
# JournalPath — canonical path resolver for a run's journal files
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class JournalPath:
    """Resolves canonical paths for a run's NDJSON journal files.

    The journal lives at:
        {root}/{run_hash}/manifest.journal.ndjson

    A temporary file used during atomic initialization:
        {root}/{run_hash}/manifest.journal.ndjson.tmp
    """

    run_hash: str
    root: Path

    @property
    def journal_path(self) -> Path:
        """Final journal path: {root}/{run_hash}/manifest.journal.ndjson."""
        return self.root / self.run_hash / "manifest.journal.ndjson"

    @property
    def journal_tmp_path(self) -> Path:
        """Temp path used during atomic initialization (renamed to final)."""
        return self.root / self.run_hash / "manifest.journal.ndjson.tmp"


# ---------------------------------------------------------------------------
# Internal helper — atomic initialization
# ---------------------------------------------------------------------------


def _atomic_initialize(journal_path: Path) -> None:
    """Ensure the journal file exists durably, using .tmp + os.rename.

    If the journal already exists this is a no-op.  If a .tmp leftover from a
    previous crash exists it is overwritten (the .tmp is always empty or
    incomplete — the only safe recovery is to start fresh; real entries are
    only ever appended directly to the final file by JournalWriter).

    Design decision (documented here per NOTE-001):
    The .tmp file is used *only* during first initialization to guarantee the
    journal file exists as a durable inode before the first append.  Actual
    row appends go directly to the final file in "ab" mode — they do NOT use
    tmp+rename because POSIX rename would lose previous entries.  This matches
    the NOTE-001 pattern: atomic rename for the manifest.json (whole-file
    replacement), plain fsync-append for the journal (grow-only log).
    """
    tmp_path = Path(str(journal_path) + ".tmp")

    if journal_path.exists():
        # Already initialized — clean up any stale .tmp silently.
        if tmp_path.exists():
            tmp_path.unlink()
        return

    # Write an empty file to .tmp, fsync it, then rename atomically.
    with tmp_path.open("wb") as fh:
        fh.flush()
        os.fsync(fh.fileno())

    os.rename(tmp_path, journal_path)


# ---------------------------------------------------------------------------
# JournalWriter
# ---------------------------------------------------------------------------


class JournalWriter:
    """Append-only writer for a manifest.journal.ndjson file.

    Each ``append`` call serialises one dict as a JSON line and durably flushes
    it to disk via ``f.flush()`` + ``os.fsync(fileno())``.  The file is opened
    in binary-append mode (``"ab"``) so concurrent readers always see a
    consistent prefix.

    Usage — context manager (recommended)::

        with JournalWriter(path) as writer:
            writer.append(row)

    Usage — explicit close::

        writer = JournalWriter(path)
        writer.append(row)
        writer.close()

    The writer can be re-instantiated after close; it picks up at the end of
    the existing file because ``"ab"`` mode always seeks to EOF before writing.
    """

    _fh: IO[bytes]
    _closed: bool

    def __init__(self, journal_path: Path) -> None:
        _atomic_initialize(journal_path)
        self._fh = journal_path.open("ab")
        self._closed = False

    # ------------------------------------------------------------------
    # Core write interface
    # ------------------------------------------------------------------

    def append(self, row: dict[str, object]) -> None:
        """Serialize *row* as one JSON line and fsync to disk.

        Raises:
            JournalCorruptionError: if json.dumps fails or fsync raises.
            RuntimeError: if called after close().
        """
        if self._closed:
            raise RuntimeError("JournalWriter is closed")

        entry_id = str(row.get("eval_id", ""))
        entry_type = str(row.get("status", "unknown"))
        span_attrs: dict[str, str | int] = {
            "pollmevals.journal.entry_type": entry_type,
            "pollmevals.journal.entry_id": entry_id,
        }

        with tracer.start_as_current_span("journal.append", attributes=span_attrs) as span:
            try:
                line = json.dumps(row, default=str) + "\n"
            except (TypeError, ValueError) as exc:
                span.record_exception(exc)
                span.set_status(StatusCode.ERROR, str(exc))
                raise JournalCorruptionError(f"Failed to serialize row to JSON: {exc}") from exc

            span.set_attribute("pollmevals.journal.size_bytes", len(line.encode()))

            try:
                self._fh.write(line.encode())
                self._fh.flush()
                os.fsync(self._fh.fileno())
            except OSError as exc:
                span.record_exception(exc)
                span.set_status(StatusCode.ERROR, str(exc))
                raise JournalCorruptionError(f"Failed to write/fsync journal entry: {exc}") from exc

    def append_many(self, rows: Iterable[dict[str, object]]) -> None:
        """Append multiple rows, each with its own fsync.

        Correctness over speed: every row is individually durable so a crash
        between rows leaves the journal in a valid state (all rows up to the
        last successful fsync are readable).
        """
        for row in rows:
            self.append(row)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Flush, fsync, and close the file descriptor."""
        if self._closed:
            return
        try:
            self._fh.flush()
            try:
                os.fsync(self._fh.fileno())
            except OSError as e:
                # fsync returns EINVAL on filesystems that do not support it
                # (tmpfs on GitHub Actions runners, certain overlay mounts).
                # Durability is undefined there anyway — log and continue.
                if e.errno != errno.EINVAL:
                    raise
                logger.warning(
                    "os.fsync returned EINVAL (likely tmpfs/non-durable fs); "
                    "journal flushed but not fsynced"
                )
        finally:
            self._fh.close()
            self._closed = True

    def __enter__(self) -> JournalWriter:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        self.close()


# ---------------------------------------------------------------------------
# JournalReader
# ---------------------------------------------------------------------------


class JournalReader:
    """Read-only accessor for a manifest.journal.ndjson file.

    Designed for append-tolerant reading: a truncated last line (caused by a
    crash mid-write) is silently skipped with a WARN log rather than raising,
    so callers always get a consistent prefix of completed entries.
    """

    def __init__(self, journal_path: Path) -> None:
        self._path = journal_path

    # ------------------------------------------------------------------
    # Core read interface
    # ------------------------------------------------------------------

    def read_all(self) -> Generator[dict[str, object], None, None]:
        """Yield each valid JSON line as a dict.

        Tolerant of a truncated last line (crash mid-write): if the final
        line cannot be decoded as JSON it is skipped and a WARNING is logged.
        All other lines must be valid JSON; a mid-file corruption raises
        ``JournalCorruptionError``.
        """
        if not self._path.exists() or self._path.stat().st_size == 0:
            return

        with self._path.open("rb") as fh:
            lines = fh.read().splitlines()

        for idx, raw_line in enumerate(lines):
            line = raw_line.decode(errors="replace").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                is_last = idx == len(lines) - 1
                if is_last:
                    logger.warning(
                        "Journal truncated last line skipped (crash mid-write?): "
                        "line=%d err=%s path=%s",
                        idx + 1,
                        exc,
                        self._path,
                    )
                    return
                raise JournalCorruptionError(
                    f"Journal corrupt at line {idx + 1}: {exc} in {self._path}"
                ) from exc
            if not isinstance(obj, dict):
                raise JournalCorruptionError(
                    f"Journal line {idx + 1} is not a JSON object: {type(obj).__name__}"
                )
            yield obj

    def count(self) -> int:
        """Return the number of valid (non-empty) lines in the journal.

        Uses mmap for large files; falls back to line iteration for small ones.
        A truncated last line is not counted (mirrors read_all semantics).
        """
        if not self._path.exists():
            return 0

        file_size = self._path.stat().st_size
        if file_size == 0:
            return 0

        # Fast path: mmap-based newline count, then verify last line.
        try:
            with self._path.open("rb") as fh:
                mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
                try:
                    total_newlines = mm[:].count(b"\n")
                    # Check whether the file ends with a newline.
                    # If the very last byte is not \n the last line is partial.
                    ends_with_newline = mm[file_size - 1 : file_size] == b"\n"
                finally:
                    mm.close()
        except (ValueError, OSError):
            # mmap can fail on empty or very small files — fall through.
            return sum(1 for _ in self.read_all())

        if ends_with_newline:
            return total_newlines
        # File does NOT end with a newline — the trailing bytes are a partial
        # (potentially truncated) line that has no terminating \n.
        # The `total_newlines` count already reflects the number of *completed*
        # newline-terminated lines, so the partial fragment is not counted.
        # Attempt to parse it only to decide whether to include it.
        last_line = self._path.read_bytes().rsplit(b"\n", 1)[-1].strip()
        if not last_line:
            return total_newlines
        try:
            json.loads(last_line)
            # Parseable despite missing newline — count it as a complete entry.
            return total_newlines + 1
        except json.JSONDecodeError:
            # Truncated/corrupt trailing fragment — skip it, return completed lines.
            return total_newlines

    def eval_ids(self) -> set[str]:
        """Extract the ``eval_id`` field from every readable row.

        Rows missing ``eval_id`` are silently skipped (dict.get returns None).
        """
        ids: set[str] = set()
        for row in self.read_all():
            eid = row.get("eval_id")
            if isinstance(eid, str):
                ids.add(eid)
        return ids
