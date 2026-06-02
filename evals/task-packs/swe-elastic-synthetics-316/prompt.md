# Bug fix: elastic/synthetics

You are fixing a real bug in the open-source repository `elastic/synthetics` at commit `f52f0bf3d18ca418d1eec4afd1370751fdd914ce`.

## Issue

propagate errors from `beforeAll` and `afterAll` hooks
+ Now error in the `beforeAll` and `afterAll` hooks would be captured and reported as error, but they will not be associated with the reporters in the correct way. 
+ Without associating these errors, the Uptime UI will have no information about what happened during the context of a single execution. 

We have to figure out a way to solve this problem.

## Task

Modify the typescript source so the reported problem is resolved. Produce a patch against the repository at the given base commit that makes the failing tests pass without breaking the existing passing tests.

Constraints:
  - Change only what the fix requires; keep the diff minimal and focused.
  - Do not edit the test files — they are the hidden acceptance criteria.
  - Preserve the existing public API unless the issue explicitly requires a change.

Output a unified diff (git patch) of your source changes.
