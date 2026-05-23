---
name: Feature
about: New capability traced to a Functional Requirement in a PRD
title: "[FR-XXX] <one-line capability statement>"
labels: type/feat
assignees: ''
---

## Trace

- **PRD**: `prd-<slug>` (e.g. `prd-v0-1-smoke-evaluation-run`)
- **FR**: FR-XXX
- **Phase**: phase/1-foundation | phase/2-smoke | phase/3-judges | phase/4-leaderboard | phase/5-release

## Capability

Format: `<actor> can <action> <object> [under <condition>]`.

Example: *Maintainer can validate task specs against JSON Schema via `make validate-tasks`*.

## Acceptance Criteria

- [ ] Given … When … Then …
- [ ] Given … When … Then …

## Implementation locus

- File / module: `apps/eval-core-py/src/...`
- Touches: …

## Dependencies

- Blocked by: #NNN (other issues), `EVID-XXX` (forgeplan evidence)
- Blocks: #NNN

## Evidence requirement

After implementation, link a forgeplan `evidence` artifact with `verdict / congruence_level / evidence_type` to the parent PRD so R_eff can rise above 0.

## Notes

(Free-form context, prior art links, screenshots.)
