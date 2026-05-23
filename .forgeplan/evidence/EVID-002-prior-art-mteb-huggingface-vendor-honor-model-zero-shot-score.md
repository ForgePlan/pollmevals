---
depth: standard
id: EVID-002
kind: evidence
last_modified_at: 2026-05-23T19:28:53.982824+00:00
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

## Summary

External prior art review of MTEB (Massive Text Embedding Benchmark, Muennighoff et al. 2022, "Maintaining MTEB" 2025). MTEB is relevant for **methodology and leaderboard hygiene**, not its task content (embeddings vs POLLMEVALS chat/coding/docs). Validates POLLMEVALS's sandbox-based verification approach and surfaces a structural fairness lesson from the January 2026 Voyage incident.

## Key Findings

### Trust model — community honor with explicit caveats

MTEB operates on a community-honor model: submissions arrive as GitHub PRs, maintainers do methodology peer-review, and results are **accepted on submitter's word for proprietary models** with an explicit caveat that "the API may silently serve a different model version." Open-weight models get stronger guarantees because revision hashes are pinned.

### Contamination policy — zero-shot score as display, not gate

MTEB does **not** hard-exclude models trained on benchmark-adjacent data. Instead it computes a **zero-shot score** `z = 1 − n_train/n_total` reflecting what fraction of benchmark datasets the model was NOT trained on, displayed alongside the main score. Initially MTEB filtered to 100%-zero-shot only; after community pushback relaxed to "contextual transparency" — show the score, let users decide.

A July 2024 GitHub issue revealed that **24% of English datasets and 46% of French datasets contained train-test leaks within MTEB's own dataset splits** (not model training data). The team closed the issue without a documented remediation.

Source: <https://github.com/embeddings-benchmark/mteb/issues/1036>.

### Verification mechanism — open-weight vs proprietary asymmetry

- **Open-weight models**: CI runs Pydantic schema validation, cross-platform tests (Linux/Windows, Python 3.9-3.12), mock-task regression checks, and version-pinned reproducibility (MTEB version + dataset version + model revision hash all recorded).
- **Proprietary models**: no technical verification — it is a trust assumption documented explicitly in the "Maintaining MTEB" paper.

Source: <https://arxiv.org/html/2506.21182v1>.

### Voyage incident (Jan 2026) — structural fairness lesson

RTEB added a second trust layer — a sealed private test set evaluated exclusively by maintainers. This **immediately exposed a conflict-of-interest flaw**: Voyage co-developed the private datasets and had advance access. The private leaderboard column was removed.

**Rule**: task contributors cannot submit models for evaluation on tasks they contributed.

Sources: <https://github.com/embeddings-benchmark/mteb/issues/3934>, <https://thenewstack.io/exploring-rteb-a-new-benchmark-to-evaluate-embedding-models/>.

## Implications for POLLMEVALS

1. **POLLMEVALS deliberately diverges from honor model.** Eval execution happens inside our own sandbox; we capture `stdout/stderr/trace_json` as content-addressed artifacts. The eval engine is the authority, not vendor self-reports. This closes the gap MTEB acknowledges but has not solved.
2. **"In-distribution fraction" as a display field** (modeled on MTEB's zero-shot score) is worth a future ADR — show, don't block, when a model's training data overlaps benchmark-adjacent corpora. Captured in EPIC-001 ER-5 risk.
3. **Structural fairness rule** if/when POLLMEVALS accepts community task contributions: contributors cannot submit models on tasks they wrote. Worth capturing as a future ADR trigger.

## Sources

1. <https://arxiv.org/html/2506.21182v1> — "Maintaining MTEB" 2025 (primary source for contamination policy, CI verification, weaknesses)
2. <https://github.com/embeddings-benchmark/mteb/issues/1036> — 24% EN / 46% FR dataset leak rate (July 2024)
3. <https://huggingface.co/blog/rteb> — RTEB introduction (private-dataset hybrid strategy)
4. <https://github.com/embeddings-benchmark/mteb/issues/3934> — RTEB private-column removal (Jan 2026)
5. <https://thenewstack.io/exploring-rteb-a-new-benchmark-to-evaluate-embedding-models/> — RTEB analysis

## Confidence

🟢 High — the 2025 "Maintaining MTEB" paper is the authors' own self-assessment, GitHub issues are primary-sourced, and the RTEB controversy is documented from the MTEB team's own tracker.

## Open Questions

- Whether MTEB's zero-shot score is computed automatically from training data cards on HF Hub, or relies entirely on submitter self-declaration — the paper is ambiguous on mechanics.
- MTEB's plan for private-column restoration "from diverse organizations" has no stated timeline as of Jan 2026 issue close.

## Related Artifacts

- PRD-001 (informs — auto-linked)
- EPIC-001 ER-5 (in-distribution fraction risk)
- Future ADR: structural fairness for community task contributions (v1.0+)
- Future Note: "in-distribution fraction" display field design (PRD-004 leaderboard)



