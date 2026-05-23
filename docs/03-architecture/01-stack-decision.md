# 03 — Stack decision

## Decision

Use a hybrid stack:

- TypeScript for public product plane.
- Python + MoleculerPy-ready architecture for eval execution plane.
- Rust later for hardened execution components.

## Accepted stack

| Layer | Technology |
|---|---|
| Site | Next.js 15, Tailwind, shadcn/ui-compatible component structure |
| API | Hono, TypeScript, Zod, OpenAPI-ready routes |
| Eval core | Python 3.12, Pydantic, PyYAML |
| Service bus | NATS |
| Cache / queue | Redis |
| DB | Postgres |
| Artifacts | R2 in production, local filesystem in development |
| LLM gateway | LiteLLM |
| Eval framework | Inspect AI-compatible task model |
| Sandbox | Docker first; gVisor/Firecracker later |
| Future systems layer | Rust |

## Why not Rust first

Rust is excellent for sandbox runners, hashing, trace normalization and high-throughput execution. It is not the fastest way to iterate on methodology, Inspect AI wrappers, scoring policy, task specs and judge calibration.

Use Rust after the contracts stabilize.

## Migration path to Rust

| Component | First implementation | Rust rewrite trigger |
|---|---|---|
| Sandbox runner | Python invoking Docker | untrusted community tasks |
| Artifact hasher | Python hashlib | artifact volume becomes high |
| Trace normalizer | Python | tool trace throughput becomes bottleneck |
| Worker supervisor | Python process model | long-running eval workers become unstable |
