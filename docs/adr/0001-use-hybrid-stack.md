# ADR — Hybrid TypeScript + Python stack

Date: 2026-05-23

## Status

Accepted.

## Context

POLLMEVALS needs both public product surfaces and Python-heavy eval infrastructure. The project owner also has MoleculerPy and MoleculerJS experience.

## Decision

Use TypeScript for public product/control-plane and Python for eval execution plane. MoleculerPy is allowed in eval services. MoleculerJS or Hono is used in API/product plane. Rust is deferred to hardened runtime components.

## Consequences

- Fast MVP iteration.
- Natural integration with Inspect AI and scoring code.
- Product surface remains stable if eval workers fail.
- Future Rust migration remains possible behind stable contracts.
