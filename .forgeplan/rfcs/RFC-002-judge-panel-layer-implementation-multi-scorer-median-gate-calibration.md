---
depth: standard
id: RFC-002
kind: rfc
last_modified_at: 2026-05-24T19:09:50.884374+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-002
  relation: informs
- target: ADR-003
  relation: informs
- target: ADR-004
  relation: informs
- target: EVID-004
  relation: informs
- target: PRD-001
  relation: informs
- target: EVID-001
  relation: informs
- target: NOTE-002
  relation: informs
status: draft
title: judge panel layer implementation — multi_scorer + median + α gate + calibration
---

# RFC-002: judge panel layer implementation — multi_scorer + median + α gate + calibration

> **STATUS: draft (standard)** — operationalises PRD-002 decisions Q1-Q5 into concrete implementation slices. Depth is standard (not deep): Q1 (Inspect AI multi_scorer per-judge access) is assumed-true for v0.1; refutation in the Phase 3 Week 1 spike triggers ADR-006 pivot. PRD-002 itself carries the full ADI cycle + Trust Calculus per NOTE-002 contract.

## Summary

This RFC operationalises PRD-002 (judge-panel methodology + scoring infrastructure) into five mergeable code slices delivered by Phase 3 Weeks 1-4. A new `JudgePanel` module lives at `apps/eval-core-py/src/orchestrator/judge_panel.py`, parallel to `eval_caller.py`. `GridRunner._run_single` gains one new step after candidate SCORED, before journal append — invoking `JudgePanel.score()` then `JudgePanel.aggregate()`. Krippendorff α uses bootstrap CI 2000 resamples with publication gate on **CI lower-bound ≥ 0.70** (PRD-002 Q2). Self-judging is refused at **vendor-family level** (not raw string), covering OpenRouter cross-route variants. The Phase 3 Week 1 spike verifies hypothesis H1 (Inspect AI per-judge Score access) before committing the multi_scorer path — refutation triggers reserved ADR-006 pivot to custom `@scorer` per judge.

## Motivation

After PRD-001 ships the smoke pipeline on automatic metrics only, **PRD-002** layers a multi-judge scoring layer that is mandatory before any public leaderboard publication — frozen methodology (`docs/02-methodology/judge-policy.md` v0.1.0) requires median across ≥3 judges + Krippendorff α ≥ 0.70 + calibration MAD ≤ 1.5. PRD-002 resolves the five open methodology questions (Q1-Q5); this RFC turns those decisions into a concrete code drop.

**Success criteria (lifted verbatim from PRD-002)**:

- **SC-1**: Krippendorff α — gate uses **CI lower-bound ≥ 0.70** (bootstrap 2000 resamples, 95% CI)
- **SC-2**: zero self-judging incidents (family-level match, not string match)
- **SC-3**: per-judge calibration MAD ≤ 1.5 on a 0-10 scale
- **SC-4**: identification-probe accuracy ≤ 30% across judges (150-sample probe)

**Cost envelope**:

- PRD-001 NFR-001: smoke run total ≤ $50 (45 evals, candidate-only)
- PRD-002 NFR-001 (judge layer addition): **$12 ± $3** per smoke (≈ $5 candidate + $6.75 judges + buffer); ≤ $35 weekly
- PRD-002 NFR-005: separate billing — judges use `OPENROUTER_API_KEY_JUDGE`, distinct from candidate `OPENROUTER_API_KEY`

## Options Considered

| Option | Approach | Verdict |
|---|---|---|
| **A. Custom multi-call orchestrator** — POLLMEVALS hand-rolls N parallel HTTP calls to LiteLLM per eval, builds own Score model, aggregates manually. | Pros: zero framework dependency, full control. Cons: ~600 LOC of duplication of what Inspect AI already provides; abandons EVID-004's 94% Trust-Calculus win on Inspect AI. | **REJECTED** — duplicates existing capability. |
| **B. Inspect AI `multi_scorer(model_graded_qa(model=[...]))` with `mean_score` reducer** — use Inspect's built-in default. | Pros: smallest LOC. Cons: contradicts frozen methodology (scoring.md mandates **median**, not mean); EVID-001 documents the HELM-vs-POLLMEVALS divergence on exactly this point. | **REJECTED** — violates methodology v0.1.0. |
| **C. Inspect AI `multi_scorer` with per-judge surface + POLLMEVALS-owned median + Krippendorff α** — chosen path. Inspect AI handles routing + model_graded_qa template; we own aggregation. | Pros: leverages 94% Trust-Calculus from EVID-004; methodology-compliant median; α/CI calc isolated in one method. Cons: load-bearing assumption (H1) that Inspect surfaces per-judge `Score` — verified by Phase 3 Week 1 spike. | **CHOSEN** (Q1 assumption; Slice B has fallback for refutation). |
| **D. Inspect AI per-eval call with N separate `@scorer`-decorated functions** — bypass multi_scorer entirely. | Pros: guaranteed per-judge surface (each scorer is its own Score). Cons: bigger blast radius (changes Task signature); doubles framework integration cost. | **HELD AS FALLBACK** — Slice B switches to this if H1 refutes; ADR-006 (reserved) captures the pivot. |

**Other axes considered** (decided in PRD-002, not re-litigated here):

- Point estimate vs CI lower-bound for α gate → **CI lower-bound** (PRD-002 Q2)
- Calibration ownership: shared vs per-task → **per-task** (PRD-002 Q4, `evals/task-packs/<slug>/calibration/`)
- Degraded-panel policy: skip eval, proceed N-1, hard-fail → **proceed N-1 with α=None** (PRD-002 Q3); abort run if > 20% degraded
- Identification-probe methodology → **150 samples, one-word forced choice** (PRD-002 Q5)

## Proposed Direction

### Architecture overview

Where the layer lives:

```
apps/eval-core-py/src/orchestrator/
├── grid_runner.py        ← unchanged surface; _run_single gets one new step
├── eval_caller.py        ← unchanged
├── journal.py            ← unchanged (JournalWriter still appends a single EvalRow)
├── cost.py               ← BudgetGate gets judge cost folded in (NFR-005)
└── judge_panel.py        ← NEW MODULE (Slices A-D)
```

The new module sits **parallel** to `eval_caller.py` — same Protocol-driven testability seam pattern (EVID-015), no inheritance, no framework coupling. Concurrency control (semaphore-then-bulkhead in Phase 3+) lives outside `JudgePanel`, matching how `EvalCaller` declines concurrency responsibility (eval_caller.py:13-14).

### Data flow (text diagram — terminal-readable)

```
EvalRequest                              EvalCaller.call()  → EvalResult(EvalRow status=SCORED)
                                                                         │
                                          ┌──────────────────────────────┘
                                          ▼
                                   JudgePanel.score(eval_result, task_id)
                                          │
                                          │ ← reads OPENROUTER_API_KEY_JUDGE
                                          │ ← anonymises raw output (signatures/idioms stripped)
                                          │ ← randomises judge_order per eval (H2)
                                          ▼
                              Inspect AI multi_scorer(model_graded_qa(model=[j1,j2,j3]))
                                          │
                                          ▼
                                   list[Judgment]   (per-judge Score objects — H1 dependency)
                                          │
                                          ▼
                                   JudgePanel.aggregate(judgments)
                                          │
                                          │ ← median per criterion (NOT mean — EVID-001)
                                          │ ← Krippendorff α + bootstrap CI 2000 resamples
                                          ▼
                                   JudgeAggregation { median_per_criterion,
                                                      alpha_point,
                                                      alpha_ci_lower,
                                                      alpha_ci_upper,
                                                      judge_status: FULL|DEGRADED }
                                          │
                                          ▼
                          EvalRow extended:  judgments + judge_aggregate + judge_status
                                          │
                                          ▼
                                   JournalWriter.append(row)   ← single append, atomic
```

### GridRunner integration point

Per `grid_runner.py:_run_single`:

| grid_runner.py line | Current behaviour | New behaviour |
|---|---|---|
| 230, 241 (BudgetGate) | Checks running_total vs BUDGET_ABORT_PCT pre-call | Same, but BudgetGate's threshold check now folds `estimated_judge_cost_for_this_eval` into the post-call accounting (NFR-005) |
| 259 (`_caller.call(request)`) | Candidate LLM round-trip → EvalResult | Unchanged |
| **NEW between 269 and 291** | — | `if result.eval_row.status == SCORED: judgments = await judge_panel.score(result, request.task_id); aggregation = judge_panel.aggregate(judgments)` — eval_row is rebuilt with judgments + judge_aggregate + judge_status |
| 304 (`journal_writer.append`) | Persists EvalRow as-is | Persists the extended EvalRow (single atomic append) |

The judge call is **inside** the semaphore-protected block (grid_runner.py:238 `async with self._semaphore`) for Phase 2C single-process; Phase 3+ moves judge calls to a separate `judge-svc` MoleculerPy worker (ADR-004) so judge concurrency is independent from candidate concurrency.

### New EvalRow fields

Extend `apps/eval-core-py/src/contracts/eval_row.py`:

```python
class JudgeStatus(StrEnum):
    FULL = "full"          # all N judges responded
    DEGRADED = "degraded"  # N-1 responded; α=None for this eval (Q3)
    FAILED = "failed"      # < N-1 responded; row marked status=FAILED

class Judgment(BaseModel):
    judge_model_id: str
    judge_order: int                                   # 0-indexed randomised position (H2)
    rubric_version: str
    rubric_scores: dict[str, float]                    # per-criterion 0-10
    total_score: float                                 # weighted median per scoring.md
    judge_reasoning_ref: ArtifactRef | None = None     # optional CoT artifact

class JudgeAggregation(BaseModel):
    median_per_criterion: dict[str, float]
    median_total: float
    alpha_point: float | None      # None when DEGRADED (Q3)
    alpha_ci_lower: float | None
    alpha_ci_upper: float | None
    judge_status: JudgeStatus
    n_judges_responded: int
    n_judges_requested: int

# EvalRow gains (frozen=True preserved; both optional for back-compat with smoke runs without judges):
judgments: list[Judgment] | None = None
judge_aggregate: JudgeAggregation | None = None
```

### Billing isolation (NFR-005)

`JudgePanel.__init__` reads `api_key_env` (default `"OPENROUTER_API_KEY_JUDGE"`) via `os.environ`. The candidate `InspectEvalCaller` continues reading `OPENROUTER_API_KEY`. LiteLLM proxy receives two distinct Bearer tokens → separate spend rows in OpenRouter `/credits`. Acceptance: integration test asserts `JudgePanel` sends a different Authorization header than `InspectEvalCaller` for the same eval.

## Implementation Phases

Each slice is independently mergeable. Slice ordering reflects dependency: A → B → C → D → E.

### Slice A — JudgePanel module skeleton + self-judging guard (FR-002, SC-2)

**File**: `apps/eval-core-py/src/orchestrator/judge_panel.py` (NEW)

**Class skeleton**:

```python
class SelfJudgingError(ValueError):
    """Raised when judge_models contains the candidate's vendor family.

    Cardinal-sin guard per judge-policy.md:1. Family-level match (NOT raw
    string) — `openrouter/anthropic/claude-haiku` and `anthropic/claude-sonnet`
    both normalise to family `anthropic`.
    """


class JudgePanel:
    def __init__(
        self,
        judge_models: list[str],
        candidate_model_id: str,
        rubric_version: str,
        *,
        base_url: str = "http://localhost:4000",
        api_key_env: str = "OPENROUTER_API_KEY_JUDGE",
    ) -> None:
        self._guard_self_judging(judge_models, candidate_model_id)
        # ... store fields ...

    async def score(self, eval_result: EvalResult, task_id: str) -> list[Judgment]: ...

    def aggregate(self, judgments: list[Judgment]) -> JudgeAggregation: ...

    async def run_calibration(self, task_id: str) -> CalibrationResult: ...

    @staticmethod
    def _normalise_model_family(model_id: str) -> str:
        """Strip provider prefix; return vendor family token.

        Examples (verified by unit test):
          openrouter/anthropic/claude-sonnet-4-6  -> anthropic
          anthropic/claude-haiku                  -> anthropic
          openrouter/openai/gpt-5-mini            -> openai
          openrouter/google/gemini-3-flash        -> google
          openrouter/cerebras/qwen-3-14b          -> cerebras   (open-weight host treated as own family)
          openrouter/runpod/llama-4-70b           -> runpod
        """

    @classmethod
    def _guard_self_judging(cls, judge_models: list[str], candidate_model_id: str) -> None:
        cand_family = cls._normalise_model_family(candidate_model_id)
        for jm in judge_models:
            if cls._normalise_model_family(jm) == cand_family:
                raise SelfJudgingError(
                    f"Self-judging refused: candidate family={cand_family!r} "
                    f"appears in judge_models={judge_models!r} (offender={jm!r}). "
                    f"See PRD-002 SC-2 and judge-policy.md:1."
                )
```

**Self-judging semantics**:

- **NOT silent skip** — raise immediately. Orchestrator catches `SelfJudgingError` and records a FAILED `EvalRow` with `error_class=CONTRACT_VIOLATION` and detail `"SELF_JUDGING"` (uses existing `ErrorClass.CONTRACT_VIOLATION` enum; a new `ErrorClass.SELF_JUDGING` may be added later but reuses the existing slot for v0.1).
- Cross-route variants: `_normalise_model_family` splits on `/`, drops first segment if it equals `openrouter`, returns the next segment. Unit test covers all 5 ADR-003 lineup permutations.

**Acceptance criteria**:

- Unit test 1: `JudgePanel(judge_models=["openrouter/anthropic/claude-sonnet-4-6"], candidate_model_id="openrouter/anthropic/claude-haiku")` → raises `SelfJudgingError` with offender named.
- Unit test 2: `JudgePanel(judge_models=["openrouter/anthropic/claude-sonnet-4-6"], candidate_model_id="anthropic/claude-haiku")` → raises (cross-route variant).
- Unit test 3: `JudgePanel(judge_models=["openrouter/anthropic/...", "openrouter/openai/...", "openrouter/google/..."], candidate_model_id="openrouter/cerebras/qwen-3-14b")` → constructs cleanly (open-weight candidate, all 3 closed-family judges).
- Unit test 4: empty `judge_models=[]` → raises `ValueError("at least one judge required")`.

### Slice B — Inspect AI multi_scorer wiring + Phase 3 Week 1 spike (FR-001, H1 verification)

**Spike first** (one-day): see § Phase 3 Week 1 spike below — write a 30-LOC verification script. If H1 holds (per-judge `Score` objects individually accessible), proceed with Slice B implementation. If H1 refuted, **file ADR-006** (reserved) and revise Slice B to use custom `@scorer` per judge plus manual aggregation.

**Implementation (assuming H1 holds)**:

```python
async def score(self, eval_result: EvalResult, task_id: str) -> list[Judgment]:
    """Score one candidate output across the panel.

    Wraps Inspect AI's:
        multi_scorer(model_graded_qa(model=[j1, j2, j3]), reducer=mean_score())

    NOTE: Inspect AI's default reducer is `mean_score`; we override to NOT
    reduce here — we want per-judge Score objects (one per judge) and we
    compute median ourselves in aggregate() per docs/02-methodology/scoring.md
    (and EVID-001: HELM uses mean, POLLMEVALS uses median).

    Returns one Judgment per judge model. Position in the returned list
    matches the randomised judge_order (H2 mitigation of position bias).
    """
    # 1. Load rubric for task_id from evals/task-packs/<slug>/rubric.yaml
    # 2. Build anonymised submission (strip greetings, signatures, "as an AI" — per runbook 07:33-43)
    # 3. Randomise judge order (H2): rng.shuffle(judge_models_for_this_call)
    # 4. Invoke Inspect AI multi_scorer:
    #       scorer = multi_scorer(model_graded_qa(model=[...]), reducer=None)
    #    OR if reducer=None unsupported: read per-judge entries from EvalLog.samples[0].scores
    #       (which is a dict[str, Score] keyed by scorer name)
    # 5. For each judge, build Judgment with rubric_scores + total_score
    # 6. Return list[Judgment]
```

**Per-judge access strategy**:

- **Primary path** (H1 holds): use `multi_scorer(model_graded_qa(model=[...]), reducer=None)` or the Inspect AI option that surfaces per-judge `Score` (see EVID-004 ref to `scorers.html`).
- **Fallback path** (H1 partially holds — reducer is mandatory): build N separate `@scorer`-decorated functions, one per judge model; pass all N to the `Task(scorers=[s1, s2, s3])` argument; read per-judge results from `EvalLog.samples[0].scores` dict (keyed by scorer name).

**Acceptance criteria**:

- Integration test with `respx`-mocked LiteLLM proxy returning 3 distinct judge responses → `JudgePanel.score()` returns 3 `Judgment` objects with distinct `judge_model_id` values + per-criterion rubric scores.
- Position bias mitigation verified: same panel called twice on identical input produces different `judge_order` values across calls (within at most 6 permutations for 3 judges).

### Slice C — Krippendorff α + bootstrap CI computation (FR-003, SC-1)

**Library**: `krippendorff` (PyPI, MIT). Pin: `krippendorff>=0.7.0,<0.8` in `apps/eval-core-py/pyproject.toml`.

**Method**:

```python
def aggregate(self, judgments: list[Judgment]) -> JudgeAggregation:
    """Median + Krippendorff α + bootstrap CI.

    Per docs/02-methodology/scoring.md: median (NOT mean) across judges.
    Per PRD-002 Q2 (decision): publication gate uses CI lower-bound,
    NOT point estimate.

    Args:
        judgments: list of N Judgment objects (one per judge). N must be
            >= 2 to compute α; N >= 3 is the publication policy minimum.

    Returns:
        JudgeAggregation with:
          - median_per_criterion / median_total (numpy.median)
          - alpha_point: Krippendorff's α (ordinal level of measurement)
          - alpha_ci_lower / alpha_ci_upper: bootstrap 95% CI (2000 resamples)
          - judge_status: FULL if len(judgments) == n_judges_requested,
                          else DEGRADED with α=None (per Q3)
    """
    import krippendorff
    import numpy as np

    if len(judgments) < self._n_judges_requested:
        # Q3 degraded policy: α=None for this eval
        return JudgeAggregation(
            median_per_criterion=...,
            median_total=...,
            alpha_point=None,
            alpha_ci_lower=None,
            alpha_ci_upper=None,
            judge_status=JudgeStatus.DEGRADED,
            n_judges_responded=len(judgments),
            n_judges_requested=self._n_judges_requested,
        )

    # Build M x N reliability matrix: M rubric criteria rows, N judge columns
    matrix = np.array([[j.rubric_scores[crit] for j in judgments] for crit in criteria])

    alpha_point = krippendorff.alpha(
        reliability_data=matrix,
        level_of_measurement="ordinal",
    )

    # Bootstrap 95% CI — 2000 resamples per PRD-002 NFR (SC-1 spec)
    rng = np.random.default_rng(seed=42)  # fixed seed for reproducibility
    boot_alphas = []
    for _ in range(2000):
        sample_idx = rng.integers(0, matrix.shape[1], size=matrix.shape[1])
        boot_alphas.append(krippendorff.alpha(matrix[:, sample_idx], level_of_measurement="ordinal"))
    alpha_ci_lower, alpha_ci_upper = np.percentile(boot_alphas, [2.5, 97.5])

    return JudgeAggregation(
        median_per_criterion={c: float(np.median(matrix[i])) for i, c in enumerate(criteria)},
        median_total=float(np.median([j.total_score for j in judgments])),
        alpha_point=float(alpha_point),
        alpha_ci_lower=float(alpha_ci_lower),
        alpha_ci_upper=float(alpha_ci_upper),
        judge_status=JudgeStatus.FULL,
        n_judges_responded=len(judgments),
        n_judges_requested=self._n_judges_requested,
    )
```

**Publication gate semantics** (consumed downstream by manifest aggregator, NOT inside `aggregate()`):

- Per-eval `alpha_ci_lower` is reported. Run-level gate evaluates: `min(eval.judge_aggregate.alpha_ci_lower for eval in run.evals) >= 0.70`.
- Decision Q2: gate uses **CI lower-bound**, NOT point. A run with point α=0.72 but CI=[0.65, 0.78] is **REFUSED**.

**Acceptance criteria**:

- Golden test 1: hand-crafted 3-judge × 4-criterion matrix with known α = 0.83 (from `krippendorff` package own examples) → `alpha_point` matches within 0.001.
- Golden test 2: perfectly-agreeing matrix (all judges identical scores) → α = 1.0, CI = [1.0, 1.0].
- Golden test 3: orthogonal-disagreement matrix → α near 0, CI bracket includes 0.
- Bootstrap-CI test: fixed seed produces deterministic CI bounds (regression-safe).

### Slice D — Calibration suite + identification probe (FR-004, FR-005, SC-3, SC-4)

**Calibration sample layout** (per PRD-002 Q4):

```
evals/task-packs/be_01_jwt_auth/calibration/
├── perfect/
│   ├── sample-001.md       # canonical JWT middleware (gold)
│   ├── sample-002.md
│   └── ...                  # 10 samples
├── good/                    # 10 samples — minor issues (one missing test case)
├── mediocre/                # 10 samples — works but verbose/under-tested
├── poor/                    # 10 samples — partial impl + bugs
└── broken/                  # 10 samples — doesn't compile / wrong abstraction
calibration.yaml             # task-specific calibration meta (gold scores per level)
```

`calibration.yaml`:

```yaml
task_id: be_01_jwt_auth
rubric_version: "1.0"
gold_scores:
  perfect: 9.0
  good: 7.5
  mediocre: 5.0
  poor: 2.5
  broken: 0.5
mad_threshold: 1.5
n_samples_per_level: 10
```

**Calibration runner**:

```python
async def run_calibration(self, task_id: str) -> CalibrationResult:
    """Run each judge on all 50 calibration samples for one task.

    Returns per-judge MAD + rank correlation. Refuses to publish run
    (raises CalibrationFailedError) if any judge MAD > 1.5 per task
    (PRD-002 FR-004, SC-3).
    """
    # 1. Load evals/task-packs/<slug>/calibration/*.md (50 samples)
    # 2. For each judge model and each sample:
    #      score = await self._score_one(judge, sample, rubric)
    #      record (gold_score, judge_score, judge_model_id)
    # 3. Per judge:
    #      mad = mean(|score - gold| for sample in samples)
    #      rank_corr = scipy.stats.spearmanr(gold_scores, judge_scores).correlation
    # 4. Return CalibrationResult with structured per-judge metrics
    # 5. Caller (Phase 3 entrypoint) checks any judge mad > 1.5 → raise
```

**Identification probe** (FR-005, SC-4):

```python
async def run_identification_probe(self, task_id: str) -> ProbeResult:
    """SC-4 anonymisation effectiveness probe.

    Per PRD-002 Q5: 150 samples (10 × 5 quality levels × 3 tasks).
    Each sample is shown to each judge with prompt:
      "Below is a model output. Which of {claude, gpt, gemini} most likely
       produced it? Respond with one word."

    Returns aggregate accuracy across all judges. Caller (Phase 3 entrypoint)
    checks > 0.30 → refuse to publish; record EVID with the probe result.
    """
```

**Acceptance criteria**:

- Calibration unit test: synthetic 5-quality-level samples + mock judge returning gold_score + ε → MAD ≤ 0.5; assert pass.
- Calibration boundary test: mock judge returning gold_score + 2.0 (systematic bias) → MAD = 2.0; assert `CalibrationFailedError` raised by caller (we do NOT raise inside `run_calibration` itself — the runner returns the result; the caller decides what to do with it).
- Probe unit test: synthetic outputs stripped of family idioms → mock judge guessing randomly → accuracy ~33%; assert ≤ 30% pass.
- Wall-clock test (PRD-002 NFR-003): single-judge calibration of 50 samples completes in ≤ 10 min with mocked LiteLLM (asserts loop structure, not real latency).

### Slice E — GridRunner integration + degraded panel policy (FR-001, Q3 + NFR-001)

**Changes to `grid_runner.py`**:

1. Constructor gains `judge_panel: JudgePanel | None = None` (optional for back-compat with smoke runs without judges).
2. Constructor gains `judge_cost_estimate_per_eval: Decimal = Decimal("0.15")` (3 judges × ≈ $0.05 average per PRD-002 NFR-001 derivation).
3. **Pre-call budget gate** (grid_runner.py:230-246): include `self._judge_cost_estimate_per_eval` in the projected total when computing whether to continue. The current `should_continue(self._running_total)` becomes `should_continue(self._running_total + self._judge_cost_estimate_per_eval)` so judge spend is reserved upfront.
4. **Post-candidate-SCORED hook** (new code between grid_runner.py:269 and :291):

```python
if self._judge_panel is not None and result.eval_row.status == EvalStatus.SCORED:
    try:
        judgments = await self._judge_panel.score(result, request.task_id)
        aggregation = self._judge_panel.aggregate(judgments)
    except SelfJudgingError:
        raise  # contract violation — surfaces as FAILED row via existing gather path
    except JudgeUnavailableError as exc:
        # Q3 degraded policy: proceed at N-1, mark this eval DEGRADED, alpha=None
        judgments = exc.partial_judgments
        aggregation = self._judge_panel.aggregate(judgments)  # returns judge_status=DEGRADED

    # Rebuild EvalRow with judge fields (EvalRow is frozen; model_copy + update)
    result = EvalResult(
        request=request,
        eval_row=result.eval_row.model_copy(update={
            "judgments": judgments,
            "judge_aggregate": aggregation,
        }),
        exception=None,
        started_at=result.started_at,
        completed_at=datetime.now(UTC),
    )
    # Add judge cost to running total (NFR-001)
    self._running_total += sum(j.cost_usd for j in judgments)
```

5. **Run-level degraded abort** (post-grid, in `GridRunner.run`): after `await asyncio.gather`, count `n_degraded = sum(1 for r in results if isinstance(r, EvalResult) and r.eval_row.judge_aggregate is not None and r.eval_row.judge_aggregate.judge_status == DEGRADED)`. If `n_degraded / total_attempted > 0.20` → set `GridRunResult.judge_panel_breach = True` and orchestrator entrypoint refuses to publish (manifest still written with `status="degraded"` per ADR-003 precedent).

**Acceptance criteria**:

- Integration test 1: 3 working judges → 45-eval grid completes with all rows `judge_status=FULL`.
- Integration test 2: 1 of 3 judges returns httpx.HTTPStatusError 429 after retries → eval marked `judge_status=DEGRADED`, `alpha_*=None`, run continues. With only that one eval degraded out of 45, `n_degraded/45 = 0.022` < 0.20, run NOT aborted.
- Integration test 3: 12 of 45 evals (≈ 27%) end up degraded → `judge_panel_breach=True`, orchestrator entrypoint refuses publication; manifest written with `status="degraded"`.
- Cost integration test: dry-run with 45 evals × (0.012 candidate + 0.15 judge) = $7.29 ≤ $50 NFR-001 envelope.

### Phase 3 Week 1 spike (H1 verification — Q1 decision dependency)

**Spike script**: `apps/eval-core-py/scripts/inspect_ai_h1_spike.py` (NEW, ≤ 30 LOC, deleted after verdict).

**Pseudocode**:

```python
"""Spike: verify Inspect AI multi_scorer surfaces per-judge Score objects.

If this script's assertion fires, file ADR-006 (pivot to custom @scorer per
judge) and revise RFC-002 Slice B accordingly.
"""

import asyncio
from inspect_ai import Task, eval, Sample
from inspect_ai.scorer import multi_scorer, model_graded_qa

# Tiny one-sample task — does the model output contain "foo"?
task = Task(
    dataset=[Sample(input="Say 'foo'.", target="foo")],
    scorer=multi_scorer(
        scorers=[
            model_graded_qa(model="openrouter/anthropic/claude-haiku-4-5", template="..."),
            model_graded_qa(model="openrouter/openai/gpt-5-mini", template="..."),
        ],
        reducer=None,   # ← THE QUESTION: does Inspect AI honour reducer=None?
    ),
)
log = asyncio.run(eval(task, model="openrouter/anthropic/claude-haiku-4-5"))

# H1 assertion
sample = log[0].samples[0]
scores = sample.scores  # expected: dict[str, Score] with 2 entries — one per judge
assert isinstance(scores, dict), f"H1 REFUTED — scores is {type(scores)}, not dict"
assert len(scores) == 2, f"H1 REFUTED — got {len(scores)} per-judge entries, expected 2"
print("H1 SUPPORTED — per-judge Score access available.")
```

**Verdicts**:

- **H1 SUPPORTED** → proceed with Slice B as drafted; record EVID-{h1-spike} with verdict=supports, CL=3.
- **H1 REFUTED** → file ADR-006 (reserved slot per PRD-002 Q1) "pivot from Inspect AI multi_scorer to custom @scorer per judge"; revise Slice B fallback path to primary; schedule slip ~1 week per PRD-002 Risks.

**Budget**: ≤ $0.05 in real LLM spend (3 prompts × 2 judges = 6 cheap calls); spike runs on dev machine, not in CI.

## Test plan

| Test layer | What it covers | Tooling |
|---|---|---|
| Unit | Self-judging guard (cross-route variants), `_normalise_model_family` edge cases, median calculation, Krippendorff α on golden data, JudgeStatus state machine | pytest, no external deps |
| Unit | EvalRow extension (`judgments`/`judge_aggregate` round-trip via `model_dump`/`model_validate`) | pytest + pydantic v2 |
| Integration | 3-judge mocked panel → 3 Judgment objects; degraded-panel 2-of-3 case; full-failure case | respx (HTTPX mocker), `FakeJudgeCaller` (Protocol mirror of FakeEvalCaller) |
| Calibration | Synthetic 5-quality-level samples → MAD computed; MAD > 1.5 surfaces as `CalibrationFailedError` upstream | pytest + synthetic fixtures |
| Cost | Dry-run smoke-grid estimate (45 evals × $0.012 candidate + $0.15 judge) ≤ $50 NFR-001 envelope | unit (no network) |
| Regression | All existing 358 tests stay green after EvalRow extensions (default-None judge fields preserve back-compat) | pytest -q |
| Spike (one-off, manual) | H1 verification — Inspect AI multi_scorer per-judge Score access | `apps/eval-core-py/scripts/inspect_ai_h1_spike.py` |

**Test fixtures required** (new under `apps/eval-core-py/tests/fixtures/`):

- `judge_panel/three_judge_full_response.json` — three valid judge JSON responses
- `judge_panel/one_judge_429.json` — one rate-limit response (drives DEGRADED test)
- `judge_panel/golden_alpha_matrix.npy` — 3-judge × 4-criterion matrix with known α = 0.83
- `judge_panel/calibration_synthetic/{perfect,good,mediocre,poor,broken}/sample-*.md` — 5 levels × 3 samples each = 15 synthetic fixtures for fast tests (the real 50-sample suites live in `evals/task-packs/<slug>/calibration/`)

## Cost model (concrete)

| Phase | Candidate calls | Judge calls (× 3) | Estimated cost | Source |
|---|---|---|---|---|
| Smoke (45 evals = 5 models × 3 tasks × 3 seeds) | 45 × $0.012 ≈ **$0.54** | 45 × 3 × $0.05 ≈ **$6.75** | **$7.29 ± $1** | matches PRD-002 NFR-001 $12 ± $3 (with buffer for retries) |
| Calibration session (1 task × 3 judges × 50 samples) | — | 150 × $0.05 ≈ **$7.50** | **≤ $5 amortised** (cached per task version per PRD-002 NFR-001) | PRD-002 NFR-001 |
| Identification probe (one-off per weekly run) | — | 150 samples × 3 judges × $0.05 ≈ **$22.50** | one-off baseline | runs once per quarter expected; not weekly |
| Weekly (≈ 200 evals × 3 judges) | 200 × $0.012 ≈ $2.40 | 200 × 3 × $0.05 = $30.00 | **$32 ± $5** | ≤ $35 PRD-002 NFR-001 |

**Cost gate behaviour** (Slice E):

- Pre-call: `BudgetGate.should_continue(running_total + 0.15)` reserves judge spend upfront → no surprise overrun.
- Post-call: actual judge cost (sum of `judgments[i].cost_usd`) added to `running_total`. Delta vs estimate logged at DEBUG level.
- Run-level abort: if `running_total >= 0.80 × budget` mid-run (existing AC-3), no further evals scheduled; judge calls for in-flight evals are completed (judges already inside semaphore-protected block).

## Invariants

What MUST never be violated by this RFC:

1. **EvalRow `frozen=True` preserved** — judge fields are added as `Optional` with `default=None`; mutations use `model_copy(update=...)` only.
2. **FR-009 invariant preserved** — failed/degraded judge calls never drop an eval; the row is written to the journal with `judge_status=DEGRADED` or `error_class=CONTRACT_VIOLATION`.
3. **ADR-002 reproduce semantics preserved** — `make reproduce HASH=...` re-runs evaluator + judge aggregation against cached raw_output without re-calling any LLM. Judges' calls are part of the immutable run; reproduce never re-fires judges.
4. **Methodology v0.1.0 pin preserved** — median (not mean), Krippendorff α (not Cohen's κ), ≥3 judges, family-level self-judging guard, blind labels + anonymisation. Any change goes through ADR, not silent edit.
5. **Billing isolation preserved** — `OPENROUTER_API_KEY_JUDGE` is read only by `JudgePanel`; `OPENROUTER_API_KEY` only by `InspectEvalCaller`. No mixed-key path.
6. **multi_scorer with mean reducer NEVER used** — overriding the Inspect AI default is the load-bearing methodology difference; a future PR using `reducer=mean_score` is a v0.1.0 violation.

## Rollback Plan

If the RFC-002 implementation fails, rollback paths are scoped per slice:

| Failure mode | Rollback action |
|---|---|
| **H1 spike refutes** (Inspect AI multi_scorer per-judge surface unavailable) | File ADR-006 (reserved). Slice B fallback path becomes primary (N separate `@scorer`-decorated functions). Schedule slips ~1 week. No code in main yet — pure RFC revision. |
| **Slice A merged but self-judging guard misses a route** (escape hatch slip) | Hotfix: extend `_normalise_model_family` regex; add the missing route to the unit test matrix; revert via a follow-up commit, not branch rewind. Critical-severity bug = immediate fix-forward. |
| **Slice C Krippendorff α computation buggy on POLLMEVALS data** | Disable α gate at Phase 3 entry (run continues with α=None across all evals); manifest tagged `status="calibration-not-ready"`. Fix via follow-up commit; no destructive history rewrite. |
| **Slice D calibration runner times out (NFR-003 breach)** | Reduce calibration sample count from 50 to 25 (5 levels × 5 samples); re-document threshold in PRD-002 update; ADR-005 capture rationale. |
| **Slice E budget gate overrun** (judge cost > NFR-001) | Reduce `n_judges_requested` from 3 to 2 for the over-budget weekly cycle ONLY (one-off, not policy); fix `judge_cost_estimate_per_eval` default upward; re-test. Permanent change requires new ADR. |
| **Whole layer underperforms** (α floor stays below 0.70 after 3 weekly cycles) | Status page note: "leaderboard publication paused; methodology revision in flight"; PRD-002 reopens; this RFC moves to `superseded` with a successor RFC capturing the new methodology. NO mutation of already-published runs. |

**Cannot rollback**: any EvalRow already journaled with judge fields (ADR-0002 immutability). Mistakes surface as a new run + `supersedes` link, never an in-place edit.

## Related Artifacts

| Artifact | Relation | Why |
|---|---|---|
| **PRD-002** | `informs` | Parent — Q1-Q5 decisions are load-bearing for every slice |
| **PRD-001** | `informs` | Cost envelope NFR-001 ≤ $50 must contain $12 judge layer |
| **ADR-003** | `informs` | Judge diversity (3 vendor families) drove candidate lineup — judge panel inherits the same diversity constraint |
| **ADR-004** | `informs` | MoleculerPy concurrency — Phase 3+ moves judge calls to separate `judge-svc` workers; this RFC's Phase 2C single-process is the migration baseline |
| **ADR-005** | `informs` (FUTURE) | Median + CI-lower-bound gate rationale — being authored in parallel; this RFC cross-references the decision but does not block on the ADR's creation |
| **ADR-006** | `informs` (RESERVED) | H1 refutation pivot — created only if Phase 3 Week 1 spike fails |
| **EVID-001** | `informs` | HELM uses mean across judges; POLLMEVALS uses median per scoring.md — this RFC implements that divergence |
| **EVID-004** | `informs` | Inspect AI multi_scorer + model_graded_qa prior art is the foundation for Slice B |
| **EVID-015** | `informs` | EvalCaller Protocol pattern — JudgePanel follows the same testability seam discipline |
| **NOTE-002** | `informs` | Evidence Quality Standard — every EVID born from this RFC (calibration, α, probe, cost) carries explicit ADI + Trust Calculus |

**Frozen methodology source-of-truth** (read-only, never edited by this RFC):

- `docs/02-methodology/judge-policy.md` v0.1.0 — panel rules, anti-self-judging
- `docs/02-methodology/scoring.md` v0.1.0 — median, weight formulas
- `docs/04-runbook/07-judge-panel.md` — anonymisation pipeline + calibration sample format
- `docs/04-runbook/08-scoring-contract.md` — α + bootstrap CI specification

## Risks & Mitigations

| ID | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **Cost amplification non-linear** — judge calls add 3× per eval; weekly run exceeds budget | Med | High | NFR-001 dollar ceiling enforced via BudgetGate; judge cost reserved upfront in Slice E; dry-run cost estimate before launch (per PRD-001 NFR-002 ratio gate) |
| R2 | **Inspect AI multi_scorer per-judge surface unavailable** — H1 refuted | Med | Med | Phase 3 Week 1 spike (Implementation Phases § Phase 3 Week 1 spike); ADR-006 reserved for pivot; Slice B documents fallback (`@scorer` per judge + manual aggregation) |
| R3 | **Self-judging slip at runtime** — OpenRouter route `openrouter/anthropic/...` vs direct `anthropic/...` not caught by string-match | Low | Critical | Family-level normalisation in `_normalise_model_family`; cross-route unit tests cover all 5 ADR-003 lineup permutations; CI gate on test |
| R4 | **Calibration drift between runs** — silent judge model update invalidates prior α/MAD baselines (EVID-002 Voyage lesson) | Med | High | Manifest stores `calibration_hash` (SHA256 of calibration sample set + per-judge MAD vector); weekly run compares hash vs previous; drift alert in Phase 4 |
| R5 | **Judge unavailability mid-run** — vendor outage on 1 of 3 judges drops α confidence | Med | Med | Q3 degraded policy (Slice E): proceed at N-1, `alpha=None`, `judge_status=DEGRADED`; run-level abort if > 20% degraded; EVID logs every DEGRADED eval |
| R6 | **α point ≥ 0.70 but CI lower-bound < 0.70** — first weekly can't publish | Med | Med | Decision Q2 (CI-lower-bound gate) is intentional; if refused, increase calibration sample size to tighten CI; publish "calibration-not-ready" status note instead of broken leaderboard |
| R7 | **Cross-family preference leakage** — Anthropic/OpenAI/Google share pretrain data; judges not as independent as nominal families (arxiv 2502.01534) | Med | Med | ADR-003 3-family panel is v0.1 stance; v2.0 may add open-weight judges (Qwen, Llama) for true independence; EVID tracks self-enhancement bias on every weekly run |

## Out of Scope

- **Human judges** — PRD-002 says v2.0; calibration uses synthetic gold scores in v0.1.
- **Adaptive judge selection** — fixed panel for v0.1; revisit after first 2 weekly runs (PRD-002 Out of Scope).
- **Multi-criteria per-judge weighting** — defer to v0.2; v0.1 uses uniform per-criterion median.
- **Real-time judge feedback loop** (judge → candidate refinement) — defer; would invalidate immutability per ADR-0002.
- **Pairwise comparison mode** — rubric-only for v0.1; pairwise may come in v2.0 for tie-breaking.
- **Multi-language judges** — English-only until v2.0.
- **Judge fine-tuning on POLLMEVALS calibration data** — would invalidate independence; forbidden in v0.x.
- **Cross-run α aggregation** — per-run α only in v0.1; cross-run stability metrics deferred to Phase 4.

## Next steps (Phase 3, T+2..T+4 weeks)

1. **Week 1 (spike, ≤ 1 day)**: H1 verification — run `inspect_ai_h1_spike.py`; either ADR-006 or proceed.
2. **Week 1-2 (Slice A + B)**: `JudgePanel` skeleton + self-judging guard + Inspect AI wiring + unit tests.
3. **Week 2 (Slice C)**: Krippendorff α + bootstrap CI + golden-data tests.
4. **Week 3 (Slice D)**: Calibration runner + identification probe + synthetic-fixture tests; first real calibration session against 3 judges × 3 tasks → EVID-{calibration,α}.
5. **Week 3-4 (Slice E)**: GridRunner integration; first end-to-end smoke run WITH judges (45 evals × 3 judges) → EVID-{cost,judge-smoke}.
6. **Week 4**: Identification probe runs end-to-end → EVID-probe; SC-4 verified.
7. **Week 5 (buffer)**: ADR-005 drafted with calibration data; Guardian gate review; this RFC moves draft → active iff all 4 EVID artifacts land and PRD-002 R_eff stays ≥ 0.70.

---

*Status: draft. Activation requires: (a) Phase 3 Week 1 spike outcome captured as EVID, (b) PRD-002 R_eff ≥ 0.70 maintained, (c) Guardian gate review per NOTE-002 contract.*






