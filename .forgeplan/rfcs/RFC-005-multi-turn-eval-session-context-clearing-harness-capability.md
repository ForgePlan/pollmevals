---
depth: standard
id: RFC-005
kind: rfc
links:
- target: PRD-007
  relation: based_on
- target: RFC-004
  relation: based_on
- target: ADR-010
  relation: based_on
status: active
title: Multi-turn eval session + context-clearing harness capability
---

# RFC-005: Multi-turn eval session + context-clearing harness capability

> **STATUS: draft** — SPARC Architecture artifact for v0.2. Unblocks **PRD-007** (agentic-memory & context task category) by adding the harness *mechanism* PRD-007's archetypes A1–A4 require. The decision that multi-turn + per-turn context-clearing is *needed* is already forced by **EVID-040** (R-7 harness spike, verdict ABSENT — the current harness is strictly single-turn). This RFC is the engineering design for **HOW**: a multi-turn task/stack schema (v2), an `EvalSession` Protocol seam, per-turn context-clear semantics, a `SandboxSession` lifecycle, GridRunner turn dispatch, EvalRow multi-turn capture, and **backward compatibility** with single-turn `pollmevals.task.v1` packs. Authoring agent: `claude-code/opus-4-8-1m/architecture-task-rfc-005`. Leave in **draft** — activation belongs to the orchestrator after a linked EVID exists. `forgeplan_reason RFC-005` (gemini-3.1-pro-preview, **High** confidence) was run before finalising; it confirmed the 1A+2A+3A design and surfaced three hardening points now folded into Options Considered, Invariants, Risks (R-1, R-3, R-8), and Test-Strategy Hooks (see the "ADI findings folded in" callout). **Reconciled 2026-05-30** to **ADR-010** (the decision record for Seam-3A's persistence surface) per the convergent High finding of EVID-041 (security) + EVID-042 (architecture): the L4 workspace is a **size-capped session-scoped `tmpfs` at `/workspace`** — the read-only host bind mount stays `ro` (NO `ro→rw` change). Six implementation-time preconditions from those reviews are folded into §Function Signatures item 5, Invariant 6, R-3, R-8, and Test-Strategy Hooks.

## Summary

The current eval harness is strictly single-turn: `GridSpec.iter_requests` yields one `EvalRequest` per `(model, stack, task, seed)` cell; `EvalCaller.call` issues exactly one POST to `/chat/completions` with a single-element `messages` array; `SandboxRun.run` runs one fresh, **read-only**-mounted, `network=none` Docker container per eval and removes it on completion (EVID-040, verified anchors below). There is no turn loop, no session concept, no message-history accumulation, no seam to flush in-context state, and — critically — **no writable workspace for a candidate to persist L4 file memory** across anything.

This RFC introduces a **session-shaped execution path that lives *alongside* the single-turn path**, gated by an explicit `schema_version: pollmevals.task.v2` on the task and an `execution.session_mode: multi_turn` declaration on the stack. The three load-bearing seams:

1. **EvalCaller seam** — add a **new `run_session(EvalSession) -> EvalResult` method to the `EvalCaller` Protocol**, alongside the existing `call`. (Not a generalisation of `call`; not a separate orchestrator.) Existing single-turn `call` is untouched; multi-turn tasks dispatch through `run_session`.
2. **Task schema for turns** — a **v2 task variant whose `prompt_template` is replaced by a `turns[]` array** (`{prompt, context_clear_after, expects_outcome}`), selected by `schema_version: pollmevals.task.v2`. v1 (`prompt_template: string`) stays valid and unchanged; the validator branches on `schema_version`.
3. **Context-clear vs memory-persist boundary** — a **`SandboxSession` whose lifecycle is `create_once → run_turn → clear_context_buffer → run_turn → … → destroy`**, where "context buffer" = the in-memory `messages` history passed to the model, and "persisted memory" = a **writable, size-capped session-scoped `tmpfs` mount at `/workspace`** (per **ADR-010** — the host bind mount stays `ro`, NOT loosened) plus any L5 store the stack wires. Clearing flushes `messages`; the tmpfs workspace and L5 store survive. This is the construct-validity crux of PRD-007 AC-3: recall after a flush is impossible *except* from persisted L4/L5 state.

Backward compatibility is the hard constraint: the existing **single-turn test suite stays green (pytest exit 0)**, the three v1 packs (`be_01`, `fe_01`, `doc_01`) run byte-for-byte unchanged, and RFC-004's `requirements[]` / `requirement_results[]` model is preserved — a turn's output still produces `requirement_results[]` exactly as a single-turn eval does.

## Motivation

PRD-007 needs to evaluate the L4 (file) / L5 (vector) memory rungs of the scaffolding ladder — the single most harness-discriminating axis in prior art (PRD-007 §Problem). To do that without conflating the memory layer with the base model's context-window capacity, PRD-007 AC-3 requires that **short-term context is flushed between turns** so a later turn can only recall an earlier fact from *persisted* memory. EVID-040 proved the current harness cannot express any of this — multi-turn support spans contracts, orchestrator, and sandbox layers, hence verdict ABSENT, hence "its own RFC."

**Verified anchors (EVID-040, re-confirmed by direct read during this RFC):**
- `apps/eval-core-py/src/orchestrator/eval_caller.py:122-137` — `EvalCaller` Protocol exposes only `async def call(self, request: EvalRequest) -> EvalResult`.
- `eval_caller.py:185` — `InspectEvalCaller.call`; `:207-215` — single-element `messages` array; `:230` — one POST per call; `:568` — `FakeEvalCaller.call` (the deterministic test mock, used across `test_grid_runner.py` / `test_integration.py`).
- `apps/eval-core-py/src/orchestrator/grid_runner.py:80` — `GridSpec.iter_requests` (one `EvalRequest` per cell); `:228` — `_run_single`; `:286` — `result = await self._caller.call(request)`; `:447` — `run`.
- `apps/eval-core-py/src/evaluators/sandbox/runner.py:151` — `SandboxRun` ("single-shot sandbox executor"); `:182` — `run`; `:219` — `# Security policy (frozen, NEVER loosen)`; `:221` — `read_only: True`; `:222` — `"tmpfs": config.tmpfs` (a writable tmpfs is **already** part of the frozen policy, default `{"/tmp": "size=100m"}` at `:63`); `:237` — the workspace bind mount is `mode: "ro"` (read-only).
- `docs/04-runbook/09-sandbox-security.md:22` — the frozen rule is literally **"writable tmpfs only"** (a writable tmpfs is *permitted*; the *bind* mount is what is read-only).
- `apps/eval-core-py/src/contracts/eval_row.py:108` — `EvalRow` (`frozen=True`, `extra="forbid"`); `:66` — `EvalArtifactRefs` (`extra="forbid"`).
- `packages/contracts/schemas/task.schema.json:8` — `schema_version: { "const": "pollmevals.task.v1" }`; `:16` — `prompt_template: { "type": "string" }`; `:21-54` — RFC-004 `requirements[]` (optional, already landed).
- `packages/contracts/schemas/stack.schema.json:8` — `schema_version: { "const": "pollmevals.stack.v1" }`; `:14` — `execution: { "type": "object" }` (opaque).

**Bounding constraints (inherited; carried as hard design constraints):**
- **BC1 (PRD-007 / RFC-004 C2)**: the judge pipeline, `rubric.yaml`, calibration (α/MAD), the median reducer, the self-judging guard, the anonymisation pipeline, and the `weight_components` weight vectors are **untouched**. This RFC changes *how a session is executed and captured*, never how it is scored.
- **BC2 (RFC-004 compatibility)**: a turn's deterministic evaluation still yields `requirement_results[]`; `requirements[]` stays the authoring contract. The session layer wraps the existing evaluator; it does not replace it.
- **BC3 (ADR-002 immutability)**: no in-place schema edit. v1 is frozen; multi-turn is a **v2 version bump** (`pollmevals.task.v2`). Existing v1 packs and any published runs against them remain valid forever.
- **BC4 (EVID-040 scope)**: multi-turn spans contracts + orchestrator + sandbox; the design must address all three, not patch one.
- **BC5 (back-compat)**: the single-turn test suite stays green (pytest exit 0); v1 packs run unchanged; the smoke grid (45 evals, single-turn) is unaffected.

## Proposed Direction

**The chosen architecture is one coherent design: Seam-1A + Seam-2A + Seam-3A** (each weighed against ≥2 alternatives in Options Considered, with the macro choice confirmed by the `forgeplan_reason RFC-005` ADI cycle at High confidence). In one sentence: **add a parallel session-shaped execution path, gated on `schema_version: pollmevals.task.v2`, that the existing single-turn path never sees.**

- **Seam 1A — EvalCaller Protocol gains `run_session(EvalSession) -> EvalResult` alongside the untouched `call`.** Multi-turn tasks dispatch through `run_session`; single-turn tasks keep using `call`. Both return the same `EvalResult`/`EvalRow`, so `GridRunner`'s journaling/cost/span plumbing is reused below the fork. (Rejected: 1B generalise `call` — mutates the most-tested method; 1C separate `SessionRunner` — duplicates orchestrator wiring.)
- **Seam 2A — a `pollmevals.task.v2` task variant whose `turns[]` array replaces `prompt_template`.** v1 stays frozen and valid; the validator and loader branch on `schema_version` (already a `const`). RFC-004 `requirements[]` / `prompt_ref` carry over, scoped to the turn they belong to. (Rejected: 2B keep `prompt_template` + sibling `session` block — two-source-of-truth ambiguity that threatens the AC-3 guarantee.)
- **Seam 3A — a `SandboxSession` with `create_once → run_turn → clear_context_buffer → run_turn → … → destroy`,** where the in-memory `messages` buffer is flushed each turn while a **writable, size-capped session-scoped `tmpfs` mounted at `/workspace`** (plus any stack-wired L5 store) persists across turns. This makes the persist-vs-clear boundary a *mechanical* property — recall after a flush is impossible except from persisted L4/L5 state (the PRD-007 AC-3/SC-4 crux). **The read-only host bind mount stays `ro`; nothing becomes `rw`.** (Rejected: 3B host-side memory file — re-smuggles the in-context buffer and cannot represent a stack-owned L5 store; 3C keep full history — defeats construct validity, the exact anti-pattern AC-3 prevents.)

> **Decision alignment — ADR-010 is the authority for the persistence surface.** The Seam-3A *persistence mechanism* (how L4 file memory is held across turns) is decided by **ADR-010 "Writable session-scoped sandbox workspace for multi-turn evals via tmpfs (no ro→rw bind loosening)"**. ADR-010 resolves the earlier Seam-3A ambiguity ("rw named volume *or* rw-tmpfs") in favour of a **size-capped, session-scoped `tmpfs` at `/workspace`**, created at `create_once` and gone when the session container is torn down at `destroy`. The frozen runbook rule is literally **"writable tmpfs only"** (`09-sandbox-security.md:22`) and `runner.py:222` already wires a writable tmpfs — so the L4 surface fits inside the existing policy and the feared `ro→rw` bind delta is **avoided, not necessary**. Where a file fixture must be present at session start, it is **copied from the `ro` seed into the tmpfs at `create_once`** (a one-time in-container `cp`, no host write). Wherever this RFC describes the persistence surface (Proposed Direction, Module Breakdown, Component Diagram, Data Flow, §Function Signatures item 5, Invariant 6, R-3), ADR-010 governs; if any phrasing here ever conflicts with ADR-010, ADR-010 wins. RFC-005 implementation activates only after ADR-010 is `active` (gated on its own pen-test EVID, ADR-010 Confirmation step 2).

The detailed design of this direction follows: the named modules in **Module Breakdown**, the run-time topology in **Component Diagram (prose)**, the end-to-end walk-throughs in **Data Flow**, the exact contracts/signatures in **Function Signatures / Component Contracts**, the alternatives weighed in **Options Considered**, the build order in **Implementation Phases**, and the safety/back-compat guarantees in **Invariants**, **Back-compat & Migration**, **Rollback Plan**, **Risks & Mitigations**, and **Test Strategy Hooks**.

## Module Breakdown

Named modules, one responsibility each. (Topology described in prose under "Component Diagram".)

- **contracts-task-schema-v2** — `packages/contracts/schemas/task.schema.json`: adds a `pollmevals.task.v2` variant. In v2, `turns[]` replaces the required `prompt_template`; `requirements[]` (RFC-004) and `weight_components` are unchanged. Single source of structural truth for a multi-turn task's turn sequence.
- **contracts-stack-schema-v2** — `packages/contracts/schemas/stack.schema.json`: adds `execution.session_mode: single | multi_turn` and `execution.context_clear_between_turns: bool`. A stack declaring L4/L5 declares what persists vs. clears. (The `execution` object is already opaque, so this is additive within a `stack.v2` const bump for honesty.)
- **contracts-session-models** — `apps/eval-core-py/src/contracts/`: new frozen Pydantic models `EvalSession`, `TurnSpec`, `TurnResult`; additive optional fields on `EvalRow` (`turn_count`, `turn_results[]`) and on `EvalArtifactRefs` (`turn_transcripts: ArtifactRef | None`). TS mirror in `packages/contracts/src/types.ts` moves in lock-step (SPEC-001 reconciliation rule).
- **eval-caller-session** — `eval_caller.py`: the `EvalCaller` Protocol gains `run_session`; `InspectEvalCaller.run_session` (real turn loop over the LiteLLM proxy, flushing `messages` between turns); `FakeEvalCaller.run_session` (deterministic multi-turn mock for tests).
- **grid-runner-turn-dispatch** — `grid_runner.py`: `_run_single` branches on the task's `schema_version` — v1 → `caller.call` (unchanged), v2 → `caller.run_session`. `GridSpec` is unchanged (the cell granularity stays `(model, stack, task, seed)`; turns live *inside* a cell).
- **sandbox-session** — `apps/eval-core-py/src/evaluators/sandbox/`: new `SandboxSession` wrapping the existing `SandboxRun`, with a `create_once → run_turn → clear_context_buffer → run_turn → … → destroy` lifecycle and a **size-capped, session-scoped `tmpfs` workspace at `/workspace`** (the L4 persistence surface, per ADR-010 — the host bind mount stays `ro`). The frozen-policy kwargs (`network_mode`/`read_only`/`cap_drop`/`security_opt`/`pids`/`mem`/`ulimits`) are reused **via a shared helper** so they stay verbatim across `SandboxRun` and `SandboxSession` (EVID-042 #2). `SandboxRun` (single-shot) is unchanged and keeps serving single-turn evals.
- **session-evaluator-adapter** — the per-pack evaluator chain: runs the v2 task's per-turn / end-of-session checks and emits `requirement_results[]` exactly as RFC-004 specifies — no change to the requirement model, only a per-turn invocation point.
- **task-spec-validator-v2** — `infra/scripts/validate-task-specs.py`: branches on `schema_version`; v2 packs validate `turns[]` (non-empty, each `prompt` non-empty, `context_clear_after` boolean, `prompt_ref` resolves into the turn it belongs to); v1 packs validate exactly as today.

**Explicitly NOT touched** (BC1/BC2): `judge_panel.py`, `rubric.yaml`, the median reducer, the calibration suite, the self-judging guard, the anonymisation pipeline, the `weight_components` vectors, the RFC-004 `requirements[]` item shape, `docs/04-runbook/08-scoring-contract.md`. Single-turn `EvalCaller.call`, `SandboxRun`, and the v1 task path are unchanged.

## Component Diagram (prose)

**Authoring time.** A task author writes one of two task shapes. A v1 pack (`schema_version: pollmevals.task.v1`) carries a single `prompt_template: string` — unchanged. A v2 pack (`schema_version: pollmevals.task.v2`) carries a `turns[]` array instead; each turn has a `prompt`, a `context_clear_after` flag, an optional `expects_outcome` (the outcome-taxonomy value PRD-007 FR-006 encodes as `requirements[]`), and its `requirements[]` items reference turns. `task-spec-validator-v2` reads `schema_version` and applies the matching rule set.

**Run time — direction summary.** `GridSpec.iter_requests` yields one cell per `(model, stack, task, seed)` (unchanged). `grid-runner-turn-dispatch._run_single` loads the task, reads `schema_version`, and forks: v1 → `caller.call(request)` (the existing single POST, unchanged); v2 → `caller.run_session(session)`. For v2, the caller asks `sandbox-session` to `create_once` (a size-capped tmpfs `/workspace` + the candidate's L4/L5 surface; the `ro` seed fixture is copied into the tmpfs here), then for each turn: builds the `messages` array for *this turn only* (system + this turn's user prompt — **no prior-turn history when `context_clear_between_turns` is set**), POSTs once to the proxy, hands the turn output to `session-evaluator-adapter` which runs that turn's checks and emits per-turn `requirement_results[]`, then calls `clear_context_buffer` (deep-reset the in-memory `messages`; the tmpfs workspace and L5 store are left intact). After the last turn, `destroy` tears down the container (and with it the tmpfs). The caller assembles one `EvalResult` carrying one `EvalRow` whose `turn_results[]` and aggregated `requirement_results[]` feed the **unchanged** RFC-004 pass-rate → deterministic component → `08-scoring-contract.md` weighted-sum path. Judged criteria (BC1) arrive from the untouched `judge_panel.py` path exactly as for single-turn.

**The persist-vs-clear boundary (the crux).** Two stores with opposite lifetimes inside one session: the **in-context `messages` buffer** (lifetime = one turn; flushed by `clear_context_buffer`) and the **tmpfs `/workspace` + L5 store** (lifetime = the whole session; survives every flush; destroyed only at `destroy`). A candidate that did not write to persisted memory has *nothing* to recall after a flush — which is exactly the construct-validity property PRD-007 AC-3 / SC-4 require, and the L0-stack failure edge PRD-007 FR-001 registers.

## Data Flow

**Happy path (a v2 capture+lookup task — PRD-007 A1→A2 shape).**
1. `_run_single` loads `mem_02_temporal_lookup` v2, sees `schema_version: pollmevals.task.v2`, builds an `EvalSession` from the `EvalRequest` + the task's `turns[]`, calls `caller.run_session(session)`.
2. `run_session` asks `SandboxSession.create_once` → a size-capped tmpfs `/workspace` into which the own-authored `knowledge_repo` fixture is copied from its `ro` seed (in-container `cp`, no host write), container created, kept alive.
3. **Turn 1 (capture, `context_clear_after: true`)**: `messages = [system, {user: turn1.prompt}]`; one POST; candidate writes a capture file into the tmpfs `/workspace`; `session-evaluator-adapter` checks the mutation, emits `requirement_results` for turn 1; `clear_context_buffer` deep-resets `messages` (the file in the tmpfs stays).
4. **Turn 2 (temporal lookup)**: `messages = [system, {user: turn2.prompt}]` — **no turn-1 history**; one POST; the only way the candidate can answer "which item did I capture earlier" is to read the tmpfs `/workspace` (its L4 memory); `session-evaluator-adapter` runs the deterministic normalised grounding check (RFC-004 `auto` requirement, `maps_to: correctness`), emits `requirement_results` for turn 2.
5. `destroy` tears down the container (the tmpfs vanishes with it); `run_session` returns one `EvalResult` with an `EvalRow` carrying `turn_count=2`, `turn_results[]`, and the union of per-turn `requirement_results[]`. Scoring proceeds via the unchanged RFC-004 → weighted-sum path. The turn transcripts are written as one content-addressed `turn_transcripts` artifact (immutability-friendly, ADR-002) — this is the durable record, not the ephemeral tmpfs.

**Construct-validity edge (L0 stack — PRD-007 FR-001 edge case).** Same task, `raw-llm` (L0) stack with no writable-memory wiring. Turn 1 produces output but persists nothing recoverable. After the flush, Turn 2's grounding requirement **fails** (no memory to read) — the task registers "memory absent" as a distinct, scored outcome. This is the signal PRD-007 SC-4 measures via the paired L0-vs-L4/L5 run.

**Failure path (a turn POST times out).** The per-turn POST honours the existing per-eval `timeout_s`; a turn timeout produces a `TurnResult(status=FAILED, error_class=TIMEOUT)` and the session **short-circuits** (no further turns), returning an `EvalRow(status=FAILED, error_class=TIMEOUT)` — preserved in the manifest denominator (FR-009 invariant, mirrored from single-turn). `SandboxSession.destroy` always runs in a `try/finally` (best-effort cleanup, mirroring `SandboxRun`'s existing finally-cleanup).

**Failure path (sandbox cannot create a writable session).** If `create_once` fails (daemon error, tmpfs error), the session returns `EvalRow(status=FAILED, error_class=SANDBOX_FAILURE)` — same graceful-degradation contract as single-turn today.

**v1 path (unchanged).** `be_01`/`fe_01`/`doc_01` load as `schema_version: pollmevals.task.v1`; `_run_single` forks to `caller.call`; one POST; `SandboxRun` single-shot; identical `EvalRow` shape (the new fields default to `None`/empty). The single-turn suite asserts this path; it stays green.

## Function Signatures / Component Contracts

### 1. Session contracts (Pydantic v2, `apps/eval-core-py/src/contracts/`)

```python
@dataclass(frozen=True)
class TurnSpec:
    index: int                     # 1-based turn order
    prompt: str                    # the user prompt for this turn
    context_clear_after: bool      # flush the in-context messages buffer after this turn
    expects_outcome: str | None    # outcome-taxonomy value (PRD-007 FR-006), e.g. "NONE_CLARIFICATION"

@dataclass(frozen=True)
class EvalSession:
    """All inputs to run one multi-turn (model, stack, task, seed) session.

    Mirrors EvalRequest for the single-turn path; the cell granularity is
    identical — turns live INSIDE one cell, so eval_id material is unchanged
    (back-compat: deterministic eval_id, ADR-002 run_hash unaffected).
    """
    eval_id: str
    model_id: str
    stack_id: str
    task_id: str
    seed: int
    turns: list[TurnSpec]
    context_clear_between_turns: bool   # from stack.execution; the master switch
    timeout_s: int = 300                # per-TURN wall-clock (reuses NFR-002 budget)
    max_retries: int = 2

class TurnResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    index: int
    raw_output_ref: ArtifactRef
    requirement_results: list[RequirementResult]   # RFC-004 shape, per-turn
    status: EvalStatus
    error_class: ErrorClass | None = None
    stats: EvalStats                                # per-turn cost lives here (EVID-042 #4)
```

### 2. EvalRow / EvalArtifactRefs — additive optional fields (back-compat)

`EvalRow` is `frozen=True, extra="forbid"`. New fields are **optional with defaults**, so every existing single-turn construction and the single-turn suite stay valid:

```python
# additive to EvalRow (apps/eval-core-py/src/contracts/eval_row.py)
turn_count: int | None = None              # None for single-turn evals
turn_results: list[TurnResult] | None = None

# additive to EvalArtifactRefs
turn_transcripts: ArtifactRef | None = None  # one content-addressed file with all turns (ADR-002)
```

`eval_id` material is unchanged (`run_hash:model:stack:task:seed`) — turns do not enter the hash, so a v2 task's `eval_id` is computed exactly as a v1 task's. Run immutability (ADR-002) holds: a published multi-turn `EvalRow` is frozen; corrections create a new run + `supersedes`.

**Downstream-consumer note (ADI H1 deduction).** Because `turn_count`/`turn_results`/`turn_transcripts` are *optional* (default `None`), every existing consumer (`apps/api`, `apps/site`, the manifest writer, the aggregator) keeps reading single-turn rows unchanged. A consumer that wants per-turn data MUST treat these as nullable (`turn_results is None` ⇒ single-turn). This is an explicit contract: new fields are nullable forever; no consumer may assume `turn_results` is present.

### 3. EvalCaller Protocol seam (the chosen seam — Option 1A)

```python
@runtime_checkable
class EvalCaller(Protocol):
    async def call(self, request: EvalRequest) -> EvalResult: ...        # UNCHANGED (single-turn)
    async def run_session(self, session: EvalSession) -> EvalResult: ... # NEW (multi-turn)
```

- `InspectEvalCaller.run_session`: the turn loop. Per turn, builds `messages` = `[system?] + [{role:"user", content: turn.prompt}]` when `context_clear_between_turns` is true (no prior history); POSTs once; collects the turn output; deep-resets the in-memory `messages` for the next turn. Reuses the existing 429-retry + graceful-failure helpers verbatim.
- `FakeEvalCaller.run_session`: deterministic multi-turn mock keyed on `(stack_id, task_id, seed)`, returning a fixed `TurnResult[]` so `test_grid_runner.py` can exercise the turn dispatch without network.
- **Both `call` and `run_session` return the same `EvalResult` type** carrying one `EvalRow`, so `_run_single`'s journaling / cost-attribution / span code is reused unchanged after the fork.
- **Back-compat precondition (EVID-042 #3)**: before adding `run_session` to the `@runtime_checkable` Protocol, confirm **no `isinstance(x, EvalCaller)` runtime structural check exists** in scope — adding a second method makes such a check require both methods, which an old `FakeEvalCaller` lacking `run_session` would fail. None found today; verify at implementation and add a contract test that an old structural impl still satisfies the single-turn path.

### 4. GridRunner turn dispatch

```python
async def _run_single(self, request_or_session) -> EvalResult | None:
    task_schema = load_task_schema_version(request.task_id)   # reads schema_version
    if task_schema == "pollmevals.task.v2":
        session = build_session(request, task)                # EvalRequest + turns[] -> EvalSession
        result = await self._caller.run_session(session)
    else:
        result = await self._caller.call(request)             # UNCHANGED single-turn path
    # journaling, cost attribution, OTEL span — UNCHANGED below the fork
```

`GridSpec.iter_requests` is unchanged (still one cell per `(model, task, stack, seed)`). The fork is the **only** behavioural change in `grid_runner.py`; everything below `result = ...` (budget gate, semaphore, journal, cost, judge-panel hook) is shared. A mid-session budget abort (after turn k) yields `EvalRow(status=FAILED, error_class=BUDGET)` with the partial `turn_results[]` preserved in the denominator (EVID-042 #4; extends Invariant 7 to the multi-turn case; final partial-state semantics fixed in the Phase-6 SPEC-001 amendment).

### 5. SandboxSession lifecycle (the persist-vs-clear boundary — governed by ADR-010)

```python
class SandboxSession:
    """Multi-turn sandbox: create once, run N turns, clear in-context buffer
    between turns, persist the writable tmpfs /workspace across turns, destroy
    at end. Reuses the existing single-shot SandboxRun frozen policy verbatim
    (network=none, read_only root, cap_drop=ALL, no-new-privileges,
    pids/mem/ulimits) via a shared frozen-policy-kwargs helper (EVID-042 #2);
    only the container lifetime + an added size-capped /workspace tmpfs change.
    The host bind mount stays mode:"ro" — NO ro->rw loosening (ADR-010)."""

    async def create_once(self, config: SandboxSessionConfig) -> None: ...
    async def run_turn(self, turn: TurnSpec, candidate_output: str) -> SandboxResult: ...
    def clear_context_buffer(self) -> None: ...   # deep-reset in-memory messages ONLY (no disk/tmpfs touch)
    async def destroy(self) -> None: ...          # try/finally container teardown (tmpfs vanishes with it)
```

Per **ADR-010**, `SandboxSessionConfig` reuses the frozen `SandboxConfig` security policy verbatim and adds **a writable, size-capped, session-scoped `tmpfs` mount at `/workspace`** (RAM-backed; in addition to the existing `/tmp` tmpfs) — because a candidate must be *able* to write L4 file memory. **The `/workspace` host *bind* mount stays `mode: "ro"`; nothing is changed from `ro` to `rw`.** `network_mode: none`, `read_only: true` root, `cap_drop: ALL`, `no-new-privileges`, `pids_limit`, `mem_limit`, `ulimits`, and the hard per-turn timeout are unchanged. The implementation MUST honour these ADR-010-derived preconditions:

- **Memory-budget invariant (EVID-041 F-2)**: `size(/tmp) + size(/workspace) + min_process_headroom ≤ mem_limit`. The tmpfs is RAM-backed and counts against `mem_limit` (default `512m`; `/tmp` defaults to `size=100m`), so a writable-surface DoS is bounded by the `size=` cap, not the host. A write past the cap surfaces as a clean `No space left on device` to the candidate, never a host OOM. The concrete cap is **TBD** — set from the first integration run's RAM profile; do not invent a number.
- **Fixture seeding (ADR-010)**: where a file fixture must exist at session start, it is **copied from the `ro` seed into the tmpfs during `create_once`** (one-time in-container `cp`). The copy MUST use `--no-dereference` (do not follow symlinks; reject symlinked seed entries), pin the seed to a fixed, non-templated, in-image read-only path that takes **no** task/stack-controlled path component, strip setuid/setgid bits, and run as the unprivileged sandbox user (EVID-041 F-5; CWE-59 link-following, CWE-22 path-traversal).
- **Teardown (EVID-041 F-3)**: `destroy` runs in a `try/finally` so it always fires on every turn-loop exit (success, timeout, exception, short-circuit). Because the chosen tmpfs design has **no named volume**, the leaked artifact on a hard crash is a **dangling RAM-backed container** (still holding its tmpfs RAM until reaped), not an orphan volume. A run-level reaper keyed on a `run_hash`/session tag removes any dangling **container** at run start/end.
- **Image provenance (EVID-041 F-4)**: the session container image is pinned by `sha256` digest at `create_once` (a session-lived container widens the time window of a tampered base image; `cap_drop:ALL` on a malicious image is still malicious). `trivy image <digest>` runs as part of the ADR-010 Confirmation pen-test EVID.

`clear_context_buffer` touches **only** the in-memory `messages` history (a deep reset, no retained references) — never the tmpfs, any disk path, or the L5 store; that asymmetry is the whole mechanism.

### 6. Validator (`validate-task-specs.py`) — schema-version branch

```python
if task["schema_version"] == "pollmevals.task.v2":
    # MUST: turns[] non-empty; each turn.prompt non-empty; context_clear_after is bool.
    # MUST: requirements[].prompt_ref resolves within the turn it belongs to.
    # MUST: no prompt_template key present (mutually exclusive with turns[]).
    # SHOULD: at least one turn has context_clear_after=true (else "multi-turn" is cosmetic).
else:  # pollmevals.task.v1 — UNCHANGED rule set (incl. RFC-004 requirements[] rules)
    ...
```

## Options Considered

Three load-bearing seams; each weighs ≥2 genuinely-considered alternatives. The chosen design is **one coherent whole** (1A + 2A + 3A) — no cocktail.

### Seam 1 — EvalCaller Protocol extension

**Option 1A — New `run_session(EvalSession) -> EvalResult` method alongside `call` (CHOSEN).**
- **Pros**: zero blast radius on the single-turn path — `call` is byte-for-byte unchanged, so the single-turn suite and the 3 v1 packs are untouched (BC5). `FakeEvalCaller` gains a *new* method; its existing `call` mock is unchanged, so `test_grid_runner.py`/`test_integration.py` single-turn assertions stay green. Two methods, two clearly-named contracts — a reader sees "single vs session" at the Protocol. `EvalResult`/`EvalRow` are shared, so `_run_single`'s journaling/cost/span code is reused below the fork.
- **Cons**: the Protocol now has two methods; `InspectEvalCaller` and `FakeEvalCaller` must both implement `run_session` (additive, but two impls to keep coherent). A `run_turn`-vs-`call` code-duplication risk in the retry/graceful-failure helpers — mitigated by extracting the shared POST+retry helper both call. A `@runtime_checkable` `isinstance` check would now require both methods — verified absent, gated by a precondition (EVID-042 #3).

**Option 1B — Generalise `call` to accept an optional `turns[]` (single-turn = a 1-element list).**
- **Pros**: one method, one entry point; conceptually "single-turn is just a session of length 1."
- **Cons**: changes the signature/semantics of the *existing* `call`, which the entire single-turn suite and `FakeEvalCaller` exercise — the highest-blast-radius option, directly against BC5. `EvalRequest` would have to grow a `turns` field (it is `frozen`; every caller would change), and the single-turn `messages` construction (`eval_caller.py:207`) would have to special-case "1 turn, no clear" forever. Conflates two genuinely different lifetimes (one POST vs a managed session with a sandbox) behind one name — worse clarity, more conditionals on the hot single-turn path.

**Option 1C — A separate `SessionRunner` orchestrator outside `EvalCaller`.**
- **Pros**: keeps `EvalCaller` a pure single-POST abstraction; the session machinery lives in its own class.
- **Cons**: now `grid_runner._run_single` must know about *two* unrelated executor abstractions and decide which to construct/inject, duplicating the budget/semaphore/journal/cost wiring that today lives once around `caller.call`. Two parallel injection seams in `GridRunner` is more surface than one Protocol with two methods. The `FakeEvalCaller` testability seam (EVID-007 finding #4) would have to be cloned for `SessionRunner`.

**Chosen: 1A.** It minimises blast radius on the proven single-turn path (the dominant BC5 constraint and the ADI synthesis's "isolate change, lowest blast radius" line — ADI H1, High confidence), keeps the testability seam single, and reuses `EvalResult`/`_run_single` plumbing. 1B's "elegance" buys a one-method API at the cost of mutating the most-tested method in the codebase — a net loss. 1C duplicates the orchestrator wiring for no compatibility gain.

### Seam 2 — Task schema for turns

**Option 2A — `turns[]` array replaces `prompt_template` in a `pollmevals.task.v2` variant (CHOSEN).**
- **Pros**: clean mutual exclusivity — a v2 task has `turns[]` and *no* `prompt_template`; a v1 task has `prompt_template` and *no* `turns[]`. The validator and loader branch on `schema_version` (already a `const` in the schema), so v1 packs are provably unaffected (BC3/BC5). `requirements[].prompt_ref` (RFC-004) generalises naturally to "the numbered item within the turn it belongs to." Matches ADR-002: v2 is a version bump, v1 is frozen.
- **Cons**: two schema branches to maintain (`anyOf` on `schema_version` + matching required-keys). A v1→v2 conceptual migration for an author who wants to make an existing task multi-turn (acceptable — it is a new task version anyway under ADR-002).

**Option 2B — Keep `prompt_template: string` and add a sibling `session: {...}` block.**
- **Pros**: `prompt_template` stays present, so loaders that read it never break; the session block is purely additive.
- **Cons**: ambiguous source of truth — when both `prompt_template` and `session.turns[]` exist, which drives the run? Every consumer must encode a precedence rule. It invites a "v1 task with a session block" half-state that is neither cleanly single- nor multi-turn, weakening the construct-validity guarantee (a turn's prompt could leak from `prompt_template`). RFC-004's `prompt_ref` would have two possible targets (the template vs a turn). More validator complexity, not less.

**Chosen: 2A.** Mutual exclusivity keyed on `schema_version` is the honest, ADR-002-aligned shape: v1 frozen, v2 distinct, no half-states, one unambiguous prompt source per turn. 2B's "always keep `prompt_template`" looks safer but creates a two-source-of-truth ambiguity that directly threatens the AC-3 context-clearing guarantee.

### Seam 3 — Context-clear vs memory-persist boundary

> The persistence-surface decision below is **owned by ADR-010** (see the Decision-alignment note in Proposed Direction). ADR-010 weighed four options (session-lived container + size-capped tmpfs `/workspace` [chosen]; per-turn fresh container + named volume; `rw` host bind; defer to v0.3 gVisor/Kata) plus a rejected OverlayFS variant, and chose the size-capped tmpfs because it satisfies PRD-007 AC-3 **with no `ro→rw` bind loosening**. The summary below is reconciled to that decision; ADR-010 is authoritative if any phrasing diverges.

**Option 3A — `SandboxSession` with `create_once → run_turn → clear_context_buffer → run_turn → destroy`; in-memory `messages` cleared per turn, writable size-capped tmpfs `/workspace` + L5 store persisted; host bind mount stays `ro` (CHOSEN, per ADR-010).**
- **Pros**: the two stores have explicitly opposite lifetimes, enforced in code: `clear_context_buffer` provably touches only the in-memory `messages` (never disk/tmpfs), and the tmpfs `/workspace` provably survives every flush until `destroy`. This is the *mechanical* guarantee PRD-007 AC-3 / SC-4 need — recall after a flush is impossible except from persisted L4/L5. The frozen runbook rule is literally "writable tmpfs only" and `runner.py:222` already wires a writable tmpfs, so **the feared `ro→rw` bind delta is avoided entirely** and every frozen flag is preserved verbatim (network=none, read_only root, cap_drop=ALL, no-new-privileges). tmpfs auto-clears on unmount → no dangling-volume GC burden, no host-disk leak. Survives the v0.3 gVisor/Kata → Firecracker runtime swap unchanged. An L0 stack with no persistence naturally fails the post-flush recall turn (PRD-007 FR-001 edge), so the failure mode is structural, not bolted-on. (ADI H3 + ADR-010 H1, High confidence.)
- **Cons**: the tmpfs is **RAM-backed**, so its `size=` counts against `mem_limit` — a `size=` cap is **mandatory** (the memory-budget invariant in §5; DoS mitigation) and bounds the L4 capacity a task can exercise. A session-lived container has a **longer attack-surface time window** than the single-shot model (mitigated: all hardening flags retained, per-turn root FS still `read_only`; pen-test must use a multi-turn payload — R-3). No file-level post-mortem after a crash (tmpfs vanishes; the durable record is `turn_transcripts`). New lifecycle code wrapping `SandboxRun`.

**Option 3B — No sandbox session; clear context by issuing a fresh `messages` array each turn, and rely on a *host-side* external memory file the orchestrator passes back in.**
- **Pros**: no new sandbox surface; reuses `SandboxRun` single-shot per turn.
- **Cons**: the candidate never *owns* a persistent workspace — the orchestrator would have to simulate L4 memory by threading a file in and out, which (a) is exactly the in-context buffer the design is trying to flush, dressed up as a file, and (b) cannot represent an L5 vector store the stack wires itself. It conflates "what the harness remembers" with "what the candidate persisted," destroying the attribution PRD-007 SC-6 requires. Re-creating a fresh container per turn also loses any in-sandbox process/L5 state legitimately.

**Option 3C — One long-lived container, do NOT clear `messages` (pass full history each turn); rely only on prompt instructions to "use your memory."**
- **Pros**: simplest; no flush logic.
- **Cons**: **fails the core PRD-007 construct-validity requirement** — with full history in context, a long-context base model recalls earlier facts from the in-context buffer, not from persisted memory, so the score conflates memory-layer with context-window capacity (PRD-007 R-1). This is the exact anti-pattern AC-3 exists to prevent. Rejected on correctness grounds.

**Chosen: 3A (size-capped tmpfs, no `ro→rw` bind, per ADR-010).** It is the only option that makes the persist-vs-clear boundary a *mechanical* property of the harness rather than a hope about model behaviour, which is precisely what PRD-007 AC-3/SC-4/SC-6 demand — **and** it fits inside the frozen "writable tmpfs only" policy without loosening any flag (ADR-010). 3B cannot represent a stack-owned L5 store and re-smuggles the in-context buffer as a file; 3C defeats the construct-validity purpose outright. (ADR-010 additionally rejected a `rw` named volume / `rw` host bind because each requires a mandatory runbook + MethodologyVersion amendment to permit a writable bind, which the tmpfs path avoids.)

> **ADI findings folded in (`forgeplan_reason RFC-005`, gemini-3.1-pro-preview, High confidence).** The reasoning cycle independently confirmed the 1A+2A+3A design (H1/H3 High, H2 Medium) and surfaced three hardening points reflected in this RFC: (i) the **writable-surface security delta** is a first-class risk — *and* `destroy` must run in `try/finally` with a dangling-**container** reaper (the tmpfs design has no volume to orphan) to avoid host-RAM exhaustion on a hard crash (folded into R-3 + the `SandboxSession.destroy` contract); (ii) **per-turn cost can grow unbounded** if context is *not* cleared, so context-clearing is also a cost-bounding mechanism (folded into R-5 + the Data Flow note, mirroring PRD-007 NFR-009); (iii) **context-clear must be a deep reset** of the `messages` history (not a shallow reassignment that could retain references), proven by a property test, with the `FakeEvalCaller.run_session` mock + turn-dispatch test as the load-bearing back-compat proof that the single-turn suite stays green (folded into R-1, R-8, and Test-Strategy Hooks). The ADI's recommendation: proceed with Phases 1–6, prioritising the L0-stack post-flush test. The macro 1A/1B/1C choice was made via this ADI cycle, not taste. The persistence-surface specifics were subsequently decided by **ADR-010** and re-confirmed by EVID-041 (security, CONCERNS — no blocker) + EVID-042 (architecture, fit).

## Implementation Phases

Phased so contracts land first and each phase is independently validatable; the single-turn path stays green throughout.

**Phase 1 — Contracts (additive, lock-step).** Land the `pollmevals.task.v2` variant in `task.schema.json`, `execution.session_mode`/`context_clear_between_turns` in `stack.schema.json` (with `stack.v2` const), the `EvalSession`/`TurnSpec`/`TurnResult` Pydantic models, the additive optional `EvalRow`/`EvalArtifactRefs` fields, and the TS mirror. Gate: contract round-trip tests pass; **every v1 pack still validates**; the single-turn suite is untouched (no behavioural code yet).

**Phase 2 — Validator branch.** Extend `validate-task-specs.py` to branch on `schema_version`; add the v2 `turns[]` MUST rules; v1 rule set unchanged. Gate: validator unit tests — a v2 pack with empty `turns[]` rejected; a v2 pack carrying `prompt_template` rejected; a v1 pack validates exactly as before.

**Phase 3 — EvalCaller `run_session` + FakeEvalCaller mock.** Add `run_session` to the Protocol (after verifying no `@runtime_checkable isinstance(EvalCaller)` check exists — EVID-042 #3); implement `FakeEvalCaller.run_session` (deterministic) first, then `InspectEvalCaller.run_session` (real turn loop, reusing the shared POST+retry helper). Gate: `FakeEvalCaller.call` mock unchanged → single-turn suite green; new `run_session` unit tests pass.

**Phase 4 — GridRunner turn dispatch.** Add the `schema_version` fork in `_run_single`; everything below the fork (budget/semaphore/journal/cost/judge-hook) reused. Gate: a v1 grid run is byte-identical (smoke 45-eval grid unaffected); a v2 grid run dispatches through `run_session` (driven by `FakeEvalCaller`).

**Phase 5 — SandboxSession (per ADR-010).** Extract the frozen-policy kwargs into a shared helper consumed by both `SandboxRun` and `SandboxSession` (EVID-042 #2). Implement `create_once → run_turn → clear_context_buffer → destroy` with the size-capped tmpfs `/workspace` (memory-budget invariant), the hardened in-container fixture copy from the `ro` seed, `try/finally` destroy + dangling-container reaper, and a digest-pinned image. Gate: a property test proves `clear_context_buffer` deep-resets the in-memory buffer while leaving the tmpfs file intact; the frozen security flags are asserted unchanged (network=none, read_only root, cap_drop=ALL, no-new-privileges) and the host bind mount is still `ro`; the size-cap OOM/`ENOSPC` test passes; `destroy` always runs with no residual container.

**Phase 6 — SPEC-001 amendment + first integration EVID.** Amend SPEC-001 to describe `turn_results[]`/`turn_transcripts` and the partial-state contract on a mid-session budget abort (per-turn cost in `TurnResult.stats`; abort → `EvalRow(status=FAILED, error_class=BUDGET)` with partial `turn_results[]` preserved). The orchestrator runs a mock multi-turn task end-to-end and records an EVID (the construct-validity paired-run is PRD-007's, fed by this harness). This RFC `informs` SPEC-001.

## Invariants

What MUST NEVER be violated by this RFC's implementation:

1. **Single-turn path is byte-for-byte unchanged.** `EvalCaller.call`, `SandboxRun`, `GridSpec.iter_requests`, and the v1 task/stack schema behave identically; the single-turn suite stays green (BC5).
2. **Judge pipeline untouched.** No change to `judge_panel.py`, `rubric.yaml`, the median reducer, α/MAD calibration, the self-judging guard, the anonymisation pipeline, or the `weight_components` vectors (BC1). A turn is scored through the *existing* RFC-004 → weighted-sum path.
3. **RFC-004 model preserved.** A turn's deterministic evaluation emits `requirement_results[]` of the unchanged RFC-004 shape; `requirements[]` stays the authoring contract; `prompt_ref` resolves within its turn (BC2).
4. **No in-place schema edit.** v1 (`pollmevals.task.v1`) is frozen; multi-turn is a `pollmevals.task.v2` version bump; published v1 runs remain valid forever (BC3, ADR-002).
5. **The persist-vs-clear asymmetry is mechanical.** `clear_context_buffer` deep-resets only the in-memory `messages`; it MUST NOT touch the tmpfs `/workspace`, any disk path, or the L5 store. The tmpfs workspace survives every flush until `destroy`. (This is the AC-3 guarantee.)
6. **Frozen sandbox security policy retained; NO `ro→rw` bind loosening (ADR-010).** `network_mode: none`, `read_only: true` root, `cap_drop: ALL`, `no-new-privileges`, `pids_limit`, `mem_limit`, `ulimits`, and a hard per-turn timeout are unchanged. The `/workspace` host **bind** mount stays `mode: "ro"`. The *only* additions are (a) the container lifetime (single-shot → session-scoped) and (b) a writable, size-capped, session-scoped **tmpfs** at `/workspace` whose `size=` obeys `size(/tmp)+size(/workspace)+process-headroom ≤ mem_limit`. The tmpfs is gone when the session container is destroyed; no named volume exists. Frozen-policy kwargs are reused via a shared helper so they stay verbatim (EVID-042 #2).
7. **Failures are preserved (FR-009).** A failed turn (or a mid-session budget abort) produces an `EvalRow(status=FAILED, error_class=...)` that stays in the manifest denominator with its partial `turn_results[]`; the session short-circuits but never silently drops. `destroy` runs in `try/finally`.
8. **`eval_id` material unchanged.** Turns do not enter the `eval_id` hash; a v2 task's `eval_id` is computed exactly as v1's, so the run_hash and resume invariants hold.

## Back-compat & Migration

- **v1 packs (`be_01`, `fe_01`, `doc_01`)**: zero change. They carry `schema_version: pollmevals.task.v1`, so the validator and `_run_single` route them to the unchanged path.
- **New fields are optional with defaults** (`turn_count=None`, `turn_results=None`, `turn_transcripts=None`), so every existing `EvalRow`/`EvalArtifactRefs` construction (and the single-turn suite) remains valid under `extra="forbid"`. Downstream consumers MUST treat them as nullable (see the Downstream-consumer note).
- **Authoring a multi-turn task** = a *new* v2 pack (ADR-002 version bump), never an in-place edit of a v1 pack.
- **TS / Pydantic / JSON-Schema** move in one change (SPEC-001 reconciliation rule); old `evaluator_json` / `task.yaml` / `stack.yaml` validate without the new keys.
- **Stacks**: existing v1 stacks default to `session_mode: single`; only a stack opting into multi-turn declares `session_mode: multi_turn` + `context_clear_between_turns: true`.

## Rollback Plan

| Failure mode | Rollback action |
|---|---|
| `run_session` / turn dispatch destabilises the single-turn path | The fork in `_run_single` is a single `if schema_version == v2` branch; revert the branch → all traffic flows through unchanged `call`. v2 contracts stay landed but dormant (additive/optional), so no contract rollback needed. |
| Writable session tmpfs proves a security regression (ADR-010 Confirmation pen-test) | Refuse the session tmpfs; multi-turn tasks fall back to FAILED(SANDBOX_FAILURE); the decision escalates to ADR-010 Option 4 (defer to v0.3 gVisor/Kata), **never** to a looser mount. Single-turn read-only path is untouched. |
| Dangling session containers accumulate (destroy failed on a crash) | `destroy` runs in `try/finally`; a run-level reaper removes orphaned `pollmevals-session-*` **containers** (the tmpfs design has no volume to orphan; the leaked artifact is a RAM-backed container) at run start/end, keyed on the run_hash/session tag. |
| tmpfs `size=` cap causes spurious OOM / too-small workspace | Re-tune `size=` against the first integration run's RAM profile within `mem_limit` headroom (a parameter change, not a posture change). If RAM genuinely cannot hold a task's L4 footprint, that task is the trigger to reconsider ADR-010 Option 2 (disk-backed), which then requires the mandatory runbook + MethodologyVersion amendment. |
| v2 schema branch breaks v1 validation | v2 is selected only when `schema_version == pollmevals.task.v2`; if the branch misfires, gate on the const and ship v1-only until fixed. Contracts are additive, so the package rolls back to the additive-only delta. |
| Per-turn cost blows the budget envelope | Context-clearing already bounds per-turn tokens (no growing history); additionally cap `len(turns)` via a `task.yaml` limit and reuse the existing `BudgetGate` per-turn (mid-session abort preserves partial `turn_results[]`). If still over, hold v2 packs in draft (PRD-007 owns the task-side budget gate). |
| Turn-transcript capture bloats artifact storage | `turn_transcripts` is one content-addressed file per eval (not one per turn); if still heavy, store only on failure + a sampled fraction on success. |

## Risks & Mitigations

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-1 | **Context-clear leaks** — an implementation bug leaves prior-turn history in `messages`, so recall succeeds from context, not persisted memory, silently breaking PRD-007 AC-3 construct validity. | Med | High | Invariant 5 enforced by a property test (Phase 5): after `clear_context_buffer`, the next turn's `messages` contains no prior-turn content; an L0-stack integration test must FAIL the post-flush recall turn (PRD-007 FR-001 edge) — if it passes, the clear leaked. The clear MUST be a deep reset, not a shallow reassignment that retains references (ADI H3 / EVID-041 F-6). |
| R-2 | **Back-compat regression** — a change to shared `_run_single`/`EvalResult` plumbing breaks the single-turn suite. | Med | High | Seam 1A keeps `call` untouched; the fork is the only `grid_runner` change; CI runs the full single-turn suite (pytest exit 0) as a Phase-1..6 gate. `FakeEvalCaller.call` mock is not modified; verify no `@runtime_checkable isinstance` check before adding `run_session` (EVID-042 #3). |
| R-3 | **Writable-workspace security delta + container lifecycle (ADR-010)** — adding a writable tmpfs + a session-lived container widens the attack-surface time window (ADI H2); a failed `destroy` leaves a dangling RAM-backed **container** / exhausts host RAM (EVID-041 F-3). | Med | Med | Per ADR-010: it is a **size-capped tmpfs, not a `rw` bind** — every frozen flag is retained verbatim (network=none, read_only root, cap_drop=ALL, no-new-privileges, pids/mem/ulimits, hard timeout) and the host bind mount stays `ro`, so no `ro→rw` delta exists. The memory-budget invariant `size(/tmp)+size(/workspace)+headroom ≤ mem_limit` bounds the DoS; `destroy` in `try/finally` + a dangling-**container** reaper (the tmpfs leaves no volume to orphan) prevents host-RAM leak; the image is digest-pinned (EVID-041 F-4). A **multi-turn** penetration test (stage payload turn 1 → execute/egress/host-write/tmpfs-overflow turn 2) is the High-effort evidence ADR-010 Confirmation step 2 mandates — record in a follow-up EVID; RFC-005 implementation activates only after ADR-010 is `active`. |
| R-4 | **Schema-branch drift** — v1 and v2 validation/loader branches diverge, letting a malformed v2 pack through or breaking a v1 pack. | Low | Med | One `schema_version` switch in both validator and loader; validator unit tests cover both branches incl. the "v2 must not carry `prompt_template`" mutual-exclusion rule; v1 regression test in CI. |
| R-5 | **Per-turn cost blow-up** (ADI hardening point ii) — multi-turn sessions cost more than single-turn. | Med | Med | Context-clearing bounds per-turn tokens (no growing history); per-turn reuse of the existing `BudgetGate` (mid-session abort preserves partial `turn_results[]`, EVID-042 #4); `len(turns)` cap in `task.yaml`; first-run cost is **TBD — record in a linked EVID** (mirrors PRD-007 NFR-009; no invented numbers). |
| R-6 | **Scope creep into PRD-002/judge pipeline** — adding per-turn judging tempts touching `judge_panel.py`. | Low | High | Hard Invariant 2 / BC1; turns are scored only through the existing RFC-004 → weighted-sum path; any judge-pipeline change is a separate PRD-002 artifact. |
| R-7 | **L5 store lifetime mismatch** — a stack's L5 vector store lives in a process the session does not own, so it is destroyed/reset unexpectedly between turns. | Med | Med | This RFC *enables* L4+L5 by guaranteeing the tmpfs workspace persists; it does **not** pick or build an L5 backend (out of scope). L5-backend lifetime is a stack-adapter concern; flagged for the stack-spec follow-up PRD-007 references; first L5 task gated on that. The ADI flagged that the L5 store must bind to the persisted workspace or externalise state safely (H3 assumption). |
| R-8 | **Downstream consumers assume `turn_results` exists** — a reporting/aggregation consumer crashes on the new optional fields (ADI H1 / EVID-042 #3). | Low | Med | The new EvalRow fields are nullable forever (default `None`); the Downstream-consumer note makes "treat as nullable" an explicit contract; a contract test asserts an old single-turn `EvalRow` (no turn fields) round-trips through every consumer; confirm no `isinstance(_, EvalCaller)` runtime check breaks before adding `run_session`. |
| R-9 | **Fixture-copy symlink / path-traversal (EVID-041 F-5)** — the `ro`-seed → tmpfs `cp` follows a symlink or a task-controlled seed path, materialising out-of-seed content into the writable tmpfs. | Low | Med | Copy with `--no-dereference` (reject symlinked seed entries); pin the seed to a fixed, non-templated in-image read-only path with no task/stack-controlled component; strip setuid/setgid; run as the unprivileged sandbox user; add a fixture-copy unit test (symlinked entry not dereferenced; seed path cannot escape its root). CWE-59 / CWE-22. |

## Test Strategy Hooks

What the downstream `tester` agent should target (hooks, not cases). The first is the load-bearing back-compat proof (ADI hardening point iii):

- **Single-turn back-compat gate (primary)**: the full existing single-turn suite (`test_eval_caller.py`, `test_grid_runner.py`, `test_integration.py`, `test_smoke_runner.py`) **stays green (pytest exit 0)** at every phase. (Treat the gate as "suite green", not a literal pass-count; reconcile the headline figure against an actual `pytest --collect-only -q` count when wiring — EVID-042 #5.) `FakeEvalCaller.call` and `mock_post.assert_called_once()` (single-turn) must be unaffected by adding `run_session`.
- **Context-clear deep-reset property test** (the AC-3 mechanical guarantee, ADI H3 / EVID-041 F-6): after `clear_context_buffer`, the next turn's constructed `messages` contains no prior-turn content (deep reset, no retained references); and the file written to the tmpfs `/workspace` in an earlier turn is still readable in a later turn.
- **L0-stack post-flush failure test** (ADI-prioritised): a memory-less stack FAILS the post-flush recall requirement (PRD-007 FR-001 edge) — if it passes, the context-clear leaked (couples to R-1).
- **Turn-dispatch fork test**: a v2 task dispatches through `caller.run_session`; a v1 task dispatches through `caller.call`; driven by `FakeEvalCaller` (no network).
- **`@runtime_checkable` back-compat test** (EVID-042 #3): an old structural `EvalCaller` impl lacking `run_session` still satisfies the single-turn path; confirm no `isinstance(_, EvalCaller)` check is broken by the second method.
- **Schema-branch validator tests**: v2 empty `turns[]` rejected; v2 carrying `prompt_template` rejected; v1 pack validates unchanged; `requirements[].prompt_ref` resolution within a turn.
- **RFC-004 preservation test**: a turn emits `requirement_results[]` of the unchanged shape; the pass-rate → deterministic component math is identical to single-turn.
- **Downstream-nullability contract test** (ADI H1): an old single-turn `EvalRow` (no `turn_*` fields) round-trips through the manifest writer, aggregator, `apps/api`, and `apps/site` consumers.
- **Sandbox security-flag assertion + container teardown** (ADR-010 Confirmation step 1; EVID-041 F-3): `SandboxSession.create_once` kwargs carry `network_mode=none`, `read_only=True` root, `cap_drop=[ALL]`, `no-new-privileges`, frozen pids/mem/ulimits; the host **bind** mount is still `mode:"ro"`; the only additions are the session lifetime + a size-capped `/workspace` tmpfs; `destroy` always runs (try/finally) with **no residual container**.
- **OOM / size-cap behaviour test** (ADR-010 Confirmation step 3; EVID-041 F-2): writing past the tmpfs `size=` returns a clean `No space left on device` to the candidate without killing the host; RAM stays bounded by `mem_limit`; the `size(/tmp)+size(/workspace)+headroom ≤ mem_limit` arithmetic holds.
- **Fixture-copy hardening test** (EVID-041 F-5): a symlinked seed entry is not dereferenced into the tmpfs; the seed path cannot escape its root; setuid/setgid stripped.
- **Failure/immutability hooks**: a turn timeout (or mid-session budget abort) short-circuits to `EvalRow(status=FAILED, error_class=...)` preserved in the denominator with partial `turn_results[]`; `destroy` always runs; `eval_id` for a v2 task equals the v1-shaped hash.
- **Cost hook**: per-turn cost is measured and recorded in `TurnResult.stats` (TBD magnitudes — first-run EVID), not assumed.
- **Sandbox penetration test** (High-effort, ADR-010 Confirmation step 2 / EVID-041 F-7): a malicious candidate output writes an executable payload to the tmpfs and attempts (a) execution, (b) network egress, (c) host-FS write, (d) tmpfs-overflow DoS — **using a multi-turn payload** (stage turn 1 → exploit turn 2) to prove the lifetime delta adds no escape path; all must be contained by the frozen flags / `size=` cap; record in the follow-up EVID that gates activation.

## Out of Scope

State explicitly (per the brief's scope boundary):

- **Authoring the actual memory tasks** — the four archetypes A1–A4, their `knowledge_repo` fixtures, prompts, gold, requirements, and calibration sets. That is **PRD-007**. This RFC builds only the *mechanism*.
- **Any change to the judge pipeline / `rubric.yaml` / calibration / `weight_components`** — PRD-002 turf (BC1, mirrors RFC-004 C2). This RFC reuses that infrastructure unchanged.
- **L5 vector-memory *backends*** — this RFC *enables* L4+L5 by providing the multi-turn + persist-vs-clear mechanism (a persistent tmpfs workspace + a flushable context buffer), but does **not** pick, build, or wire a specific vector store (mem0 / Hindsight / Letta / Zep). L5-backend lifetime/adapters are a stack-spec follow-up (R-7).
- **In-place schema edits** — v1 is frozen; multi-turn is a v2 bump (BC3, ADR-002). Never mutate v1.
- **The frozen sandbox runbook edit** — ADR-010 fits inside the existing "writable tmpfs only" rule and needs **no mandatory** `09-sandbox-security.md` amendment; a clarifying note (session-lived container permitted; tmpfs `size=` cap) is a deferred MethodologyVersion task, not part of this RFC.
- **Cross-session / process-restart durability** — this RFC's session is one logical run; PRD-007 Q1 resolves persistence as cross-session-via-simulated-boundary at the *task* level, which this mechanism supports (a fresh session = a flushed context), but multi-process restart durability is not built here.
- **The telemetry / trace pipeline** (EPIC-002 I3) — `turn_transcripts` capture is for the immutable record + audit, not the telemetry initiative.

## Related Artifacts

| Artifact | Relation | Note |
|----------|----------|------|
| PRD-007 | **based_on** (this agent links) | the consumer; RFC-005 inherits its problem statement and unblocks its A1–A4 archetypes. |
| ADR-010 | **based_on** (this agent links) | the decision record for Seam-3A's persistence surface — size-capped session-scoped tmpfs, no `ro→rw` bind loosening. Authoritative for the persistence mechanism; RFC-005 implementation activates only after ADR-010 is `active`. |
| EVID-040 | informs (orchestrator links) | the R-7 spike (verdict ABSENT); its "What's missing" 6-item list is this RFC's module map. Orchestrator owns this edge. |
| EVID-041 | informs (orchestrator links) | security review of ADR-010 (CONCERNS, no blocker); its F-2..F-5 preconditions are folded into §5 / R-3 / R-9 / Test Hooks. Orchestrator owns this edge. |
| EVID-042 | informs (orchestrator links) | architecture-fitness review of RFC-005 (fit; the Seam-3A drift this reconciliation fixes); its #2/#3/#4/#5 items are folded in. Orchestrator owns this edge. |
| RFC-004 | refines / compatible-with (orchestrator links) | the atomic-binary `requirements[]` contract; RFC-005 preserves it — a turn emits `requirement_results[]` unchanged. Orchestrator owns this edge. |
| PRD-002 | shares-infra (reuses, does not modify) | judge panel / calibration / `weight_components` — explicitly off-limits (BC1). |
| ADR-002 / `docs/adr/0002-run-immutability.md` | invariant | v1 frozen; multi-turn = v2 bump; published runs immutable; the durable record is `turn_transcripts`, not the ephemeral tmpfs. |
| SPEC-001 | informs (future) | `turn_results[]` / `turn_transcripts` + partial-state-on-abort amendment to the EvalRow / evaluator-json surface. |
| EVID-<id> | informs (future, to be created) | first integration run (mock multi-turn end-to-end) + per-turn cost measurement + the ADR-010 sandbox pen-test (TBD — not invented here). |

## References

- `apps/eval-core-py/src/orchestrator/eval_caller.py` — `EvalCaller` Protocol (`:122-137`), `InspectEvalCaller.call` (`:185`), single `messages` (`:207-215`), POST (`:230`), `FakeEvalCaller` (`:543/:568`).
- `apps/eval-core-py/src/orchestrator/grid_runner.py` — `GridSpec` (`:59`), `iter_requests` (`:80`), `_run_single` (`:228`), dispatch (`:286`), `run` (`:447`).
- `apps/eval-core-py/src/evaluators/sandbox/runner.py` — `SandboxRun` (`:151`), `run` (`:182`), frozen-policy comment (`:219`), `read_only:True` (`:221`), `"tmpfs": config.tmpfs` (`:222`), `_DEFAULT_TMPFS` (`:63`), `ro` bind mount (`:237`), cleanup (`:268-291`).
- `docs/04-runbook/09-sandbox-security.md` — frozen sandbox policy ("writable tmpfs only", `:22`); ADR-010 fits inside it (no mandatory amendment).
- `apps/eval-core-py/src/contracts/eval_row.py` — `EvalRow` (`:108`, frozen/extra-forbid), `EvalArtifactRefs` (`:66`), `EvalStats` (`:84`), `ErrorClass` (`:38`).
- `packages/contracts/schemas/task.schema.json` — `schema_version` const (`:8`), `prompt_template: string` (`:16`), RFC-004 `requirements[]` (`:21-54`).
- `packages/contracts/schemas/stack.schema.json` — `schema_version` const (`:8`), opaque `execution` (`:14`).
- `stacks/{raw-llm,claude-code-basic,forgeplan-framework}/stack.yaml` — single-shot `execution` contracts (no `turns`/`session` keys today).
- `apps/eval-core-py/tests/{test_eval_caller,test_grid_runner,test_integration,test_smoke_runner}.py` — the single-turn suite that stays green (pytest exit 0).
- ADR-010 — the authoritative decision for the persistence surface (size-capped tmpfs, no `ro→rw` bind); EVID-041 (security) + EVID-042 (architecture) reviews.
- Per-turn cost / latency figures and the tmpfs capacity cap are **TBD** — they belong in an EVID from the first integration run, not invented here.

