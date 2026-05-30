---
depth: standard
id: PRD-002
kind: prd
last_modified_at: 2026-05-24T10:24:03.903657+00:00
last_modified_by: claude-code/2.1.150
links:
- target: EPIC-001
  relation: based_on
status: active
title: judge panel layer — methodology + scoring infrastructure
---

# PRD-002: judge panel layer — methodology + scoring infrastructure

> **STATUS: ACTIVE (deep)** — expanded to deep depth per NOTE-002 contract: ADI cycle, Trust Calculus F/G/R, explicit risks, NFR dollar estimates, decisions on the 5 open questions logged below. Implementation lives in future RFC-002 / SPEC-002.

## Problem

После того как smoke run (PRD-001) докажет работоспособность пайплайна на automatic metrics only, без judge-слоя нельзя ни (а) сравнивать качество subjective-выходов (frontend UX, docs clarity), ни (б) опубликовать leaderboard, потому что v0.1.0 frozen methodology (`docs/02-methodology/judge-policy.md`) требует median по ≥3 судьям + Krippendorff α ≥ 0.70 + calibration MAD ≤ 1.5.

**Impact**: без PRD-002 проект застрянет на smoke-уровне — leaderboard не имеет смысла без judge-scoring; weekly cadence (PRD-003) технически возможна, но публиковать нечего; thesis "cheap-model+scaffolding beats expensive-bare-model" нельзя доказать без судей, потому что automatic metrics покрывают только coding/review (correctness, lint, type-safety), а frontend/docs требуют качественной оценки.

## Goals

| ID | Criterion | Target | Measurement |
|----|-----------|--------|-------------|
| SC-1 | Krippendorff α на judge-panel (publication gate) | **CI lower-bound ≥ 0.70** (bootstrap 2000 resamples, 95% CI) | computed from per-judge Score objects via `krippendorff` PyPI |
| SC-2 | Self-judging incidents | 0 (judge никогда не оценивает свою модель family — string match insufficient, family match required) | `SelfJudgingError` raised in `JudgePanel.__init__`; integration test asserts raise; CI gate on test |
| SC-3 | Calibration MAD on known-score samples (per judge) | ≤ 1.5 on 0-10 scale | calibration suite runs 5 quality levels × 3 tasks × 10 samples = 150 prompts per judge per session; MAD computed against gold scores |
| SC-4 | Model-ID probe accuracy (anonymisation effectiveness) | ≤ 30% (≈ random with 3-way choice + noise) | identification probe: judge prompted "which of {claude, gpt, gemini} produced this?" on 150-sample probe set (see FR-005) |

## Target Users

| Персона | Описание | Боль | Что эта PRD даёт |
|---------|----------|------|------------------|
| Maintainer (gogocat) | Готовится опубликовать первый weekly run | Нужны judge'ы поверх smoke, без которых публиковать нечего | working JudgePanel + calibration + α-gate; ≤ $35 weekly budget предсказуем |
| Methodology Reviewer (external, pre-v1.0) | Будет рецензировать перед публичным launch | Должен видеть calibration данные + α-метрику + identification probe baseline | EVID-{calibration,α,probe} артефакты после Phase 3, привязанные к этому PRD; full ADI in PRD body shows reasoning is traceable |

## Product Scope

### In Scope

- `JudgePanel` impl поверх Inspect AI's `multi_scorer(model_graded_qa(model=[...]))` (см. EVID-004) — see Architecture sketch
- **Median reducer** (override Inspect's default mean — см. EVID-001, HELM uses mean, we use median per `docs/02-methodology/scoring.md`)
- **Blind labels** — judge prompt template strips candidate model identity entirely; no leak via system prompt
- **Anonymisation pipeline** — strips signatures, greetings, "as an AI" disclaimers, model-family idioms before judge call; canonical normalisation per `docs/04-runbook/07-judge-panel.md:33-43`
- **Calibration suite** — perfect/good/mediocre/poor/broken samples per task, lives under `evals/task-packs/<slug>/calibration/` (per-task ownership — decision Q4 below)
- **Identification probe** (FR-005, new) — runs once per calibration session; gates SC-4
- **Per-judge metrics** — MAD, rank correlation, length bias (Spearman ρ between length and score), self-enhancement bias (does judge over-reward its own family on cross-family runs?)
- **Self-judging guard** — family-level match (compare normalised vendor family, not raw model ID string — `openrouter/anthropic/claude-sonnet` and `anthropic/claude-sonnet` both match `anthropic`)
- **Degraded panel policy** (decision Q3 below) — if judge unavailable, proceed at N-1 with `judge_status=DEGRADED` and α=null for that eval; abort whole run if > 20% evals degraded
- **Cost gating** — judge cost estimate folded into `BUDGET_ABORT_PCT` check in grid_runner

### Out of Scope

- Human judges (отложено до v2.0)
- Adaptive judge selection (fixed panel for v0.1; revisit after first 2 weekly runs)
- Multi-language judges (English-only до v2.0)
- Judge fine-tuning / RLHF on our calibration data (would invalidate independent evidence layer)
- Pairwise comparison mode (rubric-only for v0.1; pairwise може появиться в v2.0 для tie-breaking)

## Functional Requirements

| ID | Requirement | Acceptance |
|----|-------------|-----------|
| FR-001 | Orchestrator routes eval output to N≥3 judges from different vendor families. On judge unavailability, proceeds at N-1 with `judge_status=DEGRADED` and α=null for that eval. Run aborts if > 20% of evals end up degraded. | integration test: 3-judge panel; mock one judge failure; verify single eval marked DEGRADED + run completes; second test mocks 30% failures → run aborts. |
| FR-002 | Orchestrator refuses self-judging at family level (not string level). `JudgePanel.__init__` raises `SelfJudgingError` if any judge model family matches candidate family. | unit test: panel containing `anthropic/claude-sonnet` judging `openrouter/anthropic/claude-haiku` raises; panel of all-different families passes. |
| FR-003 | System computes median score across panel + Krippendorff α with bootstrap 95% CI (2000 resamples). Publication gate uses **CI lower-bound ≥ 0.70**, NOT point estimate (decision Q2 below). | unit test on synthetic per-judge scores: median matches numpy.median; α CI computed via `krippendorff` + bootstrap; gate semantics asserted (point=0.71 but CI lower=0.65 → REFUSE). |
| FR-004 | System runs calibration suite (5 quality levels × 3 tasks × 10 samples per judge per session) before production scoring. If any judge MAD > 1.5 → refuse to publish run. Calibration hash recorded in run manifest (NFR-004). | calibration session integration test: synthetic gold-scored samples; assert MAD computed; assert refuse on MAD > 1.5. |
| FR-005 | **(new — addresses SC-4 gap)** Identification probe runs once per calibration session: judge sees normalised output + prompt "which of {claude, gpt, gemini} produced this?". Probe set = 150 samples (10 × 5 quality levels × 3 tasks). Accuracy across all judges ≤ 30% to pass SC-4 gate. Result stored as EVID linked to this PRD on every weekly run. | probe integration test: synthetic outputs without family idioms → expected accuracy near random; assert refuse on accuracy > 30%. |

## Non-Functional Requirements

| ID | Category | Target | Rationale |
|----|----------|--------|-----------|
| NFR-001 | Cost | Smoke run (45 evals): **$12 ± $3** total (≈ $5 candidate calls + $6.75 judges + buffer). Weekly run (≈ 200 evals): **≤ $35**. Calibration session: **≤ $5** amortised (cached per task version). | Judge cost = 3× candidate cost approximate (3 judges, similar token volumes, ≈ $0.05/call avg via OpenRouter); folded into PRD-001 $50 ceiling. |
| NFR-002 | Latency | Judge round p95 ≤ 30s per eval (3 parallel judge calls + median compute) | Bound by slowest judge; parallelism via MoleculerPy workers (ADR-004). |
| NFR-003 | Calibration session wall-clock | ≤ 10 minutes per judge per task version | 50 samples × ~10s/call = 500s ≈ 8 min; tolerable cache build cost. |
| NFR-004 | Manifest integrity | Run manifest stores `calibration_hash` (SHA256 of calibration sample set + judge MAD vector) → enables cross-run drift detection | Mirrors EVID-002 Voyage incident lesson; without this, silent judge degradation invisible. |
| NFR-005 | Billing isolation | JudgePanel accepts separate `OPENROUTER_API_KEY_JUDGE` env var + base_url, distinct from candidate key | Enables independent budget tracking + auditable cost allocation. |

## ADI cycle (active deep contract per NOTE-002)

### Abduction — load-bearing hypotheses

- **H1**: Inspect AI's built-in `multi_scorer(model_graded_qa(model=[...]))` with the `median` reducer is sufficient to implement the judge panel without custom aggregation code. POLLMEVALS can delegate panel invocation and score reduction entirely to Inspect AI primitives, limiting our code to (a) self-judging enforcement and (b) Krippendorff α calculation atop Inspect's per-judge score outputs.

- **H2**: Position bias is the dominant inter-judge variance driver for POLLMEVALS task types (coding + docs + review), and randomising `judge_order` per eval will reduce disagreement by a materially measurable margin (≥ 0.5 MAD points on ≥ 2 of 3 task categories).

- **H3**: Krippendorff α ≥ 0.70 is achievable in point-estimate with N=3 judges but statistically unstable at smoke-run scale (N=45 evals × 3 judges = 135 judgments) — bootstrap 95% CI will span ≥ 0.15, making point-estimate publication gates unreliable. CI lower-bound gate is the only honest semantic.

### Deduction — observable predictions

- **H1 → Y1**: if H1 holds, Phase 3 Week 1 prototype produces a working `JudgePanel` where `multi_scorer` surfaces individual per-judge Score objects (not just aggregated majority-vote). Measurable as: ≤ 50 LOC wrapper around Inspect primitives covers FR-001 and FR-003.

- **H1 → Y1-refute**: if Inspect returns only aggregated output (no per-judge scores), custom scorer wrappers needed. Measurable as: per-judge Score access NOT available in `multi_scorer` output → spike doc + ADR-006 pivot.

- **H2 → Y2**: if H2 holds, randomised-order condition shows MAD improvement > 0.5 points vs fixed-order in calibration A/B at N=45. Measurable as: paired-t-test on calibration session deltas, p < 0.05 on ≥ 2 of 3 task categories.

- **H3 → Y3**: if H3 holds, bootstrap CI on α at smoke scale (135 judgments) spans width ≥ 0.12 (e.g., point=0.72, CI=[0.62, 0.78]). Measurable as: `krippendorff` package + bootstrap-resample script computes CI width on smoke run output.

### Induction — current evidence per prediction

| Prediction | Evidence available now | Outcome | H_i status |
|---|---|---|---|
| Y1 (per-judge access via multi_scorer) | EVID-004 (Inspect AI prior art: `model_graded_qa` accepts model list, but per-judge surface NOT yet verified for our use) | UNTESTED — Phase 3 Week 1 prototype required | **INCONCLUSIVE** (assumed holds for PRD; fallback path documented) |
| Y2 (randomisation reduces MAD ≥ 0.5) | Zheng et al. 2023 (arxiv 2306.05685) established position bias on pairwise chat preference; POLLMEVALS task types are rubric scoring — transfer assumption unverified | UNTESTED — Phase 3 calibration A/B required | **INCONCLUSIVE** (assumption explicit; PRD does not gate on this) |
| Y3 (CI width ≥ 0.12 at smoke scale) | krippendorff PyPI package supports bootstrap; no POLLMEVALS-specific run yet | UNTESTED — first smoke calibration session generates first data point | **INCONCLUSIVE** (drives gate semantics decision Q2; if CI tight, retain CI-lower-bound gate anyway — conservative) |

**ADI conclusion**: all three hypotheses are load-bearing but currently INCONCLUSIVE. PRD-002 commits to verifying H1 first (Phase 3 Week 1 spike) because H2 and H3 depend on H1's per-judge data access being available. If H1 refutes, ADR-006 captures pivot to custom scorers and Phase 3 timeline slips by ~1 week.

## Trust Calculus per design choice

| Design choice | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| Median reducer (override Inspect default mean) | 8 | 7 | 7 | 22/27 | Frozen methodology (`docs/02-methodology/scoring.md`); HELM divergence captured EVID-001 (R=8 source quality). No POLLMEVALS-specific benchmark on rubric types yet → G capped at 7. Phase 3 calibration EVID will push R to 8-9. |
| Blind labels + anonymisation pipeline | 7 | 6 | 5 | 18/27 | **Weakest overall.** Stated in `judge-policy.md:4-5`; normalisation in `runbook 07:33-43`. No POLLMEVALS-specific measurement that current rules prevent identification → R=5. **SC-4 + FR-005 identification probe directly address this** — once probe runs once, R rises to 7-8. |
| Calibration suite (5 quality levels per task) | 7 | 8 | 6 | 21/27 | Explicit in `runbook 07:46-54`. Pattern borrowed from human annotation calibration literature. No LLM-judge calibration benchmarks for POLLMEVALS task types yet → R=6. Phase 3 first calibration session lifts R to 8. |
| Krippendorff α ≥ 0.70 publication gate (CI lower-bound semantic) | 6 | 8 | 6 | 20/27 | Threshold 0.70 = Krippendorff's standard "good" cutoff but not calibrated to POLLMEVALS rubric types → F=6. G=8 because formula + bootstrap method are specified. R=6 because no run-data yet. **Decision Q2 below commits to CI-lower-bound, more conservative than point-estimate.** |
| N≥3 panel from different vendor families | 8 | 7 | 7 | 22/27 | Per ADR-003 (3-family judge diversity drove model lineup). Cross-family choice reduces correlated bias (preference leakage, arxiv 2502.01534). |
| Self-judging guard at family level | 9 | 8 | 7 | 24/27 | Cardinal-sin rule (judge-policy.md:1); CI-gated unit test. Family-level match (not string) is the gotcha — explicit in implementation. |

**Decision strength**: avg F+G+R = 21.2/27. Lowest single claim (anonymisation, 18/27) is below the NOTE-002 "weak decision" red flag of 12 but above the soft-warning level. Action: SC-4 + FR-005 identification probe is the explicit remediation; once measured, this row rises to ≈ 22/27 and the floor moves up.

## Decisions (the 5 open questions, resolved)

- **Q1 — per-judge score access via Inspect AI**: assume **H1 holds for v0.1 PRD** (Inspect's `multi_scorer(model_graded_qa(model=[...]))` surfaces per-judge Score objects). Phase 3 Week 1 prototype is the verification spike. If refuted, file **ADR-006** capturing pivot to custom scorers (NOT ADR-005 — that ID is reserved for Q2). Schedule slips ~1 week, no other PRD impact.

- **Q2 — publication gate: point estimate or CI lower-bound?**: gate uses **CI lower-bound ≥ 0.70** (bootstrap 2000 resamples, 95% CI). This is conservative — borderline runs (point=0.72, CI=[0.65, 0.78]) are refused. Rationale: H3 predicts wide CI at smoke scale, point-estimate gate is unreliable; conservative semantic protects credibility of leaderboard publication. Counter-arguments (statistical efficiency, sample-size cost) deferred to **ADR-005 (median + CI-gate rationale)** drafted in Phase 3.

- **Q3 — degraded judge panel policy**: proceed at **N-1 with `judge_status=DEGRADED` and α=null** for that eval. Abort whole run if **> 20% of evals end up DEGRADED**. Rationale: occasional vendor outage shouldn't kill a 200-eval run; systemic outage (>20%) likely indicates a broader judge-provider issue and run results would be unrepresentative anyway.

- **Q4 — calibration suite ownership**: **per-task**, lives under `evals/task-packs/<slug>/calibration/`. Each task pack carries its own 50 calibration samples (5 quality levels × 10 each). Adds to task-pack lifecycle: bumping task `version` requires re-calibrating. Rationale: judges' rubric behaviour depends on task type (coding vs docs vs review); shared calibration would mask task-specific drift.

- **Q5 — identification probe methodology (SC-4 measurement)**: probe runs **once per calibration session**. Probe set = **150 samples** (10 samples × 5 quality levels × 3 tasks). Judge prompted: *"Below is a model output. Which of {claude, gpt, gemini} most likely produced it? Respond with one word."* Accuracy across all judges combined ≤ 30% (≈ random with 3-way choice, allowing some noise above 33.3% chance) to pass SC-4. Result stored as new EVID artifact (`EVID-probe-<run_hash>`) linked to PRD-002 on every weekly run.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|:---:|:---:|------------|
| **Cost amplification non-linear** — judge calls outscale candidate calls; weekly run exceeds budget | Med | High | NFR-001 dollar ceiling ($12 smoke / $35 weekly); judge cost folded into `BUDGET_ABORT_PCT` in grid_runner; weekly run dry-run-cost-estimate before launch (per PRD-001 NFR-002 ratio gate). |
| **Judge unavailability mid-run** — vendor outage on 1 of 3 judges drops α confidence; ≥ 20% drops abort run | Med | Med | FR-001 degraded-panel policy (decision Q3); EVID logs every DEGRADED eval; manifest carries judge availability vector for post-mortem. |
| **Calibration drift between runs** — same problem as EVID-002 Voyage incident; silent judge model update invalidates prior α/MAD baselines | Med | High | NFR-004 calibration_hash in manifest; weekly run compares hash vs previous; drift detection alert if hash changes without explicit task version bump. |
| **Self-judging slip at code level** — OpenRouter routes (`openrouter/anthropic/...` vs `anthropic/...`) match by family, not raw string; bug here = cardinal-sin violation | Low | Critical | FR-002 family-level match (not string); CI gate unit test asserts raise; integration test with OpenRouter routing patterns. |
| **H1 refutation** — Inspect AI multi_scorer doesn't surface per-judge scores → need custom aggregator → ~1 week schedule slip | Med | Med | Phase 3 Week 1 prototype is the explicit go/no-go spike; ADR-006 (reserved) captures pivot if refuted. |
| **α point estimate ≥ 0.70 but CI lower-bound < 0.70** — first weekly run can't publish | Med | Med | Decision Q2 (CI-lower-bound gate) is intentional; if refused, increase calibration session size (more samples per quality level) to tighten CI; publish "calibration-not-yet-ready" status page note instead of broken leaderboard. |
| **Cross-family preference leakage** — Anthropic/OpenAI/Google models share pretrain data; judges may not be as independent as nominal families suggest (arxiv 2502.01534 preference leakage) | Med | Med | ADR-003 + 3-family panel is the v0.1 stance; v2.0 may add open-weight judges (Qwen, Llama) for true independence; EVID tracks self-enhancement bias on every weekly run. |

## Architecture sketch (handoff to RFC-002)

- **Module**: `apps/eval-core-py/src/orchestrator/judge_panel.py` (NEW, parallel to `eval_caller.py` + `grid_runner.py`)
- **Signature**:

```python
class JudgePanel:
    def __init__(
        self,
        judge_models: list[str],
        candidate_model_id: str,
        rubric_version: str,
        base_url: str | None = None,
        api_key_env: str = "OPENROUTER_API_KEY_JUDGE",
    ) -> None:
        """Self-judging guard fires here (family-level match) → SelfJudgingError."""

    async def score(self, eval_result: EvalResult, task_id: str) -> list[Judgment]:
        """Calls multi_scorer; returns per-judge Judgment list (verified by H1 spike)."""

    def aggregate(self, judgments: list[Judgment]) -> JudgeAggregation:
        """median + Krippendorff α + bootstrap CI."""
```

- **Self-judging guard** fires in `__init__` or at top of `score()` — raises `SelfJudgingError`, never silent skip.
- **Integration point**: `_run_single` in `grid_runner.py:211`. Judge calls inserted **after** `self._caller.call(request)` returns `EvalResult(status=SCORED)` at line 261, **before** `self._journal_writer.append` at line 308.
- **EvalRow extensions** (new persistent fields): `judgments: list[Judgment] | None`, `judge_aggregate: JudgeAggregation | None`, `judge_status: enum["FULL","DEGRADED","FAILED"]`.
- **Budget gating**: lines 230-246 in grid_runner; include `estimated_judge_cost_for_this_eval` in `BUDGET_ABORT_PCT` check (NFR-001 + NFR-005).
- **Billing isolation**: JudgePanel accepts own `base_url` + `api_key_env` so judge spend tracks separately from candidate spend (NFR-005).

Full implementation contract lives in **future RFC-002**; data contracts (Judgment, JudgeAggregation, calibration sample schema) in **future SPEC-002**.

## Dependencies / Related Artifacts

**Currently linked / will be linked**:

- **PRD-001** — predecessor (smoke pipeline must work before judges layered on); relation: `informs`
- **EPIC-001** — parent (judge layer is part of evaluation stack epic); relation: `based_on`
- **ADR-002** — run immutability (judgments are immutable once recorded; errors → new run + supersedes)
- **ADR-003** — 3-family judge diversity (drove the candidate model lineup AND the judge panel diversity requirement)
- **ADR-004** — MoleculerPy concurrency (judge workers run as parallel actors)
- **EVID-001** — HELM divergence: HELM uses mean, we use median; informs FR-003 + Trust Calculus row 1
- **EVID-004** — Inspect AI prior art: `multi_scorer(model_graded_qa(model=[...]))` is the foundation for H1 + architecture sketch
- **NOTE-002** — Evidence Quality Standard (this PRD's ADI + Trust Calculus structure follows the NOTE-002 contract)

**Future (will be created in Phase 3)**:

- **SPEC-002** — judge panel data contracts (Judgment, JudgeAggregation, calibration sample, identification probe sample schemas)
- **RFC-002** — judge routing implementation (Inspect AI integration, multi_scorer wrapper, family-level self-judging guard, degraded-panel policy)
- **ADR-005** — median + CI-lower-bound gate rationale (decision Q2 + counter-arguments to point-estimate)
- **ADR-006** — pivot to custom scorers if H1 refutes (reserved; only created if Phase 3 Week 1 spike fails)
- **EVID-{calibration,α,probe,cost}** — Phase 3 measurement artifacts, one per weekly run, linked back to this PRD as `informs`

**Frozen methodology source-of-truth** (read-only):

- `docs/02-methodology/judge-policy.md` (v0.1.0 frozen) — judge policy, panel rules, calibration policy
- `docs/02-methodology/scoring.md` (v0.1.0 frozen) — median reducer, weight formulas
- `docs/04-runbook/07-judge-panel.md` — anonymisation pipeline, calibration sample format
- `docs/04-runbook/08-scoring-contract.md` — α + bootstrap CI specification

## Next steps (Phase 3, T+2..T+4 weeks)

1. **Week 1**: H1 verification spike — prototype `JudgePanel.score()` against Inspect AI; verify per-judge Score surface. If refuted → ADR-006 + replan.
2. **Week 2**: Implement `JudgePanel` + self-judging guard (FR-002) + calibration runner (FR-004); SPEC-002 + RFC-002 drafted.
3. **Week 3**: First calibration session (3 judges × 3 tasks × 50 samples) → EVID-{calibration,α} → measure SC-1, SC-3 against threshold.
4. **Week 4**: Identification probe (FR-005, SC-4) → EVID-probe; first end-to-end smoke run WITH judges → EVID-cost; ADR-005 drafted with calibration data.
5. **Week 5 (buffer)**: Guardian gate review; PRD-002 status confirmed at deep / re-deepen if new evidence shifts decisions.









