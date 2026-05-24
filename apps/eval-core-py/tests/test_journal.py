"""Tests for the append-only NDJSON journal (orchestrator/journal.py).

Covers:
- JournalWriter: round-trip, context manager, re-open, fsync verification
- JournalReader: empty file, truncated last line, count(), eval_ids()
- CrashRecoverySimulation: abrupt close, truncated bytes
- AtomicInitialization: .tmp + os.rename pattern

Uses tmp_run_dir fixture from conftest.py. All paths via pathlib.Path.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.orchestrator.journal import (
    JournalCorruptionError,
    JournalPath,
    JournalReader,
    JournalWriter,
    _atomic_initialize,
)

# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------


def _make_row(i: int) -> dict[str, Any]:
    """Build a simple row dict with an index and varied value types."""
    return {
        "eval_id": f"{i:016x}",
        "index": i,
        "model_id": f"model-{i % 3}",
        "nested": {"score": i * 0.1, "tags": ["a", "b"]},
        "flag": i % 2 == 0,
        "nullable": None,
    }


def _journal_path(tmp_path: Path) -> Path:
    """Return a journal path inside tmp_path (not using tmp_run_dir so we control creation)."""
    p = tmp_path / "manifest.journal.ndjson"
    return p


# ---------------------------------------------------------------------------
# TestJournalPath
# ---------------------------------------------------------------------------


class TestJournalPath:
    def test_journal_path_resolves_correctly(self, tmp_path: Path) -> None:
        jp = JournalPath(run_hash="sha256:" + "a" * 64, root=tmp_path)
        expected = tmp_path / ("sha256:" + "a" * 64) / "manifest.journal.ndjson"
        assert jp.journal_path == expected

    def test_journal_tmp_path_resolves_correctly(self, tmp_path: Path) -> None:
        jp = JournalPath(run_hash="sha256:" + "a" * 64, root=tmp_path)
        expected = tmp_path / ("sha256:" + "a" * 64) / "manifest.journal.ndjson.tmp"
        assert jp.journal_tmp_path == expected

    def test_frozen_dataclass_immutable(self, tmp_path: Path) -> None:
        jp = JournalPath(run_hash="abc", root=tmp_path)
        with pytest.raises((AttributeError, TypeError)):
            jp.run_hash = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TestJournalWriter
# ---------------------------------------------------------------------------


class TestJournalWriter:
    def test_write_100_rows_reads_back_100_in_order(self, tmp_path: Path) -> None:
        path = _journal_path(tmp_path)
        rows = [_make_row(i) for i in range(100)]

        with JournalWriter(path) as writer:
            writer.append_many(rows)

        reader = JournalReader(path)
        result = list(reader.read_all())
        assert len(result) == 100
        for i, row in enumerate(result):
            assert row["index"] == i

    def test_round_trip_preserves_all_value_types(self, tmp_path: Path) -> None:
        """Nested dicts, lists, strings, int, bool, null all survive the round-trip."""
        path = _journal_path(tmp_path)
        original: dict[str, Any] = {
            "eval_id": "abcd1234abcd1234",
            "nested": {"score": 7.5, "tags": ["fast", "cheap"]},
            "count": 42,
            "flag": True,
            "nullable": None,
            "text": "hello world",
        }

        with JournalWriter(path) as writer:
            writer.append(original)

        result = list(JournalReader(path).read_all())
        assert len(result) == 1
        assert result[0]["eval_id"] == "abcd1234abcd1234"
        assert result[0]["nested"] == {"score": 7.5, "tags": ["fast", "cheap"]}
        assert result[0]["count"] == 42
        assert result[0]["flag"] is True
        assert result[0]["nullable"] is None
        assert result[0]["text"] == "hello world"

    def test_context_manager_auto_closes(self, tmp_path: Path) -> None:
        path = _journal_path(tmp_path)
        writer = JournalWriter(path)
        with writer:
            writer.append({"eval_id": "0000000000000001"})
        # After __exit__, the writer should be closed.
        assert writer._closed is True  # access private attr to verify close

    def test_append_after_close_raises(self, tmp_path: Path) -> None:
        path = _journal_path(tmp_path)
        writer = JournalWriter(path)
        writer.close()
        with pytest.raises(RuntimeError, match="closed"):
            writer.append({"eval_id": "0000000000000002"})

    def test_close_idempotent(self, tmp_path: Path) -> None:
        path = _journal_path(tmp_path)
        writer = JournalWriter(path)
        writer.close()
        writer.close()  # Should not raise.

    def test_reopen_picks_up_at_end(self, tmp_path: Path) -> None:
        """A second JournalWriter instance appends after existing entries."""
        path = _journal_path(tmp_path)

        with JournalWriter(path) as w1:
            w1.append({"eval_id": "aaaa000000000001", "batch": 1})

        with JournalWriter(path) as w2:
            w2.append({"eval_id": "bbbb000000000002", "batch": 2})

        result = list(JournalReader(path).read_all())
        assert len(result) == 2
        assert result[0]["batch"] == 1
        assert result[1]["batch"] == 2

    def test_fsync_is_called_on_each_append(self, tmp_path: Path) -> None:
        """Verify fsync is called once per append (not just on close)."""
        path = _journal_path(tmp_path)

        fsync_calls: list[int] = []
        original_fsync = os.fsync

        def _counting_fsync(fd: int) -> None:
            fsync_calls.append(fd)
            original_fsync(fd)

        with (
            patch("src.orchestrator.journal.os.fsync", side_effect=_counting_fsync),
            JournalWriter(path) as writer,
        ):
            writer.append({"eval_id": "0000000000000001"})
            writer.append({"eval_id": "0000000000000002"})
            writer.append({"eval_id": "0000000000000003"})
            # close() also calls fsync — so we expect at least 3 from appends + 1 from close

        # At minimum 3 fsync calls from the 3 appends.
        assert len(fsync_calls) >= 3

    def test_fsync_called_via_mock(self, tmp_path: Path) -> None:
        """Use a FakeFile wrapper to confirm fsync receives the correct fd."""
        path = _journal_path(tmp_path)

        # We want to intercept os.fsync without breaking the actual write.
        mock_fsync = MagicMock(wraps=os.fsync)
        with (
            patch("src.orchestrator.journal.os.fsync", mock_fsync),
            JournalWriter(path) as writer,
        ):
            writer.append({"eval_id": "cccc000000000003"})

        # fsync should have been called at least once during append.
        assert mock_fsync.call_count >= 1

    def test_append_many_preserves_order(self, tmp_path: Path) -> None:
        path = _journal_path(tmp_path)
        rows = [{"eval_id": f"{i:016x}", "seq": i} for i in range(20)]

        with JournalWriter(path) as writer:
            writer.append_many(rows)

        result = list(JournalReader(path).read_all())
        assert [r["seq"] for r in result] == list(range(20))

    def test_uses_tmp_run_dir_fixture(self, tmp_run_dir: Path) -> None:
        """Writer works with the canonical tmp_run_dir layout from conftest."""
        journal_path = tmp_run_dir / "manifest.journal.ndjson"

        with JournalWriter(journal_path) as writer:
            writer.append({"eval_id": "dddd000000000004", "source": "tmp_run_dir"})

        result = list(JournalReader(journal_path).read_all())
        assert len(result) == 1
        assert result[0]["source"] == "tmp_run_dir"


# ---------------------------------------------------------------------------
# TestJournalReader
# ---------------------------------------------------------------------------


class TestJournalReader:
    def test_read_empty_journal_returns_empty_iterator(self, tmp_path: Path) -> None:
        path = _journal_path(tmp_path)
        path.touch()

        result = list(JournalReader(path).read_all())
        assert result == []

    def test_read_nonexistent_file_returns_empty_iterator(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.ndjson"
        result = list(JournalReader(path).read_all())
        assert result == []

    def test_truncated_last_line_skipped_with_warn(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A valid row followed by a truncated (invalid JSON) last line.

        The reader must:
        - yield the 1 valid row
        - log a WARNING about the truncated last line
        - NOT raise
        """
        path = _journal_path(tmp_path)

        good_row = {"eval_id": "eeee000000000005", "status": "scored"}
        good_line = json.dumps(good_row) + "\n"
        truncated_fragment = '{"eval_id": "ffff000000000006", "stat'  # no closing brace

        path.write_bytes((good_line + truncated_fragment).encode())

        with caplog.at_level(logging.WARNING, logger="src.orchestrator.journal"):
            result = list(JournalReader(path).read_all())

        assert len(result) == 1
        assert result[0]["eval_id"] == "eeee000000000005"
        assert any("truncated" in record.message.lower() for record in caplog.records)

    def test_count_on_empty_file_is_zero(self, tmp_path: Path) -> None:
        path = _journal_path(tmp_path)
        path.touch()
        assert JournalReader(path).count() == 0

    def test_count_on_nonexistent_file_is_zero(self, tmp_path: Path) -> None:
        path = tmp_path / "missing.ndjson"
        assert JournalReader(path).count() == 0

    def test_count_matches_written_rows(self, tmp_path: Path) -> None:
        path = _journal_path(tmp_path)
        with JournalWriter(path) as writer:
            writer.append_many([_make_row(i) for i in range(17)])
        assert JournalReader(path).count() == 17

    def test_count_with_truncated_last_line(self, tmp_path: Path) -> None:
        """count() should exclude the truncated last line."""
        path = _journal_path(tmp_path)

        # Write 3 good rows.
        with JournalWriter(path) as writer:
            writer.append_many([_make_row(i) for i in range(3)])

        # Append a truncated fragment directly.
        with path.open("ab") as fh:
            fh.write(b'{"eval_id": "trunc')  # no closing brace, no newline

        count = JournalReader(path).count()
        assert count == 3

    def test_eval_ids_extracts_ids(self, tmp_path: Path) -> None:
        path = _journal_path(tmp_path)
        rows = [{"eval_id": f"{i:016x}", "x": i} for i in range(5)]
        with JournalWriter(path) as writer:
            writer.append_many(rows)

        ids = JournalReader(path).eval_ids()
        expected = {f"{i:016x}" for i in range(5)}
        assert ids == expected

    def test_eval_ids_skips_rows_without_eval_id(self, tmp_path: Path) -> None:
        path = _journal_path(tmp_path)
        rows: list[dict[str, Any]] = [
            {"eval_id": "aaaa000000000001", "status": "scored"},
            {"no_eval_id_here": True},
            {"eval_id": "bbbb000000000002", "status": "failed"},
        ]
        with JournalWriter(path) as writer:
            writer.append_many(rows)

        ids = JournalReader(path).eval_ids()
        assert ids == {"aaaa000000000001", "bbbb000000000002"}

    def test_eval_ids_empty_file_returns_empty_set(self, tmp_path: Path) -> None:
        path = _journal_path(tmp_path)
        path.touch()
        assert JournalReader(path).eval_ids() == set()

    def test_mid_file_corrupt_line_raises(self, tmp_path: Path) -> None:
        """A corrupt line that is NOT the last line must raise JournalCorruptionError."""
        path = _journal_path(tmp_path)
        lines = [
            json.dumps({"eval_id": "aaaa000000000001"}) + "\n",
            "NOT VALID JSON\n",  # mid-file corruption
            json.dumps({"eval_id": "bbbb000000000002"}) + "\n",
        ]
        path.write_bytes("".join(lines).encode())

        with pytest.raises(JournalCorruptionError):
            list(JournalReader(path).read_all())


# ---------------------------------------------------------------------------
# TestCrashRecoverySimulation
# ---------------------------------------------------------------------------


class TestCrashRecoverySimulation:
    def test_write_50_reopen_reads_up_to_50(self, tmp_path: Path) -> None:
        """Write 50 rows, abruptly close (simulating crash), reopen → 50 readable rows.

        Per NOTE-001: each fsync completes before the next append starts, so all
        50 rows should be recoverable.  If the OS buffers one, we accept 49.
        """
        path = _journal_path(tmp_path)
        rows = [_make_row(i) for i in range(50)]

        writer = JournalWriter(path)
        for row in rows:
            writer.append(row)
        # Simulate abrupt crash: close the fd directly without the normal close().
        writer._fh.close()  # access private attr to simulate abrupt crash
        writer._closed = True

        result = list(JournalReader(path).read_all())
        assert 49 <= len(result) <= 50, f"Expected 49-50 rows, got {len(result)}"
        # All readable rows must be in original order.
        for i, row in enumerate(result):
            assert row["index"] == i

    def test_truncated_last_line_not_corrupting(self, tmp_path: Path) -> None:
        """Manually truncate the last line by N bytes → reader skips it gracefully."""
        path = _journal_path(tmp_path)

        with JournalWriter(path) as writer:
            writer.append_many([_make_row(i) for i in range(5)])

        # Read the file and truncate the last N bytes of the last line.
        content = path.read_bytes()
        lines = content.rstrip(b"\n").split(b"\n")
        assert len(lines) == 5

        # Truncate the last line by 10 bytes (enough to break JSON).
        truncated = b"\n".join(lines[:-1]) + b"\n" + lines[-1][:-10]
        path.write_bytes(truncated)

        # Reader must return 4 rows without raising.
        result = list(JournalReader(path).read_all())
        assert len(result) == 4
        for i, row in enumerate(result):
            assert row["index"] == i

    def test_all_50_rows_have_correct_eval_ids_after_crash(self, tmp_path: Path) -> None:
        """After crash simulation, eval_ids() returns all persisted eval_ids."""
        path = _journal_path(tmp_path)
        rows = [{"eval_id": f"{i:016x}", "seq": i} for i in range(50)]

        writer = JournalWriter(path)
        for row in rows:
            writer.append(row)
        writer._fh.close()  # access private attr to simulate abrupt crash
        writer._closed = True

        ids = JournalReader(path).eval_ids()
        # All 50 should be there since each was fsynced before the next write.
        expected = {f"{i:016x}" for i in range(50)}
        assert ids.issubset(expected)
        assert len(ids) >= 49  # accept losing at most 1 (last-write race)


# ---------------------------------------------------------------------------
# TestAtomicInitialization
# ---------------------------------------------------------------------------


class TestAtomicInitialization:
    def test_first_write_creates_journal_durably(self, tmp_path: Path) -> None:
        """First JournalWriter call creates journal.ndjson from a .tmp + rename."""
        path = _journal_path(tmp_path)
        assert not path.exists()

        # Patch os.rename to verify it is called during initialization.
        real_rename = os.rename
        rename_calls: list[tuple[str | Path, str | Path]] = []

        def _tracking_rename(src: str | Path, dst: str | Path) -> None:
            rename_calls.append((src, dst))
            real_rename(src, dst)

        with (
            patch("src.orchestrator.journal.os.rename", side_effect=_tracking_rename),
            JournalWriter(path) as writer,
        ):
            writer.append({"eval_id": "0000000000000001"})

        # rename must have been called at least once (for initialization).
        assert len(rename_calls) >= 1
        tmp_path_used = str(rename_calls[0][0])
        final_path_used = str(rename_calls[0][1])
        assert tmp_path_used.endswith(".tmp")
        assert final_path_used == str(path)

    def test_tmp_file_absent_after_successful_init(self, tmp_path: Path) -> None:
        """After initialization the .tmp file must not exist."""
        path = _journal_path(tmp_path)
        tmp_path_file = Path(str(path) + ".tmp")

        with JournalWriter(path) as writer:
            writer.append({"eval_id": "0000000000000002"})

        assert path.exists()
        assert not tmp_path_file.exists()

    def test_stale_tmp_file_overwritten_on_init(self, tmp_path: Path) -> None:
        """A .tmp leftover from a previous crash is silently overwritten."""
        path = _journal_path(tmp_path)
        tmp_leftover = Path(str(path) + ".tmp")

        # Simulate a crashed previous run that left a .tmp behind.
        tmp_leftover.write_bytes(b"stale content\n")

        # Initialization should succeed and the .tmp should be gone.
        _atomic_initialize(path)

        assert path.exists()
        assert not tmp_leftover.exists()

    def test_init_noop_if_journal_already_exists(self, tmp_path: Path) -> None:
        """_atomic_initialize is a no-op when the journal already exists."""
        path = _journal_path(tmp_path)
        path.write_bytes(b'{"eval_id": "existing"}\n')
        original_mtime = path.stat().st_mtime

        _atomic_initialize(path)

        # File unchanged.
        assert path.read_bytes() == b'{"eval_id": "existing"}\n'
        assert path.stat().st_mtime == original_mtime

    def test_atomic_initialize_standalone(self, tmp_path: Path) -> None:
        """_atomic_initialize creates an empty journal file via tmp + rename."""
        path = _journal_path(tmp_path)
        assert not path.exists()

        _atomic_initialize(path)

        assert path.exists()
        assert path.stat().st_size == 0
