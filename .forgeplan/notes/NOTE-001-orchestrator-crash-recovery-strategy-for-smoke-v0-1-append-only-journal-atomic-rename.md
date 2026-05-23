---
depth: standard
id: NOTE-001
kind: note
last_modified_at: 2026-05-23T20:51:49.860607+00:00
last_modified_by: claude-code/2.1.150
links:
- target: RFC-001
  relation: informs
status: active
title: orchestrator crash recovery strategy for smoke v0.1 — append-only journal + atomic rename
---

# NOTE-001: orchestrator crash recovery strategy for smoke v0.1

## Context

Address Architect-reviewer finding #1 (HIGH — Operability + Blast radius) on RFC-001: «The 5-state machine (`created → executing → evaluating → aggregating → published`) does not specify what happens if the orchestrator crashes mid-state. There is no manifest.lock file, no two-phase commit, no journaling, no resume command.»

Этот Note фиксирует решение **до** того, как Phase 2 кодинг начнётся. Полная архитектура (если потребуется) станет ADR; Note достаточен для smoke v0.1 (single-process, single-maintainer, 45 evals — масштаб где простая стратегия работает).

## Decision

**Append-only journal + atomic rename + manual resume command**.

### Mechanism

1. **`manifest.journal.ndjson`** живёт рядом с `manifest.json` в `artifacts/runs/{run_hash}/`. Каждый раз, когда orchestrator завершает eval (scored или failed), он:
   - Пишет EvalRow JSON одной строкой в journal через `f.write(json.dumps(row) + "\n"); f.flush(); os.fsync(f.fileno())`.
   - Atomic write: пишет в `manifest.journal.ndjson.tmp`, потом `os.rename()` → final name (POSIX rename — атомарный для одинаковой файловой системы).

2. **`manifest.json`** записывается **только дважды**:
   - При status переходе → `aggregating`: orchestrator читает journal, computes aggregates, пишет в `manifest.json.tmp`, валидирует против `run-manifest.schema.json`, делает `os.rename()` → `manifest.json`. Status в manifest = `aggregating`.
   - При финальном status переходе → `published` (или `degraded`): тот же atomic pattern. После rename — `os.chmod(manifest_path, 0o444)` для hard immutability.

3. **`make resume HASH=<run_hash>`** команда:
   - Загружает journal, парсит каждую строку как EvalRow.
   - Сравнивает с expected grid (model × task × seed combinations из run_hash inputs).
   - Identifies missing eval_ids, schedules только их (skips scored и failed).
   - При rerun: existing journal entries не перезаписываются (append-only). Новые eval'ы appended в конец.
   - После завершения недостающих evals → переходит к `aggregating`.

### Crash modes covered

| Crash point | Recovery |
|-------------|----------|
| Mid-eval (LLM call in progress) | Journal не имеет entry для этого eval. `make resume` schedules его заново. Cost: 1 потерянная LLM call (~$0.10). |
| Between eval completion и journal write | f.flush + fsync minimize window. Worst case — lost entry; resume detects missing eval_id и re-runs. |
| Mid-aggregating (computing summaries) | `manifest.json.tmp` сохраняется; `manifest.json` либо предыдущая версия, либо отсутствует. Resume пере-вычисляет aggregates из journal. |
| Mid-rename | `os.rename()` atomic — либо succeeds полностью, либо не происходит. Manifest в consistent state. |
| Post-published rename | chmod 0o444 уже применён; невозможно perturb. |

### Out of scope (deferred to PRD-003)

- **Multi-process orchestrator** — для weekly run (1000+ evals) понадобится distributed coordination. Тогда journal модель эволюционирует в append-only event log (Kafka / NATS / SQLite WAL).
- **Cross-machine resume** — smoke single-machine, не applicable. PRD-003 ADR должен решить.
- **Concurrent resume** — если 2 maintainer'а одновременно запустят `make resume`, журнал может corrupt. Pessimistic file lock (`fcntl.flock`) добавим, если станет проблемой; для solo maintainer не нужно сейчас.

## Why not более сложно

- **Two-phase commit** (2PC) overkill для single-process: основная сложность 2PC — coordinator handling. Для single-process atomic rename достаточен.
- **SQLite WAL journal** — рассматривался, но adds dependency (SQLite библиотека есть в stdlib, но требует schema setup); NDJSON journal проще debug'ить (cat manifest.journal.ndjson | jq .).
- **Lock file** (`manifest.lock`) — добавляет corner case если orchestrator crashes до cleanup. Atomic rename + journal делает lock излишним.

## Compliance

- Соответствует RFC-001 § Manifest write order (расширяет её до crash-safe).
- Соответствует ADR-0002 (run immutability — published manifest unchanged after chmod 0o444).
- Не противоречит ADR-001 concurrency (semaphore tracks in-flight evals; журнал tracks completed).
- Соответствует PRD-001 SC-1 (no missing artifacts — resume recovers all evals).

## Related

- RFC-001 (extends § Manifest write order)
- ADR-001 (concurrency — concurrent writers handled при resume)
- ADR-002 (reproduce — uses cached raw_output, не нарушено crash recovery)
- SPEC-001 § Manifest schema (status state machine — recovery preserves invariants)
- Architect-reviewer EVID-007 — finding #1 fixed by this Note



