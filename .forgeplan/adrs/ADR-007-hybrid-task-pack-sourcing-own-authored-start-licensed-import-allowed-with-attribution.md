---
depth: standard
id: ADR-007
kind: adr
last_modified_at: 2026-05-26T12:08:58.007090+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-006
  relation: informs
status: active
title: Hybrid task-pack sourcing — own-authored start + licensed import allowed with attribution
---

# ADR-007: Hybrid task-pack sourcing — own-authored start + licensed import allowed with attribution

> **STATUS: draft** — authored 2026-05-26 as Wave 0 process artifact. Resolves PRD-006 §"Open question — provenance policy" and RFC-003 §G1 provenance gate.

## Context

POLLMEVALS scores LLM stacks on real tasks. The task catalog (PRD-006: 20 tasks v0.1) is the **scoring ground truth**. Each task pack contains a gold solution + 50 calibration samples (5 quality levels × 10 each). Per-task that's ~51 hand-authored or curated artefacts; the v0.1 launch catalog is ~1000 artefacts total.

Two competing priorities:

- **Anti-contamination**: candidates and judges are LLMs whose pretrain includes GitHub / Stack Overflow / public benchmarks. If a task or sample appears verbatim in their training data, the score measures *recall* not *capability*. dd.md positions anti-contamination as a load-bearing thesis (LiveBench cited as gold standard precisely because it is contamination-free).
- **Authoring throughput**: one maintainer × 1000 artefacts × ~5 minutes each = 80+ hours. Sourcing from established benchmarks (SWE-Lancer, DevBench, BigCodeBench) could cut this 5-10× — at the cost of contamination risk.

A binary policy (strict own-authored / sourcing allowed) loses either way. We need a structured hybrid.

## Decision

**Adopt a hybrid sourcing policy** with two tiers:

- **Tier 1 — Own-authored (default)**: gold solutions and calibration samples are written by the maintainer or by Task-Pack Author Agents under the RFC-003 protocol. Provenance header: `// source: own-authored YYYY-MM-DD by <author> (license: MIT)`.
- **Tier 2 — Sourced with attribution (allowed exception)**: samples may be imported from another open benchmark IFF:
  1. The source benchmark license is **MIT, Apache-2.0, or BSD** (no copyleft, no NC).
  2. **Verbatim attribution** in file header: `// source: <benchmark> task #<id> (license: <SPDX>, retrieved <ISO date>, original URL: <…>)`.
  3. The sample passes the **G4 contamination gate** (RFC-003): WebSearch first 80 chars must return 0 verbatim matches **outside the original source**. If verbatim found elsewhere, sample is contaminated — reject.
  4. The pack is **flagged** in `task.yaml`: `sourcing: hybrid` (own-authored = `sourcing: own`).
  5. Maintainer reviews EVERY sourced sample before commit.

**Tier 2 is opt-in per sample, not per pack** — a single pack can mix own-authored (most samples) with sourced (1-2 hard cases where good signal is rare).

## Considered Options

| Option | Verdict | Why |
|---|---|---|
| Strict own-authored (Tier 1 only) | Rejected | Throughput infeasible for v0.1 timeline; single-author bias is its own contamination risk |
| Open sourcing (any license, no attribution gate) | Rejected | Maximum contamination risk; defeats dd.md anti-contamination thesis |
| **Hybrid with explicit Tier 1/2 + G4 gate** | **CHOSEN** | Throughput compromise without abandoning anti-contamination |
| Per-category policy (own for FE, sourced for BE) | Rejected | Per-sample is finer-grained without added overhead |

## Consequences

### Positive

- Maintainer can borrow established benchmarks (SWE-Lancer, DevBench, BigCodeBench) for hard-to-author samples (e.g., realistic legacy code in `tst_01_legacy_function_tests`).
- Attribution headers preserve license obligations and auditable provenance.
- G4 contamination gate (RFC-003) catches the failure mode regardless of tier.
- Pack-level `sourcing:` field lets downstream consumers filter (e.g., publication-grade leaderboards may want `sourcing: own` only for v1.0).

### Negative

- Reviewer overhead: every Tier 2 sample requires WebSearch + license check + attribution-format verification. Estimate: ~3 minutes per sample vs ~1 minute for Tier 1 G1 check.
- Mixed-tier packs are heterogeneous — calibration distributions may behave differently in own vs sourced samples. Mitigate by `sourcing: hybrid` flag in task.yaml so analysis can stratify.
- Maintainer must keep license attribution table (`LICENSE.md` per pack containing all Tier 2 sources).

### Neutral

- No effect on judge methodology (PRD-002), evaluator implementation (Phase 2D), or sandbox policy (NOTE-007).
- No retroactive change: existing 3 scaffolds (be_01, fe_01, doc_01) start as Tier 1 own-authored.

## Mandatory checks per sample

| Tier | G1 header form | G4 WebSearch outcome | License check | Attribution required |
|---|---|---|---|---|
| Tier 1 own-authored | `// source: own-authored YYYY-MM-DD by <author> (license: MIT)` | 0 verbatim hits anywhere | n/a (project license = MIT) | n/a |
| Tier 2 sourced | `// source: <benchmark> task #<id> (license: <SPDX>, retrieved <ISO>, url: <…>)` | 0 verbatim hits OUTSIDE original source | MIT / Apache-2.0 / BSD only | YES — in file header + LICENSE.md |

## Eligible Tier 2 sources (allowlist for v0.1)

| Source | License | When eligible |
|---|---|---|
| SWE-Lancer | MIT | real-bug task scenarios |
| DevBench | Apache-2.0 | DB / Ops tasks |
| BigCodeBench | Apache-2.0 | function-level coding tasks |
| LiveBench | MIT | math / reasoning (out of v0.1 scope but reserved) |

Adding a source requires updating this ADR (supersession or amendment).

## Invariants

What MUST NEVER be violated:

1. **No Tier 2 import without G1 attribution header + LICENSE.md entry.** A sample on disk without provenance is automatic reject — RFC-003 G1 gate enforces.
2. **No Tier 2 source on the deny-list**, ever. HumanEval, MBPP, classic LeetCode are forbidden because they are known-saturated; using them poisons the entire scoring panel.
3. **No license downgrade.** A Tier 2 sample imported under Apache-2.0 stays under Apache-2.0 in our repo — the file header preserves SPDX. Maintainer never relicences sourced content.
4. **G4 BLOCKING applies regardless of tier.** Verbatim matches outside the original source = contamination; reject + rewrite even if attribution is correct.
5. **`sourcing:` field in task.yaml is non-mutable after lifecycle promotion to `calibration` state.** Changing the sourcing tier of a published pack requires a new task version (per task-lifecycle.md).

## Rollback Plan

| Failure mode | Rollback action |
|---|---|
| Tier 2 source becomes contaminated post-publication (e.g., source benchmark leaks into a popular blog post) | Mark affected packs `compromised` per task-lifecycle.md; supersede with Tier 1 rewrites; update this ADR's allowlist to remove the source |
| Auditor finds attribution missing on a Tier 2 sample | Hot-fix commit adding header + LICENSE.md entry; emit EVID documenting the slip; no rollback of pack lifecycle if attribution is the only gap |
| G4 false-positive rate makes Tier 2 throughput unworkable | Tighten G4 to first 120 chars (currently 80); re-author affected samples; this ADR amendment, not supersession |
| Hybrid `sourcing:` distribution shifts judge calibration outcomes outside the SC-3 MAD threshold | Stratify analysis by `sourcing:`; if Tier 2 samples consistently produce drift, ADR-007 succeeded by stricter Tier 1-only policy |
| Maintainer abandons sourcing entirely (capacity allows) | Future ADR supersedes this one; existing Tier 2 packs grandfather under the original ADR; no in-place rewrite |

## Affected Files

- `evals/task-packs/<slug>/task.yaml` — gains `sourcing: own | hybrid` field.
- `evals/task-packs/<slug>/LICENSE.md` — required for any pack with Tier 2 samples; lists each sourced sample's source + license + URL + retrieval date.
- `evals/task-packs/<slug>/gold/*` and `calibration/<level>/sample-*.{ts,md,sql}` — every file header conforms to the G1 format defined above (Tier 1 or Tier 2 variant).
- `docs/02-methodology/task-lifecycle.md` — referenced by promotion gate; no change in this ADR.
- `infra/scripts/validate-task-specs.py` — must accept new `sourcing:` field (one-line schema update, deferred to first Tier 2 pack landing).
- `.forgeplan/state/be_01.yaml`, `.forgeplan/state/fe_01.yaml`, `.forgeplan/state/doc_01.yaml` — eventually reflect sourcing tier per pack (informational).

## Out of scope

- Human-authored vs LLM-authored within Tier 1: both allowed if maintainer reviews. v0.2 may add a sub-tier "human-only" for the publication-grade leaderboard.
- Cross-language sourcing: a TS task pack may borrow a Python algorithm idea if the implementation is rewritten in TS (Tier 1 with idea attribution).
- Adversarial sourcing (e.g., HumanEval imports) explicitly forbidden — known-saturated benchmarks pollute the panel.

## Related Artifacts

- PRD-006 — parent (Tasks catalog expansion; this ADR resolves its open Q on sourcing)
- RFC-003 — operationalises G1 + G4 gates that enforce this policy
- NOTE-002 — Evidence Quality Standard governs EVID artifacts per pack
- docs/02-methodology/task-lifecycle.md — promotion gates (this ADR is upstream)
- dd.md — anti-contamination thesis source


