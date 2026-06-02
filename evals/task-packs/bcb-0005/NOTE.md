<!-- source: BigCodeBench task #BigCodeBench/5 (license: Apache-2.0, retrieved 2026-06-03, url: https://huggingface.co/datasets/bigcode/bigcodebench) -->
# Execution shape — bcb_0005

**Source**: BigCodeBench `BigCodeBench/5` (bigcode/bigcodebench), entry point `task_func`.

## What this pack is

A self-contained Python function task. Unlike `be_01_jwt_auth` (TypeScript +
vitest + a full `node_modules`/Docker toolchain), this is a single pure-Python
module scored by a `unittest.TestCase` suite. It is **close to runnable** — no
build step, no package install beyond the task's own libraries.

## Files

- `gold/solution.py` — a **runnable** reference module. Assembled verbatim from
  the dataset's `complete_prompt` (imports + `def task_func(...)` signature +
  docstring) followed by `canonical_solution` (the function body). The body
  alone is NOT a complete function — this is the key schema gotcha.
- `gold/test.py` — the verbatim BigCodeBench `unittest` suite.
- `gold/meta.json` — `entry_point` + provenance.

## Can our executor run this today?

**Not with the current single-file TypeScript/vitest executor** (that path is
hard-wired to `npx vitest` inside the `eval-ts` image). These packs need a
**Python test-runner** instead. The gap is small and mechanical:

1. Write the candidate's answer to `solution.py`.
2. Make the entry-point visible to the test module. `gold/test.py` calls
   `task_func(...)` as a **bare free name** — there is no `import` line and
   no `if __name__ == "__main__"` block. The runner must either:
   - prepend `solution.py` into the test module's namespace, or
   - inject `from solution import task_func` at the top of the test, or
   - run via `python -m unittest` with both files in one namespace.
3. Execute `python -m unittest` (or `pytest`) in the task's venv and parse the
   pass/fail/error counts into the `correctness` component.

Some suites use `unittest.mock.patch` and seeded `random`/`subprocess`; they run
in-process and need the task's third-party libs installed (see `source.libs` in
`task.yaml`). Sandbox parity with the frozen policy
(`docs/04-runbook/09-sandbox-security.md`) is a follow-up: BigCodeBench tasks
that touch the network or filesystem must run network-off with a tmpfs CWD.

**Verdict**: runnable-now for a human (`python -m unittest`); needs a small
Python test-runner adapter to wire into the POLLMEVALS evaluator chain.

## ADR-007 sourcing status

`sourcing: hybrid` (Tier-2). BigCodeBench **is** on the ADR-007 allowlist (Apache-2.0)
and this pack carries a `LICENSE.md` attribution table. Remaining gate: the **G4
contamination check** has not yet been run — catalogue-only until G4 passes for these
specific samples.
