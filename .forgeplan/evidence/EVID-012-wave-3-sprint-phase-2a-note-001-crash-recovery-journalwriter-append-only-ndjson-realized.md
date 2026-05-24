---
depth: standard
id: EVID-012
kind: evidence
last_modified_at: 2026-05-24T07:29:18.049628+00:00
last_modified_by: claude-code/2.1.150
links:
- target: NOTE-001
  relation: informs
status: active
title: 'Wave 3 (sprint phase-2A): NOTE-001 crash recovery — JournalWriter append-only NDJSON realized'
---

# EVID-012: Wave 3 — NOTE-001 crash recovery: JournalWriter append-only NDJSON realized

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: measurement

## ADI cycle (per NOTE-002)

### Abduction — hypotheses (3 candidates for "how to persist completed evals for crash recovery?")

- **H1**: SQLite WAL journal — battle-tested, transactional, ACID guarantees. Adds dependency but Python `sqlite3` is in stdlib.
- **H2**: NDJSON append-only file with fsync per row — pure stdlib (json + os.fsync), debuggable via `cat | jq`, append-only semantics map naturally to "completed evals never updated".
- **H3**: No journal — write the whole manifest.json after each completed eval (45× overhead, but unifies the storage model).

### Deduction — observable predictions

| Hypothesis | Predicted observable | Measurable as |
|---|---|---|
| H1 | SQLite requires schema setup (CREATE TABLE), connection pooling, INSERT statements; adds ~50-100 LOC overhead vs plain file I/O; debugging via `sqlite3 cli` not `cat \| jq` | Compare LOC + tooling friction for solo maintainer |
| H2 | NDJSON: `f.write(json.dumps(row) + "\n"); f.flush(); os.fsync(fileno())` — minimal stdlib code; reader is `for line in f: yield json.loads(line)`; tolerant of truncated last line (crash mid-write) | Measure: LOC, crash-simulation test, fsync verification |
| H3 | Writing manifest.json 45 times per run: 45× JSON serialization of full manifest (10s of KB each), 45× JSON Schema validation, 45× atomic rename. Plus risk of partial writes during long manifests. | Estimate IO + risk |

### Induction — evidence per prediction

| Prediction | Evidence | Outcome | H_i status |
|---|---|---|---|
| Y1 (SQLite overhead) | `journal.py` ended at 195 LOC pure stdlib. SQLite WAL would require: schema migration management, prepared statements, transaction boundaries, connection lifecycle — estimated 280-350 LOC + sqlite3 import. Debugging journal in production = `cat manifest.journal.ndjson \| jq '.eval_id'` (1 command) vs `sqlite3 journal.db "SELECT eval_id FROM evals;"` (extra tool). | SQLite is OK but heavier than needed | **H1 REJECTED** (valid but over-engineered for v0.1 smoke; revisit if write throughput becomes an issue at PRD-003 weekly scale) |
| Y2 (NDJSON works + crash-safe) | 32/32 tests PASS in 1.17s. `test_truncated_last_line_not_corrupting` confirms reader tolerance. `test_fsync_is_called_on_each_append` confirms durability call. `test_write_50_reopen_reads_up_to_50` confirms crash-simulation invariant (per NOTE-001 crash modes table). | All predictions held | **H2 SUPPORTED** |
| Y3 (whole-manifest-per-eval) | Manifest with 45 evals is ~50-100KB JSON; writing 45× = ~3-5MB IO + 45 schema validations (jsonschema is non-trivial cost on 50KB doc). Atomic rename per eval = 45 inode operations. Plus partial-write risk during writes mid-eval-completion. | Massive overhead vs append-only NDJSON | **H3 REFUTED** |

**Surviving hypothesis**: H2 — NDJSON + fsync append-only journal. Matches shipped implementation; documented in NOTE-001 § Why not более сложно.

## Trust Calculus per load-bearing claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| 32/32 journal tests PASS in 1.17s | 9 | 9 | 9 | 27/27 | F: explicit pass count + wall clock. G: precise. R: reproducible `pytest`. |
| fsync called on every append (durability) | 9 | 9 | 8 | 26/27 | F: two distinct tests (counting wrapper + MagicMock.wraps). G: per-call assertion. R: deterministic mock-based verification. Drops 1 on R because OS-level fsync semantics also depend on filesystem (ext4/zfs/btrfs differ — not POLLMEVALS scope). |
| Crash simulation: truncated last line tolerated | 8 | 8 | 8 | 24/27 | F: explicit `test_truncated_last_line_not_corrupting`. G: tested by manual byte truncation. R: reproducible. Drops because actual OS-level crash (power loss) not simulated — only mid-write byte truncation. |
| `_atomic_initialize` uses `.tmp + os.rename` for first creation only | 9 | 8 | 9 | 26/27 | F: explicit design decision documented in docstring. G: code path clearly separates init vs append. R: POSIX rename atomicity is well-documented stdlib behavior. |
| Append uses direct write (NOT tmp+rename) — would truncate journal | 9 | 9 | 9 | 27/27 | F: design decision documented in NOTE-001 + docstring with rationale. G: explicit explanation of why rename would truncate. R: POSIX rename semantics are authoritative; verified by counter-example reasoning. |
| `eval_ids()` returns set[str] for Wave 5 `make resume` | 8 | 8 | 8 | 24/27 | F: explicit method signature + return type. G: tested with full set. R: standard set semantics. |
| mypy --strict 0 issues on 2 source files | 9 | 8 | 9 | 26/27 | F: --strict. G: "0 issues, 2 files". R: deterministic. |

**Decision strength**: average sum = 25.7/27 (95%). Two 27/27 claims. Weakest: crash simulation (24/27) — would improve with real OS-level fault injection (out of scope for v0.1).

## Wave summary

- **Sprint**: phase-2A, **Wave**: 3 of 5 (parallel with manifest-writer)
- **Worker**: `journal` (agents-core:coder)
- **Files** (~648 LOC): journal.py (195) + test_journal.py (453, 32 tests across 4 classes)
- **Pipeline gates**: pytest 32/32 PASS (1.17s), mypy --strict ✓ (0 issues), ruff ✓ (1 auto-fix: import sorting)

## Acceptance criteria validation (NOTE-001 § Mechanism)

- ✓ Per-row durability: `f.write+flush+fsync` pattern enforced
- ✓ Atomic `.tmp + os.rename` for first creation
- ✓ Append-only post-init (POSIX `"ab"` mode); rename deliberately NOT used (would truncate grow-only journal)
- ✓ Reader tolerance for truncated last line
- ✓ Crash simulation passes (NOTE-001 crash modes table)
- ✓ `eval_ids() -> set[str]` for Wave 5 `make resume` (FR-011)
- ✓ `count()` fast-path

## Conclusions

- **Surviving hypothesis**: H2 (NDJSON + fsync append-only — pure stdlib, debuggable, crash-safe)
- **Decision strength**: 95%
- **Follow-up evidence needed**: PRD-003 weekly-scale measurement (will journal handle 1000+ evals/run with same simplicity?) — if write throughput becomes an issue, revisit H1 (SQLite WAL) via new ADR

## Related Artifacts

- NOTE-001 (informs — auto-linked; this is implementation receipt)
- RFC-001 § Crash Recovery (foundation realized)
- PRD-001 FR-011 (`make resume HASH=<x>` — journal is the state recovery depends on)
- EVID-013 (Wave 3 sibling — manifest-writer; together: crash-recovery infrastructure)
- NOTE-002 (Evidence Quality Standard — retrofit)


