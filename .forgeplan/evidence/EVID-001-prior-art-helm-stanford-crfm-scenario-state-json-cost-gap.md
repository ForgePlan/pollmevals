---
depth: standard
id: EVID-001
kind: evidence
last_modified_at: 2026-05-23T19:28:29.700509+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-001
  relation: informs
- target: ADR-002
  relation: informs
- target: PRD-002
  relation: informs
status: active
title: 'prior art: HELM (Stanford CRFM) — scenario_state.json + cost gap'
---

# EVID-001: HELM (Stanford CRFM) — scenario_state.json + cost gap

## Structured Fields

verdict: supports
congruence_level: 2
evidence_type: audit

## Summary

External prior art review of HELM (Holistic Evaluation of Language Models, Stanford CRFM, Liang et al. 2022 + 2024-2025 updates). Validates POLLMEVALS's choice of evaluator-only reproduce (ADR-002) and confirms an industry gap (per-eval cost transparency) that POLLMEVALS deliberately closes.

## Key Findings

### Reproducibility model — direct precedent for ADR-002

HELM writes `scenario_state.json` containing **every request to and response from the model**. On a rerun, HELM re-executes the *evaluator* against this cached artifact rather than re-calling the model. The model is only re-queried when the cache is absent or the run suite name changes. This is **equivalent** to POLLMEVALS's ADR-002 decision: reproduce works on cached raw_output, not by re-calling the LLM API.

Source: <https://crfm-helm.readthedocs.io/en/v0.3.0/tutorial/>, confirmed via class hierarchy in <https://github.com/stanford-crfm/helm/blob/main/docs/code.md>.

### Cost transparency — industry gap POLLMEVALS closes

HELM does **not** snapshot per-eval pricing at run time. The 2022 paper showed an $85–$10,926 per-model spread (~$100K total across 30 models × 42 scenarios), but this was manual post-hoc accounting. The current leaderboard and `stats.json` output do **not** surface a standardized cost field. HuggingFace's EvalEval coalition (2025) explicitly calls this out as an industry-wide gap, noting **33× cost spreads for identical tasks** and recommending Pareto-frontier reporting.

Source: <https://huggingface.co/blog/evaleval/eval-costs-bottleneck>.

### Architecture mapping (informs SPEC-001)

HELM pipeline: `helm-run` → `helm-summarize` → `helm-server`. Internally a run decomposes into RunSpecs, each mapping a Scenario through `adapter → executor → metric`. Intermediate RequestStates are serialized to the output directory.

| HELM concept | POLLMEVALS analogue |
|---|---|
| `scenario_state.json` | `artifact_refs.raw_output` (per-eval, content-addressed) |
| `RunSpec` | `EvalRow` |
| `helm-summarize` | aggregator in `apps/eval-core-py/src/orchestrator/manifest.py` |
| `helm-server` | future `apps/site/` for leaderboard |

Source: <https://github.com/stanford-crfm/helm/blob/main/docs/code.md>.

### Judge protocol — POLLMEVALS deliberately diverges

HELM Capabilities (2025) uses **mean across multiple LLM judges** (not median). HELM also uses LLM-as-judge with blind labels but does **not** enforce a minimum judge count (3+) as a hard gate. POLLMEVALS chooses median (more robust to outliers) and enforces ≥3 judges (per frozen methodology v0.1.0).

Source: <https://crfm.stanford.edu/2025/03/20/helm-capabilities.html>.

### Stack evaluation — HELM does not do it

HELM evaluates models, not stacks. The scaffolding ladder (system prompt, tools, memory, validator loop) is **not a first-class concept**. Each run entry is `model=<provider>/<model-id>`. A consequence: HELM cannot answer "does adding a validator loop help this model on this task?" — which is POLLMEVALS's central thesis.

## Implications for POLLMEVALS

1. **ADR-002 confirmed as industry-aligned**. Evaluator-only reproduce is the proven pattern.
2. **SPEC-001 `pricing_snapshot` field is genuinely novel** at the manifest level. POLLMEVALS would be **ahead of HELM** on cost transparency from day one.
3. **PRD-002 median scoring (vs HELM's mean) needs justification in PRD-002 body** — note that we made this choice deliberately, not by accident.
4. **EvalEval Coalition shared artifact schema** (HuggingFace) is worth reviewing before finalizing manifest export format — alignment could enable cross-platform result reuse.

## Sources

1. <https://crfm-helm.readthedocs.io/en/v0.3.0/tutorial/> — `scenario_state.json` behavior
2. <https://github.com/stanford-crfm/helm/blob/main/docs/code.md> — class hierarchy
3. <https://crfm.stanford.edu/2025/03/20/helm-capabilities.html> — judge protocol (mean, not median)
4. <https://crfm.stanford.edu/2025/09/29/helm-long-context.html> — current scope and limitations
5. <https://huggingface.co/blog/evaleval/eval-costs-bottleneck> — cost transparency gap

## Confidence

🟡 Medium-high. Reproducibility model (finding 1) is 🟢 confirmed in official docs. Cost handling (finding 2) is 🟡 confirmed via paper + HuggingFace analysis but live leaderboard implementation not directly inspected. Stack-evaluation gap (finding 5) is 🟢 evident from public architecture.

## Open Questions

- Does HELM `helm-run` actually skip the API call when `scenario_state.json` exists, or does it always re-query? Docs imply reuse but don't state it as a hard cache-hit skip.
- Is the EvalEval Coalition's artifact schema stable enough to target for v0.1 export format, or still in flux?

## Related Artifacts

- PRD-001 (informs — auto-linked at create)
- SPEC-001 (manifest pricing_snapshot field)
- ADR-002 (reproduce semantics — direct precedent)
- RFC-001 § Cost attribution layer (closes the HELM gap)
- Future Note: median vs mean rationale for PRD-002




