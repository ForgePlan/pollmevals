# Task lifecycle policy v0.1.0

## States

| State | Meaning |
|---|---|
| draft | task is being written |
| calibration | task has known-good/medium/bad samples under test |
| active_private | used as held-out task |
| active_public | public task in regular run |
| cooldown | task is public but gold is not yet published |
| published_gold | gold solution is visible |
| retired | not used in future scoring |
| compromised | task leaked or became contaminated |

## Gates

A task may become active only after:

- gold solution passes evaluator;
- broken sample fails;
- mediocre sample scores between bad and good;
- evaluator runtime is bounded;
- license and IP status are clear;
- contamination scan is clean;
- rubric is clear enough for judge agreement.
