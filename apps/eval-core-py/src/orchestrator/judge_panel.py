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
from typing import TYPE_CHECKING

from inspect_ai.model import GenerateConfig

from src.contracts import JudgeAggregation, Judgment

if TYPE_CHECKING:
    from inspect_ai.model import Model as InspectModel

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

        Slice B implementation: Inspect AI list-of-scorers wiring per EVID-023
        (multi_scorer() is broken in inspect_ai==0.3.46 — use list path instead).

        Returns one Judgment per judge. Position in the returned list matches
        the randomised judge_order (H2 position-bias mitigation).

        NOTE: This is a Slice B stub — raises NotImplementedError until Slice B
        is merged.
        """
        raise NotImplementedError(
            "JudgePanel.score() is not implemented yet — Slice B. "
            "See RFC-002 Slice B for the Inspect AI list-of-scorers wiring plan."
        )

    def aggregate(self, judgments: list[Judgment]) -> JudgeAggregation:
        """Compute median + Krippendorff alpha + bootstrap CI across the panel.

        Per docs/02-methodology/scoring.md: median (NOT mean — EVID-001).
        Per PRD-002 Q2: publication gate uses CI lower-bound >= 0.70 (bootstrap
        2000 resamples, 95% CI).

        NOTE: This is a Slice C stub — raises NotImplementedError until Slice C
        is merged.
        """
        raise NotImplementedError(
            "JudgePanel.aggregate() is not implemented yet — Slice C. "
            "See RFC-002 Slice C for the Krippendorff alpha + bootstrap CI plan."
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
                get_model(f"openai/{jm}", config=self._judge_config) for jm in self._judge_models
            ]
        return self._judge_model_objects
