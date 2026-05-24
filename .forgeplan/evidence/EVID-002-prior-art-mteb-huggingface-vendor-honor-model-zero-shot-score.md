---
depth: standard
id: EVID-002
kind: evidence
last_modified_at: 2026-05-24T07:38:53.796067+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-001
  relation: informs
- target: PRD-002
  relation: informs
status: active
title: 'prior art: MTEB (HuggingFace) — vendor honor model + zero-shot score'
---

# EVID-002: MTEB (HuggingFace) — vendor honor model + zero-shot score

## Structured Fields

verdict: supports
congruence_level: 2
evidence_type: audit

## ADI cycle (per NOTE-002 — retrofit)

### Abduction — research questions framed as hypotheses

- **H1**: Major leaderboards (MTEB-class) perform cryptographic / technical verification of vendor-submitted scores.
- **H2**: MTEB operates on a community honor model — submissions accepted on vendor's word for proprietary models, with documented caveat about silent model updates.
- **H3**: Adding a private test set (RTEB-style) closes the honor-model gap without introducing structural fairness issues.

### Induction — verification per hypothesis

| Prediction | Evidence | Outcome | H_i status |
|---|---|---|---|
| Y1 (technical verification) | "Maintaining MTEB" paper (Muennighoff et al. 2025, arxiv 2506.21182) §Trust Model: "for proprietary models: no technical verification — it is a trust assumption documented explicitly" | False | **H1 REFUTED** |
| Y2 (honor model + caveat) | Same paper: "submitter's word for proprietary models (API-served) with explicit caveat that 'the API may silently serve a different model version'"; open-weight pin revision hashes | Confirmed exactly as predicted | **H2 SUPPORTED** |
| Y3 (private set closes gap) | RTEB rollout Jan 2026 → Voyage incident: co-developed private datasets, had advance access; private leaderboard column REMOVED after fairness scrutiny | Closes gap but introduces NEW gap (conflict-of-interest) | **H3 REFUTED** |

## Trust Calculus per load-bearing claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| MTEB has no technical verification for proprietary model submissions | 8 | 8 | 9 | 25/27 | F: paper-authors' self-admission. G: scope precisely (proprietary only). R: peer-reviewed paper (arxiv preprint, but written by MTEB maintainers themselves). |
| 24% EN / 46% FR datasets had train-test leaks (within MTEB's own corpus) | 9 | 9 | 9 | 27/27 | F: explicit percentages. G: precise (which datasets, which language splits). R: MTEB GitHub issue #1036 — first-party authoritative source. |
| Zero-shot score `z = 1 − n_train/n_total` displayed (not gating) | 8 | 8 | 8 | 24/27 | F: formula stated. G: explicit display vs gate distinction. R: "Maintaining MTEB" paper. |
| RTEB Voyage incident: task contributor had advance access; column removed Jan 2026 | 9 | 8 | 9 | 26/27 | F: documented in MTEB issue #3934. G: precise (which org, which dates). R: MTEB team's own issue tracker — authoritative. |
| Rule: task contributors cannot submit models for own tasks | 7 | 7 | 8 | 22/27 | F: derived rule, not yet formal policy in MTEB. G: stated as principle. R: drawn from incident — strong inference but not yet doctrine. |

**Decision strength**: average sum = 24.8/27 (92%). One 27/27 claim (24/46% leak rate from MTEB's own GitHub issue). Weakest: contributor-cannot-submit rule (22/27) — would strengthen if MTEB formalizes it in their submission guide.

## Key Findings (preserved)

### Trust model — community honor with explicit caveats

MTEB operates on community honor: PR submissions + maintainer methodology review + accepted on submitter's word for proprietary models. Open-weight gets stronger guarantees (revision hashes pinned).

### Contamination policy — zero-shot score as display

`z = 1 − n_train/n_total` displayed alongside main score; initially filtered to 100% zero-shot only, after pushback relaxed to "contextual transparency". GitHub issue #1036 (July 2024): 24% EN / 46% FR datasets had train-test leaks within MTEB's own splits.

Source: <https://github.com/embeddings-benchmark/mteb/issues/1036>.

### Verification mechanism

Open-weight: CI runs Pydantic schema, Linux/Windows cross-platform tests, version-pinned reproducibility. Proprietary: no technical verification.

Source: <https://arxiv.org/html/2506.21182v1>.

### Voyage incident (Jan 2026) — structural fairness lesson

RTEB private test set → Voyage co-developed datasets, had advance access → private column removed. Rule: task contributors cannot submit models for evaluation on tasks they contributed.

Sources: <https://github.com/embeddings-benchmark/mteb/issues/3934>, <https://thenewstack.io/exploring-rteb-a-new-benchmark-to-evaluate-embedding-models/>.

## Conclusions

- **Surviving hypothesis**: H2 (honor model + explicit caveat) — POLLMEVALS deliberately diverges
- **Decision strength**: 92%
- **POLLMEVALS implication**: eval execution INSIDE own sandbox + content-addressed artifacts = eval engine, not vendor, is authority. Closes MTEB's known unsolved gap.
- **Follow-up evidence needed**: monitor MTEB private-column restoration plan (no timeline as of Jan 2026 issue close)

## Sources

1. <https://arxiv.org/html/2506.21182v1> — "Maintaining MTEB" 2025
2. <https://github.com/embeddings-benchmark/mteb/issues/1036> — leak rates
3. <https://huggingface.co/blog/rteb> — RTEB introduction
4. <https://github.com/embeddings-benchmark/mteb/issues/3934> — Voyage incident
5. <https://thenewstack.io/exploring-rteb-a-new-benchmark-to-evaluate-embedding-models/>

## Related Artifacts

- PRD-001 (informs — auto-linked)
- EPIC-001 ER-5 (in-distribution fraction risk)
- Future ADR: structural fairness for community task contributions (v1.0+)
- Future Note: "in-distribution fraction" display field design (PRD-004 leaderboard)
- NOTE-002 (Evidence Quality Standard — retrofit)

