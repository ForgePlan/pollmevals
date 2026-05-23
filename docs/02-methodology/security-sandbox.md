# Security sandbox policy v0.1.0

## MVP sandbox

- Docker container per evaluator.
- Network disabled.
- Read-only base filesystem.
- Writable tmpfs with size limit.
- CPU, memory, PID and file size limits.
- All Linux capabilities dropped.
- Hard timeout.

## v1 hardening

- gVisor or Kata Containers for community tasks.
- Firecracker microVM for enterprise or untrusted evaluator code.
- Per-run ephemeral workspace.
- Artifact export only; no persistent writable volume.
