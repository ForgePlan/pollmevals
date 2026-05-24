"""JudgePanel — multi-judge scoring layer for POLLMEVALS (RFC-002).

This module is the parallel companion to eval_caller.py — same Protocol-driven
testability seam discipline (EVID-015), no inheritance, no framework coupling.

Slice A (this file): skeleton + self-judging guard.
Slice B (score()): Inspect AI list-of-scorers wiring (per EVID-023 findings).
Slice C (aggregate()): Krippendorff alpha + bootstrap CI computation.
Slice D (run_calibration()): calibration suite + identification probe.
Slice E (grid_runner.py): GridRunner integration.

Key finding from EVID-023 H1 spike:
  - multi_scorer() is BROKEN in inspect_ai==0.3.46 — do NOT use.
  - Production path: pass a LIST of model_graded_qa scorers to Task(scorer=[...]).
  - Inspect AI auto-assigns names: 'model_graded_qa', 'model_graded_qa_1', …
  - Judge max_tokens MUST be capped via get_model(config=GenerateConfig(max_tokens=N))
    to avoid OpenRouter HTTP 402 budget exhaustion on long-context models.

Concurrency is OUTSIDE this module — same discipline as eval_caller.py:13-14.
"""

from __future__ import annotations

import logging
import os
import pathlib
import random
from decimal import Decimal
from typing import TYPE_CHECKING

from inspect_ai.model import GenerateConfig

from src.contracts import JudgeAggregation, Judgment

if TYPE_CHECKING:
    from inspect_ai import Task as InspectTask
    from inspect_ai.log import EvalLog
    from inspect_ai.model import Model as InspectModel
    from inspect_ai.solver import Solver

    from src.orchestrator.eval_caller import EvalResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Family normalisation table
# Known vendor families: segment after optional "openrouter/" prefix.
# Keys are normalised segment values; values are the canonical family name.
# Order matters: more specific prefixes first (e.g. "meta-llama" before "meta").
# ---------------------------------------------------------------------------

_FAMILY_ALIASES: dict[str, str] = {
    # Anthropic
    "anthropic": "anthropic",
    "claude": "anthropic",  # LiteLLM proxy aliases like "claude-sonnet-4-6-judge"
    # OpenAI
    "openai": "openai",
    "gpt": "openai",  # proxy alias like "gpt-5-mini-judge"
    # Google
    "google": "google",
    "gemini": "google",  # proxy alias like "gemini-3-flash"
    # Meta / Llama
    "meta-llama": "meta-llama",
    "meta": "meta-llama",
    "llama": "meta-llama",
    # Qwen (Alibaba)
    "qwen": "qwen",
    "alibaba": "qwen",
}

# Default judge max_tokens cap per EVID-023 finding (prevents HTTP 402 on
# OpenRouter when key budget is low — Claude Sonnet native max is 65k).
_DEFAULT_JUDGE_MAX_TOKENS = 512


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class SelfJudgingError(ValueError):
    """Raised when judge_models contains the candidate's vendor family.

    Cardinal-sin guard per judge-policy.md:1. Family-level match (NOT raw
    string) — 'openrouter/anthropic/claude-haiku' and 'anthropic/claude-sonnet'
    both normalise to family 'anthropic'.

    SC-2 in PRD-002: zero self-judging incidents. This guard fires in
    JudgePanel.__init__ so the panel never reaches score() with a violation.
    """


# ---------------------------------------------------------------------------
# Family normalisation (static, no network)
# ---------------------------------------------------------------------------


def _normalise_model_family(model_id: str) -> str:
    """Extract vendor family from a model ID string.

    Handles three routing patterns:
      1. OpenRouter prefix:  openrouter/anthropic/claude-sonnet-4-6  → anthropic
      2. Direct vendor:      anthropic/claude-haiku                  → anthropic
      3. LiteLLM proxy alias: claude-sonnet-4-6-judge               → anthropic
                              gpt-5-mini-judge                       → openai
                              gemini-3-flash                         → google

    Algorithm:
      - Split on '/'.
      - If first segment is 'openrouter', drop it.
      - The next segment is the family candidate.
      - Look up _FAMILY_ALIASES for the canonical name.
      - If not found, return the candidate as-is (unknown family treated as
        its own unique family — prevents false self-judging refusals for
        open-weight models served on specialised hosts like 'runpod').

    Examples (all verified by unit tests):
      openrouter/anthropic/claude-sonnet-4-6    → anthropic
      anthropic/claude-haiku                    → anthropic
      openrouter/openai/gpt-5-mini              → openai
      openrouter/google/gemini-3-flash-preview  → google
      openrouter/meta-llama/llama-3.3-70b       → meta-llama
      openai/Qwen/Qwen3-14B                     → qwen  (note: openai prefix here is the
                                                         provider hub, not the vendor family)
      claude-sonnet-4-6-judge                   → anthropic  (proxy alias)
    """
    parts = model_id.split("/")

    # Drop the aggregator prefix if present.
    if parts[0].lower() == "openrouter":
        parts = parts[1:]

    # Drop generic provider prefixes that are NOT themselves vendor families.
    # "openai/" used as the OPENAI_BASE_URL routing prefix in Inspect AI (see
    # inspect_ai_h1_spike.py:213) means the next segment is the actual vendor.
    # Only drop if there are 3+ segments: openai/Qwen/Qwen3-14B → Qwen/Qwen3-14B.
    # With 2 segments (openai/gpt-5-mini), "openai" is the vendor itself — keep it.
    if parts[0].lower() == "openai" and len(parts) >= 3:
        parts = parts[1:]

    family_candidate = parts[0].lower()

    # Handle proxy aliases that embed the family in the model name itself
    # (e.g. "claude-sonnet-4-6-judge" → "claude-" prefix → anthropic).
    if family_candidate not in _FAMILY_ALIASES:
        for prefix, canonical in _FAMILY_ALIASES.items():
            if family_candidate.startswith(prefix):
                return canonical
        # Unknown family — return the raw candidate so it's treated as its
        # own unique family (no false self-judging refusal for novel hosts).
        return family_candidate

    return _FAMILY_ALIASES[family_candidate]


# ---------------------------------------------------------------------------
# JudgePanel
# ---------------------------------------------------------------------------


class JudgePanel:
    """Multi-judge scoring panel for one evaluation pass.

    Parallel to EvalCaller — same Protocol-driven testability seam (EVID-015).
    Concurrency is the caller's responsibility (matches eval_caller.py:13-14).

    Self-judging guard fires in __init__ — raises SelfJudgingError immediately
    if any judge family matches the candidate family (PRD-002 SC-2, FR-002).

    Billing isolation: reads api_key_env (default OPENROUTER_API_KEY_JUDGE)
    from os.environ — separate from candidate's OPENROUTER_API_KEY (NFR-005).

    Args:
        judge_models: list of judge model IDs (≥1 required). Each must be in
            a different vendor family from the candidate, and ideally from
            different families among themselves (ADR-003 diversity constraint).
        candidate_model_id: the model being evaluated. Used solely for the
            self-judging guard — not passed to any LLM call.
        rubric_version: identifies which rubric YAML the judges will use.
        base_url: LiteLLM proxy base URL. Defaults to localhost:4000.
        api_key_env: env var name holding the judge billing key (NFR-005).
        judge_max_tokens: output token cap per judge call. Default 512 per
            EVID-023 finding — prevents HTTP 402 budget exhaustion.
    """

    def __init__(
        self,
        judge_models: list[str],
        candidate_model_id: str,
        rubric_version: str,
        *,
        base_url: str = "http://localhost:4000",
        api_key_env: str = "OPENROUTER_API_KEY_JUDGE",
        judge_max_tokens: int = _DEFAULT_JUDGE_MAX_TOKENS,
    ) -> None:
        if not judge_models:
            raise ValueError("at least one judge required")

        # SC-2 guard: must fire before any other state is set.
        self._guard_self_judging(judge_models, candidate_model_id)

        self._judge_models = list(judge_models)
        self._n_judges_requested = len(judge_models)
        self._candidate_model_id = candidate_model_id
        self._rubric_version = rubric_version
        self._base_url = base_url.rstrip("/")
        self._api_key_env = api_key_env
        self._judge_max_tokens = judge_max_tokens

        # Store the GenerateConfig; model objects are created lazily in score()
        # to avoid requiring OPENAI_API_KEY at construction time (unit tests run
        # without real credentials — RFC-002 Slice A explicitly permits deferral).
        # Slice B's score() calls _make_judge_models() which calls get_model().
        # EVID-023: GenerateConfig(max_tokens=512) prevents HTTP 402 budget
        # exhaustion on OpenRouter (Claude Sonnet native max is 65k).
        self._judge_config = GenerateConfig(max_tokens=judge_max_tokens)
        # Lazily populated by _make_judge_models() on first score() call.
        self._judge_model_objects: list[InspectModel] | None = None

        logger.debug(
            "JudgePanel created: n_judges=%d candidate=%s rubric=%s max_tokens=%d",
            len(self._judge_models),
            candidate_model_id,
            rubric_version,
            judge_max_tokens,
        )

    # ------------------------------------------------------------------
    # Public interface (Slices B and C — stubs for Slice A)
    # ------------------------------------------------------------------

    async def score(self, eval_result: EvalResult, task_id: str) -> list[Judgment]:
        """Score one candidate output across the full judge panel.

        Uses Inspect AI's list-of-scorers path (Task(scorer=[s1, s2, s3])).
        Per-judge Score objects are read from EvalLog.samples[0].scores (a dict
        keyed by auto-assigned scorer names: 'model_graded_qa', 'model_graded_qa_1',
        ...).

        API source: Context7 /ukgovernmentbeis/inspect_ai — model_graded_qa,
        Task(scorer=[...]), EvalLog.samples[].scores pattern.
        Confirmed working by EVID-023 H1 spike (inspect_ai==0.3.46).

        NOTE: multi_scorer() is BROKEN in inspect_ai==0.3.46 (runtime crash
        "Object score does not have registry info"). Do NOT use multi_scorer()
        until upstream fix lands (github.com/UKGovernmentBEIS/inspect_ai/issues/4027).

        IMPORTANT: always cap judge max_tokens explicitly via
        get_model(judge, config=GenerateConfig(max_tokens=512)) — the default
        is the model's native max (65k for Claude Sonnet), which exhausts
        OpenRouter monthly budget on the first run (HTTP 402 confirmed EVID-023).

        Args:
            eval_result: the completed candidate evaluation (status=SCORED).
                         raw candidate output is read from the local artifact URI
                         stored in eval_result.eval_row.artifact_refs.raw_output.
            task_id: task identifier (e.g. "be_01_jwt_auth") — used as the
                     judge prompt context and for rubric loading in future slices.

        Returns:
            One Judgment per judge model. Position in the list matches the
            randomised judge_order (H2 position-bias mitigation per RFC-002).
        """
        from inspect_ai import Task
        from inspect_ai.dataset import Sample
        from inspect_ai.scorer import model_graded_qa
        from inspect_ai.solver import solver as _solver

        # ── 1. Read raw candidate output from artifact URI ─────────────────
        raw_output_text = self._read_raw_output(eval_result)

        # ── 2. Build forwarding solver — injects pre-computed output so
        #       judges grade existing text, not a new generation ────────────
        @_solver
        def _forwarding_solver(forced_output: str) -> Solver:
            """Return a solver that plants pre-computed text into TaskState.output.

            This avoids re-generating the candidate response — judges receive
            the same text that the candidate actually produced.
            """
            from inspect_ai.model import ModelOutput
            from inspect_ai.solver import Generate, TaskState

            async def _solve(state: TaskState, generate: Generate) -> TaskState:
                state.output = ModelOutput.from_content(
                    model=str(state._model),
                    content=forced_output,
                )
                state.completed = True
                return state

            return _solve

        # ── 3. Randomise judge order (H2 position-bias mitigation) ──────────
        judge_ids_shuffled = list(self._judge_models)
        random.shuffle(judge_ids_shuffled)

        # ── 4. Build per-judge scorers with explicit max_tokens cap ──────────
        #       EVID-023 finding #3: without this cap, HTTP 402 on OpenRouter.
        judge_model_objs = self._make_judge_models()
        # Rebuild in shuffled order (judge_model_objs preserves init order,
        # so we need to re-map after shuffling).
        original_order = list(self._judge_models)
        judge_models_in_shuffled_order = [
            judge_model_objs[original_order.index(jid)] for jid in judge_ids_shuffled
        ]

        scorers = [model_graded_qa(model=jm) for jm in judge_models_in_shuffled_order]

        # ── 5. Build a minimal Task for judging ──────────────────────────────
        #       input = task description (so judges understand context)
        #       target = empty (model_graded_qa grades completion vs input)
        #       The forwarding solver injects raw_output_text into state.output.
        sample_input = (
            f"[POLLMEVALS judge task] task={task_id} "
            f"model={eval_result.request.model_id} "
            f"stack={eval_result.request.stack_id} "
            f"seed={eval_result.request.seed}\n\n"
            f"Evaluate the following model output for task '{task_id}':\n\n"
            f"{raw_output_text}"
        )

        judge_task = Task(
            dataset=[
                Sample(
                    input=sample_input,
                    target="",  # judges grade via model_graded_qa template
                    metadata={"forced_output": raw_output_text},
                )
            ],
            solver=_forwarding_solver(forced_output=raw_output_text),
            scorer=scorers,
        )

        # ── 6. Run judges via Inspect AI eval_async ───────────────────────────
        #       We set OPENAI_BASE_URL + OPENAI_API_KEY so Inspect AI routes
        #       through the LiteLLM proxy (same pattern as spike script line 183).
        logs = await self._run_judge_task(judge_task)

        # ── 7. Parse per-judge Score from EvalLog.samples[0].scores ──────────
        #       Keys are auto-assigned: 'model_graded_qa', 'model_graded_qa_1', …
        #       Per EVID-023: dict with N entries, one per scorer in the list.
        if not logs:
            raise RuntimeError("JudgePanel.score(): Inspect AI eval_async returned no logs")
        # Import EvalLog for isinstance narrowing so mypy knows .samples exists.
        from inspect_ai.log import EvalLog as _EvalLog

        log = logs[0]
        if not isinstance(log, _EvalLog):
            raise RuntimeError(
                f"JudgePanel.score(): unexpected log type {type(log).__name__}; expected EvalLog"
            )
        if not log.samples:
            raise RuntimeError("JudgePanel.score(): EvalLog has no samples")

        sample = log.samples[0]
        # sample.scores is dict[str, Score] | None in inspect_ai type stubs.
        raw_scores = sample.scores
        scores_dict = raw_scores if isinstance(raw_scores, dict) else {}

        judgments: list[Judgment] = []
        for idx, judge_id in enumerate(judge_ids_shuffled):
            # Scorer names: first scorer = 'model_graded_qa', subsequent = 'model_graded_qa_1', etc.
            # Inspect AI uses the auto-suffix pattern confirmed in EVID-023.
            scorer_key = "model_graded_qa" if idx == 0 else f"model_graded_qa_{idx}"
            score_obj = scores_dict.get(scorer_key)

            if score_obj is None:
                # Fallback: try positional access if naming pattern shifted.
                score_obj_list = list(scores_dict.values())
                score_obj = score_obj_list[idx] if idx < len(score_obj_list) else None

            if score_obj is None:
                logger.warning(
                    "JudgePanel.score(): no Score for judge %s (scorer_key=%s); available keys=%s",
                    judge_id,
                    scorer_key,
                    list(scores_dict.keys()),
                )
                # Skip this judge rather than crash; caller handles missing judgments.
                continue

            # model_graded_qa returns 'C' (correct) or 'I' (incorrect) for QA-style.
            # Slice C+ will use multi-criterion rubric scores. For Slice B:
            # "C" -> 1.0 (correct), "I" -> 0.0 (incorrect), scaled to 0-10.
            raw_value = score_obj.value
            if isinstance(raw_value, (int, float)):
                numeric_01 = max(0.0, min(1.0, float(raw_value)))
            elif isinstance(raw_value, str):
                numeric_01 = 1.0 if raw_value.upper() == "C" else 0.0
            else:
                numeric_01 = 0.0

            # Scale 0-1 -> 0-10 for Judgment.total_score (validated ge=0, le=10).
            total_score_10 = numeric_01 * 10.0

            judgments.append(
                Judgment(
                    judge_model_id=judge_id,
                    judge_order=idx,
                    rubric_version=self._rubric_version,
                    rubric_scores={"overall": total_score_10},
                    total_score=total_score_10,
                    raw_explanation=str(score_obj.explanation or ""),
                    latency_ms=0,  # TODO Slice E — read from log.stats
                    tokens_in=0,  # TODO Slice E
                    tokens_out=0,  # TODO Slice E
                    cost_usd=Decimal("0"),  # TODO Slice E (litellm.cost_per_token)
                )
            )

        return judgments

    def aggregate(self, judgments: list[Judgment]) -> JudgeAggregation:
        """Compute median + Krippendorff alpha + bootstrap CI across the panel.

        Per docs/02-methodology/scoring.md: median per criterion (NOT mean — EVID-001).
        Per PRD-002 Q2 / ADR-005: publication gate uses CI lower-bound >= 0.70
        (bootstrap 2000 resamples, 95% CI, deterministic seed=42 per ADR-005
        invariant "bootstrap_seed recorded in manifest for reproducibility").

        Matrix layout: N judge rows x M criteria columns.
        krippendorff.alpha() expects rows=coders (judges), cols=items (criteria).
        Krippendorff alpha level_of_measurement="ordinal" per ADR-005 invariant
        ("Rubric scores are ordered but score-distance is not metric").

        Degraded panel (PRD-002 Q3): if len(judgments) < _n_judges_requested
        return judge_status="DEGRADED" with all alpha fields = None.

        Args:
            judgments: list of Judgment objects from score() — one per judge.
                       At least 1 required (JudgeAggregation.n_judges_used >= 1).

        Returns:
            JudgeAggregation with median_per_criterion, alpha fields, and
            judge_status. Bootstrap CI uses 2000 resamples (ADR-005 / SC-1).

        Library: krippendorff>=0.7,<1 (Thomas Grill PyPI package).
        Import: krippendorff.alpha(reliability_data, level_of_measurement)
        Confirmed: Library-first lookup via Context7 (aleph-alpha variant found
        at /aleph-alpha/krippendorff-aleph-alpha uses different API; standard
        `krippendorff` PyPI package confirmed by RFC-002 pin + ADR-005 references).
        """
        import krippendorff  # type: ignore[import-untyped]
        import numpy as np

        # ── Collect all criteria present across all judgments (sorted for determinism)
        criteria = sorted({c for j in judgments for c in j.rubric_scores})

        # ── Compute median per criterion (always computed, even in DEGRADED path)
        median_per_criterion: dict[str, float] = {}
        for crit in criteria:
            scores_for_crit = [j.rubric_scores[crit] for j in judgments if crit in j.rubric_scores]
            if scores_for_crit:
                median_per_criterion[crit] = float(np.median(scores_for_crit))

        # ── Degraded panel check (PRD-002 Q3): N-1 → alpha=None ────────────────
        if len(judgments) < self._n_judges_requested:
            return JudgeAggregation(
                median_per_criterion=median_per_criterion,
                alpha_point=None,
                alpha_ci_lower=None,
                alpha_ci_upper=None,
                judge_status="DEGRADED",
                n_judges_used=len(judgments),
            )

        # ── Build N x M reliability matrix: N judge rows, M criteria columns ──
        # krippendorff.alpha() expects rows=coders (judges), cols=items (criteria).
        # NaN fills missing criterion scores (krippendorff treats NaN as "missing
        # data" — annotator did not rate this item, which is the correct semantics).
        n_judges = len(judgments)
        matrix = np.array(
            [[j.rubric_scores.get(crit, np.nan) for crit in criteria] for j in judgments],
            dtype=float,
        )

        # ── Point estimate (ordinal level per ADR-005) ─────────────────────────
        alpha_point = float(
            krippendorff.alpha(
                reliability_data=matrix,
                level_of_measurement="ordinal",
            )
        )

        # ── Bootstrap 95% CI — 2000 resamples, deterministic seed=42 (ADR-005) ─
        # Resample judges (rows) with replacement — each resample is a virtual panel
        # of n_judges drawn with replacement from the actual panel.
        rng = np.random.default_rng(seed=42)
        boot_alphas: list[float] = []
        for _ in range(2000):
            # Resample judge rows with replacement.
            idx = rng.integers(0, n_judges, size=n_judges)
            boot_matrix = matrix[idx, :]
            try:
                a = float(
                    krippendorff.alpha(
                        reliability_data=boot_matrix,
                        level_of_measurement="ordinal",
                    )
                )
                # Reject NaN (degenerate sample where all judges gave identical
                # scores — alpha is undefined; krippendorff returns nan in that case).
                if not np.isnan(a):
                    boot_alphas.append(a)
            except Exception:
                # Degenerate sample — krippendorff may raise on edge cases.
                # Skip rather than crash; CI computed from valid samples only.
                pass

        if boot_alphas:
            alpha_ci_lower, alpha_ci_upper = (
                float(v) for v in np.percentile(boot_alphas, [2.5, 97.5])
            )
        else:
            # Fallback: all resamples degenerate → CI collapses to the point estimate.
            alpha_ci_lower = alpha_point
            alpha_ci_upper = alpha_point

        return JudgeAggregation(
            median_per_criterion=median_per_criterion,
            alpha_point=alpha_point,
            alpha_ci_lower=alpha_ci_lower,
            alpha_ci_upper=alpha_ci_upper,
            judge_status="OK",
            n_judges_used=len(judgments),
        )

    # ------------------------------------------------------------------
    # Self-judging guard (static — no network, no external deps)
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_model_family(model_id: str) -> str:
        """Public static wrapper — delegates to module-level function.

        Exposed as a static method so callers can test normalisation without
        constructing a full JudgePanel instance.
        """
        return _normalise_model_family(model_id)

    @classmethod
    def _guard_self_judging(cls, judge_models: list[str], candidate_model_id: str) -> None:
        """Raise SelfJudgingError if any judge family matches the candidate family.

        PRD-002 FR-002 + SC-2: zero self-judging incidents. Family-level match
        (NOT raw string) — prevents OpenRouter cross-route variants from slipping
        through (e.g. 'openrouter/anthropic/claude-haiku' and 'anthropic/claude-sonnet'
        both normalise to family 'anthropic').

        Semantics: NOT silent skip — raise immediately. The orchestrator catches
        SelfJudgingError and records a FAILED EvalRow with
        error_class=CONTRACT_VIOLATION.
        """
        cand_family = cls._normalise_model_family(candidate_model_id)
        for jm in judge_models:
            judge_family = cls._normalise_model_family(jm)
            if judge_family == cand_family:
                raise SelfJudgingError(
                    f"Self-judging refused: candidate family={cand_family!r} "
                    f"appears in judge_models={judge_models!r} (offender={jm!r}). "
                    f"See PRD-002 SC-2 and judge-policy.md:1."
                )

    # ------------------------------------------------------------------
    # Accessors (read-only views of init-time state)
    # ------------------------------------------------------------------

    @property
    def judge_models(self) -> list[str]:
        """Return the list of judge model IDs (copy — immutable view)."""
        return list(self._judge_models)

    @property
    def rubric_version(self) -> str:
        return self._rubric_version

    @property
    def api_key(self) -> str:
        """Resolve the judge API key from the environment at access time.

        Returns empty string if the env var is not set (allows unit tests to
        construct JudgePanel without real credentials).
        """
        return os.environ.get(self._api_key_env, "")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_judge_models(self) -> list[InspectModel]:
        """Lazily instantiate Inspect AI judge model objects.

        Called by score() (Slice B). Deferred from __init__ so that unit
        tests can construct JudgePanel without OPENAI_API_KEY in the
        environment (the guard logic is credential-free).

        EVID-023: uses "openai/" prefix to route through OPENAI_BASE_URL
        (LiteLLM proxy). GenerateConfig(max_tokens=512) prevents HTTP 402.
        """
        from inspect_ai.model import get_model

        if self._judge_model_objects is None:
            self._judge_model_objects = [
                get_model(
                    self._proxy_alias_for(jm),
                    config=self._judge_config,
                )
                for jm in self._judge_models
            ]
        return self._judge_model_objects

    def _proxy_alias_for(self, judge_id: str) -> str:
        """Build the Inspect AI model string that routes through LiteLLM proxy.

        Per EVID-023 spike script (line 213): "openai/" prefix tells Inspect AI
        to use OPENAI_BASE_URL (which we point at the LiteLLM proxy at
        self._base_url).  The judge_id is passed through as-is; if it already
        contains a "/" the LiteLLM proxy resolves it via its model_list config.

        Examples:
          "claude-sonnet-4-6-judge"         → "openai/claude-sonnet-4-6-judge"
          "openrouter/anthropic/claude-..."  → "openai/openrouter/anthropic/claude-..."
              (technically valid; LiteLLM strips the openai/ routing prefix)

        For production use, judge model IDs should match the model_name entries
        in infra/litellm-config.yaml (e.g. "claude-sonnet-4-6-judge").
        """
        if judge_id.startswith("openai/"):
            return judge_id  # already prefixed
        return f"openai/{judge_id}"

    def _read_raw_output(self, eval_result: EvalResult) -> str:
        """Read the candidate's raw output text from the local artifact file.

        The artifact URI has the form "file://artifacts/evals/{row_id}/{label}-{sha256}.txt".
        We strip the "file://" prefix and resolve relative to CWD.

        If the file cannot be read (e.g. in unit tests with stub URIs), falls back
        to a placeholder string so that test mocks can verify the rest of the flow
        without requiring real disk I/O.
        """
        if eval_result.eval_row is None:
            return "[no eval_row — candidate output unavailable]"

        uri = eval_result.eval_row.artifact_refs.raw_output.uri
        if not uri.startswith("file://"):
            # Non-local URI (e.g. r2://...) — cannot read locally.
            return f"[non-local artifact uri={uri}]"

        file_path = pathlib.Path(uri[len("file://") :])
        try:
            return file_path.read_text(encoding="utf-8")
        except OSError:
            logger.debug(
                "_read_raw_output: cannot read artifact at %s — "
                "returning placeholder (unit test or missing artifact)",
                file_path,
            )
            return f"[artifact not readable: {uri}]"

    async def _run_judge_task(self, judge_task: InspectTask) -> list[EvalLog]:
        """Run a judge Task via Inspect AI eval_async, with proxy env wiring.

        Sets OPENAI_BASE_URL and OPENAI_API_KEY in the process environment so
        Inspect AI routes all "openai/" prefixed model calls through our
        LiteLLM proxy (same pattern as spike script, lines 183-184).

        Returns the list[EvalLog] from eval_async.
        """
        from inspect_ai import eval_async as _inspect_eval_async
        from inspect_ai.log import EvalLog as _EvalLog

        old_base_url = os.environ.get("OPENAI_BASE_URL")
        old_api_key = os.environ.get("OPENAI_API_KEY")
        try:
            os.environ["OPENAI_BASE_URL"] = self._base_url
            api_key = self.api_key or "none"
            os.environ["OPENAI_API_KEY"] = api_key

            # eval_async is a native coroutine in inspect_ai — await directly.
            result = await _inspect_eval_async(
                judge_task,
                log_dir="/tmp/pollmevals_judge_logs",
                log_level="warning",
            )
            if not result:
                return []
            return [r for r in result if isinstance(r, _EvalLog)]
        finally:
            # Restore original env state.
            if old_base_url is None:
                os.environ.pop("OPENAI_BASE_URL", None)
            else:
                os.environ["OPENAI_BASE_URL"] = old_base_url
            if old_api_key is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = old_api_key
