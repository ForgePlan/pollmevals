---
depth: standard
id: PRD-009
kind: prd
links:
- target: ADR-012
  relation: based_on
- target: EPIC-002
  relation: refines
status: draft
title: 'Best-of-N flagship run-mode: capability ceiling AND reliability aggregates (I6)'
---

# PRD-009: Best-of-N flagship run-mode — capability ceiling AND reliability aggregates (I6)

> Implementation PRD for **initiative I6 of EPIC-002** (POLLMEVALS v0.2). Turns the **ADR-012** decision (Option C — best-of-N as an optional `flagship_triggered` run-mode reporting capability ceiling AND reliability **separately**, never best-only) into a buildable spec. `based_on` ADR-012; `refines` EPIC-002 (I6). This PRD is **purely additive** to the active scoring contract (PRD-002) and reuses the active manifest contract (SPEC-001) — it adds two aggregates and a flagship-only attempt count; it does **not** change `final_score`, the per-seed median + bootstrap CI, the judge pipeline, the `run_type` enum, or `seed_set`.
>
> SPARC phase: **Specification**. Status: **draft** (activation belongs to the orchestrator after a pilot EVID lands — see Open Questions). ADI run on parent ADR-012 (`forgeplan_reason`, gemini-3.1-pro-preview, High confidence) confirmed Option C and surfaced the evidence-needs captured as Open Questions below.

## Problem

POLLMEVALS today runs one attempt per seed — `(model, stack, task, seed, region) → output` — and reports a **per-seed median + bootstrap 95% CI** across seeds (`docs/02-methodology/scoring.md`). That distribution answers *"does this stack usually do the task?"* (central tendency) and captures variance as the seed spread. It does **not** answer a different, distinct question: *"can this stack **ever** do the task?"* — because **median ≠ max**. There is today no explicit **CAPABILITY-CEILING** metric separate from **RELIABILITY**.

The pain (parent: EPIC-002 I6; decision: ADR-012): a **flaky** stack (occasionally brilliant, usually mediocre) and a **steady** stack (consistently good) can share the same central tendency and be indistinguishable, or conversely share a ceiling while differing wildly in consistency. A maintainer comparing flagship stacks cannot currently tell these apart. Prior art (AfterQuery App-Bench, project memory `research-afterquery-appbench`) measures the ceiling via **best-of-3** but reports **only the best** — which **HIDES variance**, the exact thing POLLMEVALS commits never to do (`docs/02-methodology/scoring.md`; `CONTEXT.md` anti-glossary: *"Score — always a distribution"*).

ADR-012 resolved this: adopt best-of-N's *capability-ceiling method* but report **both** ceiling **and** reliability, never collapse to one number — and gate it to flagship runs because each attempt is scored by the full judge panel (PRD-002, N≥3 judges), so N attempts cost **×N judge calls** (the dominant cost line; project memory point: a 2+2 sample with 2 judges ≈ $0.01, judge tokens dominating candidate tokens). This PRD specifies the run-config, the two additive aggregates, the immutability/manifest extension, the leaderboard rendering, and the cost accounting. It does **not** re-decide any of ADR-012's settled choices; it resolves ADR-012's explicitly-deferred open questions (the value of N, the exact reliability metric, leaderboard rendering, Pareto interaction) **with a method**, not invented numbers.

## Goals

- Make **capability ceiling** an explicit, first-class reported aggregate (max final_score over N attempts, with its own bootstrap CI), distinct from the canonical median + bootstrap CI — answering *"can it ever?"* observably.
- Make **reliability** an explicit, first-class reported aggregate across the N attempts (primary metric chosen by pilot — pass@1 / score-std / CI-width), reported **separately** from ceiling — answering *"does it consistently?"* observably.
- A **flaky** stack and a **steady** stack with comparable ceilings are **distinguishable** in the output — variance is never hidden (honors `scoring.md` "never hide variance"; ADR-012 Invariant 1).
- Best-of-N is **opt-in and cost-bounded**: it runs only under `flagship_triggered` (SPEC-001), never under default `smoke`/`weekly`; default-run budgets (PRD-002 NFR-001) are untouched.
- The canonical scoring contract (PRD-002 `final_score`, per-seed median + bootstrap CI, judge calibration α/MAD gates) and the manifest contract (SPEC-001 `run_type`, `seed_set`) **survive untouched** — this layer is strictly additive.

## Non-Goals / Out of scope

- **Making best-of-N the default.** It is flagship-only (ADR-012 Invariant 4); default `smoke`/`weekly` runs are unchanged. Out of scope to enable N>1 on default runs.
- **Best-only reporting.** Reporting the single best attempt is **rejected by ADR-012** (Option B, Invariant 1) — it hides variance. Out of scope, forbidden.
- **Changing the canonical `final_score` / per-seed median + bootstrap CI / judge pipeline.** PRD-002 stays untouched. Ceiling and reliability are **auxiliary** aggregates computed beside `final_score`, never folded into it (ADR-012 Invariant 2/3). This PRD adds aggregates only.
- **Changing the `run_type` enum or `seed_set` semantics** (SPEC-001). Best-of-N **reuses** `flagship_triggered` and the existing explicit `seed_set` list (N seeds = N attempts). No new run-model is invented.
- **Inventing a parallel attempt mechanism.** N attempts are produced by the existing multi-seed fan-out (ADR-012 §Decision-2). A separate "attempt" axis distinct from seeds is out of scope.
- **Solving the Pareto-frontier interaction.** Whether best-of-N implies a *second* frontier (ceiling-vs-cost distinct from median-vs-cost) and how it renders is a **deferred design question** — noted as an Open Question with a method, **not solved here** (ADR-012 deferred list).
- **Choosing the heuristic-cheap-judge variant (Option E).** Judging only a heuristically-selected "best" attempt was rejected by ADR-012 (falsifies the ceiling, smuggles best-only bias). Every attempt is judged by the full panel. Out of scope.
- **Importing external task content.** Only the *method* (multiple attempts → ceiling) is adopted (ADR-007); no AfterQuery task content (ADR-012 Invariant 6).

## Target users / actors

- **POLLMEVALS maintainer (gogocat)** — the primary human actor. Configures a `flagship_triggered` run with N>1 to compare flagship stacks where the capability-ceiling-vs-reliability distinction matters (e.g. "stack A is occasionally brilliant but flaky; stack B is steady — which do I recommend for production?"). Reads ceiling + reliability + median on the leaderboard.
- **Methodology reviewer (external, pre-launch)** — consumes the published flagship run to verify variance is reported (not hidden) and that the two aggregates are clearly distinct from `final_score`.
- **System actor — orchestrator grid runner** (`apps/eval-core-py/src/orchestrator/grid_runner.py`) — fans out N seeds per `(model, stack, task)` for a flagship best-of-N run, reusing existing seed fan-out.
- **System actor — aggregation step** (run status `aggregating`, SPEC-001 state machine) — computes the ceiling and reliability aggregates alongside the existing per-seed median + bootstrap CI.
- **System actor — leaderboard renderer** (`apps/site/`) — displays ceiling + reliability + median together without implying a single winner.
- **System actor — cost/budget gate** (`grid_runner` budget check, PRD-002 NFR-001 / NFR-005) — enforces flagship-only gating and accounts for the ×N (candidate + judge) cost.

## Functional Requirements

Each FR is a checkbox item with a one-line behaviour statement, a priority, and acceptance criteria. Every "System shall" statement is observable. Measurement-method detail (the statistical machinery behind ceiling/reliability/cost) lives in the NFRs and the Open Questions, not here.

- [ ] **FR-001** (must): System shall accept an OPTIONAL best-of-N run configuration that produces **N attempts** per `(model, stack, task)` by reusing the existing multi-seed mechanism — **N distinct seeds = the N attempts** (SPEC-001 `seed_set`, `minItems: 1`) — and shall map this configuration **only** onto the `flagship_triggered` run_type. No parallel run-model is introduced.
  - Given a run configured with `run_type=flagship_triggered` and a best-of-N config of N seeds (N=TBD per OQ-1, candidate 3), when the grid runner expands the grid, then it produces exactly N attempts per `(model, stack, task)` cell, one per distinct seed, using the existing seed fan-out (no new attempt axis).
  - Given a run configured with `run_type` ∈ {`smoke`, `weekly`, `calibration`, `ablation`}, when a best-of-N config (N>1) is supplied, then the system shall refuse/ignore the best-of-N expansion and run a single attempt per seed as today (gating — see FR-006).
  - Given the run manifest, when written, then `run_type=flagship_triggered` and `seed_set` lists exactly the N seeds used (SPEC-001 contract unchanged).

- [ ] **FR-002** (must): System shall compute and record a **CAPABILITY-CEILING** aggregate = **max `final_score` over the N attempts**, with its own confidence interval, as a NEW aggregate stored **beside** the existing per-seed median+CI. It shall **not** modify or replace `final_score` (ADR-012 Invariant 2; PRD-002 `final_score` contract untouched).
  - Given N completed, scored attempts for a `(model, stack, task)` cell, when the aggregation step runs (status `aggregating`), then it records a `capability_ceiling` value = max of the N `final_score` values, with a confidence interval computed over the N attempts (method per NFR-001 / scoring.md).
  - Given the recorded aggregates, when inspected, then `capability_ceiling ≥ median` holds by construction (max ≥ central tendency) on every cell.
  - Given the manifest, when validated, then the canonical per-seed `median` + 95% CI is still present and unchanged, and `final_score` semantics (PRD-002: weighted sum of 0–10 components) are unaltered — `capability_ceiling` is an additional key, never a substitution.

- [ ] **FR-003** (must): System shall compute and record a **RELIABILITY** aggregate across the N attempts, reported **separately** from the ceiling — never collapsed into a single "best" number (ADR-012 Invariant 1). The **primary** reliability metric is **TBD** (candidates: pass@1 success rate / score std-dev / CI-width — chosen and justified by pilot per OQ-2). The system shall record the chosen primary metric and MAY record secondaries for cross-check.
  - Given N scored attempts for a cell, when aggregation runs, then it records a `reliability` aggregate (primary metric per OQ-2) as a distinct manifest key, alongside but separate from `capability_ceiling` and `median`.
  - Given two cells with comparable `capability_ceiling`, when their `reliability` aggregates differ (one flaky, one steady), then the recorded `reliability` values differ measurably (the metric discriminates — see FR-005 / AC-3).
  - Given the output, when rendered or serialized, then no field collapses ceiling and reliability into one scalar; both are independently readable (ADR-012 Invariant 1).

- [ ] **FR-004** (must): System shall record each of the N attempts as its own **immutable, content-addressed artifact** (ADR-0002; ADR-012 Invariant 5), and the run manifest (SPEC-001) shall record the attempts and their seeds. No attempt is mutated or dropped; more attempts means more artifacts, never edits in place.
  - Given a best-of-N flagship run, when each attempt completes, then its outputs are written as content-addressed artifacts under the SPEC-001 layout (`evals/{eval_id}/{type}-{sha256}.{ext}`), one `eval_id` per attempt (the existing `eval_id = sha256(run_hash + model_id + stack_id + task_id + seed)[:16]` already disambiguates by seed).
  - Given a published best-of-N manifest, when a process attempts to mutate any attempt's artifact or score, then the write fails (read-only mode / object-lock per SPEC-001 AC-2).
  - Given the manifest, when read, then all N attempts for each cell appear in `evals[]` (none dropped, mirroring SPEC-001 AC-5 for failed evals) and their seeds are recoverable from `seed_set` + each `EvalRow.seed`.

- [ ] **FR-005** (must): System shall render the leaderboard for a best-of-N flagship run showing the **capability ceiling**, the **reliability** aggregate, AND the canonical **median + CI** **together**, in a layout that does **not** imply a single winner / does not present a lone "best" number (ADR-012 Invariant 1; anti-Option-B). The exact visual layout is **TBD** per OQ-3 (resolved by a UI/CLI mock).
  - Given a published best-of-N flagship run, when the leaderboard renders a `(model, stack, task)` row, then capability ceiling, reliability, and median+CI are all visible and visually distinct (no single column is presented as "the score").
  - Given a flaky stack (high ceiling, low reliability) and a steady stack (comparable ceiling, high reliability), when both are rendered, then a reader can distinguish them from the displayed ceiling + reliability without consulting raw data (the discrimination is surfaced, not buried).
  - Given the rendering, when reviewed against the OQ-3 mock, then it matches the agreed no-single-winner layout (clutter acceptance is the OQ-3 gate).

- [ ] **FR-006** (must): System shall account for best-of-N cost as **×N the single-attempt cost INCLUDING the full judge panel per attempt** (judges are the dominant line — PRD-002 NFR-001, `CONTEXT.md` cost definition), shall reflect this in the run's `aggregates.total_cost_usd` (SPEC-001), and shall **enforce flagship-only gating** so default `smoke`/`weekly` budgets never absorb the ×N cost (ADR-012 Invariant 4).
  - Given a best-of-N flagship run with N attempts per cell, when costs are aggregated, then `aggregates.total_cost_usd` = the sum over all N×cells of (candidate call cost + full judge-panel cost per attempt) — i.e. ≈ N× the single-attempt total per cell, within measurement tolerance (TBD% per OQ-6 — candidate ±10% mirroring SPEC-001 cost cross-check).
  - Given a best-of-N config supplied with `run_type` ∈ {`smoke`, `weekly`}, when the run is launched, then the gating refuses to apply N>1 (no ×N judge cost is incurred on default runs) — verified by a gating test.
  - Given the budget gate (`BUDGET_ABORT_PCT`, PRD-002 NFR-001/NFR-005), when a flagship best-of-N run's projected cost exceeds the flagship cap, then the run aborts/degrades per existing budget policy (the ×N cost is included in the projection, not discovered after the fact).

## Non-Functional Requirements

Each NFR has a category, a measurable threshold, and a measurement method. Unknown numbers are `TBD` with a method — never invented.

### NFR-001 — Cost (flagship best-of-N envelope)
- **Category**: cost
- **Threshold**: Flagship best-of-N run total ≈ **N × the single-attempt flagship cost**, including the judge panel per attempt. Absolute cap = **TBD** (the flagship-run budget cap; the smoke cap is $50 per SPEC-001 / PRD-002 NFR-001 — the flagship cap is set by the I6 pilot, not invented here). Single-attempt cost basis is grounded by the existing measured data point (~$0.01 for a 2+2 sample with 2 judges, judge tokens dominating; project memory) — to be re-measured at flagship scale.
- **Measurement**: `aggregates.total_cost_usd` from the manifest cross-checked against the LiteLLM proxy `/credits` (SPEC-001 cross-check, delta > 10% → alert); the per-attempt ×N multiplier validated by the OQ-1 pilot dry-run-cost-estimate before launch (PRD-002 NFR-002 ratio gate pattern).

### NFR-002 — Additivity / contract non-regression
- **Category**: compatibility
- **Threshold**: **Zero** change to `final_score` semantics, the per-seed median+CI, the PRD-002 judge calibration gates (α ≥ 0.70 CI-lower, MAD ≤ 1.5), the SPEC-001 `run_type` enum, and the SPEC-001 `seed_set` semantics. The two new aggregates appear only as additional keys under `aggregates` / `per_task_metrics` (already an open map in SPEC-001).
- **Measurement**: schema diff on `run-manifest.schema.json` shows only additive keys (no removed/changed required fields); a default `smoke`/`weekly` run's manifest is structurally identical to pre-change output (no new required fields on default runs); PRD-002 acceptance tests still pass unchanged.

### NFR-003 — Immutability
- **Category**: reliability
- **Threshold**: 100% of best-of-N attempts are immutable content-addressed artifacts (ADR-0002); 0 in-place mutations after `published`.
- **Measurement**: attempt artifacts written read-only (mode 0444 / object-lock per SPEC-001 AC-2); a mutation-attempt test fails the write; manifest re-read after publish is unchanged.

### NFR-004 — Reliability-metric discriminating power (gates the choice of metric)
- **Category**: methodology quality
- **Threshold**: The chosen primary reliability metric (OQ-2) must **measurably separate** a known-flaky from a known-steady stack on pilot data — separation magnitude **TBD** (the discrimination threshold is set by the pilot; not invented). If the candidate metric cannot separate them, it is rejected in favour of an alternative (pass@1 / std / CI-width).
- **Measurement**: OQ-2 pilot computes all candidate metrics on a flaky-vs-steady stack pair and selects the metric with the clearest separation; recorded in the pilot EVID.

### NFR-005 — Leaderboard legibility (gates the rendering)
- **Category**: usability
- **Threshold**: Ceiling + reliability + median+CI render together **without unacceptable clutter** — acceptability is a **TBD** qualitative gate defined by the OQ-3 mock review (no invented numeric clutter score).
- **Measurement**: OQ-3 UI/CLI mock reviewed against the "no single winner, all three legible" criterion; sign-off recorded in the rendering EVID.

## Constraints

### Technical
- Must reuse the existing multi-seed fan-out in `apps/eval-core-py/src/orchestrator/grid_runner.py` (N seeds = N attempts); no parallel attempt mechanism (ADR-012 §Decision-2).
- Must extend `packages/contracts/schemas/run-manifest.schema.json` + `apps/eval-core-py/src/contracts/` **additively** — the two aggregate keys go under `aggregates` / `per_task_metrics` (already an open map, SPEC-001); `run_type` and `seed_set` are reused unchanged.
- Aggregates computed at the `aggregating` status step of the SPEC-001 run state machine, beside the existing per-seed median+CI.
- Judge panel is invoked per attempt via the existing PRD-002 pipeline (Inspect AI `multi_scorer` / list-of-scorers per EVID-023) — no change to judge invocation, only N× as many invocations.

### Business
- Cost-bounded by flagship-only gating: default-run budgets (PRD-002 NFR-001, $50 smoke) must never absorb the ×N judge cost (ADR-012 Invariant 4).
- v0.2 scope; solo maintainer (gogocat); method-only adoption from AfterQuery (ADR-007) — no external task content.

### Regulatory
- None specific. (Provenance discipline per ADR-007 / EPIC-002 Success Criterion 4: zero external task content — a methodology constraint, not a legal one.)

## SMART Acceptance Criteria (top-level, ship-or-not-ship)

These are the criteria for the entire specification. Each is Specific, Measurable, Achievable, Relevant, Time-bound. Unknown numbers carry a method (TBD-with-pilot), never an invented value.

1. **AC-1 — End-to-end record**: A `flagship_triggered` best-of-N run (N=**TBD**, candidate 3 — fixed by OQ-1 pilot) over **≥ 1** `(model, stack, task)` cell records, within that single run's `aggregating` step, **all four** of: N immutable content-addressed attempts (in `evals[]`), a `capability_ceiling` aggregate (max + CI), a `reliability` aggregate (primary metric per OQ-2), and the canonical per-seed `median`+CI — and the resulting manifest passes `run-manifest.schema.json` validation with **0 errors**. *(Measured by: schema validation pass + manifest field-presence assertion on the pilot run.)*

2. **AC-2 — Construction sanity + distinctness**: On the recorded run, **`capability_ceiling ≥ median ≥ floor`** holds by construction for every cell (max ≥ central tendency ≥ min — a sanity invariant), AND the `reliability` aggregate is computed and is a **distinct field** from `capability_ceiling` (not derived as a trivial restatement of it). *(Measured by: per-cell numeric assertion `ceiling ≥ median ≥ floor` and a field-distinctness check on the manifest.)*

3. **AC-3 — Flaky vs steady distinguishable (the whole point)**: Given a **flaky** stack (high ceiling, low reliability) and a **steady** stack (comparable ceiling, high reliability) in the same run, the two are **distinguishable in the output** — their `reliability` aggregates differ by at least the OQ-2-pilot-set discrimination threshold (**TBD**, set by pilot), and the difference is visible on the leaderboard (FR-005). Variance is not hidden. *(Measured by: the OQ-2 pilot's flaky-vs-steady separation result + a leaderboard-render check that both rows are distinguishable.)*

4. **AC-4 — Gating + cost**: Best-of-N **never** runs under `smoke`/`weekly` run_type (gating verified by a test that supplies N>1 under each default run_type and asserts a single attempt per seed is run / N>1 is refused), AND the flagship run's `aggregates.total_cost_usd` ≈ **N×** the single-attempt cost **including judges**, within **TBD%** tolerance (candidate ±10%, mirroring the SPEC-001 LiteLLM cost cross-check). *(Measured by: gating unit test + manifest `total_cost_usd` vs N× single-attempt baseline, cross-checked against LiteLLM `/credits`.)*

## Open Questions

The questions that block finalisation/activation, each with a **method** to resolve and a `TBD` owner. These are exactly ADR-012's explicitly-deferred questions plus one hidden assumption surfaced by the parent ADI. Activation of this PRD requires the OQ-1/OQ-2/OQ-3 pilot EVID to land (the ADI cycle's evidence-needs).

- **OQ-1 — The value of N.** AfterQuery used 3; the right N for POLLMEVALS is **TBD**. *Method*: a small pilot plots **marginal capability-ceiling gain vs the linear ×N judge-cost increase** and picks the knee (ADI evidence-need, Medium effort). Candidate N=3 pending the plot. — owner: TBD
- **OQ-2 — The exact reliability metric.** **pass@1 success rate** vs **score std-dev** vs **CI-width** (or a combination) — **TBD**. *Method*: the OQ-1 pilot computes all candidates on a known **flaky-vs-steady** stack pair and selects the metric with the clearest separation (NFR-004; ADI evidence-need, Medium effort); justify the primary, record secondaries. — owner: TBD
- **OQ-3 — Leaderboard rendering.** How ceiling **and** reliability render alongside the canonical median+CI **without clutter** — **TBD**. *Method*: a low-effort **UI/CLI mock** reviewed against the "no single winner, all three legible" gate (NFR-005; ADI evidence-need, Low effort). — owner: TBD
- **OQ-4 — Pareto-frontier interaction.** Whether best-of-N implies a **second** Pareto frontier (**ceiling-vs-cost** distinct from the existing **median-vs-cost**) and how that is presented — **TBD**, **not solved in this PRD** (ADR-012 deferred). *Method*: a follow-up design note / mini-ADR once OQ-1–OQ-3 land and there is real flagship best-of-N data to reason over; flagged as a design question, deliberately deferred. — owner: TBD
- **OQ-5 — Seed-independence assumption (surfaced by parent ADI).** The ceiling is only meaningful if **N distinct seeds generate sufficiently independent attempts** (parent ADI H1 assumption). If attempts are near-identical (low seed sensitivity for a given stack/task), the "ceiling" degenerates toward the median and adds little signal. *Method*: the OQ-1 pilot also inspects inter-attempt variance per cell; if attempts are near-degenerate for a class of tasks, record that best-of-N adds little there (and possibly restrict N>1 to high-variance task types). — owner: TBD
- **OQ-6 — Cost tolerance %.** The exact acceptable tolerance on "≈ N×" cost (FR-006 / AC-4) — candidate ±10% mirroring the SPEC-001 LiteLLM cross-check, but **TBD** confirmation. *Method*: confirm against the OQ-1 pilot's measured cost vs N× baseline. — owner: TBD

## Related Artifacts

- **ADR-012** — the parent decision this PRD implements (`based_on`). Decided Option C: best-of-N as optional `flagship_triggered` run-mode reporting capability ceiling AND reliability separately, never best-only; reuse multi-seed mechanism; additive to PRD-002. This PRD resolves ADR-012's four deferred open questions (N, reliability metric, leaderboard rendering, Pareto interaction) with methods. Honors ADR-012's six invariants.
- **EPIC-002** — roadmap parent (`refines`). This is initiative **I6** ("Best-of-N attempts — capability ceiling vs reliability; report variance"). Authoring this PRD is the "activation + I6 PRD" follow-up the EPIC lists for I6.
- **PRD-002** (active) — judge/scoring infrastructure. **Additive** relationship (prose only, no graph edge from this PRD per the orchestrator's link discipline): the two aggregates sit **beside** `final_score`; PRD-002's `final_score` contract, α/MAD calibration gates, and NFR-001 budgets are **untouched**. PRD-002 lists "Pairwise comparison mode" under v0.1 Out-of-Scope but **not** best-of-N — no contradiction.
- **SPEC-001** (active) — manifest + eval + artifact contracts. **Reused, not changed** (prose only, no graph edge): `run_type=flagship_triggered` and the explicit `seed_set` list (N seeds = N attempts) are reused as-is; the two aggregates surface under the existing open `aggregates` / `per_task_metrics` map; per-attempt artifacts use the existing content-addressed `eval_id` / path layout.
- **ADR-0002** (legacy `docs/adr/0002-run-immutability.md`) — each attempt is a new immutable content-addressed artifact; nothing edited in place (FR-004, NFR-003).
- **ADR-007** — prior-art sourcing, method only: best-of-N's *method* is adopted; no AfterQuery task content.
- **EVID (to be created — gates activation)**: the OQ-1/OQ-2/OQ-3 **pilot EVID** (choose N via marginal-ceiling-vs-cost; select the reliability metric via flaky-vs-steady separation; sign off the rendering mock). This PRD stays **draft** until that EVID lands and the orchestrator activates — consistent with ADR-012's Trust-Calculus R=5 remediation.

> Note: per the orchestrator's strict link discipline for this task, this PRD declares exactly two graph edges — `based_on` ADR-012 and `refines` EPIC-002. All other relationships above are descriptive prose, not link declarations.


