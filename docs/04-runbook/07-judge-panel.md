# 11 — Judge Panel Design

## Why judge panel exists

Automatic metrics work well for executable code tasks. They do not fully evaluate documentation, architecture, code review quality, design reasoning or pattern compliance.

POLLMEVALS therefore uses a panel of LLM judges only where automatic metrics are insufficient.

## Core rules

1. A model never judges itself.
2. Use at least 3 judges for each judged output.
3. Prefer judges from different model families.
4. Use blind labels and normalized submissions.
5. Use median score, not mean, for robustness.
6. Run calibration before production judging.
7. Publish inter-judge agreement.
8. Store judge version and rubric version.

## Judge workflow

```text
raw_output
  → normalization
  → anonymized submission
  → judge calls with randomized order
  → rubric JSON per judge
  → median per criterion
  → agreement calculation
  → final judged component
```

## Normalization requirements

Remove or normalize:

- greetings;
- “here is the solution” framing;
- model signatures;
- markdown noise;
- code fences when task expects code only;
- formatting differences that do not matter;
- explanatory prose when task expects implementation.

## Calibration

Each judge must score known samples:

- perfect;
- good;
- mediocre;
- poor;
- broken;
- equivalent paraphrases.

Calibration metrics:

- mean absolute deviation from expected;
- rank correlation with expected order;
- tendency to over-score;
- tendency to prefer verbosity;
- agreement with other judges.

## Publication threshold

If judge agreement is too low, publish the run as experimental or exclude judge-scored components from final leaderboard until rubric is fixed.
