---
depth: standard
id: NOTE-008
kind: note
last_modified_at: 2026-05-28T13:01:02.156885+00:00
last_modified_by: claude-code/2.1.152
status: active
title: tech-debt cleanup Wave 0+1 deferred — A3 + Fishbone analysis pre PRD-006 Wave 1
---

# A3 + Fishbone — Wave 0+1 deferred tech-debt cleanup pre PRD-006 Wave 1

Single-page A3 analysis (Background → Current → Target → Analysis → Countermeasures → Plan → Follow-up) plus a Fishbone (Ishikawa) systemic-vs-local debt split. Produced as Step 1 of a 5-step Smith Plan dispatch on 2026-05-28. Do not activate — orchestrator activates at Step 5 after guardian gate.

## Background

Why this matters now:

- PR #22 merged 2026-05-26 — 3 task packs (`be_01_jwt_auth`, `fe_01_multistep_form`, `doc_01_cli_readme`) authored from empty scaffold to calibration-ready state.
- 75 calibration samples (5 idioms/voices × 5 bands × 3 packs) + 3 gold solutions are live.
- Anti-SLOP gates G1 + G3 + G4 PASS on 91 files; RFC-003 (authoring protocol) + ADR-007 (hybrid sourcing) are both active.
- BUT: 4 NOW-block deferred operational items + 1 decision-debt blind spot (ADR-007 active without linked evidence) + 7 blocked upstream artifacts remain.
- Next big sprint is PRD-006 Wave 1: 7 new task packs × ~50–60h via RFC-003 parallel dispatch — that would land 7 more gold solutions + 175 more calibration samples on top of a shaky foundation.

In Toyota A3 terms: we shipped a content wave with hot-fix discipline (merge then patch). Wave 1 is the leverage event — if we let it run with un-backfilled evidence and missing infra, every defect compounds 7×.

## Current state

Existing tech-debt landscape, concretely:

- **4 NOW-block operational items**:
  1. Docker image `pollmevals-eval-ts:0.1.0` not built locally (sandbox needs the container to run TS evaluators).
  2. Dynamic eval verification deferred — `CorrectnessEvaluator` + `CoverageEvaluator` never run against the 75 calibration samples to confirm band separation.
  3. Lifecycle promote 3 packs from `lifecycle_state=draft` → `calibration` (per `docs/04-runbook/task-lifecycle.md`).
  4. Type narrowing fix at `apps/eval-core-py/src/.../gold/solution.ts:55` (1-line patch — `unknown` should narrow to `string` via `typeof` guard).
- **1 decision-debt blind spot**: ADR-007 "Hybrid task-pack sourcing (50% generated, 50% curated)" — `status=active` but no EVID linked, so `R_eff(ADR-007) = 0.0`. 75 current + 175 future calibration samples are built on this rule.
- **7 blocked upstream artifacts** (dependency chain — listed for visibility, not for this sprint):
  - ADR-004 ← PRD-003
  - EVID-022 ← EVID-021
  - NOTE-006 ← NOTE-005
  - RFC-003 ← PRD-006
  - SPEC-002 ← PRD-004 + NOTE-005
  - PRD-006 ← NOTE-005
  - NOTE-005 ← NOTE-004
- **Hindsight MCP disconnected this session** — no auto-recall, no manual `memory_retain` possible. Lessons learned this sprint will need to be re-captured next session if Hindsight reconnects.

## Target state

Quantifiable end-state for this 1-hour 5-step sprint:

- `forgeplan health` reports **0 Blind Spots** (ADR-007 must no longer appear in that section).
- `docker build infra/docker/eval-ts/ -t pollmevals-eval-ts:0.1.0` exits 0 on the maintainer's laptop.
- 3 task packs verified at `lifecycle_state=calibration` (per `docs/04-runbook/task-lifecycle.md` checklist).
- Dynamic eval (`CorrectnessEvaluator` + `CoverageEvaluator`) shows the expected band separation on the 75 calibration samples: `broken band ≤ 0.20`, `perfect band ≥ 0.85`.
- Type narrowing at `gold/solution.ts:55` fixed (1-line patch, `tsc --noEmit` green).
- All 6 artifacts (this NOTE A3, EVID ADI for ADR-007, code-diff Docker + dynamic-eval verification, code-diff lifecycle promote + type fix, EVID from tester subagent, EVID from guardian subagent with verdict) land in **one PR** per user preference (`feedback_fewer_larger_prs.md`).
- The 7 blocked upstream artifacts remain **untouched** — deliberate scope decision. They unblock with NOTE-004/005 cleanup in a separate sprint, not this one.

## Analysis

See the `## Fishbone` section below for the full systemic-vs-local debt split across 4 standard fishbone bones (People/Process, Tools/Infra, Methods, Measurement).

**Root cause one-liner**: Wave 0+1 closed with operational hot-fix discipline (merge then patch) rather than full evidence-chain closure — this is acceptable if cleaned up **before** Wave 1 leverages it, unacceptable if Wave 1 starts first.

## Countermeasures

The 5-step Smith Plan dispatch, briefly:

1. **Step 1 (this NOTE)** — articulate why-now via A3 + Fishbone. Output: NOTE-008 in draft.
2. **Step 2 — ADI EVID for ADR-007** — decision-debt first because ADR underpins all 75 + future 175 samples. If the ADI cycle surfaces `verdict: refutes`, we catch it BEFORE leveraging the rule, not after.
3. **Step 3 — Docker image build + dynamic eval verification** — operational debt. Parallel-safe with Step 4 once Step 2 is green.
4. **Step 4 — Lifecycle promote 3 packs → calibration + type narrowing fix at `gold/solution.ts:55`** — finish the NOW-block.
5. **Step 5 — Tester EVID + Guardian gate verdict** — guardian links the evidence chain (NOTE-008 ← EVID-ADI ← code-diffs ← tester-EVID ← guardian-EVID), produces a verdict, and only THEN activates NOTE-008 + ADR-007 evidence. One PR.

## Plan

Sequencing rationale (why this order):

- **Decision-debt before operational-debt** (Step 2 before Steps 3–4) because ADR-007 ADI backfill could surface a `verdict: refutes` outcome that requires a Row 7 re-decision. Better to discover this BEFORE we invest Docker-image and lifecycle-promotion effort than AFTER. If Step 2 reveals weak grounds, Steps 3–4 may need to be re-scoped to a different ADR.
- **One PR at the end** (Step 5) per user preference (`feedback_fewer_larger_prs.md` — "Fewer larger PRs > many micro-PRs"). The single `chore:` PR folds: A3 NOTE creation, ADR-007 EVID, Docker image build artifact, lifecycle promote diffs, type narrowing fix, tester EVID, guardian EVID + verdict. Reviewers see the whole picture in one diff.
- **7 blocked upstream artifacts NOT addressed** — scope discipline. NOTE-004/005 cleanup belongs to a separate sprint with its own A3.

## Follow-up

What gets re-examined 1 week after the PR merges:

- Re-run `forgeplan health` — confirm 0 Blind Spots, `R_eff(ADR-007) > 0`.
- Run `forgeplan list --status draft` — confirm 15 drafts is the floor, not growing (currently 15; growth would mean we are accumulating debt faster than we close it).
- If next sprint (PRD-006 Wave 1) reveals that the ADR-007 evidence was insufficient to support the 50/50 hybrid decision at higher leverage → write `note-techdebt-wave0-rollback-rationale` and reopen ADR-007 via Row 7 (supersede with a corrected ADR).
- **Hindsight reconnection check** — if `mcp__plugin_fpl-hsmem_hindsight__*` tools come back online next session, retain at most 3 non-obvious findings from this sprint:
  1. Rationale for decision-debt-first ordering (this A3's Plan section).
  2. Observed band separation post-dynamic-eval (numeric result from Step 3).
  3. Any new G-gate (anti-SLOP) failure modes surfaced by Step 4 lifecycle-promote checks.

## Fishbone (Ishikawa) — systemic vs local debt split

Categorisation across the 4 standard fishbone bones. **Systemic** = pattern that will repeat across waves and needs a meta-fix; **Local** = one-off miss, fix-and-forget.

| Category | Systemic (pattern, will repeat) | Local (one-off, fix-and-forget) |
|---|---|---|
| **People / process** | ADR-007 active without evidence reveals a pattern — when content waves merge fast, evidence-backfill discipline slips. Meta-fix candidate: pre-merge hook that blocks activation of any ADR with `R_eff = 0`. | None |
| **Tools / infra** | Docker image missing reveals — `infra/docker/eval-ts/` Dockerfile is not in CI build matrix. Meta-fix candidate: CI step that builds the image on every push to `main`, OR documented manual procedure pinned in the runbook. | Type narrowing at `gold/solution.ts:55` — one-line miss, no pattern. |
| **Methods** | Lifecycle promote is a documented per-pack manual step (per `docs/04-runbook/task-lifecycle.md`) — pattern question: should this be automated via post-merge hook? Pending decision; for this sprint, manual is OK. | None |
| **Measurement** | Dynamic eval verification deferred because Docker image deferred — circular dependency. Meta-fix candidate: make a built Docker image a hard prereq for `forgeplan activate` on any task pack (add to lifecycle gate). | None |

**Systemic bones** (ADR-007 evidence-backfill discipline; Docker-image-as-prereq for task-pack activation) need follow-up beyond this sprint — they belong in a future RFC for the Wave authoring protocol, not in this NOTE. **Local bones** (type narrowing at `gold/solution.ts:55`) are one-shot and close inside this sprint.

---

**Status**: draft (orchestrator activates after Step 5 guardian gate).
**Links**: none yet (orchestrator builds the evidence chain at Step 5).
**Refs**: `note-tech-debt-cleanup-wave-0-1-deferred-a3-fishbone-analysis-pre-prd-006-wave-1`





