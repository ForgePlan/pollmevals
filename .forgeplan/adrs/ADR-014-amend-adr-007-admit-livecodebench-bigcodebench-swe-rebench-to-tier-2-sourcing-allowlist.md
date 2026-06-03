---
depth: standard
id: ADR-014
kind: adr
last_modified_at: 2026-06-02T23:45:47.872374+00:00
last_modified_by: claude-code/2.1.156
links:
- target: ADR-007
  relation: refines
- target: PRD-006
  relation: informs
status: active
title: Amend ADR-007 — admit LiveCodeBench, BigCodeBench, SWE-rebench to Tier-2 sourcing allowlist
---

## Context

ADR-007 set a two-tier sourcing policy: Tier-1 own-authored, Tier-2 sourced-with-attribution under an **MIT / Apache-2.0 / BSD** license, gated by **G4** (contamination check) and per-pack `LICENSE.md`. Its eligible-source allowlist names SWE-Lancer, DevBench, **BigCodeBench**, LiveBench (ADR-007 lines 79-88), and states: *"Adding a source requires updating this ADR."*

In June 2026 we imported 30 third-party packs to grow the catalogue (PR #45, catalogue-only): 10× BigCodeBench (`bcb-*`), 10× LiveCodeBench AtCoder-2025 (`lcb-atcoder-*`), 10× SWE-rebench-V2 (`swe-*`). The import exposed three gaps in ADR-007:

1. **LiveCodeBench is not on the allowlist** — ADR-007 lists *LiveBench* (a different benchmark). LiveCodeBench is MIT and fits the Tier-2 license rule, but is unlisted.
2. **SWE-rebench-V2 is unlisted, and its dataset wrapper is CC-BY-4.0** — outside the MIT/Apache/BSD enumeration. The underlying repo code carries its own per-instance license (8/10 MIT/Apache/BSD; 1× CC0-1.0 `rust-bitcoin`; 1× custom `aiohttp`).
3. **None has passed G4 yet** — the 30 packs are flagged `sourcing: hybrid`, catalogue-only, not scored (see `evals/task-packs/IMPORTED-CATALOGUE.md`).

The maintainer decided to **admit all three sources**. This ADR records that decision and amends ADR-007's allowlist + license rule accordingly. ADR-007 stays active and is `refines`-linked, not superseded.

## Decision

Amend ADR-007 Tier-2 sourcing as follows.

**Selected**: Admit all three import sources, with a license rule keyed on the **per-instance code license** rather than the dataset-wrapper license.

**Why Selected**: It maximises catalogue throughput (the explicit v0.1 priority in ADR-007's Context) while keeping the anti-contamination thesis intact — because the **G4 contamination gate stays BLOCKING for every imported sample regardless of source**, and the redistribution obligation is governed by the code's own license, which is what we actually re-host in `gold/`.

Concretely:

- **Allowlist += LiveCodeBench** (MIT) and **BigCodeBench** (Apache-2.0; clarify it is admitted via the HF `datasets-server` route used by `ingest_bigcodebench.py`).
- **Allowlist += SWE-rebench-V2** with a **per-instance license rule**: the authoritative license for a `swe-*` pack is the **upstream repository's code license** recorded in its `task.yaml` provenance header. The **CC-BY-4.0 dataset wrapper is satisfied by attribution** (we cite `nebius/SWE-rebench-V2` + URL in every pack), which CC-BY requires and we provide.
- **Quarantine** the two non-permissive SWE instances: `swe-rust-bitcoin-rust-bitcoin-2255` (**CC0-1.0** — public-domain, redistributable but outside the MIT/Apache/BSD set) and `swe-aio-libs-aiohttp-9047` (**custom** — needs manual GitHub license verification). Both stay catalogue-only until the maintainer signs off the specific license; neither blocks the other 28.
- **G4 stays BLOCKING**: no imported sample enters a scored Run until WebSearch of its first 80 chars returns 0 verbatim matches outside the original source (ADR-007 invariant #4). LICENSE.md per pack is required at promotion time (deferred for LCB/SWE while catalogue-only).

## Alternatives Considered

| Option | Verdict | Why |
|--------|---------|-----|
| A — admit all three (per-instance license rule + quarantine CC0/custom) | **Chosen** | Maximum catalogue, principled license stance, thesis preserved by keeping G4 blocking |
| B — admit LiveCodeBench + BigCodeBench only; hold all SWE-rebench | Rejected | Drops the highest-signal source (real repo bugs) over a wrapper-license technicality the per-instance rule resolves |
| C — defer the whole amendment to v0.2 | Rejected | Leaves 30 packs permanently un-promotable; the import already happened and is honestly flagged |
| D — drop SWE-rebench entirely | Rejected | CC-BY is an attribution license, not a contamination signal; G4 (not license) is our anti-contamination control |

## Consequences

### Positive
- 28 of 30 imported packs become **promotable** (pending G4 + runner support) — large catalogue growth for v0.2.
- A clear, reusable rule for dataset-of-code sources: judge the **code** license, satisfy the **wrapper** by attribution.
- Anti-contamination posture unchanged — G4 remains the load-bearing gate.

### Negative (trade-offs)
- Per-instance license bookkeeping for SWE packs (already recorded in each `task.yaml` header; LICENSE.md generation deferred to promotion).
- Two packs (CC0, custom) sit in quarantine — a small manual review backlog.

### Risks
- A future SWE-rebench-V2 instance could carry a copyleft/NC code license; the per-instance rule must reject it (not auto-admit by source).
- G4 false-negatives on widely-discussed benchmark problems (BigCodeBench is a known public benchmark) — mitigated by G4 being mandatory and the post-2024-cutoff nature of the LCB/SWE imports.

## Invariants

- **The per-instance code license is authoritative for `swe-*` packs.** A pack whose upstream code license is not MIT/Apache/BSD/CC0-with-signoff stays catalogue-only.
- **G4 contamination gate is BLOCKING for every imported sample**, regardless of source or tier (re-affirms ADR-007 invariant #4).
- **No license downgrade** — imported `gold/` content keeps its upstream SPDX (ADR-007 invariant #3); fixtures stay verbatim, excluded from formatters/linters.
- **Quarantined packs (CC0/custom) never enter a scored Run** without explicit maintainer license sign-off.
- **The ADR-007 deny-list still holds** — HumanEval, MBPP, classic LeetCode remain forbidden.

## Evidence Requirements

- A G4 contamination report (EVID) per imported pack before it joins a scored Run — 0 verbatim matches outside the source.
- A per-pack `LICENSE.md` generated at promotion time (BCB already has one).
- Maintainer sign-off note for the 2 quarantined packs (or their removal).

## Valid Until

**Дата**: `valid_until` — review at v0.2 catalogue freeze, or earlier on a refresh trigger.

**Refresh Triggers**:
- A new import source is proposed (requires another ADR amendment).
- An admitted source changes its dataset or code license.
- G4 starts producing systematic false-negatives on an admitted source → tighten the gate (ADR-007 rollback row).

## Admissibility

- NOT: admitting a SWE-rebench instance whose upstream code license is copyleft or non-commercial.
- NOT: scoring any imported pack before its G4 report exists.
- NOT: editing imported `gold/` fixtures to satisfy our linters.

## Related Artifacts

| Artifact | Type | Relation |
|----------|------|----------|
| ADR-007 | ADR | refines |
| PRD-006 | PRD | informs |
| IMPORTED-CATALOGUE.md | doc | implements |




