---
depth: standard
id: EVID-001
kind: evidence
last_modified_at: 2026-05-24T07:38:24.747577+00:00
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

## ADI cycle (per NOTE-002 — retrofit, lighter form for external research)

### Abduction — research questions framed as hypotheses

- **H1**: HELM's "reproducibility" claim means full-pipeline determinism — re-running yields byte-equal evaluator output AND byte-equal model output.
- **H2**: HELM's reproducibility is evaluator-only — model outputs cached in `scenario_state.json`; re-runs replay evaluator against cache, never re-call model.
- **H3**: HELM provides per-eval cost transparency in current leaderboard (a feature POLLMEVALS doesn't need to build).

### Induction — verification per hypothesis

| Prediction | Evidence | Outcome | H_i status |
|---|---|---|---|
| Y1 (full-pipeline determinism) | crfm-helm.readthedocs.io tutorial confirms `scenario_state.json` contains "every request to and response from the model"; re-run uses cache | False — model NOT re-called | **H1 REFUTED** |
| Y2 (evaluator-only cache replay) | Same docs: "On a rerun, HELM re-executes the *evaluator* against this cached artifact rather than re-calling the model" + `stanford-crfm/helm/blob/main/docs/code.md` class hierarchy confirms RequestState serialization | Pattern exactly matches POLLMEVALS ADR-002 design | **H2 SUPPORTED** |
| Y3 (per-eval cost in HELM live) | EvalEval Coalition blog (HuggingFace 2025) explicitly calls cost transparency "industry-wide gap"; HELM 2022 paper had $85-$10,926 per-model spread but as POST-HOC manual accounting; live leaderboard `stats.json` has no standardized cost field | HELM does NOT provide; POLLMEVALS must build | **H3 REFUTED** |

## Trust Calculus per load-bearing claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| HELM uses `scenario_state.json` for evaluator-only reproduce (validates ADR-002) | 8 | 8 | 9 | 25/27 | F: explicit doc quotation. G: precise file name + behavior. R: crfm-helm.readthedocs.io (official Stanford docs). |
| HELM does NOT snapshot per-eval pricing (POLLMEVALS gap to close) | 8 | 7 | 8 | 23/27 | F: stated as absence. G: HELM 2022 paper has $85-$10,926 numbers but POST-HOC. R: EvalEval HuggingFace blog (secondary source) + paper (primary). |
| 33× cost spread for identical tasks (industry-wide gap) | 8 | 9 | 7 | 24/27 | F: explicit number. G: 33× quantified. R: HuggingFace EvalEval Coalition blog (analysis), not peer-reviewed; would benefit from cross-source confirmation. |
| HELM Capabilities 2025 uses mean (not median) across judges | 8 | 8 | 8 | 24/27 | F: blog post explicitly stated. G: precise (mean vs median). R: crfm.stanford.edu blog (first-party but blog format, not peer-reviewed). |
| HELM does NOT evaluate stacks (model-only) | 8 | 8 | 9 | 25/27 | F: explicit from class hierarchy. G: confirmed in `docs/code.md`. R: stanford-crfm/helm source repo (authoritative). |
| EvalEval Coalition shared artifact schema exists on HF | 7 | 6 | 7 | 20/27 | F: mentioned as artifact-sharing schema. G: not detailed (would need schema doc fetch). R: HF blog reference, but schema URL/repo not yet pulled directly. |

**Decision strength**: average sum = 23.5/27 (87%). All claims ≥ 12. Weakest: EvalEval schema specifics (20/27) — improves if we directly fetch the schema repo and verify shape before designing POLLMEVALS manifest export format (deferred to Phase 2B).

## Key Findings (preserved from original retrofit body)

### Reproducibility model — direct precedent for ADR-002

HELM writes `scenario_state.json` containing every request to and response from the model. On a rerun, HELM re-executes the evaluator against this cached artifact rather than re-calling the model. Equivalent to POLLMEVALS's ADR-002 decision.

Source: <https://crfm-helm.readthedocs.io/en/v0.3.0/tutorial/>, confirmed via <https://github.com/stanford-crfm/helm/blob/main/docs/code.md>.

### Cost transparency — industry gap POLLMEVALS closes

HELM does not snapshot per-eval pricing at run time. The 2022 paper showed $85-$10,926 per-model spread (~$100K total across 30 models × 42 scenarios), manual post-hoc accounting. EvalEval Coalition (HF 2025) calls out 33× cost spreads as industry-wide gap.

Source: <https://huggingface.co/blog/evaleval/eval-costs-bottleneck>.

### Architecture mapping (informs SPEC-001)

`helm-run` → `helm-summarize` → `helm-server`. RunSpec → Scenario → adapter → executor → metric. RequestStates serialized.

| HELM concept | POLLMEVALS analogue |
|---|---|
| `scenario_state.json` | `artifact_refs.raw_output` (content-addressed) |
| `RunSpec` | `EvalRow` |
| `helm-summarize` | `apps/eval-core-py/src/orchestrator/manifest.py` aggregator |
| `helm-server` | future `apps/site/` leaderboard |

### Judge protocol — POLLMEVALS deliberately diverges

HELM Capabilities 2025: mean across judges, no minimum panel count gate. POLLMEVALS: median + ≥3 judges.

Source: <https://crfm.stanford.edu/2025/03/20/helm-capabilities.html>.

### Stack evaluation — HELM does NOT

Each run entry is `model=<provider>/<model-id>`. No L0-L8 layering. Cannot answer "does adding a validator loop help this model on this task?"

## Conclusions

- **Surviving hypothesis**: H2 — evaluator-only reproduce model; HELM's pattern directly validates POLLMEVALS ADR-002
- **Decision strength**: 87% (24/27 average)
- **Follow-up evidence needed**: directly fetch EvalEval Coalition's artifact-sharing schema repo (current claim 20/27) before finalizing POLLMEVALS manifest export format

## Sources

1. <https://crfm-helm.readthedocs.io/en/v0.3.0/tutorial/>
2. <https://github.com/stanford-crfm/helm/blob/main/docs/code.md>
3. <https://crfm.stanford.edu/2025/03/20/helm-capabilities.html>
4. <https://crfm.stanford.edu/2025/09/29/helm-long-context.html>
5. <https://huggingface.co/blog/evaleval/eval-costs-bottleneck>

## Related Artifacts

- PRD-001 (informs — auto-linked)
- SPEC-001 (manifest pricing_snapshot field — closes HELM gap)
- ADR-002 (reproduce semantics — direct precedent)
- RFC-001 § Cost attribution layer
- EVID-014 (Wave 4 cost implementation — operationalizes the closure of HELM gap)
- Future Note: median vs mean rationale for PRD-002
- NOTE-002 (Evidence Quality Standard — retrofit)



