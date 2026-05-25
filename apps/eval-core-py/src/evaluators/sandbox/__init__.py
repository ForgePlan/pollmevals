"""Docker-backed sandbox helper for dynamic evaluators.

Per NOTE-007: evaluators that execute candidate code (vitest, pytest,
v8 coverage instrumentation) MUST go through the sandbox; static
evaluators (lint, complexity, secret_scan, type_safety) run on the host.

Frozen security policy lives in docs/02-methodology/security-sandbox.md
(v0.1.0) and docs/04-runbook/09-sandbox-security.md. This package
materialises that policy in code.
"""

from .runner import SandboxConfig, SandboxResult, SandboxRun, SandboxTimeoutError

__all__ = [
    "SandboxConfig",
    "SandboxResult",
    "SandboxRun",
    "SandboxTimeoutError",
]
