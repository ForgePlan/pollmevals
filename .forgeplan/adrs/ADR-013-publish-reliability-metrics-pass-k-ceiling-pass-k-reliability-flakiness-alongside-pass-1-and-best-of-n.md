---
depth: standard
id: ADR-013
kind: adr
last_modified_at: 2026-06-01T23:14:28.582415+00:00
last_modified_by: claude-code/2.1.156
links:
- target: PRD-009
  relation: informs
- target: NOTE-011
  relation: informs
status: draft
title: 'Publish reliability metrics: pass@k ceiling + pass^k reliability + flakiness alongside pass@1 and best-of-N'
---

# ADR-013: Publish reliability metrics — pass@k + pass^k + flakiness

| Field | Value |
|-------|-------|
| Status | Proposed |
| Date | 2026-06-02 |
| Deciders | maintainer |

## Context and Problem Statement

A single `pass@1` (resolved rate) hides RELIABILITY: a stack that solves a task in
1 of 5 independent runs and one that solves it in 5 of 5 can report the same
headline number, yet they are very different products to ship. Our methodology
tenet is "never hide variance" — but pass@1 alone does exactly that.

Prior art (NOTE-011, Nebius SWE-rebench, 2026) reports BOTH pass@k (solved in ≥1
of k — capability ceiling) AND pass^k (solved in ALL k — reliability); their gap
is "flakiness" (got lucky once). Their finding "GPT-5.5 relies much less on luck"
is exactly a pass^k signal that pass@1 cannot express.

We already plan best-of-N (PRD-009) for the capability CEILING. The missing half
is the reliability FLOOR. How should the scoring contract report reliability?

## Decision Drivers

- Honesty about luck/variance ("never hide variance" tenet; CI already required).
- Cheap, deterministic, orthogonal to scoring policy (pure math over per-seed
  solved-flags; already implemented + tested).
- Pairs cleanly with best-of-N (PRD-009): ceiling vs floor.
- Aligns with credible external prior-art (SWE-rebench), easing comparison.

## Considered Options

- **A. pass@1 only (status quo)** — one resolved-rate number per cell.
- **B. + best-of-N capability ceiling only (PRD-009)** — pass@1 + pass@k.
- **C. + pass^k reliability + flakiness (CHOSEN)** — pass@1 + pass@k + pass^k +
  flaky (= pass@k − pass^k).
- **D. Gate publication on a pass^k threshold** — refuse to publish a stack whose
  pass^k is below some bar.

## Decision Outcome

Chosen: **Option C.** For each (model, stack, task-set) the run reports the full
quartet — `pass@1`, `pass@k` (ceiling), `pass^k` (reliability), and
`flaky = pass@k − pass^k` (the got-lucky band) — over k independent seeds.

- Implementation already merged: `apps/eval-core-py/src/scoring/pass_k.py` (PR #29)
  + unbiased `pass_at_k_estimator` for the n>k case.
- `k` is a methodology parameter (the smoke grid already runs k=3 seeds).
- **No hard pass^k threshold at v0.1** (rejects Option D for now): pass^k is a
  transparency/distribution metric, not a publication GATE. Setting a gate bar is
  deferred to a future MethodologyVersion once we have real multi-seed data to
  calibrate it.

## Consequences

- (+) Luck/variance is visible and quantified; two stacks with equal pass@1 are
  distinguished by pass^k. Honest reporting per our tenet.
- (+) Ceiling (best-of-N / pass@k) and floor (pass^k) are reported together — the
  complete capability-vs-reliability picture.
- (−) Requires k ≥ 2 independent runs per cell → cost scales ~×k for the
  multi-seed cells. Mitigated: the smoke grid already runs k=3; production picks k
  per run-type.
- This is a scoring-contract addition → bump MethodologyVersion when it lands in
  the published contract. A future ADR formalises a pass^k publication threshold
  if/when Option D becomes warranted.

## Invariants

- Run immutability (ADR-0002) holds: pass@k / pass^k are computed at AGGREGATION
  over already-recorded per-seed evals; they never mutate seed results.
- `pass^k <= pass@k` for every cell and task-set (the reliability floor can never
  exceed the capability ceiling) — guaranteed by construction (`all` implies `any`).
- The "solved" predicate is supplied by the caller and is NOT defined by this
  decision; the metric stays orthogonal to how a task counts as solved.

## Rollback Plan

Additive + behind the scoring contract. To roll back: stop publishing the
pass^k / flaky columns (revert the MethodologyVersion entry); the pure functions
in `src/scoring/pass_k.py` may remain unused — nothing else depends on them being
published. No data migration: historical runs keep their recorded per-seed evals
and can be re-aggregated either way.

## Affected Files

- `apps/eval-core-py/src/scoring/pass_k.py` — the math (merged PR #29).
- `docs/02-methodology/scoring.md` + `docs/04-runbook/08-scoring-contract.md` —
  the publish-policy + new MethodologyVersion entry (pending).
- the run-aggregation layer that groups evals by (model, stack, task) across seeds
  and calls these functions (pending the executor / multi-seed real runs).

## Related Artifacts

| Artifact | Relation |
|----------|----------|
| PRD-009 | informs |
| NOTE-011 | informs |

