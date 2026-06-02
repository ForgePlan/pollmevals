---
depth: standard
id: EVID-021
kind: evidence
last_modified_at: 2026-05-24T10:30:01.511573+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-001
  relation: informs
- target: NOTE-003
  relation: informs
status: active
title: Phase 2C OTel spans + InspectEvalCaller real impl — code review of commit 0e494f6
---

# EVID-021: Phase 2C OTel spans + InspectEvalCaller real impl — code review of commit 0e494f6

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: audit

## Verdict

CONCERNS

One-line justification: The implementation is functionally sound and all 356 tests pass, but two findings require fixes before Phase 2D — a bug that misclassifies httpx timeouts as NETWORK instead of TIMEOUT, and four mypy --strict errors with incorrect `# type: ignore` annotations in the token-extraction path.

## Scope

- Parent: PRD-001
- Diff range: `433f1f7..0e494f6`
- Reviewer agent: `claude-code/sonnet-4-6/code-reviewer-task-phase2c`
- Files reviewed: 8 files, ~1124 lines added/changed
- Files: `apps/eval-core-py/src/orchestrator/telemetry.py`, `apps/eval-core-py/src/orchestrator/eval_caller.py`, `apps/eval-core-py/src/orchestrator/grid_runner.py`, `apps/eval-core-py/src/orchestrator/journal.py`, `apps/eval-core-py/src/orchestrator/cost.py`, `apps/eval-core-py/tests/test_telemetry.py`, `apps/eval-core-py/tests/test_eval_caller.py`, `apps/eval-core-py/pyproject.toml`

## Tools run

| Tool | Exit | Notes |
|---|---|---|
| pytest (356 tests) | 0 | 356 passed, 1 skipped — clean |
| mypy --strict (5 files) | 1 | 4 errors in `eval_caller.py:355-356` — wrong `type: ignore` tag + real attr-defined errors |
| ruff check | 0 | clean |
| ruff format | n/a | not run (format check only on changed files) |

## Findings

| # | Severity | Category | Location | Description | Recommended fix |
|---|---|---|---|---|---|
| 1 | HIGH | Bug | `apps/eval-core-py/src/orchestrator/eval_caller.py:274` | `except TimeoutError` does NOT catch `httpx.TimeoutException` subclasses (`httpx.ReadTimeout`, `httpx.ConnectTimeout`, `httpx.WriteTimeout`). `httpx.TimeoutException` inherits from `httpx.TransportError -> httpx.HTTPError`, not from Python's built-in `TimeoutError`. At runtime, any httpx-generated timeout falls through to `except httpx.HTTPError` and gets classified as `ErrorClass.NETWORK` instead of `ErrorClass.TIMEOUT`. FR-009 compliance is preserved (no exception escapes) but the `error_class` is wrong, breaking downstream filtering by error class. | Change `except TimeoutError` to `except (TimeoutError, httpx.TimeoutException)` — add the httpx exception class explicitly |
| 2 | HIGH | Bug | `apps/eval-core-py/src/orchestrator/eval_caller.py:355-356` | `usage.get("prompt_tokens")` and `usage.get("completion_tokens")` called on `usage: dict[str, object] \| {}` — but `{}` is typed as `object` (result of `data.get("usage") or {}`), so `.get()` is not available on the inferred `object` type. mypy --strict reports `"object" has no attribute "get" [attr-defined]` on both lines. The existing `# type: ignore[arg-type]` suppresses the wrong error code; the actual error is `[attr-defined]`. The code is functionally correct at runtime (both branches return a dict) but the type annotation is imprecise and the wrong ignore tag means the real error is still emitted by mypy. | Change `usage = data.get("usage") or {}` to `usage: dict[str, object] = {}; _u = data.get("usage"); usage = _u if isinstance(_u, dict) else {}` — this narrows the type correctly and eliminates the need for `type: ignore` |
| 3 | MEDIUM | Architecture | `apps/eval-core-py/src/orchestrator/journal.py:159-177` | The `journal.append` span does not call `span.record_exception(exc)` nor `span.set_status(StatusCode.ERROR, ...)` on the `JournalCorruptionError` re-raise paths (both the serialization catch and the OSError catch). OTel convention requires error recording on spans before the exception propagates, otherwise Tempo shows the span as OK even when the journal corrupted. `grid_runner.py` does this correctly for `eval.run_single` spans. | Add `from opentelemetry.trace import StatusCode` import to `journal.py`; in both `except` blocks inside the `with tracer.start_as_current_span(...)` context, add `span.record_exception(exc); span.set_status(StatusCode.ERROR, str(exc))` before the `raise` |
| 4 | MEDIUM | Architecture | `apps/eval-core-py/src/orchestrator/cost.py:333-342` | The `cost.reconcile_litellm` span has no error recording. The method returns a value (never raises), so no exception path exists — but this is only because the warning writes to stderr silently. If a future change adds an exception path, the span will silently show OK. More concretely: span attributes are set before `start_as_current_span`, so if the reconcile method were async or the provider changed the span attributes are computed from pre-span values. This is a minor OTel style issue — `span_attrs` are passed as constructor arguments which is correct practice; no functional bug now. | No immediate action required; note that if an exception path is added to `reconcile_with_litellm`, error recording must be added to the span context. Low priority. |
| 5 | MEDIUM | Architecture | `apps/eval-core-py/src/orchestrator/telemetry.py:39` | `_PROVIDER_INSTALLED` is a module-level global `bool`. In test suites that import and mutate this flag directly (see `test_telemetry.py:_reset_telemetry_module`), the flag is reset but `trace.set_tracer_provider(provider)` has already been called in prior tests, so `trace.get_tracer_provider()` may return a stale provider. The test workaround uses a standalone in-process `TracerProvider` (not the global) for the span-creation smoke test, which is correct. However, in production code where `init_tracing` is called before a test that also calls `init_tracing`, the second call will get a tracer backed by the already-registered provider even if a different endpoint was configured for the second call. This is documented behavior but the `_PROVIDER_INSTALLED` guard does not check if the existing provider matches the requested endpoint. | This is acceptable for Phase 2C (single-process deployment); document in the docstring that the endpoint argument on the second call is silently ignored. Add a `logger.warning` when endpoint mismatch is detected on a subsequent call. |
| 6 | MEDIUM | Bug | `apps/eval-core-py/src/orchestrator/eval_caller.py:262-268` | HTTP 4xx errors (other than 429) map to `ErrorClass.SANDBOX_FAILURE`. Per FR-009 and the domain model, `SANDBOX_FAILURE` should represent provider/infra failures (5xx-class), not client errors like 400 Bad Request or 401 Unauthorized. A 401 from the LiteLLM proxy (wrong API key) should be `ErrorClass.AUTH_FAILURE` or at minimum be distinguishable from a proxy crash. The current code merges `400-499` (excluding 429) into `SANDBOX_FAILURE`, making it impossible to diagnose auth vs. bad-request vs. server-crash from the `error_class` field alone. | Check `ErrorClass` enum for an `AUTH_FAILURE` value; if present, map `401/403` to it; map `400/422` to a new `REQUEST_ERROR` class. If neither exists, at minimum record the HTTP status code in `error_detail` (which the current code already does via the f-string) and add a comment explaining why `SANDBOX_FAILURE` is used as a catch-all pending enum expansion. |
| 7 | LOW | Test gap | `apps/eval-core-py/tests/test_eval_caller.py` | No test for httpx `TimeoutException` (e.g. `httpx.ReadTimeout`) specifically — the existing `test_timeout_returns_timeout_failure` uses `TimeoutError()` (built-in), not `httpx.ReadTimeout`. Because of Finding #1, an httpx timeout would actually produce `NETWORK` at runtime, but the test using built-in `TimeoutError` passes because that is caught by `except TimeoutError`. The test therefore does NOT prove that httpx network timeouts are classified as `TIMEOUT`. | Add `test_httpx_read_timeout_returns_timeout_failure` that raises `httpx.ReadTimeout(request=None)` as the side_effect and asserts `error_class == ErrorClass.TIMEOUT` |
| 8 | LOW | Docs | `apps/eval-core-py/src/orchestrator/eval_caller.py:156` | `TODO(Phase 2D): replace direct HTTP with inspect_ai.eval() wiring` — no owner or date on the TODO. Project convention is `TODO(Phase 2D)` form which is acceptable per the codebase, but the connection to an actual forgeplan artifact is missing. | Add `# see PRD-001 FR-003` after the TODO to link it to the tracked requirement |
| 9 | LOW | Style | `apps/eval-core-py/src/orchestrator/eval_caller.py:355-356` | `# type: ignore[arg-type]` suppresses the wrong error category (the actual mypy error is `[attr-defined]`, not `[arg-type]`). This causes mypy to emit the `[unused-ignore]` warning on top of the real error, making the output noisier than necessary. | Fix per Finding #2 (proper type narrowing eliminates both ignore comments) |

## Positive observations

- Retry logic counting is correct: `while attempt <= _RETRY_MAX` with `attempt` starting at 0 produces exactly 4 HTTP calls (1 initial + 3 retries) and 3 sleep calls at 1.0 s, 2.0 s, 4.0 s — exactly matching the test assertions. No off-by-one.
- `grid_runner.py` OTel instrumentation is well-done: `span.record_exception(exc)` + `span.set_status(StatusCode.ERROR)` are present on the caller exception path (line 300-302), and span attributes use a consistent `pollmevals.*` namespace throughout.
- `_make_stub_artifact_refs` and `_make_failed_result` / `_make_success_result` pattern cleanly separates the "always return a valid EvalRow" (FR-009) contract from the success path. The decomposition is readable and testable.
- Test coverage for the retry ladder is thorough: 429-then-200, exhausted 429, exponential backoff assertion, FR-009 compliance on exhaustion — all present and using `patch("asyncio.sleep")` to avoid real delays.
- `init_tracing` correctly uses env-var overrides with the 12-factor precedence order (env > explicit arg > built-in default).

## Hook bypass investigation

The coder reported that `.claude/settings.json` (or a lefthook hook) flagged `eval()` as a security concern. Investigation results:

- `lefthook.yml` does NOT exist at the project root — confirmed by `ls` check.
- `.claude/settings.json` contains only: (1) a `PreToolUse/Bash` hook that blocks `forgeplan delete/reset/destroy` without `--yes`, (2) Hindsight MCP recall/retain hooks. No pattern matching on Python `eval()` or file content.
- The reported hook rejection was a false positive from Claude Code's own `Edit`-tool safety check, not from `lefthook` or a custom hook. The `Edit` tool's heuristic appears to have flagged the filename `eval_caller.py` or the domain word "eval" in the file as potentially dynamic-code usage.
- Grep of all 5 changed source files confirms **zero instances of `eval(`, `exec(`, `compile(`** in the diff. The only `eval` tokens are domain vocabulary (filename, class names, parameter names, comments referencing `inspect_ai.eval()` in a docstring).
- **Verdict**: tooling false-positive. No security issue.
- **Action item**: if the `Edit`-tool heuristic is configurable, add an allowlist entry for `eval_caller.py` in `.claude/settings.local.json`; alternatively, document that `Write` is the safe bypass path when `Edit` incorrectly rejects a file on filename pattern alone. No hook tightening needed — the existing hooks are correctly scoped.

## Test coverage delta

- Before this commit: 333 tests passing
- After this commit: 356 passed, 1 skipped (+23 new tests)
- Branches gained: HTTP 200 happy path, 429-then-200 recovery, 429 exhaustion, exponential backoff timing, 500 SANDBOX_FAILURE, 400 SANDBOX_FAILURE, network error NETWORK, timeout (built-in TimeoutError), FR-009 on exhaustion, FakeEvalCaller determinism/failure paths, telemetry idempotency, env-var overrides, span creation smoke
- Branches still uncovered: httpx.TimeoutException classification (Finding #1 and #7), httpx.ReadTimeout specifically, partial/malformed JSON response body from LiteLLM (resp.json() throws), concurrent call behaviour under asyncio.Semaphore with real InspectEvalCaller

## ADI cycle

### Abduction — hypotheses (>=3)

- **H1**: The implementation is production-ready for Phase 2C: correct retry semantics, correct OTel instrumentation, clean types, comprehensive tests — suitable to activate PRD-001 evidence after minor doc fixes only.
- **H2**: The implementation has a latent bug in the exception handling hierarchy: httpx timeouts are misclassified, mypy errors indicate imprecise types, and OTel error recording is incomplete on journal/cost spans — CONCERNS verdict, fixes required before Phase 2D handoff.
- **H3**: The implementation has a structural design gap: using `SANDBOX_FAILURE` for all 4xx errors conflates auth failures with server crashes, and the module-level `_PROVIDER_INSTALLED` global is fragile in multi-process / test isolation scenarios — BLOCKER on architecture grounds.

### Deduction — observable predictions

- **H1 → Y1**: if H1 holds, mypy --strict produces 0 errors, all 356 tests pass, and no exception classification bug exists in the retry loop; measurable by running the tools.
- **H2 → Y2**: if H2 holds, mypy --strict produces errors on the type-ignore lines, a test using `httpx.ReadTimeout` (not built-in `TimeoutError`) would fail with the wrong error_class, and journal spans would show no `ERROR` status in Tempo on journal corruption; measurable via mypy output, test assertion, grep for record_exception.
- **H3 → Y3**: if H3 holds, the `ErrorClass` enum would lack a value for auth/client-error, the `_PROVIDER_INSTALLED` flag would cause silent endpoint mismatch in multi-instance scenarios; measurable via enum inspection and tracing the second-call code path.

### Induction — evidence per prediction

| Prediction | Evidence | Outcome | H_i status |
|---|---|---|---|
| Y1: mypy 0 errors | `uv run mypy --strict` on 5 files | 4 errors in eval_caller.py:355-356 | H1 REFUTED |
| Y1: 356 tests pass | pytest run | 356 passed, 1 skipped | H1 SUPPORTED on tests |
| Y1: no exception classification bug | `python3 -c` MRO check: `httpx.TimeoutException` is not subclass of `TimeoutError` | `except TimeoutError` misses httpx timeouts | H1 REFUTED |
| Y2: mypy errors present | confirmed above | errors at lines 355-356 with wrong `[arg-type]` vs actual `[attr-defined]` | H2 SUPPORTED |
| Y2: httpx.ReadTimeout misclassified | MRO verification | `httpx.ReadTimeout` → `httpx.HTTPError` → caught as NETWORK not TIMEOUT | H2 SUPPORTED |
| Y2: journal spans no ERROR status | grep for `record_exception` in journal.py and cost.py | zero hits in both files | H2 SUPPORTED |
| Y3: SANDBOX_FAILURE for all 4xx | grep error_class assignments | 4xx mapped to SANDBOX_FAILURE at line 267 | H3 partially SUPPORTED |
| Y3: _PROVIDER_INSTALLED multi-instance fragile | code review of telemetry.py + test helper resetting flag | flag is module-level; test workaround sidesteps real provider; for Phase 2C single-process this is acceptable | H3 INCONCLUSIVE (not a blocker for current deployment model) |

Surviving hypothesis: **H2** — CONCERNS verdict. H1 is refuted by two real bugs and mypy errors. H3 is partially supported but does not rise to BLOCKER because the `_PROVIDER_INSTALLED` fragility is acceptable for the current single-process deployment and the 4xx `error_class` issue is a design concern rather than a data-loss or security failure.

## Trust Calculus per claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| httpx.TimeoutException not subclass of built-in TimeoutError | 8 | 9 | 9 | 26 | Verified via `python3 -c` MRO inspection; httpx source code confirms |
| mypy --strict emits 4 errors on eval_caller.py:355-356 | 8 | 9 | 9 | 26 | Direct tool output captured |
| journal.py and cost.py spans lack error recording | 7 | 8 | 8 | 23 | Grep + code read; OTel spec defines this as required practice |
| 356 tests pass, 1 skipped | 9 | 9 | 9 | 27 | Direct pytest run in same environment |
| Retry logic counting is correct (4 calls, 3 sleeps, delays 1/2/4s) | 8 | 9 | 9 | 26 | Verified by simulation script matching test assertions |
| Hook bypass is a false-positive (no dynamic eval() in diff) | 8 | 9 | 8 | 25 | Grep of all 5 changed files confirms zero eval()/exec()/compile() |

Decision strength: all claims 23-27/27; weakest is OTel error-recording finding at 23 (the OTel spec reference is authoritative but not a hard correctness failure for current phase). No claim below 12 — decision is solid.

## Conclusions

- Surviving hypothesis: H2 — CONCERNS
- Decision strength: high (all claims verified by tool output or direct code inspection)
- Follow-up evidence needed: one additional EVID (post-fix) confirming `mypy --strict` clean + httpx.TimeoutException test added, before Phase 2D activation

## Next steps

- CONCERNS: dispatch coder for Findings #1, #2, #3, #7 (the two bugs + journal OTel error recording + missing test)
- Finding #6 (4xx error_class) is a design concern — create a Tactical note before Phase 2D to decide whether `ErrorClass` enum expansion is in scope
- Finding #4 and #5 are LOW priority — address in Phase 2D if time allows
- Re-review the patched diff before activating PRD-001's Phase 2C gate

## Related Artifacts

- Parent: PRD-001
- Related EVIDENCE: EVID-020 (Phase 2B bootstrap — predecessor evidence)
- Related NOTE: NOTE-003 (observability stack research — OTel design rationale)
- Commit: `0e494f6`




