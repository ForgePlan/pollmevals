---
depth: standard
id: ADR-004
kind: adr
last_modified_at: 2026-05-24T08:33:37.837405+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-003
  relation: refines
- target: ADR-001
  relation: based_on
status: active
title: Adopt MoleculerPy as distributed orchestrator for PRD-003 weekly cadence
---

# ADR-004: Adopt MoleculerPy as distributed orchestrator for PRD-003 weekly cadence

## Status

draft (proposed)

## Context

POLLMEVALS Phase 2A shipped a single-process orchestrator (`apps/eval-core-py/src/orchestrator/grid_runner.py`) using `asyncio.gather(*, return_exceptions=True) + asyncio.Semaphore(3)` per ADR-001. This handles smoke run (45 evals) cleanly but **ADR-001 § Consequences explicitly mandates** migration before weekly run (PRD-003): *«При переходе к weekly run (PRD-003) — обязательно переход на Option B (per-provider semaphores) или Option C (distributed job queue Celery+Redis)»*.

PRD-003 scope: weekly cron every Monday 03:00 UTC, ≤ 4-hour wall clock, ≤ $200 budget, eventually 1000+ evals/run when judges (PRD-002) and stack expansion land. Single-process won't survive at that scale (semaphore contention, no fault isolation between providers, no cross-machine workers).

**Critical new context** (discovered during Phase 2A close, 2026-05-24): POLLMEVALS `MASTER.md` vision **already commits MoleculerPy for the eval plane** (10 explicit mentions: «Eval plane → Python 3.12+ + MoleculerPy», «MoleculerPy services: orchestrator, worker, judge, stats»). This was not yet reflected in the forgeplan graph. AND user gogocat is OWNER of MoleculerPy GitHub org (`github.com/MoleculerPy`) — fix path is in-house.

This ADR formalises the vision commitment in the forgeplan graph and provides the explicit migration plan from Phase 2A baseline.

## Decision Drivers

- **PRD-003 scale**: 1000+ evals/run at full PRD-002 judge expansion; single-process insufficient.
- **ADR-001 mandate**: explicit upgrade path to Option B or C required before PRD-003.
- **POLLMEVALS thesis (per CLAUDE.md)**: Python-heavy stack — Python-native distributed framework preferred over JVM/Erlang frameworks.
- **NATS transport**: already in POLLMEVALS infra plan (`Makefile docker-up` includes NATS) — chosen framework should consume NATS natively.
- **Per-provider bulkhead** (ADR-001 Option B): independent concurrency limits per provider (Claude 5 / OpenRouter Llama 1) to maximize throughput while respecting rate limits.
- **Circuit breaker** (RFC-001 RR-3): LiteLLM proxy cost log lag + EPIC-001 ER-2 provider instability need protection.
- **Phase 2A migration cost**: `EvalCaller` Protocol (EVID-015) was deliberately designed as testability seam — wraps cleanly into a distributed framework's action call.
- **Owner-mediated fix path** (key F+G+R uplift): user owns MoleculerPy org; bug-fix is in-house, not 3rd-party blocked.
- **Mutual ecosystem benefit**: POLLMEVALS becomes MoleculerPy's first production user → flywheel.

## Considered Options

### Option A: Continue single-process `asyncio.gather + Semaphore(3)` to PRD-003

- **Pros**: Zero migration cost. Same code as Phase 2A.
- **Cons**: Directly contradicts ADR-001 mandate. Will not scale: 1000+ evals × 5 min average wall clock = ~80 hours single-machine. Cannot exercise per-provider bulkhead. No fault isolation. ER-2 (provider instability) becomes pipeline-wide blocker.
- **Verdict**: REJECTED — ADR-001 already foresaw this; not viable at PRD-003 scale.

### Option B: Celery + Redis (industry-standard Python distributed task queue)

- **Pros**: Battle-tested (15+ years), large community, mature docs.
- **Cons**: Heavy stack (Redis broker + result backend + worker processes); per-task overhead measurable; bulkhead requires manual queue-per-provider setup; circuit breaker not built-in; tracing requires separate OTel/Datadog integration; sharding via separate Celery Beat schedulers. Not Python-native to NATS (Redis preferred transport). **3rd-party — fix path blocked by upstream maintenance cadence.**
- **Verdict**: Functional but high friction; doesn't leverage user's MoleculerPy ownership.

### Option C: MoleculerPy (Python port of Moleculer.js, owned by user gogocat) — **CHOSEN**

- **Pros**:
  - Built-in **bulkhead** isolation (= ADR-001 Option B at framework level, no manual queue management)
  - Built-in **circuit breaker** (closes RFC-001 RR-3 + EPIC-001 ER-2 without custom code)
  - Native **NATS transport** (matches POLLMEVALS infra plan)
  - Built-in **service discovery** (masterless — add/remove workers without coordinator restart)
  - Built-in **Prometheus metrics + Jaeger tracing** (no separate OTel integration)
  - Built-in **load balancing strategies** including sharding (per-task or per-model distribution)
  - **Python-native** — matches POLLMEVALS eval plane (vs Celery which mixes paradigms)
  - **Owned by user gogocat** → fix path in-house, R uplift in Trust Calculus (EVID-018 R=9 vs typical 3rd-party R=6-7)
  - POLLMEVALS adoption creates **mutual ecosystem flywheel**
  - MoleculerPy repo shows production discipline (1850 KB, MIT, 0 open issues, CHANGELOG 28 KB, KNOWN-ISSUES 9 KB, CI/codecov/pre-commit/docker-compose/security policy — per EVID-018 audit)
- **Cons**:
  - **Young (4 months, created 2026-01-31)** — limited battle-testing at scale.
  - MoleculerPy primitives parity with Moleculer.js NOT yet independently verified via POLLMEVALS integration tests (EVID-018 R=7 on this claim until first Phase 3 test).
  - 0 declared production users in MoleculerPy README — POLLMEVALS becomes first (acceptable, mitigated by ownership).
- **Verdict**: CHOSEN — owner-mediated fix path + Python-native fit + vision alignment outweigh the youth risk.

### Option D: Build custom Python distributed orchestrator on raw NATS

- **Pros**: Maximum control; no framework dependency.
- **Cons**: Re-implements service discovery, bulkhead, circuit breaker, load balancing — estimated 2000+ LOC + ongoing maintenance. Reinvents MoleculerPy's value proposition. Owner-fix-path advantage of MoleculerPy is lost.
- **Verdict**: REJECTED — duplicates owned framework.

## Decision Outcome

**Chosen: Option C — Adopt MoleculerPy for PRD-003 distributed orchestrator.**

Architecture (Phase 3 target):

```
┌────────────────────────────────────────────────────────────┐
│  POLLMEVALS Broker (NATS transport per POLLMEVALS Makefile)│
└────────────────────────────────────────────────────────────┘
         ↑                  ↑                   ↑
┌────────────────┐  ┌────────────────┐   ┌────────────────┐
│ scheduler-svc  │  │ worker-svc     │   │ judge-svc      │
│ ────────────── │  │ ────────────── │   │ ────────────── │
│ • cron trigger │  │ • bulkhead     │   │ • multi_scorer │
│ • grid plan    │  │   per provider │   │ • Krippendorff │
│ • dispatch via │  │ • circuit      │   │   α calc       │
│   action calls │  │   breaker per  │   │ • blind label  │
│                │  │   model        │   │   anonymizer   │
└────────────────┘  └────────────────┘   └────────────────┘
         ↓                  ↓                   ↓
┌────────────────────────────────────────────────────────────┐
│  Phase 2A wrappers (preserved as-is, no rewrite):          │
│  JournalWriter, ManifestWriter, contracts, CostReconciler  │
└────────────────────────────────────────────────────────────┘
```

**Migration mechanics** (from Phase 2A code):

1. `GridRunner` becomes one action in `scheduler-svc` (wraps existing async logic)
2. `EvalCaller` Protocol implementations (currently `FakeEvalCaller` + `InspectEvalCaller` stub) become actions in `worker-svc`
3. `MAX_CONCURRENT_EVALS=3` global Semaphore is replaced by per-provider bulkhead config (e.g. `bulkhead.concurrency = {anthropic: 5, openai: 5, google: 3, cerebras: 2, runpod: 1}`)
4. Cost cross-check (Wave 4 EVID-014) becomes a separate service/action invoked by scheduler
5. Existing journal/manifest writers stay file-system (R2 in v0.2+) — orchestration distributed, storage centralized

**No code changes in Phase 2A or 2B.** This ADR is forward-looking; implementation begins Phase 3 (after Phase 2B real-LLM smoke run published).

## Invariants

What MUST never be violated by this decision:

1. **Phase 2A `EvalCaller` Protocol is the migration seam** — any future Phase 2B/2C code MUST go through `EvalCaller`, not bypass it via direct `inspect_ai.eval(...)` calls.
2. **FR-009 invariant preserved** — distributed worker failures still result in stored EvalRow with `error_class`, never dropped.
3. **ADR-002 reproduce semantics preserved** — distributed orchestration does NOT change `make reproduce` (still evaluator-only on cached raw_output).
4. **Methodology version pinning preserved** — distributed runs still pin `methodology_version: v0.1.0` per SPEC-001.
5. **MoleculerPy version pinned exact** in pyproject.toml when adopted — same discipline as `inspect-ai==0.3.46` per RFC-001 RR-1.

## Rollback Plan

If MoleculerPy adoption fails at Phase 3:

| Failure mode | Rollback action |
|--------------|-----------------|
| MoleculerPy critical bug surfaces, user-fix takes >2 weeks | Stop Phase 3; fall back to Phase 2A code; PRD-003 weekly cadence delayed; document as ADR superseding decision |
| MoleculerPy performance insufficient (>10× overhead vs Celery baseline test) | Re-evaluate Option B (Celery+Redis) via new ADR; preserve Phase 2A primitives |
| Bulkhead + circuit breaker primitives missing or buggy | User-fix in MoleculerPy upstream (in-house path; acceptable timeline per EVID-018) |
| MoleculerPy project abandoned (low probability — owned by user) | Fork to POLLMEVALS-internal maintenance; same code base, no migration |

**Cannot rollback**: data written via distributed run (manifest, journal). Per ADR-0002 published runs immutable; failed runs documented in postmortem.

## Affected Files

When Phase 3 implementation begins:

- `apps/eval-core-py/pyproject.toml` — add `moleculerpy` exact pin + `moleculerpy-channels` if needed for messaging
- `apps/eval-core-py/src/services/` (NEW) — scheduler-svc, worker-svc, judge-svc
- `apps/eval-core-py/src/orchestrator/grid_runner.py` — wrap in `@action` for MoleculerPy
- `apps/eval-core-py/src/orchestrator/eval_caller.py` — `InspectEvalCaller.call` becomes action handler
- `infra/docker-compose.litellm.yml` (already exists) — add `nats-server` service if not already there
- `infra/scripts/moleculerpy-broker-up.sh` (NEW) — wrap NATS + broker startup
- `Makefile` — add `make broker-up`, `make broker-down`, `make weekly-run` targets

## Preconditions for adopting

Before Phase 3 implementation begins:

- Phase 2A merged ✓ (commit `0bbd6f4` 2026-05-24)
- Phase 2B published (real LLM smoke run successful, ≥1 postmortem)
- MoleculerPy `>=` minimum version with bulkhead + circuit breaker + NATS transport documented APIs
- User confirms commitment to fix MoleculerPy issues within agreed SLA (e.g. ≤ 1 week for blockers)
- POLLMEVALS team reviews ADR-004 at Phase 3 entry gate

## Postconditions after adopting

After Phase 3 ships with MoleculerPy:

- Weekly run cadence works at ≥3 concurrent provider-isolated workers
- Circuit breaker observably opens on provider failures (verifiable via Prometheus metrics)
- Bulkhead per-provider concurrency configurable without code changes
- Service discovery allows adding worker nodes without orchestrator restart
- POLLMEVALS becomes referenced production user in MoleculerPy README/docs
- EVID created measuring real-world MoleculerPy primitives parity → bumps EVID-018 R=7 claim to 27/27

## Consequences

### Positive

- ✅ ADR-001 Option B (per-provider semaphores) realized at framework level — zero custom code
- ✅ RFC-001 RR-3 (LiteLLM cost log lag) addressed via circuit breaker
- ✅ EPIC-001 ER-2 (provider instability) addressed via circuit breaker + fallback
- ✅ Phase 2A `EvalCaller` Protocol seam (EVID-015) becomes load-bearing — no refactor needed at Phase 3
- ✅ User-ownership creates feedback loop accelerating both MoleculerPy and POLLMEVALS maturity
- ✅ POLLMEVALS architecture aligns with MASTER.md vision (eliminating vision-graph drift)

### Negative

- ❌ Phase 3 implementation cost: ~2-3 weeks (scheduler-svc + worker-svc + judge-svc + tests)
- ❌ MoleculerPy young — first POLLMEVALS integration test may surface primitives gaps (mitigated by ownership: user can fix)
- ❌ NATS broker becomes critical infra dep — outage blocks distributed runs (mitigated by single-process Phase 2A code remaining as fallback)
- ❌ Russian-English MoleculerPy docs may surface translation gaps when international contributors join

### Neutral

- POLLMEVALS stack adapter spec (`stacks/*/stack.yaml`) unchanged
- Public API (Hono TypeScript) decoupled from MoleculerPy per MASTER.md ("Public API should not depend on MoleculerPy maturity during v0.1")
- Frontend (Next.js leaderboard, PRD-004) unaffected
- Methodology v0.1.0 unchanged (this is orchestration layer, not methodology)

## Compliance

- Consistent with ADR-001 § Consequences (upgrade path mandate)
- Consistent with MASTER.md vision (10 mentions of MoleculerPy in eval-plane context)
- Consistent with CLAUDE.md "frozen methodology" principle (orchestration is not methodology)
- Honors red-line list (no destructive ops, no secrets in code)

## Links

- PRD-003 (parent — implementation target)
- ADR-001 (predecessor — Option B/C upgrade path)
- ADR-002 (reproduce semantics preserved by this decision)
- RFC-001 (Phase 2A baseline; EvalCaller Protocol from RR-7 is migration seam)
- EVID-015 (EvalCaller Protocol architect finding #4 — seam ready)
- EVID-016 (GridRunner — single-process baseline; becomes scheduler-svc action)
- EVID-018 (MoleculerPy capability audit — supporting evidence for this decision)
- EPIC-001 (ER-2 provider instability addressed; ER-7 Inspect AI risk unchanged)
- MASTER.md (vision alignment source)
- External: github.com/MoleculerPy/moleculerpy, github.com/MoleculerPy/moleculerpy-channels, moleculer.services/docs/0.14/
- NOTE-002 (Evidence Quality Standard — applied to EVID-018)





