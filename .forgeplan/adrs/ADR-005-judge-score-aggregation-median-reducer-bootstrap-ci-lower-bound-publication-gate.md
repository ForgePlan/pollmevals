---
depth: standard
id: ADR-005
kind: adr
last_modified_at: 2026-05-24T19:05:51.683473+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-002
  relation: informs
- target: EVID-001
  relation: informs
- target: RFC-002
  relation: informs
status: active
title: judge score aggregation — median reducer + bootstrap CI lower-bound publication gate
---

# ADR-005: judge score aggregation — median reducer + bootstrap CI lower-bound publication gate

## Status

draft

> Companion artifact: **RFC-002** (implementation plan, authored in parallel under the same `PRD-002` parent). Cross-reference is intentional — both documents share `informs → PRD-002` and `informs → EVID-001` parent edges. Once RFC-002 lands, orchestrator should add an explicit `informs` edge ADR-005 ↔ RFC-002.

## Context

POLLMEVALS uses LLM judges to score subjective eval outputs (frontend UX, docs clarity, review quality) where automatic metrics are insufficient. Two interlocking design choices in PRD-002 — the per-eval **reducer** (how N per-judge scores collapse to 1 published number per criterion) and the **publication gate** on Krippendorff α (the inter-judge agreement threshold below which a run is refused publication) — are declared by frozen methodology v0.1.0 (`docs/02-methodology/judge-policy.md:7` = "median"; `:27` = "α ≥ 0.70") but without rationale or gate semantics (point estimate vs. confidence-interval bound). PRD-002 Q1 and Q2 captured the choices; this ADR captures **why**.

The reducer choice matters because Inspect AI's default `multi_scorer(model_graded_qa(model=[list]))` aggregates via majority-vote (for classification) or arithmetic mean (for scalar rubric scores). At N=3 judges (the methodology floor), a single outlier judge owns 1/3 of the mean weight — one judge mis-scoring a `7/10` answer as `2/10` pulls the published score from `7.0` to `~5.3` even when the other two judges agreed at `7`. The methodology source-of-truth (`scoring.md:27`) and `judge-policy.md:7` both name median, but the divergence from HELM (EVID-001, claim 4: "HELM Capabilities 2025 uses mean") is undocumented in rationale form.

The publication gate semantics matter because at smoke-run scale (45 evals × 3 judges = 135 judgments) Krippendorff α has wide sampling variance. PRD-002 H3 predicts bootstrap 95% CI width ≥ 0.12 (e.g., point=0.72, CI=[0.62, 0.78]). Under a **point-estimate** gate, a run with "true" α ≈ 0.65 can pass by sampling luck whenever its observed point lands above 0.70. Under a **CI lower-bound** gate, that same run is refused — the gate trades occasional false-negatives (well-agreed runs rejected) for protection against false-positives (weakly-agreed runs published).

## Decision Drivers

- **Single-judge outlier robustness at N=3**: median weight on any single judge is 0 once a second judge disagrees; arithmetic mean weight is always 1/N. At N=3 the difference is operationally large.
- **Frozen methodology already declares median** (`judge-policy.md:7`, `scoring.md:27`) — this ADR formalises rationale rather than choosing fresh.
- **Small-N statistical instability of α** at smoke scale (135 judgments) — point-estimate gates are unreliable when CI width exceeds the gate margin.
- **Conservative-vs-lenient gate trade-off**: false-negative on borderline runs (cost: re-run or add judges) is cheaper and more reversible than a false-positive (cost: published leaderboard credibility damage that compounds over time).
- **Bootstrap CI is industry-standard for small-sample inference** and already declared by `scoring.md:45` ("bootstrap 95% confidence interval") for category aggregates — extending it to the α gate is consistent.
- **Reversibility**: both choices revert via a single config-flag flip (`reducer: median|mean`, `gate_mode: ci_lower|point`) plus re-scoring archived manifests; no schema migration required.

## Considered Options

### Reducer

#### Option R1: Median per criterion (CHOSEN)

`final_score[criterion] = statistics.median(per_judge_rubric_scores[criterion])`, computed independently per rubric criterion. For documentation tasks (`scoring.md:27`), the final published score is the mean of criterion medians.

- **Pros**: Outlier-robust at N=3 (single outlier weight = 0 when a second judge disagrees). Aligned with frozen methodology. Trivially reproducible (`statistics.median` is deterministic). Already documented in `scoring.md:27` for docs tasks.
- **Cons**: Discards distribution information beyond the centre. With even N (N=4) median is the mean of the two middle values, partially defeating the outlier-robustness argument; this ADR only applies cleanly for odd N. Mitigation: report IQR alongside in manifests for transparency.

#### Option R2: Arithmetic mean (Inspect AI default)

`final_score[criterion] = sum(scores) / len(scores)`.

- **Pros**: Inspect AI default — zero custom code. Smooth (small changes in any judge's score move final score by 1/N). Familiar to HELM users (EVID-001 claim 4).
- **Cons**: Single outlier at N=3 owns 1/3 of the published number. A judge mis-scoring 7→2 shifts published score from 7.0 to 5.3 — a 1.7-point swing on a 0-10 scale. At our publication threshold (calibration MAD ≤ 1.5), this single-judge outlier is enough to make a passing run look failing. Diverges from frozen methodology without ADR cover.

#### Option R3: Trimmed mean (e.g., 20% trim)

`final_score[criterion] = mean(sorted(scores)[trim:-trim])`.

- **Pros**: Robust to outliers while preserving more distributional information than median.
- **Cons**: 20% of 3 = 0.6 → trim degenerates to "drop one extreme" which IS median at N=3 (drop top OR bottom = median of remaining 2 = mean of remaining 2). Becomes meaningfully different from median only at N≥5. Over-engineering for v0.1; revisit if panel size grows.

### Publication gate semantics

#### Option G1: Bootstrap CI lower-bound ≥ 0.70 (CHOSEN)

Compute Krippendorff α (ordinal level), resample 2000× (per PRD-002 SC-1 — PRD says 2000, decision drivers above used 1000; ADR aligns with the binding PRD value), gate on lower edge of the 95% bootstrap CI.

- **Pros**: Refuses runs that "luck into" passing despite wide CI. Conservative — false-negative cost (re-run, add judges) is reversible and cheap; false-positive cost (published leaderboard with weakly-agreed scores) damages credibility cumulatively. Consistent with `scoring.md:45` bootstrap-CI policy.
- **Cons**: ~5% false-negative rate near the boundary (true α exactly 0.70, CI happens to span below). Estimated; not empirically verified at POLLMEVALS scale. Adds ~1-3s computation per α call (negligible at v0.1 throughput). Risks rejecting first weekly run if calibration is thin; mitigation: enlarge calibration sample size to tighten CI before publication, OR publish a "calibration-not-yet-ready" status page instead.

#### Option G2: Point estimate ≥ 0.70 (Krippendorff default reading)

Gate on the observed sample α directly.

- **Pros**: Higher statistical efficiency — fewer runs rejected by chance. Simpler narrative ("α ≥ 0.70").
- **Cons**: At smoke-scale CI width (PRD-002 H3 predicts ≥ 0.12), a true α of 0.65 has a real chance of producing a sample α ≥ 0.70. Publishing such a run is a false-positive whose cost is hard to undo (retraction beats publication for credibility damage). Asymmetric error costs argue against this option.

#### Option G3: Bootstrap CI upper-bound ≥ 0.70

Gate on upper edge of 95% bootstrap CI.

- **Pros**: Highest statistical power (most permissive).
- **Cons**: Nearly any run with non-trivial α has an upper CI > 0.70. Effectively no gate. Rejected on grounds of being ceremony rather than test.

## Decision

**1. Reducer (per FR-003)**: use **median per criterion** as the per-eval reducer over N judges' scores. Implemented as `statistics.median(per_judge_rubric_scores[criterion])` for each rubric criterion independently. For documentation tasks (`scoring.md:27`), the final published score is the arithmetic mean of criterion medians (this two-stage aggregation is intentional and load-bearing — see Invariants).

**2. Publication gate (per FR-003 + SC-1)**: use **bootstrap CI lower-bound ≥ 0.70** on Krippendorff α (ordinal level). Compute α via the `krippendorff` Python package; resample 2000× for the 95% bootstrap CI; gate on the lower bound.

Both decisions are reversible via config flags; rollback paths are documented below.

## Consequences

### Positive

- Single-judge outlier cannot dominate a published score; methodology robustness lifts at the operationally critical N=3 floor.
- Conservative α gate maintains publication credibility at the cost of occasional re-runs — error costs are now asymmetric in the correct direction (false-negative cheap, false-positive expensive).
- Both choices align with frozen methodology v0.1.0 — this ADR backfills rationale without forcing methodology changes.
- Manifest stores both point α and CI bounds, enabling post-hoc analysis of gate behaviour and supporting future ADRs that may revisit the threshold.

### Negative

- Median discards distribution information beyond the centre; an honest dashboard needs IQR alongside median for transparency. Mitigation: manifest schema (`packages/contracts/schemas/run-manifest.schema.json`) carries `judge_aggregate.iqr` per criterion.
- Conservative gate rejects some "true α ≈ 0.70" runs by chance — estimated ~5% false-negative rate at smoke scale. Operational cost: re-run cost (~$12 smoke / ~$35 weekly) is bounded and budgeted.
- Bootstrap computation adds ~1-3s per α calculation. Negligible at v0.1 scale; revisit if α is computed inside a tight loop (it is not — once per run).
- Median is well-defined only for odd N; at even N (N=4) it averages the two middle values, partially defeating the outlier argument. Mitigation: degraded-panel policy (PRD-002 Q3) keeps N=3 as the typical operating point; runs with even N flagged in manifest.

### Neutral

- Methodology source-of-truth (`docs/02-methodology/judge-policy.md:7`, `scoring.md:27`) gains an ADR reference in the form of a footnote / comment when next touched — no content change to methodology itself (it is frozen v0.1.0).
- Inspect AI's default reducer is overridden; this is the first place POLLMEVALS extends rather than uses Inspect's defaults, setting precedent for future custom scorers.

## Invariants

- **Median is computed per criterion, NOT averaged across criteria first.** Order of operations: per-judge rubric scores → median per criterion → (for docs) mean of criterion medians. Inversion (mean across criteria first, then median across judges) would re-introduce single-judge outlier sensitivity.
- **Krippendorff α `level_of_measurement` is `ordinal`**, NOT `nominal` or `interval`. Rubric scores are ordered (7 > 5 > 2) but score-distance is not metric (7→5 ≠ 5→3 in semantic terms).
- **Bootstrap resamples = 2000** (per PRD-002 SC-1). Seed is deterministic and recorded in `run_manifest.judge_aggregate.bootstrap_seed` for reproducibility.
- **Self-judging guard (PRD-002 FR-002) runs BEFORE the reducer.** Excluded judges never enter the median or the α computation. This is enforced in `JudgePanel.__init__`, not in `aggregate()`.
- **Degraded judges (PRD-002 Q3) reduce N but do not nullify the eval.** Manifest records the effective N per eval; runs with > 20% degraded evals abort entirely per PRD-002 Q3.

## Rollback Plan

Both decisions are reversible via a single config-flag flip + re-scoring of archived manifests; no schema migration required.

1. **Reducer change** (median → mean, or median → trimmed mean):
   - Flip `reducer: mean` in `apps/eval-core-py/src/orchestrator/judge_panel.py` config.
   - Re-score last 4 weekly run manifests under both reducers; record delta.
   - File new ADR documenting empirical justification.
   - Methodology v0.1.0 (`scoring.md:27`) is frozen — reducer change requires methodology version bump to v0.2.0, gated by external review.

2. **Gate change** (CI-lower → point estimate):
   - Flip `gate_mode: point` in `JudgePanel` config.
   - Re-evaluate last 4 weekly runs to count how many would have passed under point gate but failed under CI-lower (the false-negative rate).
   - Document delta in new ADR. If false-negative rate is empirically ≤ 2%, point gate may be defensible; if higher, retain CI-lower.

3. **Combined change**: both toggles flip together via one config commit (`reducer: median|mean`, `gate_mode: ci_lower|point`). Rollback is a 1-line revert.

4. **Recompute trigger**: any reducer or gate change MUST be paired with a recompute of α and median for all published manifests still in the active leaderboard window (per ADR-002 run immutability — old runs are NOT mutated in place; recompute produces NEW EVID artifacts linking to the original runs with `informs` relation).

## Affected Files

| File | Change |
|---|---|
| `apps/eval-core-py/src/orchestrator/judge_panel.py` | NEW (per RFC-002) — hosts reducer + α gate logic |
| `apps/eval-core-py/src/contracts/manifest.py` | ADD fields: `judge_aggregate.alpha_point`, `alpha_ci_lower`, `alpha_ci_upper`, `alpha_ci_method`, `bootstrap_seed`, `iqr_per_criterion` |
| `packages/contracts/schemas/run-manifest.schema.json` | ADD same fields; semver bump from 0.1.x → 0.2.x (additive but schema-visible) |
| `docs/02-methodology/judge-policy.md` | Line 7 (median) and line 27 (α ≥ 0.70) gain ADR-005 reference — comment-only, methodology body unchanged (frozen v0.1.0) |
| `evals/task-packs/<slug>/calibration/` | Golden samples must verify under both reducers (median and mean) — rollback safety check |
| `apps/eval-core-py/tests/test_judge_panel.py` | NEW — unit tests for reducer + gate semantics per FR-003 acceptance criteria |

## Decision Outcome

Chosen: **R1 (median) + G1 (bootstrap CI lower-bound ≥ 0.70)**.

R1 is chosen because median's outlier robustness at N=3 is the dominant concern under POLLMEVALS's operating reality (3-judge panel floor per `judge-policy.md`); R3 (trimmed mean) degenerates to median at N=3 and is over-engineering; R2 (mean) re-introduces single-judge outlier sensitivity in the exact regime where the methodology is most fragile.

G1 is chosen because the asymmetric error costs (false-positive damages credibility cumulatively; false-negative costs one re-run) argue for the conservative gate. G2 (point estimate) has unacceptable false-positive rate at smoke-scale CI widths predicted by PRD-002 H3. G3 (CI upper-bound) is too permissive to function as a gate.

Both decisions integrate cleanly with PRD-002's broader contract: median feeds FR-003's aggregation step, and CI-lower-bound aligns with SC-1's "bootstrap 2000 resamples, 95% CI" measurement spec. Both are reversible via 1-line config flips (Rollback Plan); both produce evidence trail (manifest fields, calibration EVIDs) that supports future revisitation.

## Trust Calculus per claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| Median is more outlier-robust than mean at N=3 | 9 | 8 | 8 | 25/27 | Mathematically provable; single-outlier-weight argument is formal. F=9 (statement is precise: "weight on a single outlier is 0 when ≥1 other judge disagrees"). G=8 (concrete N=3 example, 7→2 outlier swings mean by 1.7). R=8 (textbook robust statistics; no POLLMEVALS-specific bench yet). |
| Inspect AI `multi_scorer` supports median reducer override | 7 | 6 | 6 | 19/27 | Per EVID-004; needs Phase 3 Week 1 verification (PRD-002 H1 spike). If H1 refutes, custom scorer needed (ADR-006 reserved), but reducer decision itself is unchanged — only implementation path shifts. |
| Krippendorff α with N=3 judges × 45 evals produces CI width ≥ 0.12 | 6 | 6 | 5 | 17/27 | Estimated from Krippendorff's small-sample tables (Krippendorff 2004, ch. 11); not directly measured on POLLMEVALS data. Phase 3 first calibration session is the empirical check. PRD-002 H3 marks INCONCLUSIVE. |
| CI lower-bound ≥ 0.70 gate has ~5% false-negative rate near boundary | 5 | 5 | 4 | 14/27 | Order-of-magnitude estimate from bootstrap-CI theory; not formally derived for POLLMEVALS rubric distributions. Flagged for follow-up measurement in Phase 3 calibration EVID. |
| Median weight on outlier = 0 once second judge disagrees | 9 | 9 | 9 | 27/27 | Definitional. The median of any 3-element multiset is the middle element by rank order; outlier rank by definition is the extreme, never the middle as long as ≥2 others form a "middle" range. |
| Bootstrap CI on α is industry-standard for small-sample agreement metrics | 7 | 6 | 7 | 20/27 | Krippendorff's textbook recommends bootstrap for N<200 reliability decisions; `krippendorff` PyPI package implements it. R=7 (textbook + library both align). |

**Decision strength**: average sum = (25+19+17+14+27+20)/6 = **20.3/27 (75%)**. Weakest single claim is row 4 (gate false-negative rate, 14/27) — above the NOTE-002 "weak decision" red flag of 12 but warrants follow-up. **Action**: Phase 3 calibration EVID measures actual false-negative rate empirically, lifting row 4 R-score from 4 to 7-8.

## Related

- **PRD-002** (informs — parent): Q1 (median assumption), Q2 (CI lower-bound gate), Q5 (identification probe); FR-003 (acceptance for both reducer + gate)
- **EVID-001** (informs): HELM uses mean, POLLMEVALS diverges to median; direct rationale for the divergence
- **EVID-004** (informs, via PRD-002): Inspect AI prior art — `multi_scorer(model_graded_qa(model=[...]))` is the integration point for the reducer override
- **NOTE-002** (informs): Evidence Quality Standard — ADI cycle + Trust Calculus structure of this ADR follows the NOTE-002 contract
- **ADR-002** (informs): run immutability — rollback recomputes produce NEW EVID artifacts, never mutate published manifests in place
- **ADR-003** (informs): 3-family judge diversity — N=3 is the panel floor that makes outlier robustness operationally critical
- **RFC-002** (companion, parallel-authored): implementation plan for `JudgePanel.aggregate()`; will carry `informs` edge to this ADR once landed (orchestrator to add)
- **SPEC-002** (future): judge panel data contracts — JudgeAggregation schema will carry the CI-bound fields defined in Affected Files
- **ADR-006** (reserved): pivot to custom scorers if PRD-002 H1 refutes; reducer decision in this ADR is unchanged either way, only the implementation path shifts

## References

- Krippendorff K. (2004) *Content Analysis: An Introduction to Its Methodology*, ch. 11 — α threshold guidelines (0.667 tentative / 0.80 strong / 0.70 widely-cited "good") + bootstrap recommendations for N<200
- `krippendorff` PyPI package — ordinal-level α with bootstrap CI support; supports deterministic seed for reproducibility
- HELM Capabilities 2025 (EVID-001 claim 4) — divergence: HELM uses mean, POLLMEVALS uses median
- `docs/02-methodology/judge-policy.md:7` (median), `:27` (α ≥ 0.70) — frozen methodology v0.1.0 source-of-truth
- `docs/02-methodology/scoring.md:27` (docs tasks: mean of criterion medians), `:45` (bootstrap 95% CI for aggregates)
- `docs/04-runbook/08-scoring-contract.md` — α + bootstrap CI spec details for run manifest
- Zheng et al. 2023 (arxiv 2306.05685) — position bias and reducer interaction in LLM-as-judge panels
- PRD-002 H3 — predicts CI width ≥ 0.12 at smoke-scale (135 judgments); empirical check is Phase 3 Week 3







