# ADR 0002 — Immutable completed runs

Date: 2026-05-23

## Status

Accepted.

## Decision

A completed run is immutable. Scores, raw outputs, model snapshots, task snapshots and methodology snapshots are not edited in place.

## Rationale

Evaluation credibility depends on reproducibility and auditability. If a bug is discovered, a replacement run is created and linked to the superseded run.

## Consequences

- Requires content-addressed artifacts.
- Requires run manifest.
- Requires versioned tasks and methodology.
